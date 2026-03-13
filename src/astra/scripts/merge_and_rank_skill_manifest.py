#!/usr/bin/env python3
from __future__ import annotations

"""
合并领域过滤与可执行性过滤结果，构建带排序信息的 skill manifest。

主要功能：
- 读取 domain filter 与 executability filter 各自输出的 jsonl 结果（按 dir_name 对齐）
- 计算是否 eligible（同时满足领域相关性、可执行性与风险约束）
- 为每个 skill 计算 selection_score，并生成全局排序与按 primary_domain 的局部排序
- 输出完整 manifest jsonl、汇总 summary.json，以及可选的「每个领域 top-k」子集

推荐使用 Hydra 配置（在项目根目录运行）：
    # 1. 先跑领域过滤与可执行性过滤，产出中间结果
    uv run -m astra.scripts.filter_skills_by_domain mode=run
    uv run -m astra.scripts.filter_skills_by_executability mode=run

    # 2. 使用本脚本合并两路结果并打分排序（使用默认配置 src/astra/configs/merge_skill_manifest.yaml）
    uv run -m astra.scripts.merge_and_rank_skill_manifest

    # 3. 通过 Hydra 覆盖输出路径或 top-k 等参数，例如：
    uv run -m astra.scripts.merge_and_rank_skill_manifest \
        output_manifest=artifacts/skill_manifest_custom.jsonl \
        top_k_per_domain=3 \
        output_selected=artifacts/skill_manifest_top3.jsonl
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import hydra
from hydra.utils import get_original_cwd
from omegaconf import DictConfig

DEFAULT_BLOCKED_RISK_FLAGS = {
    "oauth",
    "browser_only",
    "requires_live_account",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSONL 解析失败: {path} 第 {line_no} 行: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL 行必须是对象: {path} 第 {line_no} 行")
            rows.append(obj)
    return rows


def clamp_float(value: Any, *, low: float, high: float, default: float = 0.0) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, x))


def normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def index_by_dir_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        dir_name = str(row.get("dir_name", "")).strip()
        if not dir_name:
            continue
        out[dir_name] = row
    return out


def build_manifest_record(
    *,
    dir_name: str,
    domain_row: dict[str, Any] | None,
    exec_row: dict[str, Any] | None,
    blocked_risk_flags: set[str],
) -> dict[str, Any]:
    domain_row = domain_row or {}
    exec_row = exec_row or {}

    skill_name = str(
        domain_row.get("skill_name") or exec_row.get("skill_name") or dir_name
    ).strip()

    matched_domains = normalize_str_list(domain_row.get("matched_domains", []))
    primary_domain = str(domain_row.get("primary_domain", "")).strip()
    risk_flags = normalize_str_list(exec_row.get("risk_flags", []))

    record: dict[str, Any] = {
        "dir_name": dir_name,
        "skill_name": skill_name,
        "domain_match": bool(domain_row.get("match", False)),
        "domain_reason": str(domain_row.get("reason", "")).strip(),
        "matched_domains": matched_domains,
        "primary_domain": primary_domain,
        "bfcl_relevance_score": clamp_float(
            domain_row.get("bfcl_relevance_score"), low=0.0, high=5.0
        ),
        "domain_confidence": clamp_float(
            domain_row.get("domain_confidence"), low=0.0, high=1.0
        ),
        "tool_call_intensity_score": clamp_float(
            domain_row.get("tool_call_intensity_score"), low=0.0, high=5.0
        ),
        "multi_turn_potential_score": clamp_float(
            domain_row.get("multi_turn_potential_score"), low=0.0, high=5.0
        ),
        "executability_match": bool(exec_row.get("match", False)),
        "executability_reason": str(exec_row.get("reason", "")).strip(),
        "mockability_score": clamp_float(
            exec_row.get("mockability_score"), low=0.0, high=5.0
        ),
        "determinism_score": clamp_float(
            exec_row.get("determinism_score"), low=0.0, high=5.0
        ),
        "schema_clarity_score": clamp_float(
            exec_row.get("schema_clarity_score"), low=0.0, high=5.0
        ),
        "state_complexity_score": clamp_float(
            exec_row.get("state_complexity_score"), low=0.0, high=5.0
        ),
        "multi_turn_fitness_score": clamp_float(
            exec_row.get("multi_turn_fitness_score"), low=0.0, high=5.0
        ),
        "expected_data_yield_score": clamp_float(
            exec_row.get("expected_data_yield_score"), low=0.0, high=5.0
        ),
        "risk_flags": risk_flags,
    }

    blocked_hits = [flag for flag in risk_flags if flag in blocked_risk_flags]

    eligible = all(
        [
            record["domain_match"],
            record["executability_match"],
            record["bfcl_relevance_score"] >= 3.5,
            record["mockability_score"] >= 3.5,
            record["determinism_score"] >= 3.0,
            record["schema_clarity_score"] >= 3.5,
            record["state_complexity_score"] <= 3.5,
            bool(record["primary_domain"]),
            len(blocked_hits) == 0,
        ]
    )

    selection_score = (
        0.30 * record["bfcl_relevance_score"]
        + 0.20 * record["mockability_score"]
        + 0.15 * record["determinism_score"]
        + 0.15 * record["schema_clarity_score"]
        + 0.10 * record["tool_call_intensity_score"]
        + 0.10 * record["expected_data_yield_score"]
        + 0.05 * record["multi_turn_potential_score"]
        + 0.05 * record["multi_turn_fitness_score"]
        - 0.15 * record["state_complexity_score"]
    )

    notes: list[str] = []
    if record["bfcl_relevance_score"] >= 4.0:
        notes.append("high BFCL relevance")
    if record["mockability_score"] >= 4.0:
        notes.append("high mockability")
    if record["schema_clarity_score"] >= 4.0:
        notes.append("clear schema potential")
    if record["state_complexity_score"] <= 2.0:
        notes.append("low state complexity")
    if blocked_hits:
        notes.append(f"blocked by risk flags: {', '.join(blocked_hits)}")
    if not notes:
        notes.append("mixed profile")

    record.update(
        {
            "eligible": eligible,
            "selection_score": round(selection_score, 6),
            "selection_notes": "; ".join(notes),
            "rank_within_primary_domain": None,
            "rank_global": None,
        }
    )
    return record


def assign_ranks(records: list[dict[str, Any]]) -> None:
    eligible_records = [r for r in records if r.get("eligible")]

    eligible_records.sort(
        key=lambda r: (
            float(r.get("selection_score", 0.0)),
            float(r.get("bfcl_relevance_score", 0.0)),
            float(r.get("mockability_score", 0.0)),
            float(r.get("schema_clarity_score", 0.0)),
        ),
        reverse=True,
    )
    for idx, record in enumerate(eligible_records, 1):
        record["rank_global"] = idx

    domain_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in eligible_records:
        primary_domain = str(record.get("primary_domain", "")).strip()
        if primary_domain:
            domain_groups[primary_domain].append(record)

    for _, group in domain_groups.items():
        group.sort(
            key=lambda r: (
                float(r.get("selection_score", 0.0)),
                float(r.get("bfcl_relevance_score", 0.0)),
                float(r.get("mockability_score", 0.0)),
            ),
            reverse=True,
        )
        for idx, record in enumerate(group, 1):
            record["rank_within_primary_domain"] = idx


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    domain_buckets: dict[str, int] = defaultdict(int)
    eligible_count = 0
    for row in rows:
        if row.get("eligible"):
            eligible_count += 1
            domain = str(row.get("primary_domain", "")).strip()
            if domain:
                domain_buckets[domain] += 1

    top_global = [
        {
            "dir_name": row.get("dir_name", ""),
            "primary_domain": row.get("primary_domain", ""),
            "selection_score": row.get("selection_score", 0.0),
            "rank_global": row.get("rank_global"),
        }
        for row in rows
        if row.get("eligible") and row.get("rank_global") is not None and row["rank_global"] <= 20
    ]

    summary = {
        "total": len(rows),
        "eligible": eligible_count,
        "ineligible": len(rows) - eligible_count,
        "eligible_by_primary_domain": dict(sorted(domain_buckets.items())),
        "top_global": top_global,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def select_top_k_per_domain(
    rows: list[dict[str, Any]],
    *,
    top_k_per_domain: int,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not row.get("eligible"):
            continue
        domain = str(row.get("primary_domain", "")).strip()
        if not domain:
            continue
        groups[domain].append(row)

    selected: list[dict[str, Any]] = []
    for _, group in sorted(groups.items()):
        group.sort(
            key=lambda r: (
                float(r.get("selection_score", 0.0)),
                float(r.get("bfcl_relevance_score", 0.0)),
                float(r.get("mockability_score", 0.0)),
            ),
            reverse=True,
        )
        selected.extend(group[:top_k_per_domain])
    return selected


def run(cfg: DictConfig) -> int:
    """根据 Hydra 配置合并 domain / executability 结果并生成 manifest。"""
    base = Path(get_original_cwd())

    def resolve_path(raw: str | None) -> Path | None:
        if raw is None or str(raw).strip() == "":
            return None
        p = Path(str(raw))
        if not p.is_absolute():
            p = (base / p).resolve()
        return p

    domain_path = resolve_path(cfg.domain_result)
    exec_path = resolve_path(cfg.executability_result)
    if domain_path is None or exec_path is None:
        raise ValueError("domain_result 和 executability_result 路径不能为空")

    domain_rows = read_jsonl(domain_path)
    exec_rows = read_jsonl(exec_path)
    domain_index = index_by_dir_name(domain_rows)
    exec_index = index_by_dir_name(exec_rows)

    blocked_risk_flags = set(DEFAULT_BLOCKED_RISK_FLAGS)
    extra_flags = getattr(cfg, "blocked_risk_flags", None)
    if extra_flags:
        for x in extra_flags:
            s = str(x).strip()
            if s:
                blocked_risk_flags.add(s)

    all_dir_names = sorted(set(domain_index) | set(exec_index))
    manifest_rows = [
        build_manifest_record(
            dir_name=dir_name,
            domain_row=domain_index.get(dir_name),
            exec_row=exec_index.get(dir_name),
            blocked_risk_flags=blocked_risk_flags,
        )
        for dir_name in all_dir_names
    ]

    assign_ranks(manifest_rows)
    manifest_rows.sort(
        key=lambda r: (
            0 if r.get("eligible") else 1,
            r.get("primary_domain", ""),
            -(float(r.get("selection_score", 0.0))),
            r.get("dir_name", ""),
        )
    )

    output_manifest = resolve_path(cfg.output_manifest)
    if output_manifest is None:
        raise ValueError("output_manifest 路径不能为空")
    write_jsonl(output_manifest, manifest_rows)

    summary_path = resolve_path(getattr(cfg, "output_summary", None))
    if summary_path is None:
        summary_path = output_manifest.with_name("skill_manifest_summary.json")
    write_summary(summary_path, manifest_rows)

    top_k_per_domain = int(getattr(cfg, "top_k_per_domain", 0) or 0)
    output_selected = resolve_path(getattr(cfg, "output_selected", None))
    if top_k_per_domain > 0 and output_selected is not None:
        selected = select_top_k_per_domain(
            manifest_rows,
            top_k_per_domain=top_k_per_domain,
        )
        selected.sort(
            key=lambda r: (
                r.get("primary_domain", ""),
                r.get("rank_within_primary_domain") or 10**9,
                r.get("dir_name", ""),
            )
        )
        write_jsonl(output_selected, selected)

    print(f"Wrote manifest: {output_manifest}")
    print(f"Wrote summary:  {summary_path}")
    if top_k_per_domain > 0 and output_selected is not None:
        print(f"Wrote selected: {output_selected}")
    return 0


@hydra.main(
    config_path=str(
        Path(__file__).resolve().parent.parent / "configs"
    ),
    config_name="merge_skill_manifest",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    raise SystemExit(run(cfg))


if __name__ == "__main__":
    main()
