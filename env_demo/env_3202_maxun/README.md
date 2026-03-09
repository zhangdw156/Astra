# Maxun Skill - 完整实现

基于 maxun skill 的完整多轮对话工具调用数据生成环境。

## 目录结构

```
maxun/
├── SKILL.md                    # 原始技能定义
├── docker/                     # Docker 相关文件
│   ├── Dockerfile              # 容器镜像构建
│   └── docker-compose.yaml    # 服务编排
├── pyproject.toml              # Python 依赖（uv 管理）
├── mcp_server.py               # MCP 服务入口
├── tools.jsonl                 # 工具定义（用于 blueprint 生成）
│
├── tools/                      # MCP 工具定义
│   ├── __init__.py
│   ├── list_robots.py          # 列出所有机器人
│   ├── get_robot.py            # 获取机器人详情
│   ├── run_robot.py            # 执行机器人爬取
│   ├── list_runs.py            # 列出运行记录
│   ├── get_run_result.py       # 获取运行结果
│   └── abort_run.py            # 中止运行
│
└── mocks/                      # Mock API 服务
    └── maxun_api.py            # Maxun Mock API
```

## 快速开始

### 1. 启动服务

```bash
# 在 maxun 目录下执行

# 构建并启动所有服务
docker compose -f docker/docker-compose.yaml up -d

# 查看日志
docker compose -f docker/docker-compose.yaml logs -f

# 停止服务
docker compose -f docker/docker-compose.yaml down
```

### 2. 使用 MCP 服务

MCP 服务运行在 `http://localhost:8000`，支持 stdio 和 SSE 模式。

## 可用工具

| 工具名称 | 功能 |
|----------|------|
| `list_robots` | 列出所有 Maxun 机器人 |
| `get_robot` | 获取机器人详情 |
| `run_robot` | 执行机器人爬取网站 |
| `list_runs` | 列出机器人的运行记录 |
| `get_run_result` | 获取运行结果 |
| `abort_run` | 中止正在运行的机器人 |

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MAXUN_API_BASE` | http://localhost:8001 | Maxun Mock API 地址 |
| `MAXUN_API_KEY` | mock-api-key | Maxun API Key |

## 数据合成工作流

### 步骤 1: 准备场景

定义多轮对话场景：

```json
{
  "session_id": "session_001",
  "skill": "maxun",
  "scenarios": [
    {
      "turn": 1,
      "user": "列出我的机器人",
      "expected_tool": "list_robots",
      "expected_params": {}
    },
    {
      "turn": 2,
      "user": "运行 robot-001",
      "expected_tool": "run_robot",
      "expected_params": {"robot_id": "robot-001"}
    }
  ]
}
```

### 步骤 2: 调用工具

LLM 根据用户输入选择工具：

```
User: 列出我的机器人
Assistant: 让我帮你查看可用的机器人。
[Calls: list_robots(limit=10)]
```

### 步骤 3: 收集轨迹

记录完整的对话轨迹用于训练：

```json
{
  "session_id": "session_001",
  "turns": [
    {
      "role": "user",
      "content": "列出我的机器人"
    },
    {
      "role": "assistant",
      "content": "让我帮你查看可用的机器人。",
      "tool_calls": [
        {
          "name": "list_robots",
          "arguments": {"limit": 10}
        }
      ]
    },
    {
      "role": "tool",
      "name": "list_robots",
      "content": "Found 4 robot(s):\n\n**ID:** robot-001\n**Name:** Product Scraper..."
    }
  ]
}
```

## 注意事项

- 所有工具调用都通过 Mock API 返回预设数据
- Mock 数据是静态的，适合训练"工具选择"能力
- 不需要真实 API Key
- 数据与时间无关，适合任意时刻训练