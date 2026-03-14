#!/usr/bin/env python3
"""
Agent-driven batch synthesis pipeline for executable env backends.

This keeps the original planner -> simulation -> eval flow, but targets
migrated skills that expose executable backends under `environment_profile.json`
and `backend.py`.

Example:
    uv run exps/data_synthesis_workflow/pipeline4_selected_skills_agentic.py \
        --selected-skills artifacts/skill_manifest_top3.jsonl \
        --skills-root artifacts/env_top30_skills \
        --persona-path persona/persona_5K.jsonl \
        --count-per-skill 50 \
        --output-root artifacts/pipeline4_results \
        --planner-prompt-path src/astra/prompts/planner_agent.md \
        --user-prompt-path src/astra/prompts/user_agent.md \
        --tool-prompt-path src/astra/prompts/tool_agent.md \
        --eval-prompt-path src/astra/prompts/eval_agent.md \
        --max-workers 4 \
        --base-port 18000 \
        --shuffle-personas \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from astra.agent import EvalAgent, EvalAgentConfig
from astra.agent import PlannerAgent, PlannerAgentConfig
from astra.agent import ToolAgentConfig
from astra.agent import UserAgentConfig
from astra.simulation import (
    MCPRuntimeConfig,
    SimulationRunner,
    SimulationRunnerConfig,
    SynthesisPipeline,
    SynthesisPipelineConfig,
)


def load_selected_skills(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"selected_skills.jsonl not found: {path}")

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
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


def build_agents_and_pipeline(
    *,
    output_root: Path,
    planner_prompt_path: Path,
    user_prompt_path: Path,
    tool_prompt_path: Path,
    eval_prompt_path: Path,
    port: int,
) -> SynthesisPipeline:
    planner_agent = PlannerAgent(
        PlannerAgentConfig(
            prompt_path=planner_prompt_path,
        )
    )

    simulation_runner = SimulationRunner(
        config=SimulationRunnerConfig(
            max_turns=12,
            early_task_end_policy="fallback",
            validate_tool_calls=True,
            assistant_state_key="simulation",
            assistant_verbose=False,
            assistant_enable_mcp_patch=True,
            assistant_enable_json_patch=True,
            runtime=MCPRuntimeConfig(
                host="127.0.0.1",
                port=port,
                transport="sse",
                server_name="skill-tools",
                start_timeout_sec=30,
                poll_interval_sec=0.5,
            ),
        ),
        user_agent_config=UserAgentConfig(
            prompt_path=user_prompt_path,
            model_temperature=0.5,
        ),
        tool_agent_config=ToolAgentConfig(
            prompt_path=tool_prompt_path,
            model_temperature=0.3,
        ),
    )

    eval_agent = EvalAgent(
        EvalAgentConfig(
            prompt_path=eval_prompt_path,
            model_temperature=0.2,
            max_message_chars=4000,
        )
    )

    return SynthesisPipeline(
        config=SynthesisPipelineConfig(
            output_root=output_root,
            evaluate_after_run=True,
            reuse_runtime=True,
            save_blueprint=True,
            save_trajectory=True,
            save_evaluation=True,
            save_manifest=True,
            min_eval_score=None,
            allowed_hallucination_risks=None,
            fail_fast=False,
        ),
        planner_agent=planner_agent,
        simulation_runner=simulation_runner,
        eval_agent=eval_agent,
    )


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def allocate_ports(*, count: int, base_port: int) -> list[int]:
    ports: list[int] = []
    candidate = base_port
    while len(ports) < count:
        if candidate not in ports and is_port_available(candidate):
            ports.append(candidate)
        candidate += 1
    return ports


def run_one_skill(
    *,
    record: dict[str, Any],
    skills_root: Path,
    persona_lines: list[str],
    count_per_skill: int,
    output_root: Path,
    planner_prompt_path: Path,
    user_prompt_path: Path,
    tool_prompt_path: Path,
    eval_prompt_path: Path,
    port: int,
) -> tuple[str, int, int]:
    skill_dir = resolve_skill_dir(record, skills_root)
    validate_program_skill_dir(skill_dir)
    skill_name = skill_dir.name
    tools_path = skill_dir / "tools.jsonl"
    skill_output_root = output_root / skill_name

    pipeline = build_agents_and_pipeline(
        output_root=skill_output_root,
        planner_prompt_path=planner_prompt_path,
        user_prompt_path=user_prompt_path,
        tool_prompt_path=tool_prompt_path,
        eval_prompt_path=eval_prompt_path,
        port=port,
    )

    if count_per_skill <= len(persona_lines):
        selected_personas = persona_lines[:count_per_skill]
    else:
        selected_personas = list(persona_lines)
        extra = count_per_skill - len(persona_lines)
        if extra > 0:
            selected_personas.extend(random.choices(persona_lines, k=extra))

    batch_result = pipeline.run_batch(
        skill_dir=skill_dir,
        persona_texts=selected_personas,
        tools_path=tools_path,
    )
    return skill_name, batch_result.succeeded_count, batch_result.failed_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent-driven batch synthesis for executable env backends"
    )
    parser.add_argument("--selected-skills", type=Path)
    parser.add_argument("--skills-root", type=Path, required=True)
    parser.add_argument("--persona-path", type=Path, required=True)
    parser.add_argument("--count-per-skill", type=int, default=20)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--planner-prompt-path", type=Path, required=True)
    parser.add_argument("--user-prompt-path", type=Path, required=True)
    parser.add_argument("--tool-prompt-path", type=Path, required=True)
    parser.add_argument("--eval-prompt-path", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--base-port", type=int, default=18000)
    parser.add_argument("--limit-skills", type=int, default=0)
    parser.add_argument("--shuffle-personas", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    skills_root = args.skills_root.resolve()
    persona_path = args.persona_path.resolve()
    output_root = args.output_root.resolve()
    planner_prompt_path = args.planner_prompt_path.resolve()
    user_prompt_path = args.user_prompt_path.resolve()
    tool_prompt_path = args.tool_prompt_path.resolve()
    eval_prompt_path = args.eval_prompt_path.resolve()

    if args.selected_skills is not None:
        records = load_selected_skills(args.selected_skills.resolve())
    else:
        records = discover_program_skills(skills_root)

    if args.limit_skills > 0:
        records = records[: args.limit_skills]

    persona_lines = load_persona_lines(persona_path)
    if args.shuffle_personas:
        random.shuffle(persona_lines)

    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Pipeline4 (agent-driven executable env synthesis)")
    print("=" * 60)
    print(f"Skills root:          {skills_root}")
    print(f"Persona path:         {persona_path}")
    print(f"Count per skill:      {args.count_per_skill}")
    print(f"Output root:          {output_root}")
    print(f"Planner prompt:       {planner_prompt_path}")
    print(f"User prompt:          {user_prompt_path}")
    print(f"Tool prompt:          {tool_prompt_path}")
    print(f"Eval prompt:          {eval_prompt_path}")
    print(f"Max workers:          {args.max_workers}")
    print(f"Base port:            {args.base_port}")
    print(f"Selected skill count: {len(records)}")
    print("=" * 60)

    succeeded_skills = 0
    failed_skills: list[str] = []
    ports = allocate_ports(count=len(records), base_port=args.base_port)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = []
        for idx, record in enumerate(records):
            port = ports[idx]
            futures.append(
                executor.submit(
                    run_one_skill,
                    record=record,
                    skills_root=skills_root,
                    persona_lines=persona_lines,
                    count_per_skill=args.count_per_skill,
                    output_root=output_root,
                    planner_prompt_path=planner_prompt_path,
                    user_prompt_path=user_prompt_path,
                    tool_prompt_path=tool_prompt_path,
                    eval_prompt_path=eval_prompt_path,
                    port=port,
                )
            )

        for future in as_completed(futures):
            try:
                skill_name, succeeded_count, failed_count = future.result()
                succeeded_skills += 1
                print(
                    f"[OK] {skill_name} | succeeded_samples={succeeded_count} | failed_samples={failed_count}"
                )
            except Exception as exc:
                failed_skills.append(str(exc))
                print(f"[FAIL] {exc}")

    print("\n" + "=" * 60)
    print("Completed")
    print(f"Succeeded skills: {succeeded_skills}")
    print(f"Failed skills:    {len(failed_skills)}")
    if failed_skills:
        print("Failures:")
        for item in failed_skills:
            print(f" - {item}")
    print("=" * 60)

    return 1 if failed_skills else 0


if __name__ == "__main__":
    sys.exit(main())
