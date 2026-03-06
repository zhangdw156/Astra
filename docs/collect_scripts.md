# collect_scripts 脚本

`astra.scripts.collect_scripts` 递归遍历 `skillshub/`，将含有可执行 `scripts` 子目录的目录复制到 `skills/`。

## 作用

- 递归遍历 `skillshub_root` 下所有目录
- 若某目录存在 `scripts` 子目录且其中包含可执行脚本，则将该目录复制到 `skills_output`
- 支持 **dry_run**（仅打印）和 **run**（实际复制）两种模式

## 可执行脚本判定

满足以下任一条件即视为可执行脚本：

- 文件具有执行权限（`chmod +x`）
- 文件首行含 shebang（`#!/usr/bin/env python` 等）
- 文件扩展名为 `.py`、`.sh`、`.bash`、`.zsh`

## 配置

通过 Hydra 加载配置，默认配置：`exps/skill_discovery/collects.yaml`。也可以通过 Hydra 的 `--config-path` 与 `--config-name` 切换配置：

```yaml
skillshub_root: skillshub   # skillshub 根目录（相对项目根）
skills_output: skills       # 输出目录
mode: dry_run               # dry_run | run
```

## 使用

**建议在项目根目录执行**，以便相对路径正确解析。

```bash
# 使用默认配置
uv run python -m astra.scripts.collect_scripts

# run 模式：实际复制
uv run python -m astra.scripts.collect_scripts mode=run

# 命令行覆盖或显式指定配置
uv run python -m astra.scripts.collect_scripts mode=run skillshub_root=/path/to/skillshub
uv run python -m astra.scripts.collect_scripts --config-path=exps/skill_discovery --config-name=collects mode=run
```

**exps/skill_discovery/run.sh**：可选传入配置文件路径，其余为 Hydra overrides：

```bash
./exps/skill_discovery/run.sh
./exps/skill_discovery/run.sh mode=run
```
