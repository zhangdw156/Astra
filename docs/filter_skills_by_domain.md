# filter_skills_by_domain 脚本

`astra.scripts.filter_skills_by_domain` 基于 `artifacts/multi_turn_func_doc` 归纳的领域描述，用 OpenAI 对 `skills/` 下每个 skill 做「是否覆盖这些领域」的判定，只保留判定为符合的 skill，并写出保留列表。

## 作用

- 从 `artifacts/multi_turn_func_doc/` 下各 NDJSON 归纳出**目标领域摘要**（供 System 提示）
- 对 `skills_dir` 下每个子目录：读取 **SKILL.md 全部内容** + 目录名，作为 User 提示，调用大模型判定是否匹配任一领域
- 输出：`match=true` 的 skill 目录名写入 `skills_kept.txt`；判定结果缓存到 `filter_result.json`，支持断点续跑

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
artifacts_func_doc_dir: artifacts/multi_turn_func_doc
mode: dry_run    # dry_run | test（仅 1 个 skill）| run
concurrency: 5   # 并发请求数（仅 run 时生效）
```

## 使用

**建议在项目根目录执行**。

```bash
# dry_run：仅打印待判定数量与示例，不调用 API
uv run -m astra.scripts.filter_skills_by_domain

# test：仅处理 1 个 skill，调用 LLM 并写结果，用于验证流程
uv run -m astra.scripts.filter_skills_by_domain mode=test

# run：实际调用 LLM，写保留列表到 Hydra 输出目录下的 skills_kept.txt
uv run -m astra.scripts.filter_skills_by_domain mode=run

# 显式指定配置
uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery --config-name=filter_by_domain mode=run
```

更多说明见 [exps/skill_discovery/README.md](../exps/skill_discovery/README.md) 中的「领域过滤」小节。
