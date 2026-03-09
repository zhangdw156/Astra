# 轨迹质量评估 Demo（trajectory_eval_demo）

使用 prompts/trajectory_evaluator.md 提示词 + agent_demo/out_trajectory.json 调用大模型，对单条多轮对话轨迹做质量 / 幻觉评估。

评估输出结构化 JSON，包含整体评分、幻觉风险标签、优缺点与修复建议，可作为数据合成流水线的第二道「质量门」。

## 依赖

- 项目根目录 `.env` 中配置：
  - `OPENAI_API_KEY`（必填）
  - `OPENAI_MODEL`（必填）
  - `OPENAI_BASE_URL`（可选，兼容非 OpenAI 兼容接口）
- 安装依赖：

```bash
pip install openai python-dotenv
# 或者
uv pip install openai python-dotenv
```

## 运行

在项目根目录执行：

```bash
python exps/data-synthesis-workflow/trajectory_eval_demo/run_trajectory_eval.py \
  --trajectory exps/data-synthesis-workflow/agent_demo/out_trajectory.json
```

可选参数：

- `--trajectory <path>`：轨迹 JSON 路径（默认 `exps/data-synthesis-workflow/agent_demo/out_trajectory.json`）
- `--output / -o <path>`：评估结果输出路径（默认 `trajectory_eval_demo/out_trajectory_eval.json`）

## 输入格式

默认输入为 `agent_demo/run_agent_simulation.py` 生成的 `out_trajectory.json`，结构大致如下：

- `blueprint_id` / `skill_name` / `persona_id`
- `system_message`：原始系统提示词
- `agent_system_prompt`：qwen-agent 实际看到的完整 system prompt（含工具说明）
- `tools`：可用工具名称列表
- `turns`：完整多轮对话轨迹，每项为：
  - `role`：`"user"` / `"assistant"` / `"function"`
  - `content`：自然语言文本或工具返回内容
  - 可选 `reasoning_content`：模型思考过程（仅用于理解意图，不直接作为训练数据）
  - 可选 `function_call`：当 role 为 `"assistant"` 时的工具调用信息

## 提示词与输出

评估使用的提示词位于：

- `exps/data-synthesis-workflow/prompts/trajectory_evaluator.md`

模型输出为一个 JSON 对象，示意结构：

```json
{
  "score": 4.3,
  "hallucination_risk": "low",
  "labels": {
    "has_hallucination": false,
    "tool_misuse": false,
    "contradicts_tool_results": false,
    "ignores_tool_results": false,
    "low_relevance": false,
    "unsafe_content": false
  },
  "reasoning": {
    "summary": "...",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "suggested_fixes": ["..."]
}
```

后续可以在数据合成主流程中：

- 过滤掉 `score` 低于阈值或标记 `hallucination_risk` 较高的样本
- 利用 `suggested_fixes` 作为再生成 / 人工检查的参考

