# filter_skills_by_domain 脚本

`astra.scripts.filter_skills_by_domain` 基于 `artifacts/multi_turn_func_doc` 的领域摘要与专用提示词模板，用 OpenAI 对 `skills/` 下每个 skill 做「是否与这些领域相关」的判定，只保留判定为相关的 skill，不匹配的 skill 目录会被直接删除。

## 作用

- **领域摘要**：优先从「提示词数据目录」下的 `domain_summary.txt` 。摘要通过占位符 `{{domain_summary}}` 填入系统提示。
- **提示词**：系统/用户提示从「提示词数据目录」的 `filter_system.txt`、`filter_user.txt` 加载（默认目录为包内 `src/astra/scripts/_filter/data`，可通过配置 `prompts_dir` 覆盖），占位符 `{{domain_summary}}`、`{{skill_content}}` 由脚本替换。判定标准为与任一领域**相关**即保留（不要求完全匹配）。逻辑与数据均在 `astra.scripts._filter` 包内。
- 对 `skills_dir` 下每个子目录：读取目录名 + **SKILL.md 全部内容**，填入 `{{skill_content}}`，调用大模型判定是否与任一领域相关
- 输出：判定为不匹配的 skill 目录会被直接删除；判定结果缓存到 `filter_result.json`，支持断点续跑

## 环境变量

在**项目根目录** `.env` 中配置（由脚本通过 python-dotenv 加载）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是 | OpenAI API 密钥 |
| `OPENAI_MODEL` | 是 | 模型名，如 `gpt-4o-mini` |
| `OPENAI_BASE_URL` | 否 | 兼容代理或自建端点 |

## 配置

通过 Hydra 加载配置，默认：`exps/skill_discovery/filter_by_domain.yaml`。

```yaml
skills_dir: skills
# prompts_dir 不配置时使用包内 src/astra/scripts/_filter/data（含 domain_summary.txt、filter_system.txt、filter_user.txt）
mode: dry_run    # dry_run | test（随机 3 个 skill）| run
concurrency: 5   # 并发请求数（仅 run 时生效）
```

## 使用

**建议在项目根目录执行**。

```bash
# dry_run：仅打印待判定数量与示例，不调用 API
uv run -m astra.scripts.filter_skills_by_domain

# test：随机抽取 3 个 skill，调用 LLM 并写结果，用于验证流程
uv run -m astra.scripts.filter_skills_by_domain mode=test

# run：实际调用 LLM，删除不匹配的 skill 目录（保留的留在 skills_dir 下）
uv run -m astra.scripts.filter_skills_by_domain mode=run

# 显式指定配置
uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery --config-name=filter_by_domain mode=run
```

更多说明见 [exps/skill_discovery/README.md](../exps/skill_discovery/README.md) 中的「领域过滤」小节。
