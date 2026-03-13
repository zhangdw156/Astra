#!/usr/bin/env python3
"""
基于 selected_skills.jsonl 的批量数据合成脚本。

目标：
- 只对 selected_skills.jsonl 中选出的 skill 跑 planner -> simulation -> eval
- 尽量贴近旧版 pipeline1 的风格，但改为显式依赖当前的 agent + simulation 模块
- 支持按 skill 并发
- 每个 skill 生成固定数量样本
- 每个 skill 使用独立 output_root，避免 artifacts 混在一起

selected_skills.jsonl 每行至少应包含：
- dir_name

可选字段：
- skill_dir（若存在则优先使用）
- 其他字段会被忽略

使用示例：
    uv run exps/data_synthesis_workflow/pipeline1_selected_skills.py \
        --selected-skills artifacts/skill_manifest_top3.jsonl \
        --skills-root skills \
        --persona-path persona/persona_5K.jsonl \
        --count-per-skill 50 \
        --output-root artifacts/pipeline1_results \
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
        raise FileNotFoundError(f"selected_skills.jsonl 不存在: {path}")

    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"selected_skills.jsonl 第 {line_no} 行 JSON 非法: {e}"
                ) from e

            if not isinstance(obj, dict):
                raise ValueError(f"selected_skills.jsonl 第 {line_no} 行不是 JSON object")

            if "dir_name" not in obj and "skill_dir" not in obj:
                raise ValueError(
                    f"selected_skills.jsonl 第 {line_no} 行缺少 dir_name 或 skill_dir"
                )

            records.append(obj)

    return records


def load_persona_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"persona 文件不存在: {path}")

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError(f"persona 文件为空: {path}")
    return lines


def resolve_skill_dir(record: dict[str, Any], skills_root: Path) -> Path:
    skill_dir = record.get("skill_dir")
    if isinstance(skill_dir, str) and skill_dir.strip():
        path = Path(skill_dir.strip())
        return path.resolve() if path.is_absolute() else (skills_root / path).resolve()

    dir_name = str(record.get("dir_name", "")).strip()
    if not dir_name:
        raise ValueError(f"record 缺少有效 dir_name: {record}")

    return (skills_root / dir_name).resolve()


def infer_project_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists() or (parent / "src").exists():
            return parent
    return start.resolve()


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

    pipeline = SynthesisPipeline(
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
    return pipeline


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
    """
    返回:
    - skill 名称
    - 成功样本数
    - 失败样本数
    """
    skill_dir = resolve_skill_dir(record, skills_root)
    skill_name = skill_dir.name
    tools_path = skill_dir / "tools.jsonl"

    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"未找到 SKILL.md: {skill_dir / 'SKILL.md'}")

    if not tools_path.exists():
        raise FileNotFoundError(f"未找到 tools.jsonl: {tools_path}")

    skill_output_root = output_root / skill_name
    pipeline = build_agents_and_pipeline(
        output_root=skill_output_root,
        planner_prompt_path=planner_prompt_path,
        user_prompt_path=user_prompt_path,
        tool_prompt_path=tool_prompt_path,
        eval_prompt_path=eval_prompt_path,
        port=port,
    )

    selected_personas = []
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
        description="基于 selected_skills.jsonl 的批量数据合成"
    )
    parser.add_argument(
        "--selected-skills",
        type=Path,
        required=True,
        help="selected_skills.jsonl 路径",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        required=True,
        help="skill 根目录",
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
        default=20,
        help="每个 skill 生成多少条样本",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="输出根目录",
    )
    parser.add_argument(
        "--planner-prompt-path",
        type=Path,
        required=True,
        help="planner agent prompt 路径",
    )
    parser.add_argument(
        "--user-prompt-path",
        type=Path,
        required=True,
        help="user agent prompt 路径",
    )
    parser.add_argument(
        "--tool-prompt-path",
        type=Path,
        required=True,
        help="tool agent prompt 路径",
    )
    parser.add_argument(
        "--eval-prompt-path",
        type=Path,
        required=True,
        help="eval agent prompt 路径",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="按 skill 并发的 worker 数",
    )
    parser.add_argument(
        "--base-port",
        type=int,
        default=18000,
        help="并发 skill 的起始端口，每个 skill 占用一个端口",
    )
    parser.add_argument(
        "--limit-skills",
        type=int,
        default=0,
        help="最多处理多少个 skill（0 表示不限制）",
    )
    parser.add_argument(
        "--shuffle-personas",
        action="store_true",
        help="是否在开始前打乱 persona 顺序",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子",
    )

    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    _project_root = infer_project_root(script_path.parent)

    random.seed(args.seed)

    selected_skills_path = args.selected_skills.resolve()
    skills_root = args.skills_root.resolve()
    persona_path = args.persona_path.resolve()
    output_root = args.output_root.resolve()
    planner_prompt_path = args.planner_prompt_path.resolve()
    user_prompt_path = args.user_prompt_path.resolve()
    tool_prompt_path = args.tool_prompt_path.resolve()
    eval_prompt_path = args.eval_prompt_path.resolve()

    records = load_selected_skills(selected_skills_path)
    if args.limit_skills > 0:
        records = records[: args.limit_skills]

    persona_lines = load_persona_lines(persona_path)
    if args.shuffle_personas:
        random.shuffle(persona_lines)

    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Pipeline1 (selected skills): 生成 blueprint / trajectory / evaluation")
    print("=" * 60)
    print(f"Selected skills:      {selected_skills_path}")
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
    print(f"Total selected skill: {len(records)}")
    print("=" * 60)

    succeeded_skills = 0
    failed_skills: list[str] = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = []
        for idx, record in enumerate(records):
            port = args.base_port + idx
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
            except Exception as e:
                failed_skills.append(str(e))
                print(f"[FAIL] {e}")

    print("\n" + "=" * 60)
    print("完成")
    print(f"成功 skill 数: {succeeded_skills}")
    print(f"失败 skill 数: {len(failed_skills)}")
    if failed_skills:
        print("失败项:")
        for item in failed_skills:
            print(" -", item)
    print("=" * 60)

    return 1 if failed_skills else 0


if __name__ == "__main__":
    sys.exit(main())