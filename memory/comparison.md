---
name: comparison
description: DeepSeek Code vs Claude Code vs Codex 功能对比与差距分析
type: analysis
---

## 核心定位

| | Claude Code | OpenAI Codex | DeepSeek Code |
|------|-------------|-------------|---------------|
| 哲学 | 副驾驶 (Copilot) | 员工 (Agent) | 副驾驶 (Copilot) |
| 运行环境 | 本地终端 + IDE | 云沙箱 | 本地终端 |
| 模型成本 | 高 | 高 | 低 (1/10-1/30) |
| 开源 | 否 | 否 | MIT |

## 功能对比

| 功能 | Claude Code | Codex | DeepSeek Code | 差距 |
|------|------------|-------|---------------|------|
| VS Code 扩展 | ✅ 原生 | ✅ | ❌ | 大 |
| IDE 内联建议 | ✅ | ✅ | ❌ | 大 |
| 文件 Diff 视图 | ✅ | ✅ | ❌ | 大 |
| 终端 UI | Ink/React 渲染 | 云端 | Rich/Python | 中 |
| 流式输出 | ✅ | ✅ | ✅ | - |
| 并行工具执行 | 子代理 | 原生大规模 | ThreadPool | 中 |
| 会话持久化 | JSONL | 云端 | JSONL | - |
| 会话恢复 | ✅ | ✅ | ✅ | - |
| Git 感知 | 自动 diff | 深度集成 | ❌ | 大 |
| 自动 commit | ✅ | ✅ | ❌ | 中 |
| MCP 协议 | ✅ | ❌ | ❌ | 中 |
| Hooks 系统 | ✅ | ❌ | ❌ | 中 |
| 权限系统 | 7 种模式 + ML | 4 种模式 | 3 种 (allow/ask/deny) | 中 |
| 只读模式 | ✅ | ✅ | ❌ | 中 |
| 子代理 | ✅ 前后台 | ✅ | ✅ 仅前台 | 中 |
| Plan 模式 | ✅ | ❌ | ❌ | 中 |
| Checkpoint/Undo | ✅ | ❌ | ❌ | 中 |
| Skills 系统 | ✅ | ❌ | ✅ 3 个 | - |
| 记忆系统 | CLAUDE.md | 云端 | DEEPSEEK.md | - |
| 模型路由 | Opus/Sonnet/Haiku | GPT-5.x | V4/R1 自动 | - |
| Prompt Caching | ✅ | ✅ | ❌ API 不支持 | - |
| 图片输入 | ✅ | ✅ | ❌ | 小 |
| Web 搜索 | 内置 | 内置 | DuckDuckGo | 小 |
| 浏览器预览 | ❌ | ✅ | ❌ | 小 |
| 安全审计 | 基础 | ✅ 强 | 基础 | 中 |
| Token 统计 | ✅ | ✅ | ✅ | - |
| SWE-bench | ~72-80% | ~80% (Pro SOTA) | 未测试 | 大 |
| 多语言 | 英文为主 | 英文为主 | 中英双语 | +优势 |
| 启动速度 | 快 | 中等 | 极快 | +优势 |
| Token 效率 | 中等 | 高 | 高 | +优势 |

## 细节差距（按优先级）

### P0 — 缺了就很难受
- **文件 Diff**：改完代码看不到改了什么。Claude Code 有漂亮的 diff 视图
- **Undo/回滚**：改错了没法撤销。Claude Code 有 checkpoint
- **Git 感知**：不知道当前分支、未提交改动。每次都要手动 git status

### P1 — 影响体验
- **权限粒度**：只有 allow/ask/deny。没有只读模式，没有按目录设置权限
- **子代理后台运行**：子代理只能前台跑，不能放手让它后台干活
- **Plan 模式**：没有独立规划阶段。Claude Code 可以先规划再执行

### P2 — 锦上添花
- **VS Code 扩展**：终端之外的另一入口
- **MCP 协议**：接入外部数据源
- **Hooks**：自定义事件拦截
- **图片输入**：DeepSeek API 可能不支持

## VS Code 扩展专项

DeepSeek Code 的 VS Code 扩展需要实现：

1. **侧边栏面板** — 类似 Claude Code 的 chat 面板
2. **内联 Diff** — 改动直接在编辑器里高亮
3. **工具调用可视化** — 可折叠的工具调用历史
4. **文件树集成** — 右键菜单触发 DeepSeek Code
5. **状态栏指示器** — 显示当前模型、token 用量
6. **诊断集成** — 错误/警告直接关联到 DeepSeek Code 分析

这些目前全是空白。
