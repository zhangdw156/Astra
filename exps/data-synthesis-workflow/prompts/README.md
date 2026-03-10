# 提示词目录

本目录存放 data-synthesis-workflow 使用的提示词模板。

## task_blueprint_generator.md

**用途**：根据 Skill 文档、工具列表和用户画像，生成多轮对话工具调用**任务蓝图**（两阶段设计）。

**输入**：
- `SKILL.md` — Skill 定义
- `tools.jsonl` — 工具 schema 列表
- `persona` — 用户画像（含 `persona` 与 `id`）

**输出**：任务配置（`task_id`、`user_intent`、`expected_tool_calls`、`expected_final_state`、`expected_output`）与交互生成配置（`system_message`、`user_agent_config`、`max_turns`、`end_condition`）。**无** `queries` 数组；用户消息由 agent_demo 阶段 User Agent 动态生成。

**调用方式**：由 `blueprint_demo/run_blueprint.py` 注入占位符后调用 LLM，程序注入 `blueprint_id`、`skill_name`、`persona_id`、`created_at` 后写入蓝图文件。

## user_agent.md

**用途**：指导 User Agent（LLM）根据任务意图与对话历史**动态生成**下一句用户消息。遵循 APIGen-MT 原则：不知工具/API、逐步透露、任务达成时输出 `[TASK_END]`、自然语言表达。

**输入**：`user_intent`、`user_agent_config`、`conversation_history`、`current_turn`、`max_turns`、`end_condition`

**输出**：单条用户消息字符串，或 `[TASK_END]` 表示结束。

**调用方式**：由 `agent_demo/run_agent_simulation.py` 在动态模式下每轮调用。

## skill_to_environment.md

**用途**：指导 OpenCode（或代码生成 Agent）根据「Skill 目录」生成「可运行 MCP 环境目录」。**显式要求先阅读参考示例**（skill → env 的生成前后目录对），再按相同模式生成。

**占位符**：
- `{REF_SKILL_DIR}` — 参考 skill 目录（需先阅读）
- `{REF_ENV_DIR}` — 参考 env 目录（生成的示例）
- `{SKILL_DIR}` — 要转换的 skill 目录
- `{ENV_DIR}` — 生成环境的目标目录

**输出**：与参考实现同构的环境目录，包含 `mcp_server.py`、`tools/*.py`、`tools.jsonl`、`docker/`、`mocks/` 等，使 Skill 中描述的命令均以 MCP 工具形式可被调用，且可 Docker 一键启动、无真实 API Key 即可跑通。新版约定支持并发合成友好的状态建模：共享静态表 + `run_id` 隔离运行态表，或在强状态环境下退回到每 run 独立 DB。

**调用方式**：通过 `opencode_demo/run_opencode_env_gen.py` 自动化调用本地 OpenCode CLI 的 `run` 命令；默认使用 `opencode_demo/2896_prediction-trader` 与 `opencode_demo/env_2896_prediction-trader` 作为参考，目标为 `skills_demo/2515-stock-monitor`，输出到 `exps/data-synthesis-workflow/env_2515_stock-monitor`。生成的新环境应说明 `run_id` 如何与轨迹、快照、日志和评估结果关联。

## trajectory_evaluator.md

**用途**：对 `agent_demo/runs/<run_id>/out_trajectory.json` 这类多轮对话轨迹调用大模型做质量评估，产出整体评分、幻觉风险、任务完成度与理由。

**输入**：完整轨迹 JSON（含 `run_id`、`turns`、`final_state_snapshot`、`expected_output`、`expected_final_state` 等）。支持 turn-based 与 flat 两种 `turns` 格式。新的 `final_state_snapshot` 优先使用 run-scoped 结构，并可附带共享静态表。

**输出**：JSON 含 `score`（0.0–5.0）、`hallucination_risk`、`task_completion_score`（0.0–1.0）、`reason`。评估前可先进行程序化验证，结果作为上下文供 LLM 参考。

**调用方式**：由 `trajectory_eval_demo/run_trajectory_eval.py` 注入 `{TRAJECTORY_JSON}` 及程序化验证结果后调用 LLM。
