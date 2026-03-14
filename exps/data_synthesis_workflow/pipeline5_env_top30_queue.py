#!/usr/bin/env python3
"""
Queue-driven synthesis pipeline for executable env backends.

Default target:
- skills: artifacts/env_top30_skills
- planner: v2
- eval: v2
- accepted high-quality samples: 1500

Smoke-test example:
    uv run exps/data_synthesis_workflow/pipeline5_env_top30_queue.py \
        --skills-root artifacts/env_top30_skills \
        --persona-path persona/persona_5K.jsonl \
        --output-root artifacts/pipeline5_env_top30_queue_run_1500 \
        --target-accepted 1500 \
        --max-total-submissions 3000 \
        --max-inflight-samples 48 \
        --simulation-workers 6 \
        --simulation-max-turns 12 \
        --base-port 19100 \
        --status-interval-sec 10 \
        --min-eval-score 4.2 \
        --allowed-hallucination-risks none,low
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from pathlib import Path
from typing import Any

from astra.synthesis_queue import (
    OpenCodeDispatcher,
    OpencodeDispatcherConfig,
    QueueStageConfig,
    SQLiteQueueStore,
    SimulationWorker,
    SimulationWorkerConfig,
    SynthesisQueueCoordinator,
)


def load_selected_skills(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"selected_skills.jsonl not found: {path}")

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"selected_skills.jsonl line {line_no} is invalid JSON: {exc}"
                ) from exc
            if not isinstance(obj, dict):
                raise ValueError(f"selected_skills.jsonl line {line_no} is not a JSON object")
            if "dir_name" not in obj and "skill_dir" not in obj:
                raise ValueError(
                    f"selected_skills.jsonl line {line_no} is missing dir_name or skill_dir"
                )
            records.append(obj)
    return records


def discover_program_skills(skills_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        if not (skill_dir / "tools.jsonl").exists():
            continue
        if not (skill_dir / "environment_profile.json").exists():
            continue
        if not (skill_dir / "backend.py").exists():
            continue
        records.append({"dir_name": skill_dir.name})
    return records


def load_persona_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"persona file not found: {path}")

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError(f"persona file is empty: {path}")
    return lines


def resolve_skill_dir(record: dict[str, Any], skills_root: Path) -> Path:
    skill_dir = record.get("skill_dir")
    if isinstance(skill_dir, str) and skill_dir.strip():
        path = Path(skill_dir.strip())
        return path.resolve() if path.is_absolute() else (skills_root / path).resolve()

    dir_name = str(record.get("dir_name", "")).strip()
    if not dir_name:
        raise ValueError(f"record is missing a valid dir_name: {record}")
    return (skills_root / dir_name).resolve()


def validate_program_skill_dir(skill_dir: Path) -> None:
    missing: list[str] = []
    for required_name in ("SKILL.md", "tools.jsonl", "environment_profile.json", "backend.py"):
        if not (skill_dir / required_name).exists():
            missing.append(required_name)
    if missing:
        raise FileNotFoundError(
            f"skill {skill_dir.name} is not a migrated executable env: missing {', '.join(missing)}"
        )


def parse_allowed_hallucination_risks(raw: str) -> tuple[str, ...] | None:
    cleaned = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(cleaned) if cleaned else None


def build_stage_config(args: argparse.Namespace) -> QueueStageConfig:
    return QueueStageConfig(
        planner_prompt_path=args.planner_prompt_path.resolve(),
        user_prompt_path=args.user_prompt_path.resolve(),
        tool_prompt_path=args.tool_prompt_path.resolve(),
        eval_prompt_path=args.eval_prompt_path.resolve(),
        planner_verbose=args.verbose_opencode,
        eval_verbose=args.verbose_opencode,
        planner_repair_attempts=args.planner_repair_attempts,
        eval_repair_attempts=args.eval_repair_attempts,
        eval_max_message_chars=args.eval_max_message_chars,
        min_eval_score=args.min_eval_score,
        allowed_hallucination_risks=parse_allowed_hallucination_risks(
            args.allowed_hallucination_risks
        ),
        simulation_max_turns=args.simulation_max_turns,
    )


def run_dispatcher_loop(dispatcher: OpenCodeDispatcher, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        handled = dispatcher.run_once()
        if not handled:
            stop_event.wait(dispatcher.config.poll_interval_sec)


def run_simulation_worker_loop(
    worker: SimulationWorker,
    *,
    stop_event: threading.Event,
) -> None:
    try:
        while not stop_event.is_set():
            handled = worker.run_once()
            if not handled:
                stop_event.wait(worker.config.poll_interval_sec)
    finally:
        worker.close()


def print_status(
    *,
    store: SQLiteQueueStore,
    target_accepted: int,
    max_total_submissions: int,
) -> None:
    summary = store.summarize_samples()
    open_jobs = store.count_open_jobs()
    planner_backlog = store.count_available_jobs(stage="planner")
    simulation_backlog = store.count_available_jobs(stage="simulation")
    eval_backlog = store.count_available_jobs(stage="eval")
    print(
        "[STATUS] submitted={submitted}/{budget} | accepted={accepted}/{target} | "
        "completed={completed} | failed={failed} | rejected={rejected} | "
        "outstanding={outstanding} | open_jobs={open_jobs} | "
        "planner_q={planner_q} | sim_q={sim_q} | eval_q={eval_q}".format(
            submitted=summary["total"],
            budget=max_total_submissions,
            accepted=summary["accepted"],
            target=target_accepted,
            completed=summary["completed"],
            failed=summary["failed"],
            rejected=summary["rejected"],
            outstanding=summary["outstanding"],
            open_jobs=open_jobs,
            planner_q=planner_backlog,
            sim_q=simulation_backlog,
            eval_q=eval_backlog,
        )
    )


def submit_until_capacity(
    *,
    coordinator: SynthesisQueueCoordinator,
    store: SQLiteQueueStore,
    skill_dirs: list[Path],
    persona_lines: list[str],
    next_submission_index: int,
    target_accepted: int,
    max_total_submissions: int,
    max_inflight_samples: int,
) -> int:
    summary = store.summarize_samples()
    outstanding = summary["outstanding"]
    accepted = summary["accepted"]

    needed = max(target_accepted - accepted, 0)
    if needed <= 0:
        return next_submission_index

    desired_outstanding = min(max_inflight_samples, needed)

    while (
        outstanding < desired_outstanding
        and next_submission_index < max_total_submissions
    ):
        skill_dir = skill_dirs[next_submission_index % len(skill_dirs)]
        persona_text = persona_lines[next_submission_index % len(persona_lines)]
        sample_id = f"queue_{next_submission_index:06d}"
        coordinator.submit_sample(
            sample_id=sample_id,
            skill_dir=skill_dir,
            persona_text=persona_text,
        )
        next_submission_index += 1
        outstanding += 1

    return next_submission_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue-driven synthesis for env_top30 executable skills"
    )
    parser.add_argument(
        "--selected-skills",
        type=Path,
        help="optional selected_skills.jsonl; defaults to discovering all migrated env skills",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=Path("artifacts/env_top30_skills"),
    )
    parser.add_argument(
        "--persona-path",
        type=Path,
        default=Path("persona/persona_5K.jsonl"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/pipeline5_env_top30_queue_results"),
    )
    parser.add_argument(
        "--queue-db",
        type=Path,
        default=None,
        help="SQLite queue database path; defaults to <output-root>/queue.sqlite3",
    )
    parser.add_argument(
        "--planner-prompt-path",
        type=Path,
        default=Path("src/astra/prompts/planner_agent_v2.md"),
    )
    parser.add_argument(
        "--user-prompt-path",
        type=Path,
        default=Path("src/astra/prompts/user_agent.md"),
    )
    parser.add_argument(
        "--tool-prompt-path",
        type=Path,
        default=Path("src/astra/prompts/tool_agent.md"),
    )
    parser.add_argument(
        "--eval-prompt-path",
        type=Path,
        default=Path("src/astra/prompts/eval_agent_v2.md"),
    )
    parser.add_argument("--target-accepted", type=int, default=1500)
    parser.add_argument(
        "--max-total-submissions",
        type=int,
        default=0,
        help="submission budget; defaults to max(target*2, target+max_inflight)",
    )
    parser.add_argument("--max-inflight-samples", type=int, default=48)
    parser.add_argument("--simulation-workers", type=int, default=6)
    parser.add_argument("--simulation-max-turns", type=int, default=12)
    parser.add_argument("--base-port", type=int, default=19000)
    parser.add_argument("--limit-skills", type=int, default=0)
    parser.add_argument("--shuffle-skills", action="store_true")
    parser.add_argument("--shuffle-personas", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--status-interval-sec", type=float, default=5.0)
    parser.add_argument("--planner-repair-attempts", type=int, default=1)
    parser.add_argument("--eval-repair-attempts", type=int, default=1)
    parser.add_argument("--eval-max-message-chars", type=int, default=4000)
    parser.add_argument("--min-eval-score", type=float, default=4.2)
    parser.add_argument(
        "--allowed-hallucination-risks",
        type=str,
        default="none,low",
        help="comma-separated values, e.g. none,low",
    )
    parser.add_argument(
        "--verbose-opencode",
        action="store_true",
        help="pass verbose=True to planner/eval OpenCode agents",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the first few planned submissions without starting workers",
    )
    args = parser.parse_args()

    if args.target_accepted <= 0:
        raise ValueError("--target-accepted must be positive")
    if args.max_inflight_samples <= 0:
        raise ValueError("--max-inflight-samples must be positive")
    if args.simulation_workers <= 0:
        raise ValueError("--simulation-workers must be positive")
    if args.simulation_max_turns <= 0:
        raise ValueError("--simulation-max-turns must be positive")

    random.seed(args.seed)

    skills_root = args.skills_root.resolve()
    persona_path = args.persona_path.resolve()
    output_root = args.output_root.resolve()
    queue_db = (
        args.queue_db.resolve()
        if args.queue_db is not None
        else (output_root / "queue.sqlite3").resolve()
    )

    if args.selected_skills is not None:
        records = load_selected_skills(args.selected_skills.resolve())
    else:
        records = discover_program_skills(skills_root)

    if args.limit_skills > 0:
        records = records[: args.limit_skills]

    skill_dirs = [resolve_skill_dir(record, skills_root) for record in records]
    for skill_dir in skill_dirs:
        validate_program_skill_dir(skill_dir)

    if args.shuffle_skills:
        random.shuffle(skill_dirs)

    if not skill_dirs:
        raise ValueError("no valid executable env skills found")

    persona_lines = load_persona_lines(persona_path)
    if args.shuffle_personas:
        random.shuffle(persona_lines)

    max_total_submissions = args.max_total_submissions
    if max_total_submissions <= 0:
        max_total_submissions = max(
            args.target_accepted * 2,
            args.target_accepted + args.max_inflight_samples,
        )

    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("Pipeline5 (queue-driven env_top30 synthesis)")
    print("=" * 72)
    print(f"Skills root:             {skills_root}")
    print(f"Persona path:            {persona_path}")
    print(f"Output root:             {output_root}")
    print(f"Queue DB:                {queue_db}")
    print(f"Target accepted:         {args.target_accepted}")
    print(f"Max total submissions:   {max_total_submissions}")
    print(f"Max inflight samples:    {args.max_inflight_samples}")
    print(f"Simulation workers:      {args.simulation_workers}")
    print(f"Simulation max turns:    {args.simulation_max_turns}")
    print(f"Base port:               {args.base_port}")
    print(f"Planner prompt:          {args.planner_prompt_path.resolve()}")
    print(f"User prompt:             {args.user_prompt_path.resolve()}")
    print(f"Tool prompt:             {args.tool_prompt_path.resolve()}")
    print(f"Eval prompt:             {args.eval_prompt_path.resolve()}")
    print(f"Min eval score:          {args.min_eval_score}")
    print(f"Allowed hallucination:   {args.allowed_hallucination_risks}")
    print(f"Selected skill count:    {len(skill_dirs)}")
    print("=" * 72)

    if args.dry_run:
        for sample_index in range(min(10, max_total_submissions)):
            skill_dir = skill_dirs[sample_index % len(skill_dirs)]
            persona_text = persona_lines[sample_index % len(persona_lines)]
            print(
                f"[DRY-RUN] sample_id=queue_{sample_index:06d} | "
                f"skill={skill_dir.name} | persona={persona_text[:90]}"
            )
        return 0

    store = SQLiteQueueStore(queue_db)
    store.initialize()
    store.recover_active_leases()
    coordinator = SynthesisQueueCoordinator(store=store, output_root=output_root)
    stage_config = build_stage_config(args)

    dispatcher = OpenCodeDispatcher(
        store=store,
        stage_config=stage_config,
        dispatcher_config=OpencodeDispatcherConfig(
            simulation_backlog_low=max(2, args.simulation_workers * 2),
            simulation_backlog_high=max(4, args.simulation_workers * 4),
            eval_backlog_high=max(4, args.simulation_workers * 4),
        ),
    )

    stop_event = threading.Event()
    threads: list[threading.Thread] = []
    workers: list[SimulationWorker] = []

    dispatcher_thread = threading.Thread(
        target=run_dispatcher_loop,
        kwargs={"dispatcher": dispatcher, "stop_event": stop_event},
        name="opencode-dispatcher",
        daemon=True,
    )
    dispatcher_thread.start()
    threads.append(dispatcher_thread)

    for worker_index in range(args.simulation_workers):
        worker = SimulationWorker(
            store=store,
            stage_config=stage_config,
            worker_config=SimulationWorkerConfig(
                worker_id=f"sim-worker-{worker_index}",
                port=args.base_port + (worker_index * 100),
            ),
        )
        workers.append(worker)
        thread = threading.Thread(
            target=run_simulation_worker_loop,
            kwargs={"worker": worker, "stop_event": stop_event},
            name=f"sim-worker-{worker_index}",
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    next_submission_index = store.summarize_samples()["total"]
    last_status_time = 0.0
    exit_code = 0
    reason = ""

    try:
        while True:
            next_submission_index = submit_until_capacity(
                coordinator=coordinator,
                store=store,
                skill_dirs=skill_dirs,
                persona_lines=persona_lines,
                next_submission_index=next_submission_index,
                target_accepted=args.target_accepted,
                max_total_submissions=max_total_submissions,
                max_inflight_samples=args.max_inflight_samples,
            )

            summary = store.summarize_samples()
            open_jobs = store.count_open_jobs()
            now = time.time()
            if now - last_status_time >= args.status_interval_sec:
                print_status(
                    store=store,
                    target_accepted=args.target_accepted,
                    max_total_submissions=max_total_submissions,
                )
                last_status_time = now

            if summary["accepted"] >= args.target_accepted:
                reason = "target accepted count reached"
                break

            if (
                next_submission_index >= max_total_submissions
                and summary["outstanding"] == 0
                and open_jobs == 0
            ):
                reason = "submission budget exhausted"
                exit_code = 1 if summary["accepted"] < args.target_accepted else 0
                break

            time.sleep(1.0)

    except KeyboardInterrupt:
        reason = "interrupted by user"
        exit_code = 130
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=5.0)
        for worker in workers:
            worker.close()
        print_status(
            store=store,
            target_accepted=args.target_accepted,
            max_total_submissions=max_total_submissions,
        )
        print(f"Exit reason: {reason or 'finished'}")
        store.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
