# 多轮对话模拟 Demo

使用 **qwen-agent** 搭建 Assistant，连接 **prediction-trader** MCP Docker 容器，根据任务蓝图模拟多轮对话，收集完整轨迹用于数据合成。

支持两种模式：
1. **动态模式**（新）：蓝图含 `user_intent`、`user_agent_config`、`max_turns`、`end_condition`，无 `queries`。由 **User Agent**（LLM）根据对话上下文逐轮生成用户消息，与助手 Agent 交互直到任务完成或达到 `max_turns`。
2. **静态模式**（兼容）：蓝图含 `queries` 数组。按预定义 query 逐轮发送用户消息。

## 流程概览

1. **启动 MCP 容器**：prediction-trader 提供 Polymarket/Kalshi 工具
2. **创建 Agent**：qwen-agent Assistant + MCP 工具列表
3. **逐轮模拟**：
   - 动态模式：User Agent 生成 user 消息 → Assistant 响应（含工具调用）→ 循环直到 `[TASK_END]` 或 `max_turns`
   - 静态模式：按 `queries` 逐轮发送 user 消息
4. **轨迹收集**：保存 turn 结构（`user_message`、`assistant_message`、`tool_calls` 等）、`final_state_snapshot`、`validation` 结果

## 依赖

```bash
pip install "qwen-agent[mcp]" openai python-dotenv
# 或
uv pip install "qwen-agent[mcp]" openai python-dotenv
```

项目根目录 `.env` 需配置：

- `OPENAI_API_KEY`（必填）
- `OPENAI_MODEL`（必填，如 `gpt-4o-mini`）
- `OPENAI_BASE_URL`（可选，兼容非 OpenAI 接口）

## 运行

### 1. 启动 prediction-trader MCP 容器

```bash
cd exps/data-synthesis-workflow/opencode_demo/env_2896_prediction-trader
docker compose -f docker/docker-compose.yaml up -d
```

MCP 服务地址：`http://localhost:8000/sse`。

### 2. 生成任务蓝图（若尚未生成）

```bash
python exps/data-synthesis-workflow/blueprint_demo/run_blueprint.py
```

输出为 `blueprint_demo/out_blueprint.json`（新格式：任务配置 + 交互生成配置）。

### 3. 执行多轮模拟

```bash
python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py
```

可选参数：

- `--blueprint <path>`：蓝图 JSON 路径（默认 `blueprint_demo/out_blueprint.json`）
- `--output / -o <path>`：轨迹输出路径（默认 `agent_demo/out_trajectory.json`）
- `--no-docker`：不自动启动 Docker，仅检查 MCP 是否可达

## 输出格式

`out_trajectory.json`：

- `trajectory_id`、`blueprint_id`、`skill_name`、`persona_id`
- `system_message`、`agent_system_prompt`、`tools`
- `turns`：每轮含 `turn_index`、`user_message`、`assistant_thinking`、`assistant_message`、`tool_calls`、`execution_time_ms`
- `final_state_snapshot`：任务结束后的数据库状态（若可获取）
- `validation`：基于输出与状态的简单验证结果
- `expected_output`、`expected_final_state`：来自蓝图，供评估使用

## 注意事项

- **User Agent**：动态模式下，`prompts/user_agent.md` 指导 LLM 生成每轮用户消息；需符合 APIGen-MT 原则（不知工具、逐步透露、自然表达）。
- **MCP 连接**：当前使用 `mcpServers.prediction-trader.url` 连接 SSE 服务。
- **final_state_snapshot**：当环境在 Docker 内运行时，宿主机可能无法读取 `data/state.db`，此时为 `null`。
- **模型**：推荐使用支持 tool calling 的模型（如 gpt-4o-mini、qwen3-max 等）。
