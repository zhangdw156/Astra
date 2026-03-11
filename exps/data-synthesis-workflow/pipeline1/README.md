# pipeline1：20 人物画像 → 20 蓝图 → 20 轨迹 → 校验

基于 `env_2896_prediction-trader`（仅 tools.jsonl）与 `persona/persona_5K.jsonl`，随机抽取 20 个人物画像，依次完成：生成 20 个蓝图、采集 20 条轨迹、对每条轨迹做质量评估。

## 依赖

- 项目根 `.env`：`OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL`（可选）
- `uv`、`qwen-agent[mcp]`（agent_demo 用）
- 从**项目根**运行本实验

## 用法

```bash
# 在项目根目录
cd /path/to/Astra

# 默认：随机 20 个人物，生成 20 蓝图、20 轨迹并评估
python exps/data-synthesis-workflow/pipeline1/run.py

# 指定人数与随机种子
python exps/data-synthesis-workflow/pipeline1/run.py --num 20 --seed 42
```

## 输出目录

- `blueprints/`：20 个 `blueprint_<i>.json`
- `trajectories/<i>/out_trajectory.json`：每条轨迹（含 messages）
- `trajectories/<i>/out_trajectory_for_eval.json`：转为含 turns 的格式供评估脚本读取
- `evals/<i>/out_trajectory_eval.json`：每条轨迹的评估结果
- `scratch/`：临时 persona 文件（每轮一个）

## 流程

1. 从 `persona/persona_5K.jsonl` 随机抽取 `--num` 条（默认 20）。
2. 对每条 persona：调用 `blueprint_demo/run_blueprint.py`（`--persona-file`、`--output`）生成蓝图。
3. 对每个蓝图：调用 `agent_demo/run_agent_simulation.py`（`--tools-path` 指向 env_2896_prediction-trader 的 tools.jsonl）采集轨迹。
4. 将轨迹由 messages 格式转为含 turns 的格式，供评估脚本使用。
5. 对每条轨迹调用 `trajectory_eval_demo/run_trajectory_eval.py` 做质量/幻觉评估。
