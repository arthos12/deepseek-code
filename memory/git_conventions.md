---
name: git_conventions
description: Git 规范与工作流
type: reference
---

## 仓库

https://github.com/arthos12/deepseek-code

## 提交流程

- 修改代码后，手动 `git add` + `git commit` + `git push`
- 不自动提交，需用户确认
- Co-Authored-By: Claude Code <noreply@anthropic.com>

## 提交格式

```
<type>: <简短描述>

- 改动点 1
- 改动点 2
```

类型: `feat` `fix` `refactor` `docs` `test` `chore`
