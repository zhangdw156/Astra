# 轨迹质量评估 Demo（trajectory_eval_demo）

使用 `prompts/trajectory_evaluator.md` 提示词 + 单条 run 轨迹 JSON 调用大模型，对多轮对话轨迹做质量 / 幻觉评估。

**程序化验证**：若轨迹含 `expected_output`、`final_state_snapshot`，先做基于输出与状态的简单检查，结果作为上下文供 LLM 参考。LLM 输出包含 `task_completion_score`（任务完成度）。

## 依赖

- 项目根目录 `.env` 中配置：
  - `OPENAI_API_KEY`（必填）
  - `OPENAI_MODEL`（必填）
  - `OPENAI_BASE_URL`（可选）
- 安装：`pip install openai python-dotenv`

## 运行

```bash
python exps/data-synthesis-workflow/trajectory_eval_demo/run_trajectory_eval.py \
  --trajectory exps/data-synthesis-workflow/agent_demo/runs/<run_id>/out_trajectory.json
```

可选参数：

- `--trajectory <path>`：轨迹 JSON 路径
- `--output / -o <path>`：评估结果输出路径；默认写到同一 run 目录下的 `out_trajectory_eval.json`

## 输入格式

支持两种 `turns` 格式：

- **Turn-based**（新）：每轮含 `turn_index`、`user_message`、`assistant_thinking`、`assistant_message`、`tool_calls`
- **Flat**（兼容）：每项含 `role`、`content`、`reasoning_content`、`function_call`

轨迹可含 `run_id`、`final_state_snapshot`、`expected_output`、`expected_final_state`、`validation`。新的 `final_state_snapshot` 优先使用 run-scoped 结构：`trajectory_run`、`tool_call_logs`、`run_output`、`run_snapshots`，并可附带共享静态表。

## 输出

评估结果 JSON 含：

- `score`：0.0–5.0 整体质量
- `hallucination_risk`：`none` / `low` / `medium` / `high`
- `task_completion_score`：0.0–1.0 任务完成度（结合 expected_output、final_state_snapshot）
- `reason`：评估理由
- `run_id`：与轨迹一致的运行 ID
- `programmatic_validation`：程序化验证结果

可据此过滤低分样本、高幻觉风险样本。

