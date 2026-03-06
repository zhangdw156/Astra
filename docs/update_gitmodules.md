# update_gitmodules 脚本

`astra.scripts.update_gitmodules` 通过 **Hydra** 加载配置（默认 `exps/skill_collection/repos.yaml`），根据配置中的仓库列表更新项目根目录的 `.gitmodules`，并对尚未在索引中的条目执行 `git submodule add`。

## 作用

- 从 Hydra 配置中读取 GitHub 仓库 URL 列表（支持 `repos` / `repositories` 或顶层 list，格式见下方）。
- 将每个 URL 按 `skillshub/{owner}_{repo}` 写入 `.gitmodules`（相对路径），已存在的 path 会保留不重复添加。
- 对「在配置中但尚未在索引中」的条目执行 `git submodule add`，使后续 `git submodule update --init --recursive` 能正确拉取。

## 文件格式

配置 YAML 示例（`repos` 或 `repositories` 下列出 URL，可含注释）：

```yaml
repos:
  - https://github.com/openai/skills
  # - https://github.com/anthropics/skills
```

## 使用

在**项目根目录**执行：

```bash
uv run python -m astra.scripts.update_gitmodules
uv run python -m astra.scripts.update_gitmodules --config-path=exps/skill_collection --config-name=repos
```

**exps/skill_collection/run.sh**：固定使用 `exps/skill_collection/repos.yaml`：

```bash
./exps/skill_collection/run.sh
```
