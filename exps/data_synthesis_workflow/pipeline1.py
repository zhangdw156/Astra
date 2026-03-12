#!/usr/bin/env python3
"""
数据合成 pipeline 1 实验。

功能：
1. 遍历一个目录下所有已经过 skill agent 处理的 skill 目录
   - 要求每个 skill 至少包含：
     - SKILL.md
     - tools.jsonl
2. 对每个 skill 合成固定数量的数据
3. 支持按 skill 并发
4. 每个 skill 输出到独立目录：
   <output_root>/<skill_name>/
5. 基于 astra.agent 与 astra.simulation 模块完成：
   planner -> blueprint
   runner  -> trajectory
   eval    -> evaluation

并发策略：
- 按 skill 并发
- 每个 skill 内顺序批量运行
- 每个 skill 使用独立的 MCP 端口，避免冲突

使用示例：
uv run exps/data_synthesis_workflow/pipeline1.py \
  --skills-root skills_demo \
  --persona-path persona/persona_5K.jsonl \
  --count-per-skill 20 \
  --output-root artifacts/pipeline1_results \
  --planner-prompt-path src/astra/prompts/planner_agent.md \
  --user-prompt-path src/astra/prompts/user_agent.md \
  --tool-prompt-path src/astra/prompts/tool_agent.md \
  --eval-prompt-path src/astra/prompts/eval_agent.md \
  --max-workers 5 \
  --base-port 18000 \
  --shuffle-personas \
  --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from astra.agent._eval_agent import EvalAgent, EvalAgentConfig
from astra.agent._planner_agent import PlannerAgent, PlannerAgentConfig
from astra.agent._tool_agent import ToolAgentConfig
from astra.agent._user_agent import UserAgentConfig
from astra.simulation import (
    MCPRuntimeConfig,
    SimulationRunner,
    SimulationRunnerConfig,
    SynthesisPipeline,
    SynthesisPipelineConfig,
)
from astra.utils import logger


# ----------------------------------------------------------------------
# General helpers
# ----------------------------------------------------------------------


def to_jsonable(obj: Any) -> Any:
    """
    将 dataclass / Path / 基础容器递归转换为可 JSON 序列化的对象。
    """
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]

    if isinstance(obj, tuple):
        return [to_jsonable(x) for x in obj]

    return obj


def load_persona_texts(persona_path: Path) -> list[str]:
    """
    读取 persona JSONL，每行作为一个 persona_text。
    """
    persona_texts: list[str] = []
    for line in persona_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            persona_texts.append(stripped)
    return persona_texts


def is_processed_skill_dir(skill_dir: Path) -> bool:
    """
    判断目录是否为一个已处理好的 skill 目录。
    """
    return (
        skill_dir.is_dir()
        and (skill_dir / "SKILL.md").exists()
        and (skill_dir / "tools.jsonl").exists()
    )


def list_processed_skill_dirs(skills_root: Path) -> list[Path]:
    """
    列出 skills_root 下所有已处理好的 skill 子目录。
    """
    if not skills_root.exists():
        return []

    return [
        p
        for p in sorted(skills_root.iterdir())
        if is_processed_skill_dir(p)
    ]


def build_persona_subset(
    all_persona_texts: list[str],
    *,
    count: int,
    seed: int,
    shuffle_personas: bool,
) -> list[str]:
    """
    为单个 skill 选择一组 persona 文本。

    策略：
    - 若 shuffle_personas=True，则打乱后取前 count 个（不足则循环复用）
    - 否则顺序取前 count 个（不足则循环复用）
    """
    if not all_persona_texts:
        raise ValueError("persona 列表为空")

    personas = list(all_persona_texts)
    if shuffle_personas:
        rnd = random.Random(seed)
        rnd.shuffle(personas)

    result: list[str] = []
    idx = 0
    while len(result) < count:
        result.append(personas[idx % len(personas)])
        idx += 1
    return result


# ----------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------


def run_one_skill_batch(
    *,
    skill_dir: str,
    output_root: str,
    persona_path: str,
    count_per_skill: int,
    planner_prompt_path: str,
    user_prompt_path: str,
    tool_prompt_path: str,
    eval_prompt_path: str,
    port: int,
    shuffle_personas: bool,
    seed: int,
    no_eval: bool,
    min_eval_score: float | None,
    allowed_hallucination_risks: tuple[str, ...] | None,
) -> dict[str, Any]:
    """
    单个 skill 的 batch worker。
    在独立进程中运行。
    """
    skill_dir_path = Path(skill_dir).resolve()
    output_root_path = Path(output_root).resolve()
    persona_path_path = Path(persona_path).resolve()

    planner_prompt = Path(planner_prompt_path).resolve()
    user_prompt = Path(user_prompt_path).resolve()
    tool_prompt = Path(tool_prompt_path).resolve()
    eval_prompt = Path(eval_prompt_path).resolve()

    skill_output_root = output_root_path / skill_dir_path.name
    skill_output_root.mkdir(parents=True, exist_ok=True)

    logger.info("Start skill batch: {}", skill_dir_path.name)

    all_persona_texts = load_persona_texts(persona_path_path)
    persona_subset = build_persona_subset(
        all_persona_texts,
        count=count_per_skill,
        seed=seed,
        shuffle_personas=shuffle_personas,
    )

    planner_agent = PlannerAgent(
        PlannerAgentConfig(
            prompt_path=planner_prompt,
            verbose=False,
        )
    )

    tool_agent_config = ToolAgentConfig(
        prompt_path=tool_prompt,
        verbose=False,
    )

    user_agent_config = UserAgentConfig(
        prompt_path=user_prompt,
        verbose=False,
    )

    runner_config = SimulationRunnerConfig(
        max_turns=20,
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
    )

    simulation_runner = SimulationRunner(
        config=runner_config,
        user_agent_config=user_agent_config,
        tool_agent_config=tool_agent_config,
    )

    eval_agent = None
    if not no_eval:
        eval_agent = EvalAgent(
            EvalAgentConfig(
                prompt_path=eval_prompt,
                verbose=False,
                max_message_chars=4000,
            )
        )

    pipeline = SynthesisPipeline(
        config=SynthesisPipelineConfig(
            output_root=skill_output_root,
            evaluate_after_run=not no_eval,
            reuse_runtime=True,
            save_blueprint=True,
            save_trajectory=True,
            save_evaluation=not no_eval,
            save_manifest=True,
            min_eval_score=min_eval_score,
            allowed_hallucination_risks=allowed_hallucination_risks,
            fail_fast=False,
        ),
        planner_agent=planner_agent,
        simulation_runner=simulation_runner,
        eval_agent=eval_agent,
    )

    batch_result = pipeline.run_batch(
        skill_dir=skill_dir_path,
        persona_texts=persona_subset,
        tools_path=skill_dir_path / "tools.jsonl",
    )

    summary = {
        "skill_name": skill_dir_path.name,
        "skill_dir": str(skill_dir_path),
        "output_root": str(skill_output_root),
        "port": port,
        "count_per_skill": count_per_skill,
        "total_count": batch_result.total_count,
        "succeeded_count": batch_result.succeeded_count,
        "failed_count": batch_result.failed_count,
        "accepted_count": batch_result.accepted_count,
        "rejected_count": batch_result.rejected_count,
    }

    (skill_output_root / "skill_batch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Finish skill batch: {}", skill_dir_path.name)
    return summary


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量复现 pipeline1 数据合成实验（按 skill 并发）"
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        required=True,
        help="skills 根目录，里面每个子目录应包含 SKILL.md 和 tools.jsonl",
    )
    parser.add_argument(
        "--persona-path",
        type=Path,
        required=True,
        help="persona JSONL 文件路径",
    )
    parser.add_argument(
        "--count-per-skill",
        type=int,
        required=True,
        help="每个 skill 合成的样本数量",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="总输出目录，每个 skill 会写到 output_root/skill_name 下",
    )
    parser.add_argument(
        "--planner-prompt-path",
        type=Path,
        required=True,
        help="planner agent prompt 模板路径",
    )
    parser.add_argument(
        "--user-prompt-path",
        type=Path,
        required=True,
        help="user agent prompt 模板路径",
    )
    parser.add_argument(
        "--tool-prompt-path",
        type=Path,
        required=True,
        help="tool agent prompt 模板路径",
    )
    parser.add_argument(
        "--eval-prompt-path",
        type=Path,
        required=True,
        help="eval agent prompt 模板路径",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="按 skill 并发的最大进程数",
    )
    parser.add_argument(
        "--base-port",
        type=int,
        default=18000,
        help="每个 skill 的本地 MCP runtime 起始端口，后续按 skill 顺序递增",
    )
    parser.add_argument(
        "--shuffle-personas",
        action="store_true",
        help="是否对 persona 打乱后再取样",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="persona 采样随机种子",
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="只生成 blueprint + trajectory，不做 evaluation",
    )
    parser.add_argument(
        "--min-eval-score",
        type=float,
        default=None,
        help="若设置，则低于该分数的样本标记为 rejected",
    )
    parser.add_argument(
        "--allowed-hallucination-risks",
        type=str,
        nargs="*",
        default=None,
        help='允许的 hallucination_risk 集合，例如: --allowed-hallucination-risks none low',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    skills_root = args.skills_root.resolve()
    persona_path = args.persona_path.resolve()
    output_root = args.output_root.resolve()

    if not skills_root.exists():
        raise SystemExit(f"skills_root 不存在: {skills_root}")
    if not persona_path.exists():
        raise SystemExit(f"persona_path 不存在: {persona_path}")
    if args.count_per_skill <= 0:
        raise SystemExit(f"count_per_skill 必须为正整数: {args.count_per_skill}")
    if args.max_workers <= 0:
        raise SystemExit(f"max_workers 必须为正整数: {args.max_workers}")
    if args.base_port <= 0:
        raise SystemExit(f"base_port 必须为正整数: {args.base_port}")

    skill_dirs = list_processed_skill_dirs(skills_root)
    if not skill_dirs:
        raise SystemExit(f"未在 {skills_root} 下找到任何已处理好的 skill 目录")

    output_root.mkdir(parents=True, exist_ok=True)

    logger.info("Found {} processed skills under {}", len(skill_dirs), skills_root)

    futures = []
    summaries: list[dict[str, Any]] = []

    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        for idx, skill_dir in enumerate(skill_dirs):
            port = args.base_port + idx
            future = executor.submit(
                run_one_skill_batch,
                skill_dir=str(skill_dir),
                output_root=str(output_root),
                persona_path=str(persona_path),
                count_per_skill=args.count_per_skill,
                planner_prompt_path=str(args.planner_prompt_path.resolve()),
                user_prompt_path=str(args.user_prompt_path.resolve()),
                tool_prompt_path=str(args.tool_prompt_path.resolve()),
                eval_prompt_path=str(args.eval_prompt_path.resolve()),
                port=port,
                shuffle_personas=args.shuffle_personas,
                seed=args.seed + idx,
                no_eval=args.no_eval,
                min_eval_score=args.min_eval_score,
                allowed_hallucination_risks=(
                    tuple(args.allowed_hallucination_risks)
                    if args.allowed_hallucination_risks
                    else None
                ),
            )
            futures.append((skill_dir.name, future))

        for skill_name, future in futures:
            try:
                summary = future.result()
                summaries.append(summary)
                logger.info(
                    "Skill {} done: succeeded={}, failed={}, accepted={}, rejected={}",
                    skill_name,
                    summary["succeeded_count"],
                    summary["failed_count"],
                    summary["accepted_count"],
                    summary["rejected_count"],
                )
            except Exception as exc:
                logger.error("Skill {} failed: {}", skill_name, exc)
                summaries.append(
                    {
                        "skill_name": skill_name,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                )

    batch_summary = {
        "skills_root": str(skills_root),
        "persona_path": str(persona_path),
        "count_per_skill": args.count_per_skill,
        "max_workers": args.max_workers,
        "base_port": args.base_port,
        "shuffle_personas": args.shuffle_personas,
        "seed": args.seed,
        "no_eval": args.no_eval,
        "min_eval_score": args.min_eval_score,
        "allowed_hallucination_risks": args.allowed_hallucination_risks,
        "num_skills": len(skill_dirs),
        "skill_summaries": summaries,
    }

    summary_path = output_root / "batch_summary.json"
    summary_path.write_text(
        json.dumps(to_jsonable(batch_summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Batch summary written to {}", summary_path)


if __name__ == "__main__":
    main()