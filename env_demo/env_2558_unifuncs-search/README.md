# UniFuncs Search Skill - 完整实现

基于 unifuncs-search skill 的完整多轮对话工具调用数据生成环境。

## 目录结构

```
unifuncs-search/
├── SKILL.md                    # 原始技能定义
├── docker/                     # Docker 相关文件
│   ├── Dockerfile              # 容器镜像构建
│   └── docker-compose.yaml    # 服务编排
├── pyproject.toml              # Python 依赖（uv 管理）
├── mcp_server.py               # MCP 服务入口
├── tools.jsonl                 # 工具 schema
│
├── tools/                      # MCP 工具定义
│   ├── __init__.py
│   └── search.py               # Web 搜索工具
│
└── mocks/                      # Mock API 服务
    └── unifuncs_api.py         # UniFuncs Mock API
```

## 快速开始

### 1. 启动服务

```bash
cd /Users/zhangdw/work/lenovo/Astra/env_demo/env_2558_unifuncs-search

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
docker compose -f docker/docker-compose.yaml exec unifuncs-search bash

# 测试搜索
python -c "from tools.search import execute; print(execute('Python'))"
```

## 可用工具

| 工具名称 | 功能 |
|----------|------|
| `search` | 执行实时网络搜索，支持全球和中国地域 |

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `UNIFUNCS_API_BASE` | http://localhost:8001 | UniFuncs Mock API 地址 |
| `UNIFUNCS_API_KEY` | mock-api-key | UniFuncs API Key |

## 数据合成工作流

### 步骤 1: 准备场景

定义多轮对话场景：

```json
{
  "session_id": "session_001",
  "skill": "unifuncs-search",
  "scenarios": [
    {
      "turn": 1,
      "user": "帮我搜索最新的AI新闻",
      "expected_tool": "search",
      "expected_params": {"query": "AI news", "area": "global"}
    }
  ]
}
```

### 步骤 2: 调用工具

LLM 根据用户输入选择工具：

```
User: 帮我搜索Python教程
Assistant: 让我帮你搜索一下Python教程。
[Calls: search(query="Python教程", area="cn")]
```

## 注意事项

- 所有工具调用都通过 Mock API 返回预设数据
- Mock 数据是静态的，适合训练"工具选择"能力
- 不需要真实 API Key
- 数据与时间无关，适合任意时刻训练