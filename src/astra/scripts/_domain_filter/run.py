"""按领域过滤 skills 的主流程（优化版）。

升级目标：
1. run 模式下对不匹配的 skill 直接删除对应目录
2. 让 domain filter 输出 richer schema，而不只是 match/reason
3. 产出 jsonl 结果，便于后续与 executability filter 合并成 manifest
"""

from __future__ import annotations

import json
import random
import re
import shutil
import threading
import time
from ast import literal_eval
from collections import Counter
from pathlib import Path
from typing import Any

from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig
from openai import OpenAI

from astra.scripts._domain_filter import domain as domain_module
from astra.scripts._domain_filter import llm
from astra.scripts._domain_filter import prompts
from astra.scripts._domain_filter import skills

_ALLOWED_MODES = {"run", "test", "dry-run"}

_DEFAULT_RESULT = {
    "match": False,
    "reason": "无法解析模型返回",
    "matched_domains": [],
    "primary_domain": "",
    "bfcl_relevance_score": 0.0,
    "domain_confidence": 0.0,
    "tool_call_intensity_score": 0.0,
    "multi_turn_potential_score": 0.0,
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


def _normalize_domains(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = item.strip()
            if s:
                out.append(s)
    # 保持顺序去重
    seen: set[str] = set()
    uniq: list[str] = []
    for item in out:
        if item not in seen:
            uniq.append(item)
            seen.add(item)
    return uniq


def _normalize_judgement(parsed: dict[str, Any]) -> dict[str, Any]:
    result = dict(_DEFAULT_RESULT)

    match = bool(parsed.get("match"))
    matched_domains = _normalize_domains(parsed.get("matched_domains"))
    primary_domain = str(parsed.get("primary_domain", "")).strip()

    if primary_domain and primary_domain not in matched_domains:
        matched_domains = [primary_domain, *matched_domains]

    if not primary_domain and matched_domains:
        primary_domain = matched_domains[0]

    result.update(
        {
            "match": match,
            "reason": str(parsed.get("reason", "")).strip() or _DEFAULT_RESULT["reason"],
            "matched_domains": matched_domains,
            "primary_domain": primary_domain,
            "bfcl_relevance_score": _coerce_score(
                parsed.get("bfcl_relevance_score"),
                low=0.0,
                high=5.0,
                default=0.0,
            ),
            "domain_confidence": _coerce_score(
                parsed.get("domain_confidence"),
                low=0.0,
                high=1.0,
                default=0.0,
            ),
            "tool_call_intensity_score": _coerce_score(
                parsed.get("tool_call_intensity_score"),
                low=0.0,
                high=5.0,
                default=0.0,
            ),
            "multi_turn_potential_score": _coerce_score(
                parsed.get("multi_turn_potential_score"),
                low=0.0,
                high=5.0,
                default=0.0,
            ),
        }
    )

    # 一致性收紧：若 match=False，则不要保留看起来高得离谱的分数
    if not result["match"]:
        result["bfcl_relevance_score"] = min(result["bfcl_relevance_score"], 2.0)
        result["tool_call_intensity_score"] = min(
            result["tool_call_intensity_score"], 2.0
        )
        result["multi_turn_potential_score"] = min(
            result["multi_turn_potential_score"], 2.0
        )

    return result


def _extract_json_candidate(text: str) -> dict[str, Any]:
    def _find_matching_brace(s: str, start: int) -> int:
        depth = 0
        in_string = False
        quote = ""
        escape = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    in_string = False
                continue
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    text = (text or "").strip()
    if not text:
        raise ValueError("空回复")

    candidates: list[str] = [text]

    fenced_start = text.find("```")
    if fenced_start != -1:
        fenced_end = text.rfind("```")
        if fenced_end > fenced_start:
            fenced_body = text[fenced_start + 3 : fenced_end].strip()
            if fenced_body.lower().startswith("json"):
                fenced_body = fenced_body[4:].strip()
            if fenced_body:
                candidates.append(fenced_body)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    # 模型可能先输出思考过程，再在尾部给出目标 JSON；优先抽取以 match 开头的对象。
    for m in re.finditer(r"\{\s*(['\"])match\1\s*:", text):
        start_idx = m.start()
        end_idx = _find_matching_brace(text, start_idx)
        if end_idx > start_idx:
            candidates.append(text[start_idx : end_idx + 1])

    seen: set[str] = set()
    for raw in candidates:
        s = raw.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 兼容部分模型输出 Python 字典风格（单引号）而非严格 JSON。
        try:
            parsed = literal_eval(s)
            if isinstance(parsed, dict):
                return parsed
        except (SyntaxError, ValueError):
            pass

    raise ValueError("无法从模型回复中提取 JSON 对象")


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


def _append_one_jsonl(path: Path, record: dict[str, Any]) -> None:
    """追加单条结果到 jsonl，用于运行中持久化，防止中途失败丢失已算结果。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_summary(path: Path, records: list[dict[str, Any]]) -> None:
    primary_counter = Counter()
    matched_domain_counter = Counter()

    for record in records:
        primary = record.get("primary_domain", "")
        if primary:
            primary_counter[primary] += 1
        for d in record.get("matched_domains", []):
            matched_domain_counter[d] += 1

    kept = [r for r in records if r.get("match")]
    summary = {
        "total": len(records),
        "matched": len(kept),
        "unmatched": len(records) - len(kept),
        "top_primary_domains": primary_counter.most_common(20),
        "top_matched_domains": matched_domain_counter.most_common(20),
        "avg_bfcl_relevance_score": (
            round(
                sum(float(r.get("bfcl_relevance_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_tool_call_intensity_score": (
            round(
                sum(float(r.get("tool_call_intensity_score", 0.0)) for r in records)
                / len(records),
                4,
            )
            if records
            else 0.0
        ),
        "avg_multi_turn_potential_score": (
            round(
                sum(float(r.get("multi_turn_potential_score", 0.0)) for r in records)
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

    domain_summary = domain_module.get_domain_summary(data_dir)
    if not domain_summary.strip():
        logger.error("领域摘要为空，请检查 prompts_dir/data 内容")
        return 1

    try:
        system_tpl, user_tpl = prompts.load_prompt_templates(data_dir)
    except FileNotFoundError as e:
        logger.error("{}", e)
        return 1

    system_content = system_tpl.replace("{{domain_summary}}", domain_summary)

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
            cache_file = Path(output_dir) / "domain_filter_result.jsonl"

    summary_file: Path | None = None
    if summary_path:
        summary_file = Path(summary_path)
        if not summary_file.is_absolute():
            summary_file = (base / summary_path).resolve()
    else:
        output_dir = HydraConfig.get().runtime.output_dir
        if output_dir:
            summary_file = Path(output_dir) / "domain_filter_summary.json"

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
                        "matched_domains": _normalize_domains(
                            obj.get("matched_domains", [])
                        ),
                        "primary_domain": str(obj.get("primary_domain", "")).strip(),
                        "bfcl_relevance_score": _coerce_score(
                            obj.get("bfcl_relevance_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "domain_confidence": _coerce_score(
                            obj.get("domain_confidence"),
                            low=0.0,
                            high=1.0,
                            default=0.0,
                        ),
                        "tool_call_intensity_score": _coerce_score(
                            obj.get("tool_call_intensity_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
                        "multi_turn_potential_score": _coerce_score(
                            obj.get("multi_turn_potential_score"),
                            low=0.0,
                            high=5.0,
                            default=0.0,
                        ),
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
        logger.debug("领域摘要预览: {} ...", domain_summary[:500])
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
    file_write_lock = threading.Lock()

    def process_one(skill_dir: Path) -> None:
        dir_name = skill_dir.name

        if dir_name in done:
            with lock:
                results.append((skill_dir, done[dir_name]))
            return

        content = skills.read_skill_content(skill_dir)
        scripts_summary = skills.summarize_scripts(skill_dir)
        user_content = (
            user_tpl.replace("{{domain_summary}}", domain_summary)
            .replace("{DOMAIN_SUMMARY}", domain_summary)
            .replace("{{dir_name}}", dir_name)
            .replace("{DIR_NAME}", dir_name)
            .replace("{{skill_content}}", content)
            .replace("{SKILL_CONTENT}", content)
            .replace("{{scripts_summary}}", scripts_summary)
            .replace("{SCRIPTS_SUMMARY}", scripts_summary)
        )

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
            # 每跑完一个 skill 立即追加写入 jsonl，防止中途失败丢失已算结果
            if cache_file:
                with file_write_lock:
                    _append_one_jsonl(cache_file, _build_record(skill_dir, out))

    threads = [threading.Thread(target=process_one, args=(d,)) for d in skill_dirs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    records = [_build_record(skill_dir, result) for skill_dir, result in results]
    records.sort(key=lambda x: x["dir_name"])

    if cache_file:
        _write_jsonl(cache_file, records)
        logger.info("已写入 domain filter 结果: {}", cache_file)

    if summary_file:
        _write_summary(summary_file, records)
        logger.info("已写入 domain filter 汇总: {}", summary_file)

    kept = [r for r in records if r.get("match")]
    # run 模式下删除不匹配的 skill 目录
    if mode == "run":
        unmatched_dirs = [skill_dir for skill_dir, result in results if not result.get("match")]
        for path in unmatched_dirs:
            try:
                shutil.rmtree(path)
                logger.info("已删除不匹配目录: {}", path)
            except Exception as e:
                logger.warning("删除目录失败 {}: {}", path, e)
        logger.info("匹配 {} / {} 个 skill，已删除 {} 个不匹配目录", len(kept), len(records), len(unmatched_dirs))
    else:
        logger.info("匹配 {} / {} 个 skill（当前为 {} 模式，未删除目录）", len(kept), len(records), mode)

    top_records = sorted(
        kept,
        key=lambda x: (
            float(x.get("bfcl_relevance_score", 0.0)),
            float(x.get("tool_call_intensity_score", 0.0)),
            float(x.get("multi_turn_potential_score", 0.0)),
            float(x.get("domain_confidence", 0.0)),
        ),
        reverse=True,
    )[:10]

    if top_records:
        logger.info("Top matched skills (按 BFCL/domain 相关性排序):")
        for idx, record in enumerate(top_records, 1):
            logger.info(
                "[{}] {} | primary_domain={} | relevance={:.2f} | tool_call={:.2f} | multi_turn={:.2f}",
                idx,
                record["dir_name"],
                record.get("primary_domain", ""),
                float(record.get("bfcl_relevance_score", 0.0)),
                float(record.get("tool_call_intensity_score", 0.0)),
                float(record.get("multi_turn_potential_score", 0.0)),
            )

    return 0
