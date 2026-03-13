"""按可执行/可模拟性过滤 skills 的主流程（优化版）。

升级目标：
1. 不再在 run 模式下直接删除目录
2. 让 executability filter 输出 richer schema，而不只是 match/reason
3. 产出 jsonl 结果，便于后续与 domain filter 合并成 manifest
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Any

from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig
from openai import OpenAI

from astra.scripts._executability_filter import llm
from astra.scripts._executability_filter import prompts
from astra.scripts._executability_filter import skills

_ALLOWED_MODES = {"run", "test", "dry-run"}

_DEFAULT_RESULT = {
    "match": False,
    "reason": "无法解析模型返回",
    "mockability_score": 0.0,
    "determinism_score": 0.0,
    "schema_clarity_score": 0.0,
    "state_complexity_score": 5.0,
    "multi_turn_fitness_score": 0.0,
    "expected_data_yield_score": 0.0,
    "risk_flags": [],
}

_ALLOWED_RISK_FLAGS = {
    "external_http",
    "oauth",
    "browser_only",
    "hardware_io",
    "high_state_complexity",
    "safety_sensitive",
    "streaming",
    "long_running_job",
    "non_deterministic",
    "filesystem_heavy",
    "gui_only",
    "requires_real_credentials",
}


def _parse_mode(raw: str) -> str:
    raw = (raw or "").strip().lower()
    if raw == "dryrun":
        raw = "dry-run"
    if raw not in _ALLOWED_MODES:
        raise ValueError(
            f"mode 只允许取 {sorted(_ALLOWED_MODES)}，当前为: {raw!r}。"
        )
    return raw


def _coerce_score(value: Any, *, low: float, high: float, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, x))


def _normalize_risk_flags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s:
            continue
        out.append(s)
    seen: set[str] = set()
    uniq: list[str] = []
    for item in out:
        if item not in seen:
            uniq.append(item)
            seen.add(item)
    return uniq


def _normalize_judgement(parsed: dict[str, Any]) -> dict[str, Any]:
    result = dict(_DEFAULT_RESULT)

    risk_flags = [
        flag for flag in _normalize_risk_flags(parsed.get("risk_flags", []))
        if flag in _ALLOWED_RISK_FLAGS
    ]

    result.update(
        {
            "match": bool(parsed.get("match")),
            "reason": str(parsed.get("reason", "")).strip() or _DEFAULT_RESULT["reason"],
            "mockability_score": _coerce_score(
                parsed.get("mockability_score"), low=0.0, high=5.0, default=0.0
            ),
            "determinism_score": _coerce_score(
                parsed.get("determinism_score"), low=0.0, high=5.0, default=0.0
            ),
            "schema_clarity_score": _coerce_score(
                parsed.get("schema_clarity_score"), low=0.0, high=5.0, default=0.0
            ),
            "state_complexity_score": _coerce_score(
                parsed.get("state_complexity_score"), low=0.0, high=5.0, default=5.0
            ),
            "multi_turn_fitness_score": _coerce_score(
                parsed.get("multi_turn_fitness_score"),
                low=0.0,
                high=5.0,
                default=0.0,
            ),
            "expected_data_yield_score": _coerce_score(
                parsed.get("expected_data_yield_score"),
                low=0.0,
                high=5.0,
                default=0.0,
            ),
            "risk_flags": risk_flags,
        }
    )

    if not result["match"]:
        result["mockability_score"] = min(result["mockability_score"], 2.0)
        result["schema_clarity_score"] = min(result["schema_clarity_score"], 2.0)
        result["expected_data_yield_score"] = min(
            result["expected_data_yield_score"], 2.0
        )

    return result


def _extract_json_candidate(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("空回复")

    fenced_start = text.find("```")
    if fenced_start != -1:
        fenced_end = text.rfind("```")
        if fenced_end > fenced_start:
            fenced_body = text[fenced_start + 3 : fenced_end].strip()
            if fenced_body.lower().startswith("json"):
                fenced_body = fenced_body[4:].strip()
            text = fenced_body

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


def _judge_one_rich(
    client: OpenAI,
    model: str,
    system_content: str,
    user_content: str,
    *,
    temperature: float = 0,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    richer JSON schema 的单次判定。
    不依赖 llm.judge_one，避免受旧 schema 限制。
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )
        text = (resp.choices[0].message.content or "").strip()
        if verbose:
            logger.info("[test] 大模型完整回复:\n{}", text)

        parsed = _extract_json_candidate(text)
        if not isinstance(parsed, dict):
            return dict(_DEFAULT_RESULT)

        return _normalize_judgement(parsed)

    except Exception as e:
        logger.warning("LLM 调用异常: {}", e)
        out = dict(_DEFAULT_RESULT)
        out["reason"] = f"调用异常: {e}"
        return out


def _build_record(skill_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "dir_name": skill_dir.name,
        "skill_name": skills.skill_name_from_dirname(skill_dir.name),
        **result,
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in records:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _write_summary(path: Path, records: list[dict[str, Any]]) -> None:
    kept = [r for r in records if r.get("match")]
    summary = {
        "total": len(records),
        "matched": len(kept),
        "unmatched": len(records) - len(kept),
        "avg_mockability_score": (
            round(
                sum(float(r.get("mockability_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_determinism_score": (
            round(
                sum(float(r.get("determinism_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_schema_clarity_score": (
            round(
                sum(float(r.get("schema_clarity_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_state_complexity_score": (
            round(
                sum(float(r.get("state_complexity_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_multi_turn_fitness_score": (
            round(
                sum(float(r.get("multi_turn_fitness_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_expected_data_yield_score": (
            round(
                sum(float(r.get("expected_data_yield_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cfg: DictConfig) -> int:
    """实际执行逻辑。"""
    skills_dir = Path(cfg.skills_dir)
    raw_prompts = cfg.get("prompts_dir")
    data_dir = prompts.DATA_DIR if not raw_prompts else Path(raw_prompts)
    mode_raw = str(cfg.get("mode", "")).strip()

    try:
        mode = _parse_mode(mode_raw)
    except ValueError as e:
        logger.error("{}", e)
        return 2

    concurrency = int(cfg.get("concurrency", 5))
    cache_path = cfg.get("filter_result_cache")
    summary_path = cfg.get("filter_result_summary")

    base = Path(get_original_cwd())
    if not skills_dir.is_absolute():
        skills_dir = (base / skills_dir).resolve()
    if data_dir != prompts.DATA_DIR and not data_dir.is_absolute():
        data_dir = (base / data_dir).resolve()

    logger.info("skills_dir: {}", skills_dir)
    logger.info("prompts_dir: {}", data_dir)
    logger.info("mode: {} (raw={})", mode, mode_raw)

    try:
        system_tpl, user_tpl = prompts.load_prompt_templates(data_dir)
    except FileNotFoundError as e:
        logger.error("{}", e)
        return 1

    system_content = system_tpl

    skill_dirs = skills.list_skill_dirs(skills_dir)
    if not skill_dirs:
        logger.info("skills 目录下无子目录")
        return 0

    logger.info("共 {} 个 skill 目录待判定", len(skill_dirs))

    is_test_run = mode == "test"
    if is_test_run:
        n_test = min(3, len(skill_dirs))
        skill_dirs = random.sample(skill_dirs, n_test)
        logger.info(
            "[test] 随机抽取 {} 个 skill 验证流程: {}",
            n_test,
            [p.name for p in skill_dirs],
        )

    cache_file: Path | None = None
    if cache_path:
        cache_file = Path(cache_path)
        if not cache_file.is_absolute():
            cache_file = (base / cache_file).resolve()
    else:
        output_dir = HydraConfig.get().runtime.output_dir
        if output_dir:
            cache_file = Path(output_dir) / "executability_filter_result.jsonl"

    summary_file: Path | None = None
    if summary_path:
        summary_file = Path(summary_path)
        if not summary_file.is_absolute():
            summary_file = (base / summary_file).resolve()
    else:
        output_dir = HydraConfig.get().runtime.output_dir
        if output_dir:
            summary_file = Path(output_dir) / "executability_filter_summary.json"

    done: dict[str, dict[str, Any]] = {}
    if cache_file and cache_file.exists():
        try:
            with cache_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    dir_name = str(obj.get("dir_name", "")).strip()
                    if not dir_name:
                        continue
                    done[dir_name] = {
                        "match": bool(obj.get("match")),
                        "reason": str(obj.get("reason", "")).strip(),
                        "mockability_score": _coerce_score(
                            obj.get("mockability_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "determinism_score": _coerce_score(
                            obj.get("determinism_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "schema_clarity_score": _coerce_score(
                            obj.get("schema_clarity_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "state_complexity_score": _coerce_score(
                            obj.get("state_complexity_score"),
                            low=0.0,
                            high=5.0,
                            default=5.0,
                        ),
                        "multi_turn_fitness_score": _coerce_score(
                            obj.get("multi_turn_fitness_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "expected_data_yield_score": _coerce_score(
                            obj.get("expected_data_yield_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "risk_flags": [
                            flag
                            for flag in _normalize_risk_flags(obj.get("risk_flags", []))
                            if flag in _ALLOWED_RISK_FLAGS
                        ],
                    }
            if done:
                logger.info("已加载缓存 {} 条结果", len(done))
        except Exception as e:
            logger.warning("读取缓存失败，忽略已有缓存: {}", e)

    if mode == "dry-run":
        logger.info(
            "[dry-run] 将判定 {} 个 skill，不调用 API（可设置 mode=run 实际调用）",
            len(skill_dirs),
        )
        for p in skill_dirs[:3]:
            logger.info(
                "[dry-run] 示例 skill: {} -> 内容长度 {}",
                p.name,
                len(skills.read_skill_content(p)),
            )
        return 0

    client, model = llm.load_env_and_client(base)
    sem = threading.Semaphore(concurrency)
    results: list[tuple[Path, dict[str, Any]]] = []
    lock = threading.Lock()

    def process_one(skill_dir: Path) -> None:
        dir_name = skill_dir.name

        if dir_name in done:
            with lock:
                results.append((skill_dir, done[dir_name]))
            return

        content = skills.read_skill_content(skill_dir)
        user_content = user_tpl.replace("{{skill_dir_name}}", skill_dir.name)
        user_content = user_content.replace("{{skill_content}}", content)

        with sem:
            out = dict(_DEFAULT_RESULT)
            for attempt in range(3):
                out = _judge_one_rich(
                    client,
                    model,
                    system_content,
                    user_content,
                    verbose=is_test_run,
                )
                if out.get("reason") and "调用异常" not in str(out.get("reason", "")):
                    break
                time.sleep(2**attempt)

            with lock:
                results.append((skill_dir, out))
                done[dir_name] = out

    threads = [threading.Thread(target=process_one, args=(d,)) for d in skill_dirs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    records = [_build_record(skill_dir, result) for skill_dir, result in results]
    records.sort(key=lambda x: x["dir_name"])

    if cache_file:
        _write_jsonl(cache_file, records)
        logger.info("已写入 executability filter 结果: {}", cache_file)

    if summary_file:
        _write_summary(summary_file, records)
        logger.info("已写入 executability filter 汇总: {}", summary_file)

    kept = [r for r in records if r.get("match")]
    logger.info("匹配 {} / {} 个 skill（本版本不执行目录删除）", len(kept), len(records))

    top_records = sorted(
        kept,
        key=lambda x: (
            float(x.get("mockability_score", 0.0)),
            float(x.get("schema_clarity_score", 0.0)),
            float(x.get("expected_data_yield_score", 0.0)),
            float(x.get("determinism_score", 0.0)),
            -float(x.get("state_complexity_score", 5.0)),
        ),
        reverse=True,
    )[:10]

    if top_records:
        logger.info("Top executable/mockable skills:")
        for idx, record in enumerate(top_records, 1):
            logger.info(
                "[{}] {} | mockability={:.2f} | schema={:.2f} | yield={:.2f} | determinism={:.2f} | state_complexity={:.2f}",
                idx,
                record["dir_name"],
                float(record.get("mockability_score", 0.0)),
                float(record.get("schema_clarity_score", 0.0)),
                float(record.get("expected_data_yield_score", 0.0)),
                float(record.get("determinism_score", 0.0)),
                float(record.get("state_complexity_score", 0.0)),
            )

    return 0
