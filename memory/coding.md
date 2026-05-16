---
name: coding
description: 编码规范与工作流
type: reference
---

## 工作流

1. **Read** — 先读相关文件，不要猜内容
2. **Plan** — 明确输入、输出、边界情况
3. **Write** — 写干净完整的代码，不截断
4. **Review** — 自审查：异常？空值？硬编码？编码？
5. **Verify** — 读回文件或运行测试，确认通过后才报成功

## 基础规则

- 路径正斜杠，encoding="utf-8"，HTTP timeout=30，try/except I/O
- 三行相似代码优于过早抽象
- 不用可变默认参数，不裸 except，不 import *
