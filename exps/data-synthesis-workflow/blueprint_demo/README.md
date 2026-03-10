# 任务蓝图生成 Demo

使用 `prompts/task_blueprint_generator.md` 提示词，结合 SKILL.md、tools.jsonl、persona 调用大模型生成多轮对话任务蓝图。

采用**两阶段蓝图**设计：输出**任务配置**（用户意图、期望工具调用序列、期望状态与输出）与**交互生成配置**（system_message、user_agent_config、max_turns、end_condition），**无**预定义的 queries 数组。具体每轮用户消息由 agent_demo 阶段的 User Agent 根据对话上下文动态生成。

## 依赖

- 项目根目录 `.env` 中配置：
  - `OPENAI_API_KEY`（必填）
  - `OPENAI_MODEL`（必填）
  - `OPENAI_BASE_URL`（可选，兼容非 OpenAI 兼容接口）

## 运行

在项目根目录执行：

```bash
uv run python exps/data-synthesis-workflow/blueprint_demo/run_blueprint.py
```

或先激活项目虚拟环境后：

```bash
python exps/data-synthesis-workflow/blueprint_demo/run_blueprint.py
```

## 输入文件

- 提示词：`exps/data-synthesis-workflow/prompts/task_blueprint_generator.md`
- Skill：`exps/data-synthesis-workflow/opencode_demo/2896_prediction-trader/SKILL.md`
- 工具列表：`exps/data-synthesis-workflow/opencode_demo/env_2896_prediction-trader/tools.jsonl`
- 用户画像：`persona/persona_5K.jsonl`（当前取第一行）

## 输出

- 控制台打印完整蓝图（含程序注入的 `blueprint_id`、`skill_name`、`persona_id`、`created_at`）
- 同目录下写入 `out_blueprint.json`
- 蓝图结构：
  - **任务配置**：`task_id`、`goals`、`possible_tool_calls`（可能的工具调用，与 goals 一一对应）、`expected_final_state`
  - **交互生成配置**：`user_agent_config`（role、personality、knowledge_boundary）、`end_condition`
- 供 agent_demo 动态用户模拟使用
