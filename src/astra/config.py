"""
Astra 项目配置模块：提供统一的项目根路径和环境变量加载。

所有依赖 .env 的脚本应使用此模块获取配置，而不是自行计算路径。
"""

import os
from pathlib import Path
from typing import Optional

# 项目根目录：通过当前文件位置推断
# src/astra/config.py -> src/astra/ -> src/ -> 项目根
_PROJECT_ROOT: Optional[Path] = None


def get_project_root() -> Path:
    """获取项目根目录（缓存结果）。"""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    return _PROJECT_ROOT


def get_env_path() -> Path:
    """获取 .env 文件路径。"""
    return get_project_root() / ".env"


def load_env() -> None:
    """从项目根 .env 加载环境变量。"""
    from dotenv import load_dotenv
    load_dotenv(get_env_path())


def get_openai_api_key() -> str:
    """获取 OpenAI API Key。"""
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("OPENAI_API_KEY 未在 .env 中配置")
    return key


def get_openai_model() -> str:
    """获取 OpenAI 模型名称。"""
    load_env()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not model:
        raise EnvironmentError("OPENAI_MODEL 未在 .env 中配置")
    return model


def get_openai_base_url() -> Optional[str]:
    """获取 OpenAI Base URL（可选）。"""
    load_env()
    url = os.environ.get("OPENAI_BASE_URL", "").strip()
    return url or None


def get_llm_config() -> dict:
    """
    获取完整的 LLM 配置字典。
    适用于 qwen-agent 或 OpenAI 客户端。
    """
    load_env()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None

    if not api_key or not model:
        raise EnvironmentError(
            "请在项目根 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL；可选 OPENAI_BASE_URL。"
        )

    return {
        "model": model,
        "model_type": "oai",
        "model_server": base_url or "https://api.openai.com/v1",
        "api_key": api_key,
    }