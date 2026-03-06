# Skill Discovery 实验

本实验负责从 `skillshub/` 中发现含可执行脚本的 skill 目录，并复制到 `skills/` 供后续使用。

## 目的

- 递归遍历 `skillshub/` 下所有目录
- 若某目录存在 `scripts` 子目录且其中包含可执行脚本，则将该目录复制到 `skills/`
- 支持 **dry_run**（仅打印将执行的操作）和 **run**（实际复制）两种模式

## 可执行脚本判定

满足以下任一条件即视为可执行脚本：

- 文件具有执行权限（`chmod +x`）
- 文件首行含 shebang（`#!/usr/bin/env python` 等）
- 文件扩展名为 `.py`、`.sh`、`.bash`、`.zsh`

## 用法

### 1. 配置文件

参数通过 Hydra 配置指定，默认配置：`exps/skill_discovery/collect_scripts.yaml`。也可以通过 Hydra 的 `--config-path` 与 `--config-name` 切换配置：

```yaml
skillshub_root: skillshub   # skillshub 根目录
skills_output: skills      # 输出目录
mode: dry_run              # dry_run | run
```

### 2. 运行

**建议在项目根目录执行**，以便相对路径正确解析。

```bash
# 使用默认配置
uv run -m astra.scripts.collect_scripts

# dry_run（默认） / run 模式
uv run -m astra.scripts.collect_scripts mode=run

# 覆盖配置项
uv run -m astra.scripts.collect_scripts mode=run skillshub_root=/path/to/skillshub
uv run -m astra.scripts.collect_scripts --config-path=exps/skill_discovery --config-name=collect_scripts mode=run
```

### 3. 快捷脚本

`run.sh` 会先切换到项目根目录再执行，因此从任意目录运行均可；可传入 Hydra 覆盖参数（如 `mode=run`）。

```bash
./exps/skill_discovery/run.sh                                    # 默认配置，dry_run
./exps/skill_discovery/run.sh mode=run                           # 实际复制
```

## 小结

| 步骤     | 操作                                                         |
|----------|--------------------------------------------------------------|
| 配置参数 | 编辑 `exps/skill_discovery/collect_scripts.yaml` 或命令行覆盖 |
| dry_run  | `./exps/skill_discovery/run.sh` 或直接 `uv run -m astra.scripts.collect_scripts` |
| 实际复制 | `./exps/skill_discovery/run.sh mode=run` |

---

## 领域过滤（filter_skills_by_domain）

在将大量 skill 复制到 `skills/` 后，可用本步骤按「是否覆盖 `artifacts/multi_turn_func_doc` 涉及领域」进行过滤，只保留与这些领域相关的 skill，减少后续使用规模。

### 原理

- **领域摘要**：从 `artifacts/multi_turn_func_doc/` 下各 JSON（NDJSON）中抽取 tool 的 `description` 与文件名，归纳成一段「目标领域」说明。
- **每个 skill**：用目录名 + 该目录下 **SKILL.md 的全部内容** 作为描述，调用大模型判断是否属于或可覆盖上述任一领域。
- **输出**：保留列表写入 `skills_kept.txt`（及 Hydra 输出目录）；判定结果会缓存到 `filter_result.json`，支持断点续跑。

### 环境变量（.env）

在**项目根目录**创建 `.env`，配置：

- `OPENAI_API_KEY`（必填）
- `OPENAI_MODEL`（必填，如 `gpt-4o-mini`）
- `OPENAI_BASE_URL`（可选，兼容代理或自建端点）

### 配置与运行

默认配置：`exps/skill_discovery/filter_by_domain.yaml`。

```bash
# 建议在项目根目录执行
uv run -m astra.scripts.filter_skills_by_domain              # dry_run，不调用 API
uv run -m astra.scripts.filter_skills_by_domain mode=test     # 仅处理 1 个 skill，验证流程
uv run -m astra.scripts.filter_skills_by_domain mode=run     # 实际调用 LLM 并写保留列表
uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery --config-name=filter_by_domain mode=run
```

| 配置项 | 说明 |
|--------|------|
| `skills_dir` | 待过滤的 skills 根目录（默认 `skills`） |
| `artifacts_func_doc_dir` | multi_turn_func_doc 路径（默认 `artifacts/multi_turn_func_doc`） |
| `mode` | `dry_run` / `test`（仅处理 1 个 skill）/ `run` |
| `concurrency` | 并发请求数（默认 5） |
