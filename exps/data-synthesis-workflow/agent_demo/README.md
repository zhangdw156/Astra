# 多轮对话模拟 Demo

使用 **qwen-agent** 搭建 Agent，连接 **prediction-trader** MCP Docker 容器，按任务蓝图模拟多轮 user 查询，收集完整对话轨迹用于数据合成。

## 流程概览

1. **启动 MCP 容器**：prediction-trader 提供 Polymarket/Kalshi 工具
2. **创建 Agent**：qwen-agent Assistant + MCP 工具列表
3. **逐轮模拟**：按蓝图 `queries` 依次发起 user 问题，Agent 调用工具并回复
4. **轨迹收集**：保存 user / assistant / function 完整轨迹为 JSON

## 依赖

```bash
# 安装 qwen-agent（含 MCP 支持）
pip install "qwen-agent[mcp]"

# 或使用 uv
uv pip install "qwen-agent[mcp]"
```

项目根目录 `.env` 需配置：

- `OPENAI_API_KEY`（必填）
- `OPENAI_MODEL`（必填，如 `gpt-4o-mini`）
- `OPENAI_BASE_URL`（可选，兼容非 OpenAI 接口）

## 运行

### 1. 启动 prediction-trader MCP 容器

```bash
cd exps/data-synthesis-workflow/prediction-trader
docker compose -f docker/docker-compose.yaml up -d
```

MCP 服务地址：`http://localhost:8000/sse`。

### 2. 生成任务蓝图（若尚未生成）

```bash
# 在项目根执行
python exps/data-synthesis-workflow/blueprint_demo/run_blueprint.py
```

输出为 `blueprint_demo/out_blueprint.json`。

### 3. 执行多轮模拟

```bash
# 在项目根执行
python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py
```

可选参数：

- `--blueprint <path>`：蓝图 JSON 路径（默认 `blueprint_demo/out_blueprint.json`）
- `--output / -o <path>`：轨迹输出路径（默认 `agent_demo/out_trajectory.json`）
- `--no-docker`：不自动启动 Docker，仅检查 MCP 是否可达

## 输出格式

`out_trajectory.json`：

```json
{
  "blueprint_id": "...",
  "skill_name": "prediction-trader",
  "persona_id": "...",
  "turns": [
    {"role": "user", "content": "I'm researching political developments..."},
    {"role": "assistant", "content": "", "function_call": {"name": "polymarket_search", "arguments": "..."}},
    {"role": "function", "name": "polymarket_search", "content": "..."},
    {"role": "assistant", "content": "Based on the results..."}
  ]
}
```

## 注意事项

- **MCP URL 支持**：当前配置使用 `mcpServers.prediction-trader.url` 连接远程 SSE 服务。若 qwen-agent 版本仅支持 `command`+`args` 启动子进程，可改用本地 stdio 模式：
  - 在 prediction-trader 目录运行 `MCP_TRANSPORT=stdio python mcp_server.py`，再在 mcpServers 中配置 `"command": "python", "args": ["mcp_server.py"]` 并指定 `cwd`。
- **依赖安装**：可使用 `pip install -r exps/data-synthesis-workflow/agent_demo/requirements.txt` 安装。
- **模型**：推荐使用支持 tool calling 的模型（如 gpt-4o-mini、qwen3-max 等）。
- **Mock 数据**：prediction-trader 容器使用 Mock API，无需真实 Polymarket/Kalshi API Key。
