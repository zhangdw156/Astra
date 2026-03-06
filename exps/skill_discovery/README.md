# Skill Discovery 实验

本实验负责从 `skillshub/` 中发现含可执行脚本的 skill 目录，并复制到 `skills/` 供后续使用。

## 目录结构

```
exps/skill_discovery/
├── configs/                    # Hydra 配置
│   ├── collect_scripts.yaml    # 收集脚本配置
│   ├── filter_by_domain.yaml   # 领域过滤配置
│   └── filter_by_executability.yaml  # 可执行性过滤配置
├── results/                    # 生成的 filter 结果（JSONL）
│   ├── filter_domain_result.json
│   └── filter_executability_result.json
├── ensure_skills_demo.py        # 确保 skills_demo 有足够数量
├── prune_skills_from_filter_results.py  # 根据 result 快速 pruning
├── run.sh                      # collect_scripts 快捷入口
└── README.md
```

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

参数通过 Hydra 配置指定，默认配置：`exps/skill_discovery/configs/collect_scripts.yaml`。也可以通过 Hydra 的 `--config-path` 与 `--config-name` 切换配置：

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
uv run -m astra.scripts.collect_scripts --config-path=exps/skill_discovery/configs --config-name=collect_scripts mode=run
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
| 配置参数 | 编辑 `exps/skill_discovery/configs/collect_scripts.yaml` 或命令行覆盖 |
| dry_run  | `./exps/skill_discovery/run.sh` 或直接 `uv run -m astra.scripts.collect_scripts` |
| 实际复制 | `./exps/skill_discovery/run.sh mode=run` |

---

## 领域过滤（filter_skills_by_domain）

在将大量 skill 复制到 `skills/` 后，可用本步骤按「是否覆盖 `artifacts/multi_turn_func_doc` 涉及领域」进行过滤，只保留与这些领域相关的 skill，减少后续使用规模。

### 原理

- **领域摘要**：默认使用包内 `src/astra/scripts/_domain_filter/data/domain_summary.txt`
- **每个 skill**：用目录名 + 该目录下 **SKILL.md 的全部内容** 作为描述，调用大模型判断是否属于或可覆盖上述任一领域。
- **输出**：判定为不匹配的 skill 目录会被直接删除；判定结果会缓存到 `filter_result.json`（默认写入 Hydra 输出目录；本实验配置里固定为 `exps/skill_discovery/results/filter_domain_result.json`），支持断点续跑。

### 环境变量（.env）

在**项目根目录**创建 `.env`，配置：

- `OPENAI_API_KEY`（必填）
- `OPENAI_MODEL`（必填，如 `gpt-4o-mini`）
- `OPENAI_BASE_URL`（可选，兼容代理或自建端点）

### 配置与运行

默认配置：`exps/skill_discovery/configs/filter_by_domain.yaml`。

```bash
# 建议在项目根目录执行
uv run -m astra.scripts.filter_skills_by_domain              # dry-run，不调用 API
uv run -m astra.scripts.filter_skills_by_domain mode=test     # 随机测试 3 个 skill，验证流程
uv run -m astra.scripts.filter_skills_by_domain mode=run     # 实际调用 LLM 并删除不匹配的 skill 目录
uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery/configs --config-name=filter_by_domain mode=run
```

| 配置项 | 说明 |
|--------|------|
| `skills_dir` | 待过滤的 skills 根目录（默认 `skills`） |
| `prompts_dir` | 提示词与领域摘要目录（不配置则使用包内 `src/astra/scripts/_domain_filter/data`，含 `domain_summary.txt`、`filter_system.txt`、`filter_user.txt`） |
| `mode` | `dry-run` / `test`（随机 3 个 skill）/ `run` |
| `concurrency` | 并发请求数（默认 5） |

---

## 可执行性过滤（filter_skills_by_executability）

本步骤按“**Docker 沙箱 + 可 mock**”的可执行性标准过滤 skills，`mode` 只有三个选项：`run` / `test` / `dry-run`（注意 `dry-run` 必须是中划线）。`run/test` 会调用大模型判定是否保留，`dry-run` 只做预览不调用 API。

### 原理

- **执行基线（背景假设）**：默认只允许在 **Docker 容器内执行**（容器可丢弃），因此破坏性文件操作通常可接受；用户信息强绑定（如社交平台/订票）也可通过 mock 绕过。
- **每个 skill**：读取目录名 + `SKILL.md` 内容，并补充 `scripts/` 概要（截断预览 + 提取 URL 证据），用于大模型判断与人类复核。

### 配置与运行

默认配置：`exps/skill_discovery/configs/filter_by_executability.yaml`。

```bash
# 建议在项目根目录执行
uv run -m astra.scripts.filter_skills_by_executability mode=dry-run
uv run -m astra.scripts.filter_skills_by_executability mode=test skills_dir=skills_demo n_test=5
uv run -m astra.scripts.filter_skills_by_executability mode=run
```

常用覆盖参数：

