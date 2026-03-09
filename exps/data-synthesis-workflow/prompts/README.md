# 提示词目录

本目录存放 data-synthesis-workflow 使用的提示词模板。

## task_blueprint_generator.md

**用途**：根据 Skill 文档、工具列表和用户画像，生成多轮对话工具调用任务蓝图。

**输入**：
- `exps/data-synthesis-workflow/2896_prediction-trader/SKILL.md` — Skill 定义
- `exps/data-synthesis-workflow/prediction-trader/tools.jsonl` — 工具 schema 列表
- `persona/persona_5K.jsonl` 中的一行 — 用户画像（含 `persona` 与 `id`）

**输出**：LLM 只产出 `queries` 数组（每项含 `query` 与 `tool_sequence`）。程序侧注入 `blueprint_id`、`skill_name`、`persona_id` 后写入蓝图文件。

**调用方式**：将上述三个输入内容注入提示词后，发给 LLM；将返回的 JSON 追加到蓝图文件（如 `blueprints.jsonl`）供后续数据合成使用。

## skill_to_environment.md

**用途**：指导 OpenCode（或代码生成 Agent）根据「Skill 目录」生成「可运行 MCP 环境目录」。

**输入**：
- Skill 目录路径（占位符：`{SKILL_DIR}`）
- SKILL.md 内容（含 Commands、Requirements、Example Usage 等）
- 可选的 scripts/ 等辅助文件

**输出**：与参考实现同构的环境目录（占位符：`{ENV_DIR}`），包含 `mcp_server.py`、`tools/*.py`、`tools.jsonl`、`docker/`、`mocks/`（若依赖外部 API），使 Skill 中描述的命令均以 MCP 工具形式可被调用，且可 Docker 一键启动、无真实 API Key 即可跑通。

**调用方式**：将本提示词与 Skill 路径/内容一并提供给 OpenCode 或代码生成 Agent，按提示词中的步骤与约定生成目标环境目录。也可通过 `opencode_demo/run_opencode_env_gen.py` 自动化调用本地 OpenCode CLI 的 `run` 命令。
