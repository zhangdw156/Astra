# Social Post Skill - 完整实现

基于 social-post skill 的完整多轮对话工具调用数据生成环境。

## 目录结构

```
social-post/
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
│   ├── post_to_twitter.py      # 发布推文
│   ├── post_to_farcaster.py    # 发布 Cast
│   ├── post_to_both.py         # 同时发布到双平台
│   ├── reply_to_twitter.py     # 回复推文
│   ├── reply_to_farcaster.py   # 回复 Cast
│   └── preview_post.py         # 预览发布内容
│
└── mocks/                      # Mock API 服务
    ├── twitter_api.py          # Twitter Mock
    └── farcaster_api.py        # Farcaster Mock
```

## 快速开始

### 1. 启动服务

```bash
# 在 social-post 目录下执行

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
docker compose -f docker/docker-compose.yaml exec social-post bash

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
result = client.call_tool("post_to_twitter", {"text": "Hello world!"})
```

## 可用工具

| 工具名称 | 功能 |
|----------|------|
| `post_to_twitter` | 发布推文到 Twitter |
| `post_to_farcaster` | 发布 Cast 到 Farcaster |
| `post_to_both` | 同时发布到双平台 |
| `reply_to_twitter` | 回复推文 |
| `reply_to_farcaster` | 回复 Cast |
| `preview_post` | 预览发布内容，验证字符限制 |

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TWITTER_API_BASE` | http://localhost:8003 | Twitter Mock API 地址 |
| `FARCASTER_API_BASE` | http://localhost:8004 | Farcaster Mock API 地址 |
| `X_CONSUMER_KEY` | mock-consumer-key | Twitter API Key |
| `X_CONSUMER_SECRET` | mock-consumer-secret | Twitter API Secret |
| `X_ACCESS_TOKEN` | mock-access-token | Twitter Access Token |
| `X_ACCESS_TOKEN_SECRET` | mock-access-secret | Twitter Access Token Secret |
| `FARCASTER_API_KEY` | mock-api-key | Farcaster API Key |

## 平台限制

- **Twitter:** 252 字符（280 字符 + 10% 安全缓冲）
- **Farcaster:** 288 字节（320 字节 + 10% 安全缓冲）

## 数据合成工作流

### 步骤 1: 准备场景

定义多轮对话场景：

```json
{
  "session_id": "session_001",
  "skill": "social-post",
  "scenarios": [
    {
      "turn": 1,
      "user": "发一条推文测试一下",
      "expected_tool": "post_to_twitter",
      "expected_params": {"text": "Test tweet"}
    },
    {
      "turn": 2,
      "user": "把这个也发到Farcaster上",
      "expected_tool": "post_to_farcaster",
      "expected_params": {"text": "Test tweet"}
    }
  ]
}
```

### 步骤 2: 调用工具

LLM 根据用户输入选择工具：

```
User: 发一条推文
Assistant: 好的，让我帮你发布一条推文。
[Calls: post_to_twitter(text="Test tweet")]
```

### 步骤 3: 收集轨迹

记录完整的对话轨迹用于训练：

```json
{
  "session_id": "session_001",
  "turns": [
    {
      "role": "user",
      "content": "发一条推文"
    },
    {
      "role": "assistant",
      "content": "好的，让我帮你发布一条推文。",
      "tool_calls": [
        {
          "name": "post_to_twitter",
          "arguments": {"text": "Test tweet"}
        }
      ]
    },
    {
      "role": "tool",
      "name": "post_to_twitter",
      "content": "## Post to Twitter\n\n### Success\n\n**Tweet ID:** 1234567890..."
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