# Skill Collection 实验

本实验负责把外部 skill 仓库纳入 `skillshub/`，作为后续收集与标准化 Skills 的素材来源。  
管理方式：**用 YAML 配置仓库列表，运行脚本更新 `.gitmodules` 并对「新增」条目执行 `git submodule add`**，使索引与配置一致，后续 `git submodule update --init` 才能正确拉取。

## 目的

- 通过配置文件维护要拉取的第三方 skill 仓库列表
- 用项目内脚本根据 YAML 重写 `.gitmodules`，并对尚未在 Git 索引中注册的子模块执行 `git submodule add`（克隆并注册）
- 已存在的子模块仅同步 `.gitmodules` 内容（如 ignore），不重复 add
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

### 2. 更新 .gitmodules 并注册新子模块

在**项目根目录**执行本实验的脚本（会传入本实验的 `repos.yaml`）：

```bash
./exps/skill_collection/run.sh
```

或直接调用（使用默认 `exps/skill_collection/repos.yaml`），也可以通过 Hydra 的 `--config-path` 与 `--config-name` 指定配置：

```bash
uv run -m astra.scripts.update_gitmodules
uv run -m astra.scripts.update_gitmodules --config-path=exps/skill_collection --config-name=repos
```

或使用 run.sh 传入配置文件路径：

```bash
./exps/skill_collection/run.sh
```

脚本会根据 YAML 重写 `.gitmodules`，并对 **YAML 中已有但尚未在 Git 索引中注册** 的子模块执行 `git submodule add`（即克隆并写入索引），这样后续 `git submodule update --init` 才会生效。已存在的子模块不会重复 add。

### 3. 拉取 / 更新 submodule

运行脚本后，**新增** 的子模块已被 add 并克隆；若需拉齐所有子模块（例如刚 clone 本仓库后），在**仓库根目录**执行：

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
| 更新 .gitmodules 并注册新子模块 | 运行 `./exps/skill_collection/run.sh`（或上面的 `uv run -m ...`） |
| 真正拉取/更新  | 在根目录执行 `git submodule update --init --recursive` 等 |
| 聚合站 URL     | 编辑 `exps/skill_collection/urls.yaml`（供后续爬取） |

脚本会维护 **`.gitmodules`** 并对**新增**子模块执行 **`git submodule add`**；之后用 Git 命令在项目根做 `submodule update --init` 或 `--remote` 即可拉齐/更新。
