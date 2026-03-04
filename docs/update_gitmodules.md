# update_gitmodules 脚本

`astra.scripts.update_gitmodules` **接受一个仓库列表 YAML 文件路径**，根据其内容仅更新项目根目录的 `.gitmodules` 文件，不执行 `git submodule add` 或 clone。

## 作用

- 从传入的 YAML 文件中读取 GitHub 仓库 URL 列表（支持 `repos` / `repositories` 或顶层 list，格式见下方）。
- 将每个 URL 按 `skillshub/{owner}_{repo}` 写入 `.gitmodules`（相对路径），已存在的 path 会保留不重复添加。
- 更新完成后，需在仓库根目录自行执行 `git submodule update --init --recursive` 拉取 submodule。

## 文件格式

YAML 文件示例（`repos` 或 `repositories` 下列出 URL，可含注释）：

```yaml
repos:
  - https://github.com/openai/skills
  # - https://github.com/anthropics/skills
```

## 使用

在**项目根目录**执行，传入仓库列表文件路径（相对当前工作目录或绝对路径）：

```bash
uv run python -m astra.scripts.update_gitmodules <repos.yaml 路径>
```

示例：

```bash
# 使用本实验的配置
uv run python -m astra.scripts.update_gitmodules exps/skill_collection/repos.yaml

# 使用项目 configs 中的配置（真正可执行，发布前会确认）
uv run python -m astra.scripts.update_gitmodules configs/repos.example.yaml

# 使用 examples 下的示例
uv run python -m astra.scripts.update_gitmodules examples/update_gitmodules/repos.example.yaml
```

## configs/ 与实验脚本

- **configs/**：存放**真正可用于执行的配置文件**；skill_collection 实验完成后、项目发布前会由维护者确认。当前为 `repos.example.yaml`。
- **exps/skill_collection/run.sh**：执行**本实验的专用配置**，即传入 `exps/skill_collection/repos.yaml` 并调用上述脚本。

## 示例

**可运行的示例** 见 **`examples/update_gitmodules/`**：

- `repos.example.yaml` — 示例仓库列表格式。
- `run.sh` — 示例：传入该目录下的 repos 文件路径并执行脚本。

文档以本文档为准；examples 目录内仅保留可运行示例与必要注释。
