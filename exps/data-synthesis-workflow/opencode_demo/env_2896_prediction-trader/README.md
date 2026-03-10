# Prediction Trader Skill - 轻量 MCP 环境（tools.jsonl-only）

本目录中的 `env_2896_prediction-trader` 是一个**轻量（light/json-only）MCP 环境**示例，符合数据合成技术路线中「仅依赖 tools.jsonl + LLM + KV state」的环境要求。它不再依赖 SQLite 数据库、`state.py`、`tools/*.py` 或 Mock API，而是通过 `tools.jsonl` 描述工具 schema，并由 LLM 在进程内维护 JSON 会话状态。

## 目录结构

```
env_2896_prediction-trader/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yaml
├── pyproject.toml
├── mcp_server.py
├── llm_response.py             # 调用大模型生成工具回复与 JSON 状态
├── tools.jsonl                 # 工具 schema 列表（name/description/inputSchema）
└── uv.lock                     # 依赖锁（由 uv sync 生成，可选）
```

## 快速开始

### 1. 本地运行（无需 Docker）

```bash
uv sync
MCP_TRANSPORT=stdio ENV_MODE=light python mcp_server.py
```

服务启动后，将根据 `tools.jsonl` 注册所有工具，工具调用结果和会话状态由 `llm_response.py` 调用大模型生成与维护。无需数据库初始化与 Mock 服务。

### 2. Docker 启动服务

```bash
# 在 env_2896_prediction-trader 目录下执行
docker compose -f docker/docker-compose.yaml up -d
docker compose -f docker/docker-compose.yaml logs -f
```

容器内会自动安装依赖并以 `ENV_MODE=light` 启动 MCP 服务，基于 `tools.jsonl` + LLM + KV state 提供工具能力，不再依赖 SQLite 或 Mock API。

### 3. 使用 MCP 服务

MCP 服务运行在 `http://localhost:8000`，支持 stdio 和 SSE 模式。

#### 通过 stdio 连接

```python
from mcp.client import MCPClient

client = MCPClient(["python", "mcp_server.py"])
tools = client.list_tools()
result = client.call_tool("kalshi_fed", {"limit": 5})
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MCP_TRANSPORT` | `http`（Docker）/ `stdio`（本地示例） | MCP 传输模式 |
| `ENV_MODE` | `light` | 环境模式，固定为轻量 json-only |
| `OPENAI_API_KEY` | （必填） | 用于 `llm_response.py` 调用大模型 |
| `OPENAI_MODEL` | （必填） | 工具回复生成所用模型，如 `gpt-4.1-mini` |
| `OPENAI_BASE_URL` | 空 | 可选自定义 OpenAI 兼容服务地址 |

## 数据合成工作流中的定位

- 该环境主要用于演示和验证 **tools.jsonl-only + LLM + KV state** 的轻量环境形态，便于快速集成到数据合成流水线中；
- blueprint 侧给出的 `initial_state` / `expected_final_state` 会在 MCP 端通过 KV JSON state 体现，并在轨迹的 `final_state` 字段中落盘；
- 不承担 SQLite schema 设计与强一致状态验证的职责，这些由单独的强状态参考环境或上游数据层负责。
