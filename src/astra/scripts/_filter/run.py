"""按领域过滤 skills 的主流程。"""

import json
import random
import shutil
import threading
import time
from pathlib import Path

from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig

from astra.scripts._filter import domain as domain_module
from astra.scripts._filter import llm
from astra.scripts._filter import prompts
from astra.scripts._filter import skills


def run(cfg: DictConfig) -> int:
    """实际执行逻辑。"""
    skills_dir = Path(cfg.skills_dir)
    raw_prompts = cfg.get("prompts_dir")
    data_dir = prompts.DATA_DIR if not raw_prompts else Path(raw_prompts)
    mode = str(cfg.mode).lower()
    concurrency = int(cfg.get("concurrency", 5))
    cache_path = cfg.get("filter_result_cache")

    base = Path(get_original_cwd())
    if not skills_dir.is_absolute():
        skills_dir = (base / skills_dir).resolve()
    if data_dir != prompts.DATA_DIR and not data_dir.is_absolute():
        data_dir = (base / data_dir).resolve()

    logger.info("skills_dir: {}", skills_dir)
    logger.info("prompts_dir: {}", data_dir)
    logger.info("mode: {}", mode)

    domain_summary = domain_module.get_domain_summary(data_dir)
    if not domain_summary.strip():
        logger.error("领域摘要为空，请检查 artifacts 目录")
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
    if mode == "test":
        n_test = min(3, len(skill_dirs))
        skill_dirs = random.sample(skill_dirs, n_test)
        logger.info("[test] 随机抽取 {} 个 skill 验证流程: {}", n_test, [p.name for p in skill_dirs])
        if not skill_dirs:
            return 0
        mode = "run"

    cache_file: Path | None = None
    if cache_path:
        cache_file = Path(cache_path)
        if not cache_file.is_absolute():
            cache_file = (base / cache_file).resolve()
    else:
        output_dir = HydraConfig.get().runtime.output_dir
        if output_dir:
            cache_file = Path(output_dir) / "filter_result.json"

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

    if mode == "dry_run":
        logger.info("[dry_run] 将判定 {} 个 skill，不调用 API（可设置 mode=run 实际调用）", len(skill_dirs))
        logger.debug("领域摘要预览: {} ...", domain_summary[:500])
        for p in skill_dirs[:3]:
            logger.info("[dry_run] 示例 skill: {} -> 内容长度 {}", p.name, len(skills.read_skill_content(p)))
        return 0

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
        content = skills.read_skill_content(skill_dir)
        user_content = user_tpl.replace("{{skill_content}}", content)
        with sem:
            for attempt in range(3):
                out = llm.judge_one(client, model, system_content, user_content, verbose=is_test_run)
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
    to_remove = [p for p, r in results if not r.get("match")]
    logger.info("保留 {} / {} 个 skill，删除 {} 个不匹配目录", len(kept), len(results), len(to_remove))

    for skill_dir in to_remove:
        try:
            shutil.rmtree(skill_dir)
            logger.debug("已删除: {}", skill_dir)
        except OSError as e:
            logger.warning("删除目录失败 {}: {}", skill_dir, e)
    if to_remove:
        logger.info("已删除 {} 个不保留的 skill 目录", len(to_remove))

    return 0
