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

**用途**：指导 OpenCode（或代码生成 Agent）根据「Skill 目录」生成「可运行 MCP 环境目录」。**显式要求先阅读参考示例**（skill → env 的生成前后目录对），再按相同模式生成。

**占位符**：
- `{REF_SKILL_DIR}` — 参考 skill 目录（需先阅读）
- `{REF_ENV_DIR}` — 参考 env 目录（生成的示例）
- `{SKILL_DIR}` — 要转换的 skill 目录
- `{ENV_DIR}` — 生成环境的目标目录

**输出**：与参考实现同构的环境目录，包含 `mcp_server.py`、`tools/*.py`、`tools.jsonl`、`docker/`、`mocks/` 等，使 Skill 中描述的命令均以 MCP 工具形式可被调用，且可 Docker 一键启动、无真实 API Key 即可跑通。

**调用方式**：通过 `opencode_demo/run_opencode_env_gen.py` 自动化调用本地 OpenCode CLI 的 `run` 命令；默认使用 `opencode_demo/2896_prediction-trader` 与 `opencode_demo/env_2896_prediction-trader` 作为参考，目标为 `skills_demo/2515-stock-monitor`，输出到 `exps/data-synthesis-workflow/env_2515_stock-monitor`。

## trajectory_evaluator.md

**用途**：对 `agent_demo/out_trajectory.json` 这类多轮对话轨迹调用大模型做质量评估，产出整体评分、幻觉风险与结构化标签。

**输入**：完整轨迹 JSON（含 `system_message`、`agent_system_prompt`、`tools`、`turns` 等）。

**输出**：一个 JSON 对象，包含：

- `score`：0.0–5.0 轨迹整体质量评分
- `hallucination_risk`：`none` / `low` / `medium` / `high`
- `labels`：多种布尔标签（如 `has_hallucination`、`tool_misuse`、`contradicts_tool_results` 等）
- `reasoning`：summary / strengths / weaknesses
- `suggested_fixes`：改进建议列表

**调用方式**：由 `trajectory_eval_demo/run_trajectory_eval.py` 注入 `{TRAJECTORY_JSON}` 并调用 LLM。
