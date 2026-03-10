# Prediction Trader Skill - 完整实现（数据库驱动版）

基于 prediction-trader skill 的完整多轮对话工具调用数据生成环境，按 DATA_SYNTHESIS_TECH_ROUTE 采用 **SQLite 状态后端 + 状态访问层**，工具与 Mock 共享同一状态，可追踪、可复现、可验证。

## 目录结构

```
env_2896_prediction-trader/
├── database/                   # SQLite 状态后端
│   ├── schema.sql              # 表结构（kalshi_markets, polymarket_events）
│   └── initial_data.sql        # 初始种子数据
├── state.py                    # 状态访问层（read/write/transaction）
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yaml
├── pyproject.toml
├── mcp_server.py
├── test_tools.py               # 本地测试（自动初始化 DB，无需 Mock）
│
├── tools/                      # MCP 工具（经 state 层读数据）
│   ├── kalshi_fed.py
│   ├── kalshi_economics.py
│   ├── kalshi_search.py
│   ├── polymarket_trending.py
│   ├── polymarket_crypto.py
│   ├── polymarket_search.py
│   ├── trending.py
│   ├── compare_markets.py
│   └── analyze_topic.py
│
└── mocks/                      # Mock API（从同一 SQLite 读取）
    ├── unifai_api.py
    └── kalshi_api.py
```

## 快速开始

### 1. 本地测试（无需 Docker）

```bash
# 在 env_2896_prediction-trader 目录下执行
uv sync
python test_tools.py
```

会先初始化 `data/state.db`（执行 schema + initial_data），再跑全部工具测试。工具直接读状态层，无需启动 Mock。

### 2. Docker 启动服务

```bash
# 在 env_2896_prediction-trader 目录下执行
docker compose -f docker/docker-compose.yaml up -d
docker compose -f docker/docker-compose.yaml logs -f
```

容器启动时会自动执行 `ensure_schema_and_initial_data()`，状态持久化到卷 `prediction-trader-data`。

### 3. 容器内测试工具

```bash
docker compose -f docker/docker-compose.yaml exec prediction-trader python test_tools.py
```

### 3. 使用 MCP 服务

MCP 服务运行在 `http://localhost:8000`，支持 stdio 和 SSE 模式。

#### 通过 stdio 连接

```python
from mcp.client import MCPClient

client = MCPClient(["python", "mcp_server.py"])
tools = client.list_tools()
result = client.call_tool("kalshi_fed", {"limit": 5})
```

## 可用工具

| 工具名称 | 功能 |
|----------|------|
| `kalshi_fed` | 获取美联储利率预测市场 |
| `kalshi_economics` | 获取 GDP/CPI 经济预测市场 |
| `kalshi_search` | 搜索 Kalshi 预测市场 |
| `polymarket_trending` | 获取 Polymarket 热门预测 |
| `polymarket_crypto` | 获取加密货币预测市场 |
| `polymarket_search` | 搜索 Polymarket 预测市场 |
| `trending` | 获取双平台热门预测市场 |
| `compare_markets` | 对比双平台特定主题市场 |
| `analyze_topic` | 全面分析特定主题市场 |

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `STATE_DB_PATH` | `./data/state.db` | SQLite 状态库路径（Docker 内为 `/app/data/state.db`） |
| `UNIFAI_API_BASE` | http://localhost:8001 | UnifAI Mock API 地址（仅 HTTP 调用方需要） |
| `KALSHI_API_BASE` | http://localhost:8002 | Kalshi Mock API 地址（仅 HTTP 调用方需要） |
| `UNIFAI_AGENT_API_KEY` | mock-api-key | UnifAI API Key |

## 数据合成工作流

### 步骤 1: 准备场景

定义多轮对话场景：

```json
{
  "session_id": "session_001",
  "skill": "prediction-trader",
  "scenarios": [
    {
      "turn": 1,
      "user": "有什么热门的预测市场吗？",
      "expected_tool": "trending",
      "expected_params": {}
    },
    {
      "turn": 2,
      "user": "我想了解比特币相关的预测市场",
      "expected_tool": "compare_markets",
      "expected_params": {"topic": "bitcoin"}
    }
  ]
}
```

### 步骤 2: 调用工具

LLM 根据用户输入选择工具：

```
User: 有什么热门的预测市场吗？
Assistant: 让我帮你查一下当前热门的预测市场。
[Calls: trending(limit=5)]
```

### 步骤 3: 收集轨迹

记录完整的对话轨迹用于训练：

```json
{
  "session_id": "session_001",
  "turns": [
    {
      "role": "user",
      "content": "有什么热门的预测市场吗？"
    },
    {
      "role": "assistant",
      "content": "让我帮你查一下当前热门的预测市场。",
      "tool_calls": [
        {
          "name": "trending",
          "arguments": {"limit": 5}
        }
      ]
    },
    {
      "role": "tool",
      "name": "trending",
      "content": "## Trending Prediction Markets\n\n### Polymarket..."
    }
  ]
}
```

## 扩展到更多 Skill

当需要添加新的 skill 时：

1. 在 `tools/` 目录添加新工具
2. 在 `mocks/` 目录添加 Mock API（如果需要）
3. `docker/Dockerfile` 会自动包含新工具

## 注意事项

- **状态后端**：工具与 Mock 均通过 `state.py` 访问同一 SQLite，数据一致、可验证。
- **可复现**：初始数据由 `database/initial_data.sql` 固定，相同环境得到相同结果。
- 不需要真实 API Key；本地测试无需启动 Mock，直接 `python test_tools.py` 即可。
