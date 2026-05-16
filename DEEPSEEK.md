# DeepSeek Code

CLI coding agent for DeepSeek models. Agentic loop, 10 tools, streaming, session persistence.

## Install

```bash
cd deepseek-code
pip install -e .
deepseek chat
```

## Memory

- [memory/coding.md](memory/coding.md) — Coding conventions
- [memory/git_conventions.md](memory/git_conventions.md) — Git conventions

## Architecture

```
deepseek chat
  └─ main.py         CLI (argparse)
       └─ agent.py    Agentic loop (messages → API → parallel tools → repeat)
            ├─ api.py          DeepSeek API (streaming, model routing)
            ├─ permissions.py  Access control (project scope, sensitive files)
            ├─ display.py      Terminal output (Rich, filler strip)
            ├─ session.py      JSONL persistence
            ├─ sub_agent.py    Sub-agent orchestration
            ├─ skills.py       SKILL.md loader
            ├─ compaction.py   Context window management
            └─ tools/          10 tools

  settings.json          Config
  settings.local.json    Your overrides (gitignored)
  memory/                Reference docs
  skills/                Loadable skills
```

## License

MIT
