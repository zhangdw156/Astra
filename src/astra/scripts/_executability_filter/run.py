"""按可执行性（docker-only + 可 mock）过滤 skills 的主流程。"""

import json
import random
import re
import shutil
import threading
import time
from pathlib import Path

from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig

from astra.scripts._executability_filter import prompts
from astra.scripts._domain_filter import llm
from astra.scripts._domain_filter import skills as skills_module


_URL_RE = re.compile(r"https?://[^\s)\"']+")

_ALLOWED_MODES = {"run", "test", "dry-run"}


def _parse_mode(raw: str) -> str:
    raw = (raw or "").strip().lower()
    if raw not in _ALLOWED_MODES:
        raise ValueError(
            f"mode 只允许取 {sorted(_ALLOWED_MODES)}，当前为: {raw!r}。"
            "注意 dry-run 必须使用中划线（不是 dry_run）。"
        )
    return raw


def _read_text_preview(path: Path, max_chars: int) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(无法读取脚本内容)"
    raw = raw.strip()
    if len(raw) > max_chars:
        return raw[:max_chars] + "\n\n[... 脚本内容已截断 ...]"
    return raw


def _summarize_scripts(skill_dir: Path, max_files: int, max_chars_per_file: int) -> str:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return "(无 scripts/ 目录)"

    files = sorted([p for p in scripts_dir.rglob("*") if p.is_file() and not p.name.startswith(".")])
    if not files:
        return "(scripts/ 为空)"

    picked = files[:max_files]
    lines: list[str] = []
    lines.append(f"scripts 文件数: {len(files)}（展示前 {len(picked)} 个）")

    urls: list[str] = []
    for f in picked:
        rel = f.relative_to(skill_dir)
        preview = _read_text_preview(f, max_chars=max_chars_per_file)
        urls.extend(_URL_RE.findall(preview))
        lines.extend(
            [
                "",
                f"--- {rel} ---",
                preview,
            ]
        )

    if urls:
        uniq = sorted(set(urls))[:50]
        lines.extend(["", "提取到的 URL（截断前 50 个）:", *[f"- {u}" for u in uniq]])

    return "\n".join(lines).strip()


def _build_skill_content_for_llm(skill_dir: Path, scripts_max_files: int, scripts_max_chars: int) -> str:
    base = skills_module.read_skill_content(skill_dir)
    scripts_summary = _summarize_scripts(
        skill_dir,
        max_files=scripts_max_files,
        max_chars_per_file=scripts_max_chars,
    )
    return f"{base}\n\n--- scripts 概要 ---\n\n{scripts_summary}\n"


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
    scripts_max_files = int(cfg.get("scripts_max_files", 3))
    scripts_max_chars = int(cfg.get("scripts_max_chars", 8_000))
    sample_n = int(cfg.get("sample_n", 3))

    base = Path(get_original_cwd())
    if not skills_dir.is_absolute():
        skills_dir = (base / skills_dir).resolve()
    if data_dir != prompts.DATA_DIR and not data_dir.is_absolute():
        data_dir = (base / data_dir).resolve()

    logger.info("skills_dir: {}", skills_dir)
    logger.info("prompts_dir: {}", data_dir)
    logger.info("mode: {} (raw={})", mode, mode_raw)
    logger.info("concurrency: {}", concurrency)
    logger.info("scripts_max_files: {}", scripts_max_files)
    logger.info("scripts_max_chars: {}", scripts_max_chars)
    logger.info("sample_n: {}", sample_n)

    try:
        system_tpl, user_tpl = prompts.load_prompt_templates(data_dir)
    except FileNotFoundError as e:
        logger.error("{}", e)
        return 1

    skill_dirs = skills_module.list_skill_dirs(skills_dir)
    if not skill_dirs:
        logger.info("skills 目录下无子目录")
        return 0

    logger.info("共 {} 个 skill 目录待判定", len(skill_dirs))

    if mode == "dry-run":
        logger.info("[dry-run] 不调用任何外部 API，不修改任何目录，仅打印示例。")
        sample_n = max(sample_n, 0)
        for p in skill_dirs[:sample_n]:
            sample = _build_skill_content_for_llm(p, scripts_max_files, min(1200, scripts_max_chars))
            logger.info("[dry-run] 示例 skill: {} -> 内容长度 {}", p.name, len(sample))
        return 0

    is_test_run = mode == "test"
    if is_test_run:
        n_test = int(cfg.get("n_test", 5))
        n_test = min(max(n_test, 1), len(skill_dirs))
        skill_dirs = random.sample(skill_dirs, n_test)
        logger.info("[test] 随机抽取 {} 个 skill 验证流程: {}", n_test, [p.name for p in skill_dirs])

    cache_file: Path | None = None
    if cache_path:
        cache_file = Path(cache_path)
        if not cache_file.is_absolute():
            cache_file = (base / cache_file).resolve()
    else:
        output_dir = HydraConfig.get().runtime.output_dir
        if output_dir:
            cache_file = Path(output_dir) / "filter_executability_result.json"

    done: dict[str, dict] = {}
    if cache_file and cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    done[obj["dir_name"]] = {"match": obj["match"], "reason": obj.get("reason", "")}
            if done:
                logger.info("已加载缓存 {} 条结果", len(done))
        except Exception:
            pass

    client, model = llm.load_env_and_client(base)

    sem = threading.Semaphore(concurrency)
    results: list[tuple[Path, dict]] = []
    lock = threading.Lock()

    def process_one(skill_dir: Path) -> None:
        dir_name = skill_dir.name
        if dir_name in done:
            with lock:
                results.append((skill_dir, done[dir_name]))
            return

        content = _build_skill_content_for_llm(skill_dir, scripts_max_files, scripts_max_chars)
        user_content = user_tpl.replace("{{skill_content}}", content)
        with sem:
            for attempt in range(3):
                out = llm.judge_one(client, model, system_tpl, user_content, verbose=is_test_run)
                if out.get("reason") and "调用异常" not in str(out.get("reason", "")):
                    break
                time.sleep(2**attempt)
            with lock:
                results.append((skill_dir, out))
                done[dir_name] = out

        if cache_file:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                line = json.dumps(
                    {"dir_name": dir_name, "match": out["match"], "reason": out.get("reason", "")},
                    ensure_ascii=False,
                ) + "\n"
                with open(cache_file, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass

    threads = [threading.Thread(target=process_one, args=(d,)) for d in skill_dirs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    kept = [p for p, r in results if r.get("match")]
    to_remove = [(p, r) for p, r in results if not r.get("match")]
    logger.info("保留 {} / {} 个 skill，删除 {} 个不保留目录", len(kept), len(results), len(to_remove))

    if is_test_run:
        for p, r in to_remove[:10]:
            logger.info("[test] drop: {} => {}", p.name, r.get("reason", ""))
        for p in kept[:10]:
            logger.info("[test] keep: {}", p.name)
        return 0

    for skill_dir, _r in to_remove:
        try:
            shutil.rmtree(skill_dir)
            logger.debug("已删除: {}", skill_dir)
        except OSError as e:
            logger.warning("删除目录失败 {}: {}", skill_dir, e)

    if to_remove:
        logger.info("已删除 {} 个不保留的 skill 目录", len(to_remove))
    return 0

