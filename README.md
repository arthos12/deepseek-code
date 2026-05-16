# DeepSeek Code

CLI coding agent for DeepSeek models. Agentic loop, streaming, 10 tools, session persistence.

## Install

```bash
cd deepseek-code
pip install -e .
```

## Commands

```bash
deepseek chat                  # Interactive mode — shows recent sessions, start new or resume
deepseek chat -p "fix a bug"  # One-shot task
deepseek chat -s <id>         # Resume a specific session
deepseek chat -m deepseek-reasoner -p "..."  # Use R1 for complex reasoning

deepseek resume                # List all saved sessions
deepseek resume <id>           # Show session info
deepseek resume <id> -p "..."  # Continue a session

deepseek list                  # List sessions (compact)
deepseek delete <id>           # Delete a session
```

## API Key

Set `DEEPSEEK_API_KEY` env var, or put in `settings.local.json`:

```json
{"api_key": "sk-..."}
```

First run prompts you interactively and saves it.

## Config

`settings.json` — defaults. `settings.local.json` — your overrides (gitignored).

Key settings: `model`, `max_turns`, `permissions`, `default_shell`.

## Project directory

DeepSeek Code works within its current directory. Files outside require approval.
Sensitive files (.env, private keys, system dirs) are always blocked.
Set `DEEPSEEK_PROJECT_DIR` to change the project boundary.

## Tools

Read · Write · Edit · Glob · Grep · Shell · WebSearch · WebFetch · TodoWrite · Agent

## Sessions

Saved as JSONL under `sessions/`. Resume with `deepseek chat` (interactive picker)
or `deepseek resume <id>`.

## License

MIT
