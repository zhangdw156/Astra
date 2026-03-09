# 任务蓝图生成 Demo

使用 `prompts/task_blueprint_generator.md` 提示词，结合 SKILL.md、tools.jsonl、persona 调用大模型生成多轮对话任务蓝图。

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
- Skill：`exps/data-synthesis-workflow/2896_prediction-trader/SKILL.md`
- 工具列表：`exps/data-synthesis-workflow/prediction-trader/tools.jsonl`
- 用户画像：`persona/persona_5K.jsonl`（当前取第一行）

## 输出

- 控制台打印完整蓝图（含程序注入的 `blueprint_id`、`skill_name`、`persona_id`）
- 同目录下写入 `out_blueprint.json`
- 蓝图中包含模型生成的 `system_message`（助手系统说明）与 `queries`（多轮 query + tool_sequence），供 agent_demo 多轮模拟使用
