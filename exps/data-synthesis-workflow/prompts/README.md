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
