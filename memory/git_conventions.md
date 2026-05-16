---
name: git_conventions
description: Git 提交与分支规范
type: reference
---

## 提交信息

```
<type>: <简短描述>

<详细说明（可选）>
```

类型：`feat` / `fix` / `refactor` / `docs` / `test` / `chore`

## 规则

- 不 amend 已推送的提交
- 不 force push 到 main/master
- 不跳过 hooks（`--no-verify`）
- 提交前验证改动（跑测试、检查 diff）
- 新功能配测试

## 常用操作

- 查看改动：`git diff` / `git status`
- 暂存特定文件：`git add <file>`，不用 `git add .`
- 不提交 secrets、`.env`、`node_modules`、`__pycache__`
