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

参数通过 Hydra 配置指定，默认配置：`exps/skill_discovery/collects.yaml`。也可以通过 Hydra 的 `--config-path` 与 `--config-name` 切换配置：

```yaml
skillshub_root: skillshub   # skillshub 根目录
skills_output: skills      # 输出目录
mode: dry_run              # dry_run | run
```

### 2. 运行

**建议在项目根目录执行**，以便相对路径正确解析。

```bash
# 使用默认配置
uv run python -m astra.scripts.collect_scripts

# dry_run（默认） / run 模式
uv run python -m astra.scripts.collect_scripts mode=run

# 覆盖配置项
uv run python -m astra.scripts.collect_scripts mode=run skillshub_root=/path/to/skillshub
uv run python -m astra.scripts.collect_scripts --config-path=exps/skill_discovery --config-name=collects mode=run
```

### 3. 快捷脚本

```bash
./exps/skill_discovery/run.sh                                    # 默认配置，dry_run
./exps/skill_discovery/run.sh mode=run                           # 实际复制
```

## 小结

| 步骤     | 操作                                                         |
|----------|--------------------------------------------------------------|
| 配置参数 | 编辑 `exps/skill_discovery/collects.yaml` 或命令行覆盖 |
| dry_run  | `./exps/skill_discovery/run.sh` 或直接 `uv run python -m astra.scripts.collect_scripts` |
| 实际复制 | `./exps/skill_discovery/run.sh mode=run` |
