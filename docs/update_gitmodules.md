# update_gitmodules 脚本

`astra.scripts.update_gitmodules` 根据 Hydra 配置中的仓库列表 YAML，**仅更新**项目根目录的 `.gitmodules` 文件，不执行 `git submodule add` 或 clone。

## 作用

- 从指定 YAML 中读取 GitHub 仓库 URL 列表（支持 `repos` / `repositories` 或顶层 list）。
- 将每个 URL 按 `skillshub/{owner}_{repo}` 写入 `.gitmodules`（相对路径），已存在的 path 会保留不重复添加。
- 更新完成后，需在仓库根目录自行执行 `git submodule update --init --recursive` 拉取 submodule。

## 配置

- Hydra 配置位于项目根 **`configs/update_gitmodules.yaml`**，其中 `repos_file` 指向仓库列表 YAML 的路径（相对项目根）。
- 仓库列表 YAML 格式示例见下方「示例」或 **`examples/update_gitmodules/`**。

## 使用

在**项目根目录**执行：

```bash
# 使用默认 configs 中的 repos_file
uv run python -m astra.scripts.update_gitmodules

# 指定其他仓库列表文件（Hydra 覆盖）
uv run python -m astra.scripts.update_gitmodules repos_file=examples/update_gitmodules/repos.example.yaml
```

## 示例

**示例配置与运行方式** 见项目内 **`examples/update_gitmodules/`** 目录：

- `repos.example.yaml` — 示例仓库列表（`repos` 键下列出 GitHub URL）。
- `run.sh` — 示例运行命令（默认或覆盖 `repos_file`）。

文档与脚本说明以本文档为准；examples 目录内仅保留可运行的示例与示例所需注释。
