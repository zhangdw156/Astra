# Issue-Driven Development

Astra 采用 **Issue-driven Development**：先开 Issue 规划，再写代码，PR 必须关联 Issue。

## 工作流

```
Issue 创建 → 讨论/细化 → 开发 → PR（关联 Issue）→ Review → Merge
```

### 1. 创建 Issue

在 [GitHub Issues](https://github.com/zhangdw156/Astra/issues) 选择模板：

| 模板 | 用途 |
|------|------|
| **Task** | 开发任务、实验步骤、重构等 |
| **Feature Request** | 新功能或增强 |
| **Bug Report** | 问题反馈 |

填写完整信息，便于后续实现和 Review。

### 2. 开发

- 从 `main` 拉新分支，命名建议：`<type>/<issue-number>-<short-desc>`  
  例：`feat/3-skill-loader`、`fix/7-hydra-output-dir`
- 实现时参考 Issue 中的 Acceptance Criteria
- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:`, `fix:`, `docs:`, `refactor:` 等

### 3. 提交 PR

- PR 描述中必须包含 `Closes #<issue-number>`
- 勾选 PR 模板中的 Checklist
- 确保 `uv run ruff check .` 和 `uv run pytest` 通过

### 4. Merge

合并后，关联的 Issue 会自动关闭。

## 分支约定

- `main`：稳定主分支
- `feat/*`：新功能
- `fix/*`：Bug 修复
- `docs/*`：文档
- `refactor/*`：重构

## 参考

- [GitHub Issue Templates](https://github.com/zhangdw156/Astra/blob/main/.github/ISSUE_TEMPLATE/)
- [Conventional Commits](https://www.conventionalcommits.org/)
