"""OpenAI 客户端与单次判定。"""

import json
import os
import sys
from pathlib import Path

from loguru import logger
from openai import OpenAI


def load_env_and_client(project_root: Path) -> tuple[OpenAI, str]:
    """从项目根 .env 加载环境变量并创建 OpenAI 客户端。缺必填项时抛出 SystemExit。"""
    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")
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


def judge_one(
    client: OpenAI,
    model: str,
    system_content: str,
    user_content: str,
    temperature: float = 0,
    verbose: bool = False,
) -> dict:
    """
    单次 LLM 判定：使用已填充占位符的系统提示与用户提示调用模型。
    返回解析后的 {"match": bool, "reason": str}，解析失败时 match=False。
    verbose 为 True 时（如 test 模式）会打印大模型完整回复。
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
