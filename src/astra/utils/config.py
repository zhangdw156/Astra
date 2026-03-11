"""
配置工具：统一的项目根路径与多 Agent 环境变量加载。

五个 Agent（均支持单独配置 API_KEY、MODEL、BASE_URL，未配置时回退到全局 OPENAI_*）：
- planner_agent: PLANNER_*，生成蓝图
- user_agent: USER_AGENT_*，生成用户消息
- assistant_agent: ASSISTANT_*，执行任务
- tool_agent: TOOL_AGENT_*，工具执行（如生成工具回复）
- eval_agent: EVAL_*，评估轨迹
"""

import os
from pathlib import Path
from typing import Optional

# 项目根：src/astra/utils/config.py -> utils -> astra -> src -> 根
_PROJECT_ROOT: Optional[Path] = None


def get_project_root() -> Path:
    """获取项目根目录（缓存）。"""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    return _PROJECT_ROOT


def get_env_path() -> Path:
    """获取 .env 文件路径。"""
    return get_project_root() / ".env"


def load_env() -> None:
    """从项目根 .env 加载环境变量。"""
    from dotenv import load_dotenv
    load_dotenv(get_env_path())


def _get_agent_config(prefix: str) -> dict:
    """按前缀获取 Agent 配置（缺省回退到 OPENAI_*）。"""
    load_env()
    api_key = os.environ.get(f"{prefix}_API_KEY", "").strip()
    model = os.environ.get(f"{prefix}_MODEL", "").strip()
    base_url = os.environ.get(f"{prefix}_BASE_URL", "").strip() or None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not model:
        model = os.environ.get("OPENAI_MODEL", "").strip()
    if base_url is None:
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    return {"api_key": api_key, "model": model, "base_url": base_url}


# ---------- planner_agent ----------

def get_planner_agent_config() -> dict:
    """Planner Agent 配置（生成蓝图）。"""
    return _get_agent_config("PLANNER")


def get_planner_agent_api_key() -> str:
    cfg = get_planner_agent_config()
    if not cfg["api_key"]:
        raise EnvironmentError("PLANNER_API_KEY 或 OPENAI_API_KEY 未在 .env 中配置")
    return cfg["api_key"]


def get_planner_agent_model() -> str:
    cfg = get_planner_agent_config()
    if not cfg["model"]:
        raise EnvironmentError("PLANNER_MODEL 或 OPENAI_MODEL 未在 .env 中配置")
    return cfg["model"]


def get_planner_agent_base_url() -> Optional[str]:
    return get_planner_agent_config()["base_url"]


# ---------- user_agent ----------

def get_user_agent_config() -> dict:
    """User Agent 配置（生成用户消息）。"""
    return _get_agent_config("USER_AGENT")


def get_user_agent_api_key() -> str:
    cfg = get_user_agent_config()
    if not cfg["api_key"]:
        raise EnvironmentError("USER_AGENT_API_KEY 或 OPENAI_API_KEY 未在 .env 中配置")
    return cfg["api_key"]


def get_user_agent_model() -> str:
    cfg = get_user_agent_config()
    if not cfg["model"]:
        raise EnvironmentError("USER_AGENT_MODEL 或 OPENAI_MODEL 未在 .env 中配置")
    return cfg["model"]


def get_user_agent_base_url() -> Optional[str]:
    return get_user_agent_config()["base_url"]


# ---------- assistant_agent ----------

def get_assistant_agent_config() -> dict:
    """Assistant Agent 配置（执行任务）。"""
    return _get_agent_config("ASSISTANT")


def get_assistant_agent_api_key() -> str:
    cfg = get_assistant_agent_config()
    if not cfg["api_key"]:
        raise EnvironmentError("ASSISTANT_API_KEY 或 OPENAI_API_KEY 未在 .env 中配置")
    return cfg["api_key"]


def get_assistant_agent_model() -> str:
    cfg = get_assistant_agent_config()
    if not cfg["model"]:
        raise EnvironmentError("ASSISTANT_MODEL 或 OPENAI_MODEL 未在 .env 中配置")
    return cfg["model"]


def get_assistant_agent_base_url() -> Optional[str]:
    return get_assistant_agent_config()["base_url"]


# ---------- tool_agent ----------

def get_tool_agent_config() -> dict:
    """Tool Agent 配置（工具执行，如生成工具回复）。"""
    return _get_agent_config("TOOL_AGENT")


def get_tool_agent_api_key() -> str:
    cfg = get_tool_agent_config()
    if not cfg["api_key"]:
        raise EnvironmentError("TOOL_AGENT_API_KEY 或 OPENAI_API_KEY 未在 .env 中配置")
    return cfg["api_key"]


def get_tool_agent_model() -> str:
    cfg = get_tool_agent_config()
    if not cfg["model"]:
        raise EnvironmentError("TOOL_AGENT_MODEL 或 OPENAI_MODEL 未在 .env 中配置")
    return cfg["model"]


def get_tool_agent_base_url() -> Optional[str]:
    return get_tool_agent_config()["base_url"]


# ---------- eval_agent ----------

def get_eval_agent_config() -> dict:
    """Eval Agent 配置（评估轨迹）。"""
    return _get_agent_config("EVAL")


def get_eval_agent_api_key() -> str:
    cfg = get_eval_agent_config()
    if not cfg["api_key"]:
        raise EnvironmentError("EVAL_API_KEY 或 OPENAI_API_KEY 未在 .env 中配置")
    return cfg["api_key"]


def get_eval_agent_model() -> str:
    cfg = get_eval_agent_config()
    if not cfg["model"]:
        raise EnvironmentError("EVAL_MODEL 或 OPENAI_MODEL 未在 .env 中配置")
    return cfg["model"]


def get_eval_agent_base_url() -> Optional[str]:
    return get_eval_agent_config()["base_url"]


# ---------- 兼容旧接口（逐步迁移后可删） ----------

def get_openai_api_key() -> str:
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("OPENAI_API_KEY 未在 .env 中配置")
    return key


def get_openai_model() -> str:
    load_env()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not model:
        raise EnvironmentError("OPENAI_MODEL 未在 .env 中配置")
    return model


def get_openai_base_url() -> Optional[str]:
    load_env()
    url = os.environ.get("OPENAI_BASE_URL", "").strip()
    return url or None


def get_llm_config() -> dict:
    """全局 LLM 配置（兼容旧接口）。"""
    load_env()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise EnvironmentError("请在 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL")
    return {
        "model": model,
        "model_type": "oai",
        "model_server": base_url or "https://api.openai.com/v1",
        "api_key": api_key,
    }