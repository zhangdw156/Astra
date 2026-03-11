# pipeline1：N 人物画像 → N 蓝图 → N 轨迹 → 校验

基于 `env_2896_prediction-trader`（仅 tools.jsonl）与 `persona/persona_5K.jsonl`，随机抽取 N 个人物画像，依次完成：生成 N 个蓝图、采集 N 条轨迹、对每条轨迹做质量评估。

## 特性

- **MCP 复用**：MCP Server 在一开始启动，整个合成过程复用，合成结束后关闭。
- **完整工具定义**：轨迹文件中保存 `tools_jsonl` 字段（tools.jsonl 的完整内容）。
- **无状态任务处理**：如果任务不涉及状态变更（如付款、订票），则 `initial_state` 和 `expected_final_state` 均为 `{}`。
- **直接轨迹评估**：使用原始 `messages` 格式进行评估，无需转换为 turns 格式。

## 依赖

- 项目根 `.env`：支持多 Agent 单独配置（见 `.env.example`）
  - 全局：`OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL`
  - Planner：`PLANNER_*`（生成蓝图）
  - User Agent：`USER_AGENT_*`（生成用户消息）
  - Assistant：`ASSISTANT_*`（执行任务）
  - Tool Agent：`TOOL_AGENT_*`（工具执行）
  - Eval：`EVAL_*`（评估轨迹）
  - 未单独配置的 Agent 会回退使用全局配置
- `uv`、`qwen-agent[mcp]`
- 从**项目根**运行本实验

## 用法

```bash
# 在项目根目录
cd /path/to/Astra

# 默认：随机 20 个人物，生成 20 蓝图、20 轨迹并评估
uv run python exps/data-synthesis-workflow/pipeline1/run.py

# 指定人数与随机种子
uv run python exps/data-synthesis-workflow/pipeline1/run.py --num 20 --seed 42
```

## 输出目录

- `blueprints/`：N 个 `blueprint_<i>.json`
- `trajectories/<i>/out_trajectory.json`：每条轨迹（含 `messages` 和 `tools_jsonl`）
- `evals/<i>/out_trajectory_eval.json`：每条轨迹的评估结果
- `scratch/`：临时 persona 文件（每轮一个）

## 流程

1. 从 `persona/persona_5K.jsonl` 随机抽取 `--num` 条（默认 20）。
2. 启动 MCP Server（将被所有轨迹复用）。
3. 对每条 persona：调用 `blueprint_demo/run_blueprint.py`（`--persona-file`、`--output`）生成蓝图。
   - 若任务不涉及状态变更，则 `initial_state` 和 `expected_final_state` 均设为 `{}`。
4. 对每个蓝图：调用 `agent_demo/run_agent_simulation.py`（`--mcp-url` 复用已有 MCP）采集轨迹。
   - 轨迹中保存 `tools_jsonl` 字段（tools.jsonl 完整内容）。
5. 对每条轨迹调用 `trajectory_eval_demo/run_trajectory_eval.py` 做质量/幻觉评估。
6. 所有轨迹合成完成后关闭 MCP Server。