- `scripts_max_files=3 scripts_max_chars=8000`：给 LLM 的脚本概要大小
- `sample_n=3`：`dry-run` 打印多少个示例 skill
- `mode`：`dry-run` / `test`（随机 N 个 skill）/ `run`
- `concurrency`：并发请求数（默认 5）

---

## 根据 filter 结果快速 pruning（prune_skills_from_filter_results）

在已生成 `results/filter_domain_result.json` 和 `results/filter_executability_result.json` 后，可用本脚本根据其中 `match=false` 的条目，删除 skills 目录下对应子目录，实现快速重新构建，无需重新调用 LLM。

### 用法

```bash
# 使用默认两个 result 文件（exps/skill_discovery/results 下），dry-run 预览
uv run exps/skill_discovery/prune_skills_from_filter_results.py --dry-run

# 实际删除
uv run exps/skill_discovery/prune_skills_from_filter_results.py

# 指定 result 文件与 skills 目录
uv run exps/skill_discovery/prune_skills_from_filter_results.py \
  --result-files exps/skill_discovery/results/filter_domain_result.json exps/skill_discovery/results/filter_executability_result.json \
  --skills-dir skills \
  --dry-run
```

| 参数 | 说明 |
|------|------|
| `--skills-dir` | 待 pruning 的 skills 根目录（默认 `skills`） |
| `--result-files` | filter result JSONL 文件列表；不指定则使用 `results/` 下默认两个 |
| `--dry-run` | 仅打印将要删除的目录，不实际删除 |

---

## 可执行性过滤之后的下一步

在完成「可执行性过滤」并得到一批“适合在 Docker 内工具化”的 skills 后，建议按下面两条线推进，以便最终在数据工厂里生成**高质量多轮工具调用轨迹**。

### 1. 为每个 skill 生成 Tool List

**目标**：把每个 skill 的能力抽象成与 `artifacts/multi_turn_func_doc` 一致的**工具 schema**，供轨迹生成与评测使用。

- **输入**：保留下的 skill 目录（`SKILL.md` + `scripts/` 内容）。
- **输出**：每个 skill 对应一份 **tool list**（JSON/NDJSON），每条工具包含：
  - `name`：工具名（如 `search_engine_query`、`get_weather`）
  - `description`：自然语言描述，便于模型选择工具
  - `parameters`：与现有 func_doc 一致的 `type` / `properties` / `required` 等

**实现思路**：

- **规则抽取**：若 skill 已有结构化入口（如 CLI `--help`、Python 函数签名），可解析生成 schema。
- **LLM 生成**：用 SKILL.md + scripts 概要调用大模型，要求输出上述格式的 tool list，便于覆盖文档型、脚本型混合的 skill。

可与 `_executability_filter` 类似，在 `src/astra/scripts/` 下新增 `_tool_extract`（或 `extract_skill_tools`）模块，输出写入 `artifacts/skill_tools/` 或实验目录。

### 2. 为 Tool List / 技能组生成可执行环境（如 Docker 镜像）

**目标**：让每个 skill（或一组依赖相近的 skills）在**可丢弃的 Docker 沙箱**里稳定、可重复执行，便于跑轨迹与 mock。

- **输入**：
  - 上一步得到的 skill 及其 tool list；
  - skill 的依赖声明（如 `metadata.openclaw.requires.bins`、`requirements.txt`、`pyproject.toml` 等）。
- **输出**：
  - **方案 A**：每个 skill 一个 Dockerfile（或镜像），镜像内安装该 skill 的 bins/python 依赖，并把 `scripts/` 挂载或复制进去，通过统一入口（如 `python -m tool_runner --skill X --tool Y --args '...'`）调用对应工具。
  - **方案 B**：按**依赖栈**对 skills 分组（例如同 Python 版本、同组系统包），每组一个基础镜像，skill 以挂载卷或复制方式注入，减少镜像数量、加快构建。

**实现思路**：

- 从 SKILL.md 的 frontmatter（如 `requires.bins`）和仓库内 `requirements.txt` 等收集依赖。
- 用模板生成 Dockerfile：基础镜像（如 `python:3.11-slim`）+ 安装 bins + `pip install` + 暴露统一 CLI 或 HTTP 入口。
- 若需 mock 外部 API，可在同一 Docker 网络内起 mock 服务，或使用录制/重放（如 vcr、responses）在镜像内回放。

### 小结

| 步骤           | 输入                     | 输出                           |
|----------------|--------------------------|--------------------------------|
| 生成 Tool List | 保留的 skill 目录        | 每 skill 一份 tool schema      |
| 可执行环境     | tool list + 依赖声明     | 每 skill 或每组一个 Docker 镜像 |

这样，第二轮过滤之后的方向就是：**先为每个 skill 生成与 multi_turn_func_doc 对齐的 tool list，再为这些 tool list（或按依赖分组）生成可执行环境（如 Docker 镜像）**，为后续多轮轨迹生成与重放打好基础。
