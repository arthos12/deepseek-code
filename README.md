# DeepSeek Code

CLI coding agent for DeepSeek models. Agentic loop, streaming output, 10+ tools, session persistence, parallel execution.

## Install

```bash
# 1. Enter the project directory
cd deepseek-code

# 2. Install in editable mode
pip install -e .

# 3. Set your API key (or enter interactively on first run)
# Option A: Environment variable
set DEEPSEEK_API_KEY=sk-your-key-here

# Option B: Put in settings.local.json
echo {"api_key": "sk-your-key-here"} > settings.local.json
```

Requirements: Python 3.10+, `openai`, `rich`, `pydantic` (installed automatically).

## Quick Start

```bash
# Interactive mode — shows welcome screen + recent sessions
deepseek chat

# One-shot task
deepseek chat -p "fix the login bug in auth.py"

# Resume a session
deepseek chat -s <session_id>

# Use DeepSeek R1 for complex reasoning
deepseek chat -m deepseek-reasoner -p "analyze this crash dump"
```

## Commands

| Command | Description |
|---------|-------------|
| `deepseek chat` | Start interactive session. Shows recent sessions, pick one or start new. |
| `deepseek chat -p "..."` | One-shot task, no interactive mode. |
| `deepseek chat -s <id>` | Resume a specific session by ID. |
| `deepseek resume` | List all saved sessions, pick one interactively. |
| `deepseek resume <id>` | Show session info. |
| `deepseek resume <id> -p "..."` | Continue a session with a new prompt. |
| `deepseek list` | List sessions (compact). |
| `deepseek delete <id>` | Delete a session. |

Interactive mode shortcuts: type `1`-`5` for common tasks (new feature/debug/review/search/test), or just describe your task. Type `/exit` to quit.

## Session Management

Sessions are saved as JSONL files under `sessions/`. Each session records the full conversation history and can be resumed later.

```bash
# List all sessions with titles
deepseek list

# Output:
#   fix the login bug
#   deepseek-chat  2026-05-16 22:37  36 msgs
#   add dark mode toggle
#   deepseek-chat  2026-05-16 21:41  15 msgs

# Resume a session
deepseek resume <id> -p "continue refactoring"
```

## Model Routing

DeepSeek Code automatically selects the right model:

| Task | Model | Context |
|------|-------|---------|
| Daily coding, writing, search | DeepSeek V4 (`deepseek-chat`) | 1M |
| Debugging, error analysis, security review | DeepSeek R1 (`deepseek-reasoner`) | 128K |

You can override with `-m`:
```bash
deepseek chat -m deepseek-reasoner -p "debug this crash"
deepseek chat -m deepseek-chat -p "add a new endpoint"
```

## Configuration

`settings.json` — default configuration. `settings.local.json` — your overrides (gitignored, for API keys and personal preferences).

Key settings:

```json
{
  "model": "deepseek-chat",
  "max_turns": 50,
  "default_shell": "powershell",
  "memory_auto_save": false,
  "permissions": {
    "allow": ["Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite", "Agent"],
    "ask": ["Shell"],
    "deny": ["Read(*.pem)", "Read(*.key)", "Write(*.env*)", "Read(*wallet*)", "Shell(rm -rf /*)"]
  }
}
```

Set project directory:
```bash
set DEEPSEEK_PROJECT_DIR=D:/my-project
```

## Memory System

DeepSeek Code reads `DEEPSEEK.md` at the project root and `memory/` for reference docs.

```
deepseek-code/
├── DEEPSEEK.md              ← Project description + memory index
└── memory/
    ├── coding.md             ← Coding conventions
    └── git_conventions.md    ← Git workflow
```

Add your own memory files and reference them in `DEEPSEEK.md`:
```markdown
- [memory/my_rules.md](memory/my_rules.md) — My project rules
```

## Tools

| Tool | Description |
|------|-------------|
| Read | Read file contents (offset/limit) |
| Write | Create or overwrite a file |
| Edit | Exact string replacement in file |
| Glob | Find files by pattern |
| Grep | Search files by regex (ripgrep or Python fallback) |
| Shell | Run shell commands |
| WebSearch | Search the web (DuckDuckGo) |
| WebFetch | Fetch and extract text from a URL |
| TodoWrite | Track task progress |
| Agent | Spawn sub-agent for independent tasks |

## Skills

`skills/` directory — loadable SKILL.md files:

| Skill | Purpose |
|-------|---------|
| brainstorming | Explore approaches before implementing |
| systematic-debugging | Diagnose bugs step by step |
| test-driven-development | Write tests before code |

Add custom skills: create `skills/<name>/SKILL.md`.

## Security

- Project directory is the boundary — operations outside require user approval
- Sensitive files (.env, private keys, wallet files, system directories) are always blocked
- Shell is the only tool that requires user confirmation by default

## Development

```bash
# Install in editable mode
pip install -e .

# Run tests
python tests/test_system.py

# Run specific test
python -m pytest tests/ -k "test_read"
```

## Troubleshooting

**API key not set**: Run `deepseek chat` — it will prompt you interactively and save to `settings.local.json`.

**SSL errors on push**: Network issue. Retry or use `git -c http.sslVerify=false push`.

**Shell commands fail**: Check that the shell type matches your system. The default is PowerShell on Windows, Bash on Linux/Mac.

**Model repeats output**: Code-level dedup is active. If you still see repetitions, restart the session.

## License

MIT
