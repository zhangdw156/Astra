#!/usr/bin/env python3
"""
轻量 MCP 服务入口：通过 Hydra 传入 tools_path 等配置，启动基于 tools.jsonl 的 MCP 服务。

不依赖 Docker 与 env 目录结构，供轨迹合成阶段按 tools 批次启停 MCP 使用。

用法（在项目根）：
  uv run -m astra.scripts.run_light_mcp
  uv run -m astra.scripts.run_light_mcp tools_path=path/to/tools.jsonl transport=sse
"""

from __future__ import annotations

import os
from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from astra.data_synthesis import create_mcp_tools_light, load_tools_from_jsonl

# 项目根目录（src/astra/scripts -> 上三级）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

_CONFIG_PATH = str(PROJECT_ROOT / "configs")


def _resolve_path(cfg: DictConfig, key: str) -> Path:
    """将配置中的路径解析为绝对路径；相对路径相对于项目根。"""
    raw = OmegaConf.select(cfg, key)
    if raw is None or raw == "":
        raise ValueError(f"配置项 {key} 必填")
    p = Path(str(raw))
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def run(cfg: DictConfig) -> None:
    """根据 Hydra 配置加载 tools.jsonl 并启动 MCP 服务。"""
    tools_path = _resolve_path(cfg, "tools_path")
    if not tools_path.exists():
        raise FileNotFoundError(f"tools_path 不存在: {tools_path}")

    prompt_path = _resolve_path(cfg, "prompt_path")
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt_path 不存在: {prompt_path}")

    env_path_raw = OmegaConf.select(cfg, "env_path")
    env_path: Path | None = None
    if env_path_raw:
        env_path = Path(str(env_path_raw))
        if not env_path.is_absolute():
            env_path = PROJECT_ROOT / env_path
        if not env_path.exists():
            env_path = None

    mcp_name_raw = OmegaConf.select(cfg, "mcp_name")
    mcp_name = str(mcp_name_raw).strip() if mcp_name_raw else tools_path.parent.name or "light-mcp"

    transport = str(OmegaConf.select(cfg, "transport")).lower().strip()
    if transport not in ("stdio", "sse"):
        transport = "stdio"

    param_normalizer_cfg = OmegaConf.select(cfg, "param_normalizer")
    param_normalizer: dict[str, str] = {}
    if param_normalizer_cfg is not None:
        raw = OmegaConf.to_container(param_normalizer_cfg, resolve=True)
        if isinstance(raw, dict):
            param_normalizer = {str(k): str(v) for k, v in raw.items()}

    from fastmcp import FastMCP

    jsonl_tools = load_tools_from_jsonl(tools_path)
    print(f"{mcp_name} MCP Server")
    print(f"tools.jsonl: {tools_path}")
    print(f"Total tools: {len(jsonl_tools)}")
    print("-" * 40)

    mcp = FastMCP(mcp_name)
    create_mcp_tools_light(
        mcp,
        jsonl_tools,
        prompt_path=prompt_path,
        env_path=env_path,
        param_normalizer=param_normalizer or None,
    )

    print("\nStarting MCP server...")
    if transport == "sse":
        os.environ["MCP_TRANSPORT"] = "sse"
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    import hydra
    from omegaconf import DictConfig

    @hydra.main(
        config_path=_CONFIG_PATH,
        config_name="light_mcp",
        version_base=None,
    )
    def main(cfg: DictConfig) -> None:
        run(cfg)

    main()
