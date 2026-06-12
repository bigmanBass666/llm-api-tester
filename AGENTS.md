# Rules

1. 配置唯一数据源: `configs/platforms.yaml`
2. 新代码导入路径: `platforms/` (禁止 `crawler/`)
3. 修改代码后运行: `pytest tests/test_platform_config.py -v`
4. Git: `<type>: <中文描述>` (type∈{feat,fix,test,docs,refactor,chore})
## PR / Commit Guidelines

### 分支策略：GitHub Flow

本项目采用 **GitHub Flow**，所有功能/修复/文档变更都通过 PR 合并。

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 稳定主分支 | 只能通过 PR 合入，禁止直接 push |
| `feature/xxx` | 新功能 | 从 `main` 拉取 |
| `fix/xxx` | Bug 修复 | 从 `main` 拉取 |
| `docs/xxx` | 文档变更 | 从 `main` 拉取 |
| `refactor/xxx` | 代码重构 | 从 `main` 拉取 |

**工作流程**：从 `main` 创建功能分支 → 开发提交 → 发起 PR → review 后合并 → 删除功能分支。

> 功能分支应为短生命周期分支，小改动也可直接用 PR from `main`。合并后及时清理。详细 Git 规范见用户全局配置 `~/.claude/rules/git_rules.md`。

## Boundaries

| Action | Rule |
|--------|------|
| `git add .` / `git add -A` | 🚫 **禁止** — 只 `git add` 相关文件，避免带走 `.env`、大文件等敏感内容 |
| 直接 push 到 `main` | 🚫 **禁止** — 所有合并必须走 PR |
| 删除功能分支 | ✅ PR 合并后自动清理 |
| 合并前未跑测试 | ⚠️ 先问用户 — 确认 CI 通过后再合 |

# Structure

```
configs/platforms.yaml → src/platform_config.py → platforms/{nvidia,zhipu}/
src/models.py (ModelInfo, TestResult, TestReport)
tests/ (pytest), examples/, scripts/batch_test.py
```

# Commands

```bash
git commit -m "<type>: <中文描述>"  # post-commit hook 自动 push，无需手动执行

pytest tests/test_platform_config.py -v  # 测试
```
