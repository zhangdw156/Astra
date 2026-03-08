# Prediction Trader Skill - 完整实现

基于 prediction-trader skill 的完整多轮对话工具调用数据生成环境。

## 目录结构

```
prediction-trader/
├── SKILL.md                    # 原始技能定义
├── docker/                     # Docker 相关文件
│   ├── Dockerfile              # 容器镜像构建
│   └── docker-compose.yaml    # 服务编排
├── pyproject.toml              # Python 依赖（uv 管理）
├── mcp_server.py               # MCP 服务入口
├── test_tools.py               # 工具测试脚本
│
├── tools/                      # MCP 工具定义
│   ├── __init__.py
│   ├── kalshi_fed.py           # 美联储利率市场
│   ├── kalshi_economics.py     # 经济预测市场
│   ├── kalshi_search.py        # 市场搜索
│   ├── polymarket_trending.py  # Polymarket 热门
│   ├── polymarket_crypto.py    # 加密货币市场
│   ├── polymarket_search.py    # Polymarket 搜索
│   ├── trending.py             # 双平台热门
│   ├── compare_markets.py      # 市场对比
│   └── analyze_topic.py        # 主题分析
│
└── mocks/                      # Mock API 服务
    ├── unifai_api.py           # UnifAI/Polymarket Mock
    └── kalshi_api.py           # Kalshi Mock
```

## 快速开始

### 1. 启动服务

```bash
# 在 prediction-trader 目录下执行

# 构建并启动所有服务
docker compose -f docker/docker-compose.yaml up -d

# 查看日志
docker compose -f docker/docker-compose.yaml logs -f

# 停止服务
docker compose -f docker/docker-compose.yaml down
```

### 2. 测试工具

```bash
# 进入容器
docker compose -f docker/docker-compose.yaml exec prediction-trader bash

# 运行测试
python test_tools.py
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
| `UNIFAI_API_BASE` | http://localhost:8001 | UnifAI Mock API 地址 |
| `KALSHI_API_BASE` | http://localhost:8002 | Kalshi Mock API 地址 |
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

- 所有工具调用都通过 Mock API 返回预设数据
- Mock 数据是静态的，适合训练"工具选择"能力
- 不需要真实 API Key
- 数据与时间无关，适合任意时刻训练
