# Astra — Agentic Skill & TRAce

面向高质量多轮工具调用对话轨迹的数据工厂，用于微调小模型以提升 Agent 能力。

## 概述

- **Skill Registry**：收集并标准化 Skills（Anthropic 风格工具定义）
- **Blueprint Engine**：生成任务蓝图（上下文、需求、计划工具序列）
- **Execution & Trace**：教师 Agent 在 mock 环境中执行并产生轨迹
- **Optimization**：筛选与精炼轨迹，得到微调数据集

## 项目结构

```
Astra/
├── configs/            # 可执行配置文件（发布前会确认）；当前为 repo.yaml
├── src/astra/         # 核心包
├── exps/               # 实验（前期逻辑）
├── examples/           # 使用示例（含脚本、配置示例）
├── skillshub/          # 收集到的外部 skill 仓库（submodule）
├── skills/             # 精选后供使用的 skills
├── artifacts/          # 生成的蓝图与轨迹
├── docs/               # 文档
└── tests/              # 测试
```

## 快速开始

```bash
# 安装依赖
uv sync
```

使用方式见 [exps/skill_collection](exps/skill_collection/README.md)、[examples/](examples/) 与 [docs/](docs/)。

## 环境变量

部分脚本（如领域过滤 `filter_skills_by_domain`）需要从项目根目录的 `.env` 读取配置。请复制示例并填写实际值：

```bash
cp .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY 等
```

`.env` 已加入 `.gitignore`，不会提交到仓库。

## 同步 Submodule（skillshub）

`skillshub/` 下的外部 skill 仓库以 Git submodule 方式管理。脚本只负责**添加** submodule，不负责后续同步。

**首次克隆本仓库后**，拉取 submodule：

```bash
git submodule update --init --recursive
```

**之后要更新** skillshub 下各仓库到最新提交：

```bash
git submodule update --remote --recursive
```

添加/维护 submodule 列表（只改 .gitmodules）见 [exps/skill_collection](exps/skill_collection/README.md)。

## 开发

采用 [Issue-driven Development](docs/development.md)：先开 Issue 再写代码，PR 须关联 Issue。

```bash
uv sync --all-groups   # 含 dev 依赖
uv run pytest         # 测试
uv run ruff check .   # 静态检查
```

## 许可证

MIT
