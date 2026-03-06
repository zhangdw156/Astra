#!/usr/bin/env python3
"""
基于 artifacts/multi_turn_func_doc 的领域描述，用 OpenAI 判断 skills/ 下各 skill 是否覆盖这些领域，只保留匹配的。

每个 skill 的判定依据：目录名 + 该目录下 SKILL.md 的全部内容（作为 User 提示）；领域摘要来自
multi_turn_func_doc 下各 JSON 的 tool description，放入 System 提示。模型返回固定 JSON：
{"match": true/false, "reason": "一句话"}。

用法：
    uv run -m astra.scripts.filter_skills_by_domain
    uv run -m astra.scripts.filter_skills_by_domain mode=run
    uv run -m astra.scripts.filter_skills_by_domain mode=test   # 仅处理 1 个 skill，验证流程
    uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery --config-name=filter_by_domain mode=run

需在项目根目录 .env 中配置：OPENAI_API_KEY、OPENAI_MODEL，可选 OPENAI_BASE_URL。
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig
from openai import OpenAI

from astra.utils.logging import setup_logging

# 项目根目录（src/astra/scripts -> 上三级）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# Hydra 默认配置目录与名称
_config_path = str(PROJECT_ROOT / "exps" / "skill_discovery")

# 单条 skill 内容长度上限（字符），超出则截断并注明，避免超 context
MAX_SKILL_CONTENT_CHARS = 80_000


def _build_domain_summary(artifacts_dir: Path) -> str:
    """
    从 artifacts/multi_turn_func_doc 下各 NDJSON 归纳出目标领域摘要文本。
    遍历每个 .json 文件，从文件名及每行 tool 的 description 抽取领域关键词，拼成一段说明。
    """
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        logger.warning("artifacts 目录不存在: {}", artifacts_dir)
        return ""

    domain_parts: list[str] = []
    seen_descriptions: set[str] = set()

    for path in sorted(artifacts_dir.glob("*.json")):
        # 文件名作为领域名（如 travel_booking -> 旅行预订）
        domain_name = path.stem.replace("_", " ").strip()
        if not domain_name:
            continue

        descriptions: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        desc = obj.get("description") or ""
                        if desc and desc not in seen_descriptions:
                            seen_descriptions.add(desc)
                            # 取前一句或前 200 字符作为该 tool 的领域描述
                            first_sentence = desc.split(".")[0].strip() + "." if "." in desc else desc[:200]
                            descriptions.append(first_sentence)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            logger.warning("无法读取文件: {}", path)
            continue

        if descriptions:
            domain_parts.append(f"- **{domain_name}**: {' '.join(descriptions[:3])}")  # 每领域最多 3 条
        else:
            domain_parts.append(f"- **{domain_name}**")

    return "目标领域（任一匹配即保留）：\n" + "\n".join(domain_parts)


def _skill_name_from_dirname(dirname: str) -> str:
    """从目录名去掉前缀序号，如 1_filehost -> filehost。"""
    return re.sub(r"^\d+_", "", dirname).strip() or dirname


def _read_skill_content(skill_dir: Path) -> str:
    """
    读取 skill 目录的 name + SKILL.md 全部内容。
    若不存在 SKILL.md，仅返回目录名（name）；若 SKILL.md 过长则截断并注明。
    """
    name = _skill_name_from_dirname(skill_dir.name)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return f"Skill name: {name}\n(无 SKILL.md，仅以目录名判断)\n"

    try:
        raw = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"Skill name: {name}\n(无法读取 SKILL.md)\n"

    if len(raw) > MAX_SKILL_CONTENT_CHARS:
        raw = raw[:MAX_SKILL_CONTENT_CHARS] + "\n\n[... 内容已截断，超过长度上限 ...]"

    return f"Skill name: {name}\n\n--- SKILL.md 内容 ---\n\n{raw}"


def _load_env_and_client():
    """从项目根 .env 加载环境变量并创建 OpenAI 客户端。缺必填项时抛出 SystemExit。"""
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None

    if not api_key or not model:
        logger.error(
            "请在项目根目录 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL；可选 OPENAI_BASE_URL。"
        )
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    return client, model


def _judge_one(
    client: OpenAI,
    model: str,
    domain_summary: str,
    skill_content: str,
    temperature: float = 0,
) -> dict:
    """
    单次 LLM 判定：该 skill 是否覆盖领域摘要中的任一领域。
    返回解析后的 {"match": bool, "reason": str}，解析失败时 match=False。
    """
    system = (
        "你是一个判断助手。任务：判断下面给出的 Skill 是否属于或可覆盖「目标领域」中的任一领域。"
        "若该 Skill 的能力与任一目标领域相关（可直接支持或间接支持该领域的工具/场景），则 match 为 true，否则为 false。"
        "只输出一个 JSON 对象，不要其他文字。格式严格为：{\"match\": true 或 false, \"reason\": \"一句话原因\"}\n\n"
        + domain_summary
    )
    user = "请判断以下 Skill 是否覆盖上述任一目标领域：\n\n" + skill_content

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        text = (resp.choices[0].message.content or "").strip()
        # 尝试从返回中提取 JSON
        for raw in (text, text.split("\n")[0], text[text.find("{") : text.rfind("}") + 1]):
            if not raw or "{" not in raw:
                continue
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                return {
                    "match": bool(parsed.get("match")),
                    "reason": str(parsed.get("reason", "")).strip() or "(无)",
                }
        return {"match": False, "reason": "无法解析模型返回为 JSON"}
    except Exception as e:
        logger.warning("LLM 调用异常: {}", e)
        return {"match": False, "reason": f"调用异常: {e}"}


def _list_skill_dirs(skills_root: Path) -> list[Path]:
    """列出 skills 根目录下所有子目录（视为 skill 目录），排除非目录与 README 等。"""
    skills_root = skills_root.resolve()
    if not skills_root.is_dir():
        return []
    return [p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith(".")]


def run(cfg: DictConfig) -> int:
    """实际执行逻辑。"""
    skills_dir = Path(cfg.skills_dir)
    artifacts_func_doc_dir = Path(cfg.artifacts_func_doc_dir)
    mode = str(cfg.mode).lower()
    concurrency = int(cfg.get("concurrency", 5))
    cache_path = cfg.get("filter_result_cache")

    base = Path(get_original_cwd())
    if not skills_dir.is_absolute():
        skills_dir = (base / skills_dir).resolve()
    if not artifacts_func_doc_dir.is_absolute():
        artifacts_func_doc_dir = (base / artifacts_func_doc_dir).resolve()

    logger.info("skills_dir: {}", skills_dir)
    logger.info("artifacts_func_doc_dir: {}", artifacts_func_doc_dir)
    logger.info("mode: {}", mode)

    domain_summary = _build_domain_summary(artifacts_func_doc_dir)
    if not domain_summary.strip():
        logger.error("领域摘要为空，请检查 artifacts 目录")
        return 1

    skill_dirs = _list_skill_dirs(skills_dir)
    if not skill_dirs:
        logger.info("skills 目录下无子目录")
        return 0

    logger.info("共 {} 个 skill 目录待判定", len(skill_dirs))

    # test 模式：只处理第一个 skill，验证端到端流程
    if mode == "test":
        skill_dirs = skill_dirs[:1]
        logger.info("[test] 仅处理 1 个 skill 以验证流程: {}", skill_dirs[0].name if skill_dirs else "(无)")
        if not skill_dirs:
            return 0
        mode = "run"  # 后续按 run 走 LLM 调用与写结果

    # 可选：从缓存加载已有结果，支持断点续跑
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
            done = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info("已加载缓存 {} 条结果", len(done))
        except Exception:
            pass

    if mode == "dry_run":
        logger.info("[dry_run] 将判定 {} 个 skill，不调用 API（可设置 mode=run 实际调用）", len(skill_dirs))
        # dry_run 下仍可打印领域摘要与若干 skill 内容样例
        logger.debug("领域摘要预览: {} ...", domain_summary[:500])
        for p in skill_dirs[:3]:
            logger.info("[dry_run] 示例 skill: {} -> 内容长度 {}", p.name, len(_read_skill_content(p)))
        return 0

    client, model = _load_env_and_client()
    import threading

    sem = threading.Semaphore(concurrency)
    results: list[tuple[Path, dict]] = []
    lock = threading.Lock()

    def process_one(skill_dir: Path) -> None:
        dir_name = skill_dir.name
        if dir_name in done:
            with lock:
                results.append((skill_dir, done[dir_name]))
            return
        content = _read_skill_content(skill_dir)
        with sem:
            for attempt in range(3):
                out = _judge_one(client, model, domain_summary, content)
                if out.get("reason") and "调用异常" not in str(out.get("reason", "")):
                    break
                time.sleep(2 ** attempt)
            with lock:
                results.append((skill_dir, out))
                done[dir_name] = out
        if cache_file:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

    threads = [threading.Thread(target=process_one, args=(d,)) for d in skill_dirs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    kept = [p for p, r in results if r.get("match")]
    logger.info("保留 {} / {} 个 skill", len(kept), len(results))

    out_dir = Path(HydraConfig.get().runtime.output_dir) if HydraConfig.get().runtime.output_dir else skills_dir
    out_dir = out_dir.resolve()
    list_path = out_dir / "skills_kept.txt"
    out_dir.mkdir(parents=True, exist_ok=True)
    list_path.write_text("\n".join(p.name for p in kept) + "\n", encoding="utf-8")
    logger.info("保留列表已写入: {}", list_path)

    return 0


@hydra.main(
    config_path=_config_path,
    config_name="filter_by_domain",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    output_dir = HydraConfig.get().runtime.output_dir
    setup_logging(output_dir)
    sys.exit(run(cfg))


if __name__ == "__main__":
    main()
