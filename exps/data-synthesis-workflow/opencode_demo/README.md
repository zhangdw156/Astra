# OpenCode 环境生成 Demo

根据 skill 目录，调用本地 OpenCode CLI 的 `run` 命令，使用 `prompts/skill_to_environment.md` 提示词，生成可运行的 MCP 环境目录。任务会显式指示 OpenCode **先阅读参考示例**（skill → env 的生成前后目录对），再按相同模式生成目标环境。

## 前置条件

1. **安装 OpenCode CLI**：
   ```bash
   curl -fsSL https://opencode.ai/install | bash
   # 或：npm install -g opencode-ai
   # 或：bun install -g opencode-ai
   ```
2. **验证安装**：`opencode --version`
3. **完成认证**：`opencode auth login`（配置至少一个 LLM 提供商）

## 运行

在项目根目录执行：

```bash
uv run python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py
```

或使用 `python` 直接运行（需确保在正确虚拟环境中）：

```bash
python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--ref-skill-dir` | `opencode_demo/2896_prediction-trader` | 参考 skill 目录（OpenCode 需先阅读） |
| `--ref-env-dir` | `opencode_demo/env_2896_prediction-trader` | 参考 env 目录（生成的示例） |
| `--skill-dir` | `skills_demo/2515_stock-monitor` | 要转换的 skill 目录 |
| `--env-dir` | `exps/data-synthesis-workflow/env_2515_stock-monitor` | 生成环境的目标目录 |

### 自定义路径

```bash
python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py \
  --ref-skill-dir opencode_demo/2896_prediction-trader \
  --ref-env-dir opencode_demo/env_2896_prediction-trader \
  --skill-dir /path/to/skill \
  --env-dir /path/to/output/env-dir
```

## 输入

- **提示词**：`exps/data-synthesis-workflow/prompts/skill_to_environment.md`
- **参考示例**（默认）：`opencode_demo/2896_prediction-trader` → `opencode_demo/env_2896_prediction-trader`
- **目标 skill**（默认）：`skills_demo/2515_stock-monitor`
- **目标 env**（默认）：`exps/data-synthesis-workflow/env_2515_stock-monitor`

脚本会替换 `{REF_SKILL_DIR}`、`{REF_ENV_DIR}`、`{SKILL_DIR}`、`{ENV_DIR}`，并在任务开头显式指示 OpenCode 先阅读参考目录，再生成。

默认生成的环境采用 **strong（强状态）模式**：

- 包含 `database/`、`state.py`、`tools/`，工具通过状态层访问 SQLite；
- `mcp_server.py` 扫描 `tools/` 中的 TOOL_SCHEMA + execute 注册 MCP 工具，真实执行数据库查询与写入。

改造后的 `mcp_server.py` 同时支持基于 `tools.jsonl` 的 **light（轻量/json-only）模式**，由环境变量 `ENV_MODE` 控制：

- `ENV_MODE=strong`：强制要求 `tools/` + `database/` + `state.py` 存在；
- `ENV_MODE=light`：仅要求 `mcp_server.py`、`pyproject.toml`、`tools.jsonl`，工具实现由 LLM（基于 `tools.jsonl` Schema）直接生成回复与会话状态；
- `ENV_MODE=auto`（默认）：优先检测 `tools/` 走 strong 模式，否则退回 `tools.jsonl` 的 light 模式。

## 输出

- OpenCode 以项目根为工作目录运行，便于访问参考目录与 `skills_demo`
- 按提示词约定，在 `--env-dir` 下生成 MCP 环境（mcp_server.py、tools/、tools.jsonl、docker/、mocks/ 等）
- 控制台输出 OpenCode 的实时输出与退出码

## 批量生成：batch_env_gen.py

对 `skills_demo/` 下的**所有 skill** 逐个调用 `run_opencode_env_gen`，将生成的环境输出到 `env_demo/env_<skill_name>`。

```bash
# 预览（不实际调用 opencode）
python exps/data-synthesis-workflow/opencode_demo/batch_env_gen.py --dry-run

# 仅处理前 3 个 skill（用于试跑）
python exps/data-synthesis-workflow/opencode_demo/batch_env_gen.py --limit 3

# 跳过已存在 mcp_server.py 的 env（断点续跑）
python exps/data-synthesis-workflow/opencode_demo/batch_env_gen.py --skip-existing

# 全量生成
python exps/data-synthesis-workflow/opencode_demo/batch_env_gen.py
```

| 参数 | 说明 |
|------|------|
| `--dry-run` | 只列出 skill 与目标 env，不调用 opencode |
| `--limit N` | 最多处理 N 个 skill（0 表示不限制） |
| `--skip-existing` | 若 `env_demo/env_xxx/mcp_server.py` 已存在则跳过 |
| `--ref-skill-dir` / `--ref-env-dir` | 参考示例目录（与 run_opencode_env_gen 一致） |

输出目录：`env_demo/env_<skill_dir_name>`（如 `env_demo/env_2515_stock-monitor`）。

## 验证 env_demo：validate_env_demo.py

对 `env_demo/` 下所有 MCP 环境执行可复现验证（结构检查、依赖安装、MCP Initialize 响应），可选调用 LLM 生成汇总报告。

```bash
# 验证所有 env
python exps/data-synthesis-workflow/opencode_demo/validate_env_demo.py

# 仅验证前 3 个（试跑）
python exps/data-synthesis-workflow/opencode_demo/validate_env_demo.py --limit 3

# 输出结果 JSON
python exps/data-synthesis-workflow/opencode_demo/validate_env_demo.py --output validate_results.json

# 验证后调用 LLM 生成中文汇总报告（需 .env 中 OPENAI_API_KEY、OPENAI_MODEL）
python exps/data-synthesis-workflow/opencode_demo/validate_env_demo.py --llm-report
```

| 参数 | 说明 |
|------|------|
| `--env-demo-dir` | env_demo 根目录（默认项目根下 env_demo） |
| `--limit N` | 最多验证 N 个 env（0 表示全部） |
| `--output PATH` | 将结果 JSON 写入指定文件 |
| `--llm-report` | 验证结束后调用 LLM 生成汇总报告与修复建议 |

验证步骤：1) 结构（mcp_server.py、tools/、pyproject.toml） 2) `uv sync` 3) MCP 服务器启动并响应 Initialize。不包含 Mock 启动与 test_tools（各 env 差异较大）。`--llm-report` 需安装 `python-dotenv` 与 `openai`，且项目根 `.env` 配置 `OPENAI_API_KEY`、`OPENAI_MODEL`。

## 单环境验证：validate_env.py（供 OpenCode 使用）

OpenCode 生成环境后需通过质量门：运行 `validate_env.py` 验证单个环境，失败则根据输出修复后重试，直到通过。

```bash
# 在项目根目录执行，传入环境目录路径
python exps/data-synthesis-workflow/opencode_demo/validate_env.py <ENV_DIR>
```

- **退出码 0**：通过，环境可运行
- **退出码 1**：失败，查看输出的 structure/uv_sync/mcp_initialize 错误并修复
- **退出码 2**：参数错误（目录不存在等）

提示词 `skill_to_environment.md` 与 `run_opencode_env_gen.py` 已将该脚本作为必做步骤纳入生成流程。

## 说明

- 脚本仅使用 Python 标准库（subprocess、pathlib、argparse），无额外依赖
- 若目标 env 目录已存在，OpenCode 可能在其中增删改文件；建议先备份或使用新建目录
- 生成耗时取决于 OpenCode 与 LLM 调用，请耐心等待
- 批量生成全量 skill 耗时较长，建议先用 `--limit` 或 `--dry-run` 验证
