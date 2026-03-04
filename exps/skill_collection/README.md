# Skill Collection 实验

本实验负责把外部 skill 仓库纳入 `skillshub/`，作为后续收集与标准化 Skills 的素材来源。  
管理方式：**用 YAML 配置仓库列表，只更新项目根目录的 `.gitmodules`**，不在此处执行 `git submodule add` 或 clone。

## 目的

- 通过配置文件维护要拉取的第三方 skill 仓库列表
- 用项目内脚本根据 YAML 只改写 `.gitmodules`（相对路径）
- 实际克隆/更新 submodule 由仓库根目录的 Git 命令完成
- 后续可在此实验内扩展：从 skillshub 解析、归一化为统一 Skill 格式，并校验后放入 `skills/`

## 怎么做

### 1. 编辑仓库列表

编辑 **`exps/skill_collection/repos.yaml`**，在 `repos` 下列出 GitHub 仓库 URL（可带 `.git` 后缀，会按需规范化）：

```yaml
repos:
  - https://github.com/openai/skills
  - https://github.com/anthropics/skills
```

对应在仓库中的路径为：`skillshub/{owner}_{repo}`（例如 `skillshub/openai_skills`）。

### 2. 只更新 .gitmodules

在**项目根目录**执行本实验的脚本（会传入本实验的 `repos.yaml`）：

```bash
./exps/skill_collection/run.sh
```

或直接传入本实验的配置文件：

```bash
uv run python -m astra.scripts.update_gitmodules exps/skill_collection/repos.yaml
```

脚本**只根据传入的 YAML 重写根目录的 `.gitmodules`**，不执行 `git submodule add` 或 clone。

### 3. 拉取 / 更新 submodule

更新完 `.gitmodules` 后，在**仓库根目录**自行执行 Git 命令完成克隆或更新：

- 首次或克隆后拉取所有 submodule：
  ```bash
  git submodule update --init --recursive
  ```
- 之后将各 submodule 更新到远端最新：
  ```bash
  git submodule update --remote --recursive
  ```

### 4. Skills 聚合站 URL（供后续爬取）

**`exps/skill_collection/urls.yaml`** 中记录了若干 Skills 聚合站/目录站的 URL（如 SkillsMP、Agent Skills、SkillStore 等），供将来通过爬虫方式发现、过滤并收集更多 skills 时使用。当前仅做登记，尚未接入爬取逻辑。

## 小结

| 步骤           | 操作                         |
|----------------|------------------------------|
| 配置仓库列表   | 编辑 `exps/skill_collection/repos.yaml` |
| 只改 .gitmodules | 运行 `./exps/skill_collection/run.sh`（或上面的 `uv run python -m ...`） |
| 真正拉取/更新  | 在根目录执行 `git submodule update --init --recursive` 等 |
| 聚合站 URL     | 编辑 `exps/skill_collection/urls.yaml`（供后续爬取） |

脚本与配置均只针对 **`.gitmodules` 的维护**；克隆与更新一律交给 Git 命令在项目根完成。
