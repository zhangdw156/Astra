#!/usr/bin/env python3
"""
统计一个生成数据目录下的 blueprint / trajectory / evaluation 产物概况。

示例：
  .venv/bin/python exps/data-synthesis-workflow/pipeline1/scripts/stats_generated_data.py
  .venv/bin/python exps/data-synthesis-workflow/pipeline1/scripts/stats_generated_data.py root=exps/data-synthesis-workflow/pipeline1/artifacts_multi
  .venv/bin/python exps/data-synthesis-workflow/pipeline1/scripts/stats_generated_data.py per_skill=true export_csv=true
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import hydra
from hydra.core.config_store import ConfigStore
from hydra.utils import get_original_cwd
from omegaconf import DictConfig, OmegaConf


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent / "artifacts_multi"


@dataclass
class StatsGeneratedDataConfig:
    root: str = str(DEFAULT_ROOT)
    per_skill: bool = False
    top_k_tools: int = 10
    json_output: bool = False
    export_csv: bool = False
    csv_dir: str = ""
    low_score_threshold: float = 4.0


cs = ConfigStore.instance()
cs.store(name="stats_generated_data", node=StatsGeneratedDataConfig)


def _safe_load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt_float(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path(get_original_cwd()) / path).resolve()


def _iter_run_dirs(root: Path) -> list[Path]:
    run_dirs: list[Path] = []
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for run_dir in sorted(p for p in skill_dir.iterdir() if p.is_dir()):
            run_dirs.append(run_dir)
    return run_dirs


def _extract_tool_calls(messages: list[dict]) -> list[str]:
    return [
        m["function_call"]["name"]
        for m in messages
        if isinstance(m, dict)
        and isinstance(m.get("function_call"), dict)
        and m["function_call"].get("name")
    ]


def build_stats(root: Path, low_score_threshold: float) -> dict:
    run_dirs = _iter_run_dirs(root)
    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir())

    stats: dict = {
        "root": str(root),
        "skill_count": len(skill_dirs),
        "run_count": len(run_dirs),
        "blueprint_count": 0,
        "trajectory_count": 0,
        "evaluation_count": 0,
        "broken_blueprint_count": 0,
        "broken_trajectory_count": 0,
        "broken_evaluation_count": 0,
        "message_counts": [],
        "user_message_counts": [],
        "assistant_message_counts": [],
        "function_message_counts": [],
        "assistant_tool_call_counts": [],
        "tool_name_counts": Counter(),
        "validation_pass_counts": Counter(),
        "score_values": [],
        "task_completion_values": [],
        "hallucination_risk_counts": Counter(),
        "missing_runs": [],
        "low_score_runs": [],
        "run_rows": [],
        "per_skill": defaultdict(
            lambda: {
                "runs": 0,
                "blueprints": 0,
                "trajectories": 0,
                "evaluations": 0,
                "scores": [],
                "tool_calls": 0,
                "messages": 0,
            }
        ),
    }

    for run_dir in run_dirs:
        skill_name = run_dir.parent.name
        run_name = run_dir.name
        per_skill = stats["per_skill"][skill_name]
        per_skill["runs"] += 1

        blueprint_path = run_dir / "blueprint.json"
        trajectory_path = run_dir / "trajectory.json"
        evaluation_path = run_dir / "evaluation.json"

        blueprint_exists = blueprint_path.exists()
        trajectory_exists = trajectory_path.exists()
        evaluation_exists = evaluation_path.exists()

        missing_parts = []
        if not blueprint_exists:
            missing_parts.append("blueprint.json")
        if not trajectory_exists:
            missing_parts.append("trajectory.json")
        if not evaluation_exists:
            missing_parts.append("evaluation.json")
        if missing_parts:
            stats["missing_runs"].append(
                {
                    "skill_name": skill_name,
                    "run_name": run_name,
                    "run_dir": str(run_dir),
                    "missing_parts": missing_parts,
                }
            )

        blueprint = None
        trajectory = None
        evaluation = None

        if blueprint_exists:
            stats["blueprint_count"] += 1
            per_skill["blueprints"] += 1
            blueprint = _safe_load_json(blueprint_path)
            if blueprint is None:
                stats["broken_blueprint_count"] += 1

        if trajectory_exists:
            stats["trajectory_count"] += 1
            per_skill["trajectories"] += 1
            trajectory = _safe_load_json(trajectory_path)
            if trajectory is None:
                stats["broken_trajectory_count"] += 1

        if evaluation_exists:
            stats["evaluation_count"] += 1
            per_skill["evaluations"] += 1
            evaluation = _safe_load_json(evaluation_path)
            if evaluation is None:
                stats["broken_evaluation_count"] += 1

        message_count = None
        user_count = None
        assistant_count = None
        function_count = None
        tool_call_count = None
        score = None
        task_completion = None
        hallucination_risk = None
        validation_passed = None

        if isinstance(trajectory, dict):
            messages = trajectory.get("messages") or []
            if isinstance(messages, list):
                message_count = len(messages)
                user_count = sum(1 for m in messages if isinstance(m, dict) and m.get("role") == "user")
                assistant_count = sum(
                    1 for m in messages if isinstance(m, dict) and m.get("role") == "assistant"
                )
                function_count = sum(
                    1 for m in messages if isinstance(m, dict) and m.get("role") == "function"
                )
                tool_calls = _extract_tool_calls(messages)
                tool_call_count = len(tool_calls)

                stats["message_counts"].append(message_count)
                stats["user_message_counts"].append(user_count)
                stats["assistant_message_counts"].append(assistant_count)
                stats["function_message_counts"].append(function_count)
                stats["assistant_tool_call_counts"].append(tool_call_count)
                stats["tool_name_counts"].update(tool_calls)
                per_skill["tool_calls"] += tool_call_count
                per_skill["messages"] += message_count

            validation = trajectory.get("validation") or {}
            output_based = validation.get("output_based") if isinstance(validation, dict) else None
            if isinstance(output_based, dict):
                validation_passed = bool(output_based.get("passed"))
                stats["validation_pass_counts"][validation_passed] += 1

        if isinstance(evaluation, dict):
            raw_score = evaluation.get("score")
            raw_task_completion = evaluation.get("task_completion_score")
            hallucination_risk = evaluation.get("hallucination_risk")
            if isinstance(raw_score, (int, float)):
                score = float(raw_score)
                stats["score_values"].append(score)
                per_skill["scores"].append(score)
            if isinstance(raw_task_completion, (int, float)):
                task_completion = float(raw_task_completion)
                stats["task_completion_values"].append(task_completion)
            if hallucination_risk:
                stats["hallucination_risk_counts"][str(hallucination_risk)] += 1

        if score is not None and score <= low_score_threshold:
            stats["low_score_runs"].append(
                {
                    "skill_name": skill_name,
                    "run_name": run_name,
                    "run_dir": str(run_dir),
                    "score": score,
                    "hallucination_risk": hallucination_risk or "",
                    "task_completion_score": task_completion,
                }
            )

        stats["run_rows"].append(
            {
                "skill_name": skill_name,
                "run_name": run_name,
                "run_dir": str(run_dir),
                "blueprint_exists": blueprint_exists,
                "trajectory_exists": trajectory_exists,
                "evaluation_exists": evaluation_exists,
                "message_count": message_count,
                "user_message_count": user_count,
                "assistant_message_count": assistant_count,
                "function_message_count": function_count,
                "tool_call_count": tool_call_count,
                "validation_output_based_passed": validation_passed,
                "score": score,
                "hallucination_risk": hallucination_risk,
                "task_completion_score": task_completion,
            }
        )

    return stats


def _build_skill_rows(stats: dict) -> list[dict]:
    rows: list[dict] = []
    for skill_name in sorted(stats["per_skill"]):
        item = stats["per_skill"][skill_name]
        score_avg = mean(item["scores"]) if item["scores"] else None
        msg_avg = (item["messages"] / item["trajectories"]) if item["trajectories"] else None
        tool_avg = (item["tool_calls"] / item["trajectories"]) if item["trajectories"] else None
        rows.append(
            {
                "skill_name": skill_name,
                "runs": item["runs"],
                "blueprints": item["blueprints"],
                "trajectories": item["trajectories"],
                "evaluations": item["evaluations"],
                "score_avg": score_avg,
                "messages_avg": msg_avg,
                "tool_calls_avg": tool_avg,
            }
        )
    return rows


def render_summary(stats: dict, *, show_per_skill: bool = False, top_k_tools: int = 10) -> str:
    lines: list[str] = []
    lines.append(f"Root: {stats['root']}")
    lines.append(f"Skills: {stats['skill_count']}")
    lines.append(f"Runs: {stats['run_count']}")
    lines.append("")
    lines.append("Coverage")
    lines.append(
        f"- blueprint.json: {stats['blueprint_count']}/{stats['run_count']} (broken: {stats['broken_blueprint_count']})"
    )
    lines.append(
        f"- trajectory.json: {stats['trajectory_count']}/{stats['run_count']} (broken: {stats['broken_trajectory_count']})"
    )
    lines.append(
        f"- evaluation.json: {stats['evaluation_count']}/{stats['run_count']} (broken: {stats['broken_evaluation_count']})"
    )
    lines.append("")

    message_counts = stats["message_counts"]
    tool_call_counts = stats["assistant_tool_call_counts"]
    score_values = stats["score_values"]
    task_completion_values = stats["task_completion_values"]

    lines.append("Trajectory")
    lines.append(
        f"- messages/run avg: {_fmt_float(mean(message_counts) if message_counts else None)}"
        f" | user avg: {_fmt_float(mean(stats['user_message_counts']) if stats['user_message_counts'] else None)}"
        f" | assistant avg: {_fmt_float(mean(stats['assistant_message_counts']) if stats['assistant_message_counts'] else None)}"
        f" | function avg: {_fmt_float(mean(stats['function_message_counts']) if stats['function_message_counts'] else None)}"
    )
    lines.append(
        f"- tool calls/run avg: {_fmt_float(mean(tool_call_counts) if tool_call_counts else None)}"
        f" | total tool calls: {sum(tool_call_counts)}"
    )
    validation_counts = stats["validation_pass_counts"]
    if validation_counts:
        lines.append(
            f"- validation output_based passed: {validation_counts.get(True, 0)}"
            f" | failed: {validation_counts.get(False, 0)}"
        )
    lines.append("")

    lines.append("Evaluation")
    lines.append(
        f"- score avg/min/max: {_fmt_float(mean(score_values) if score_values else None)}"
        f" / {_fmt_float(min(score_values) if score_values else None)}"
        f" / {_fmt_float(max(score_values) if score_values else None)}"
    )
    lines.append(
        f"- task completion avg: {_fmt_float(mean(task_completion_values) if task_completion_values else None)}"
    )
    risk_counts = stats["hallucination_risk_counts"]
    risk_summary = ", ".join(f"{risk}={risk_counts[risk]}" for risk in sorted(risk_counts)) or "-"
    lines.append(f"- hallucination risk: {risk_summary}")
    lines.append("")

    lines.append(f"Top {top_k_tools} Tools")
    for name, count in stats["tool_name_counts"].most_common(top_k_tools):
        lines.append(f"- {name}: {count}")

    lines.append("")
    lines.append(f"Missing Runs: {len(stats['missing_runs'])}")
    for item in stats["missing_runs"][:10]:
        missing = ", ".join(item["missing_parts"])
        lines.append(f"- {item['skill_name']}/{item['run_name']}: {missing}")

    lines.append("")
    lines.append(f"Low Score Runs: {len(stats['low_score_runs'])}")
    for item in sorted(stats["low_score_runs"], key=lambda x: x["score"]):
        lines.append(
            f"- {item['skill_name']}/{item['run_name']}: score={_fmt_float(item['score'])}, "
            f"risk={item['hallucination_risk'] or '-'}, "
            f"task_completion={_fmt_float(item['task_completion_score'])}"
        )

    if show_per_skill:
        lines.append("")
        lines.append("Per Skill")
        for item in _build_skill_rows(stats):
            lines.append(
                f"- {item['skill_name']}: runs={item['runs']}, blueprint={item['blueprints']}, "
                f"trajectory={item['trajectories']}, evaluation={item['evaluations']}, "
                f"score_avg={_fmt_float(item['score_avg'])}, messages_avg={_fmt_float(item['messages_avg'])}, "
                f"tool_calls_avg={_fmt_float(item['tool_calls_avg'])}"
            )

    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_csv_files(stats: dict, csv_dir: Path) -> list[Path]:
    skill_rows = _build_skill_rows(stats)
    run_rows = list(stats["run_rows"])
    missing_rows = [
        {
            "skill_name": item["skill_name"],
            "run_name": item["run_name"],
            "run_dir": item["run_dir"],
            "missing_parts": ",".join(item["missing_parts"]),
        }
        for item in stats["missing_runs"]
    ]
    low_score_rows = list(stats["low_score_runs"])

    outputs = [
        (
            csv_dir / "runs.csv",
            run_rows,
            [
                "skill_name",
                "run_name",
                "run_dir",
                "blueprint_exists",
                "trajectory_exists",
                "evaluation_exists",
                "message_count",
                "user_message_count",
                "assistant_message_count",
                "function_message_count",
                "tool_call_count",
                "validation_output_based_passed",
                "score",
                "hallucination_risk",
                "task_completion_score",
            ],
        ),
        (
            csv_dir / "skills.csv",
            skill_rows,
            [
                "skill_name",
                "runs",
                "blueprints",
                "trajectories",
                "evaluations",
                "score_avg",
                "messages_avg",
                "tool_calls_avg",
            ],
        ),
        (
            csv_dir / "missing_runs.csv",
            missing_rows,
            ["skill_name", "run_name", "run_dir", "missing_parts"],
        ),
        (
            csv_dir / "low_score_runs.csv",
            low_score_rows,
            [
                "skill_name",
                "run_name",
                "run_dir",
                "score",
                "hallucination_risk",
                "task_completion_score",
            ],
        ),
    ]

    written: list[Path] = []
    for path, rows, fieldnames in outputs:
        _write_csv(path, rows, fieldnames)
        written.append(path)
    return written


def _to_serializable(stats: dict) -> dict:
    return {
        "root": stats["root"],
        "skill_count": stats["skill_count"],
        "run_count": stats["run_count"],
        "blueprint_count": stats["blueprint_count"],
        "trajectory_count": stats["trajectory_count"],
        "evaluation_count": stats["evaluation_count"],
        "broken_blueprint_count": stats["broken_blueprint_count"],
        "broken_trajectory_count": stats["broken_trajectory_count"],
        "broken_evaluation_count": stats["broken_evaluation_count"],
        "message_counts": list(stats["message_counts"]),
        "user_message_counts": list(stats["user_message_counts"]),
        "assistant_message_counts": list(stats["assistant_message_counts"]),
        "function_message_counts": list(stats["function_message_counts"]),
        "assistant_tool_call_counts": list(stats["assistant_tool_call_counts"]),
        "tool_name_counts": dict(stats["tool_name_counts"]),
        "validation_pass_counts": {str(k): v for k, v in stats["validation_pass_counts"].items()},
        "score_values": list(stats["score_values"]),
        "task_completion_values": list(stats["task_completion_values"]),
        "hallucination_risk_counts": dict(stats["hallucination_risk_counts"]),
        "missing_runs": list(stats["missing_runs"]),
        "low_score_runs": list(stats["low_score_runs"]),
        "run_rows": list(stats["run_rows"]),
        "per_skill": {
            k: {
                **v,
                "scores": list(v["scores"]),
            }
            for k, v in stats["per_skill"].items()
        },
    }


@hydra.main(config_path=None, config_name="stats_generated_data", version_base=None)
def main(cfg: DictConfig) -> None:
    conf = OmegaConf.merge(OmegaConf.structured(StatsGeneratedDataConfig), cfg)
    root = _resolve_path(str(conf.root))
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"目录不存在或不是目录: {root}")

    stats = build_stats(root, low_score_threshold=float(conf.low_score_threshold))

    if bool(conf.json_output):
        print(json.dumps(_to_serializable(stats), ensure_ascii=False, indent=2))
    else:
        print(
            render_summary(
                stats,
                show_per_skill=bool(conf.per_skill),
                top_k_tools=int(conf.top_k_tools),
            )
        )

    if bool(conf.export_csv):
        csv_dir_raw = str(conf.csv_dir).strip()
        csv_dir = _resolve_path(csv_dir_raw) if csv_dir_raw else root / "_stats"
        written = export_csv_files(stats, csv_dir)
        print("")
        print("CSV")
        for path in written:
            print(f"- {path}")


if __name__ == "__main__":
    main()
