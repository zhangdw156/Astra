# prediction-trader 轻量环境（仅 tools.jsonl）

本目录为**仅 tools.jsonl** 的轻量环境示例，供 data-synthesis-workflow 的蓝图生成与轨迹合成使用。

## 内容

- **tools.jsonl**：每行一个工具 schema（name、description、inputSchema），对应 prediction market 相关能力（Polymarket、Kalshi 搜索与对比等）。

## 如何运行 MCP

不在此目录启动服务，而是由项目统一 runner 按 `tools_path` 启动：

```bash
# 在项目根目录执行
uv run -m astra.scripts.run_light_mcp tools_path=exps/data-synthesis-workflow/opencode_demo/env_2896_prediction-trader/tools.jsonl transport=sse
```

轨迹合成时可直接指定本目录的 tools.jsonl：

```bash
python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py --tools-path exps/data-synthesis-workflow/opencode_demo/env_2896_prediction-trader/tools.jsonl --blueprint ...
```

## 参考

- 配置默认值：`configs/light_mcp.yaml` 中的 `tools_path` 可指向本文件。
- 蓝图生成：`blueprint_demo/run_blueprint.py` 默认使用本目录的 `tools.jsonl` 作为工具列表。
