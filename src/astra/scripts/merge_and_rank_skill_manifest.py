#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge domain/executability filter results and build ranked skill manifest"
    )
    parser.add_argument(
        "--domain-result",
        type=Path,
        required=True,
        help="domain_filter_result.jsonl 路径",
    )
    parser.add_argument(
        "--executability-result",
        type=Path,
        required=True,
        help="executability_filter_result.jsonl 路径",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        required=True,
        help="输出 skill_manifest.jsonl 路径",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=None,
        help="输出 manifest_summary.json 路径",
    )
    parser.add_argument(
        "--output-selected",
        type=Path,
        default=None,
        help="输出按 primary_domain 选 top-k 的 jsonl 路径",
    )
    parser.add_argument(
        "--top-k-per-domain",
        type=int,
        default=0,
        help="若 > 0，则每个 primary_domain 选前 k 个 skill",
    )
    parser.add_argument(
        "--blocked-risk-flag",
        action="append",
        default=None,
        help="额外屏蔽的 risk flag，可多次传入",
    )
    args = parser.parse_args()

    domain_rows = read_jsonl(args.domain_result)
    exec_rows = read_jsonl(args.executability_result)
    domain_index = index_by_dir_name(domain_rows)
    exec_index = index_by_dir_name(exec_rows)

    blocked_risk_flags = set(DEFAULT_BLOCKED_RISK_FLAGS)
    if args.blocked_risk_flag:
        blocked_risk_flags.update(x.strip() for x in args.blocked_risk_flag if x.strip())

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

    write_jsonl(args.output_manifest, manifest_rows)

    summary_path = args.output_summary
    if summary_path is None:
        summary_path = args.output_manifest.with_name("skill_manifest_summary.json")
    write_summary(summary_path, manifest_rows)

    if args.top_k_per_domain > 0 and args.output_selected is not None:
        selected = select_top_k_per_domain(
            manifest_rows,
            top_k_per_domain=args.top_k_per_domain,
        )
        selected.sort(
            key=lambda r: (
                r.get("primary_domain", ""),
                r.get("rank_within_primary_domain") or 10**9,
                r.get("dir_name", ""),
            )
        )
        write_jsonl(args.output_selected, selected)

    print(f"Wrote manifest: {args.output_manifest}")
    print(f"Wrote summary:  {summary_path}")
    if args.top_k_per_domain > 0 and args.output_selected is not None:
        print(f"Wrote selected: {args.output_selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
