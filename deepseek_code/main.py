"""DeepSeek Code CLI — entry point."""

import argparse
import json
import locale
import sys
import os
from pathlib import Path

from deepseek_code.config import load_config
from deepseek_code.agent import Agent
from deepseek_code.session import (
    save_session,
    load_session,
    list_sessions,
    delete_session,
)
from deepseek_code.tools.registry import ToolRegistry
from deepseek_code.tools.file_read import ReadTool
from deepseek_code.tools.file_write import WriteTool
from deepseek_code.tools.file_edit import EditTool
from deepseek_code.tools.glob_search import GlobTool
from deepseek_code.tools.grep_search import GrepTool
from deepseek_code.tools.shell import ShellTool
from deepseek_code.tools.web_search import WebSearchTool
from deepseek_code.tools.web_fetch import WebFetchTool
from deepseek_code.tools.todo_write import TodoWriteTool
from deepseek_code.tools.agent_tool import AgentTool
from deepseek_code.tools.memory_save import MemorySaveTool
from deepseek_code.display import Display
from deepseek_code.checkpoint import Checkpoint
from deepseek_code import git_utils


def _ensure_api_key(config: dict, config_dir: str) -> None:
    """如果 api_key 为空，交互式提示用户输入，并持久化到 settings.local.json"""
    if config.get("api_key", ""):
        return

    display = Display()
    display.info("DeepSeek API key not set.")
    print()
    try:
        key = input("Enter your API key (sk-...): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        display.error("No API key provided.")
        sys.exit(1)
    if not key:
        display.error("No API key provided.")
        sys.exit(1)
    if not key.startswith("sk-"):
        display.error("Invalid format (should start with sk-).")
        sys.exit(1)

    config["api_key"] = key

    # 持久化到 settings.local.json
    local_path = Path(config_dir) / "settings.local.json"
    existing = {}
    if local_path.exists():
        try:
            existing = json.loads(local_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing["api_key"] = key
    local_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    display.info(f"API key saved to {local_path}")


def build_registry(config: dict) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ReadTool())
    reg.register(WriteTool())
    reg.register(EditTool())
    reg.register(GlobTool())
    reg.register(GrepTool())
    reg.register(ShellTool())
    reg.register(WebSearchTool())
    reg.register(WebFetchTool())
    reg.register(TodoWriteTool())
    reg.register(AgentTool(main_registry=reg, config=config))
    reg.register(MemorySaveTool(project_dir=config.get("project_dir", ".")))
    return reg


def _detect_lang() -> str:
    """Detect user language from locale. Returns 'zh' or 'en'."""
    try:
        loc = locale.getdefaultlocale()[0] or ""
        return "zh" if loc.startswith("zh") else "en"
    except Exception:
        lang = os.environ.get("LANG", "")
        return "zh" if lang.startswith("zh") else "en"


_TASK_MAP_ZH = {
    "1": "开发新功能", "2": "调试代码，修复 bug", "3": "进行代码审查",
    "4": "搜索代码并进行重构", "5": "运行测试",
}
_TASK_MAP_EN = {
    "1": "Develop a new feature", "2": "Debug code and fix a bug", "3": "Do a code review",
    "4": "Search code and refactor", "5": "Run tests",
}


def _show_startup(model: str, display) -> str:
    """Show welcome screen with logo. Returns detected language."""
    display_name = "DeepSeek V4" if model == "deepseek-chat" else (
        "DeepSeek R1" if model == "deepseek-reasoner" else model
    )
    context_size = "1M" if model == "deepseek-chat" else "128K"
    display.blank()
    display.text(r"""  +----------------------------------+
  |                                  |
  |    D E E P S E E K   C O D E    |
  |                                  |
  |     your coding partner          |
  |                                  |
  +----------------------------------+
         o
          o   ^
           o  |
            o |
             o|""")
    display.text(f"  {display_name} · {context_size} context · v0.1.0")

    # Git status at startup
    if git_utils.is_git_repo("."):
        branch = git_utils.get_branch(".")
        status = git_utils.get_status(".")
        display.text(f"  git: {branch}  {status[:60]}")
    display.blank()
    return _detect_lang()


def cmd_chat(args, config: dict):
    config_dir = os.environ.get("DEEPSEEK_CODE_DIR", str(Path(__file__).resolve().parent.parent))
    _ensure_api_key(config, config_dir)

    display = Display()
    registry = build_registry(config)
    agent = Agent(config, registry)

    resume_msgs = None
    if args.session:
        data = load_session(args.session, config["sessions_dir"])
        if data:
            resume_msgs = data.get("messages", [])
            display.info(f"Resuming session: {args.session}")
        else:
            display.error(f"Session not found: {args.session}")
            return

    prompt = args.prompt
    if not prompt:
        lang = _show_startup(agent.model, display)
        task_map = _TASK_MAP_ZH if lang == "zh" else _TASK_MAP_EN
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                display.blank()
                break
            if user_input == "/exit":
                break
            if user_input == "/new":
                resume_msgs = None
                agent = Agent(config, registry)
                display.info("Fresh session started.")
                continue
            if not user_input:
                continue
            # Session picker
            if user_input in session_map:
                data = load_session(session_map[user_input], config["sessions_dir"])
                if data:
                    resume_msgs = data.get("messages", [])
                    display.info(f"Resumed session {user_input}")
                continue
            if user_input in task_map:
                user_input = task_map[user_input]
            response = agent.run(user_input, resume_msgs)
            resume_msgs = None
            if response and not args.no_save:
                save_session(agent, config)
            display.separator()
        return

    response = agent.run(prompt, resume_msgs)
    if not args.no_save:
        sid = save_session(agent, config)
        display.info(f"Session saved: {sid}")


def cmd_resume(args, config: dict):
    config_dir = os.environ.get("DEEPSEEK_CODE_DIR", str(Path(__file__).resolve().parent.parent))
    display = Display()

    # No session_id → list and let user pick
    if not args.session_id:
        sessions = list_sessions(config["sessions_dir"])
        if not sessions:
            display.info("No sessions found. Start one with: deepseek chat")
            return
        display.info("Available sessions:")
        for i, s in enumerate(sessions[:10], 1):
            title = s.get('title', '')[:50] or s['id'][:8]
            display.text(f"  [{i}] {title}")
            display.text(f"       {s['model']}  {s['updated'][:16]}  {s['message_count']} msgs")
        try:
            choice = input("Pick a number (or Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not choice:
            return
        idx = int(choice) - 1 if choice.isdigit() else -1
        if 0 <= idx < len(sessions):
            args.session_id = sessions[idx]['id']
        else:
            display.error("Invalid choice.")
            return
    # ... continue with session resume below


    data = load_session(args.session_id, config["sessions_dir"])
    if not data:
        display.error(f"Session not found: {args.session_id}")
        return

    if args.prompt:
        _ensure_api_key(config, config_dir)
        display.info(f"Resumed session: {args.session_id} ({data.get('model', '?')}, "
                     f"{len(data.get('messages', []))} messages)")
        registry = build_registry(config)
        agent = Agent(config, registry)
        response = agent.run(args.prompt, data.get("messages", []))
        save_session(agent, config)
    else:
        display.info(f"Session: {args.session_id} ({data.get('model', '?')}, "
                     f"{len(data.get('messages', []))} messages)")
        display.info("Add -p 'your task' to continue.")


def cmd_list(args, config: dict):
    display = Display()
    sessions = list_sessions(config["sessions_dir"])
    if not sessions:
        display.info("No sessions found.")
        return
    display.info(f"{len(sessions)} session(s):")
    for s in sessions:
        title = s.get('title', '')[:50] or s['id'][:8]
        display.text(f"  {title}")
        display.text(f"  {s['model']}  {s['updated'][:19]}  {s['message_count']} msgs")


def cmd_undo(args, config: dict):
    display = Display()
    cp = Checkpoint(config.get("sessions_dir", "./sessions"))

    if args.checkpoint_id:
        record = cp.undo(args.checkpoint_id)
        if record:
            display.info(f"Undone: {record['file']} ({record['id']})")
        else:
            display.error(f"Checkpoint not found: {args.checkpoint_id}")
        return

    checkpoints = cp.list_checkpoints()
    if not checkpoints:
        display.info("Nothing to undo.")
        return

    # Undo latest
    record = cp.undo()
    if record:
        display.info(f"Undone: {record['file']} ({record['id']})")
    else:
        display.info("Nothing to undo.")


def cmd_delete(args, config: dict):
    display = Display()
    if delete_session(args.session_id, config["sessions_dir"]):
        display.info(f"Deleted: {args.session_id}")
    else:
        display.error(f"Not found: {args.session_id}")


def main():
    parser = argparse.ArgumentParser(prog="deepseek-code")
    sub = parser.add_subparsers(dest="command", help="Commands: chat, resume, list, delete")

    p_chat = sub.add_parser("chat", help="Start a new chat")
    p_chat.add_argument("-p", "--prompt", type=str, help="User prompt")
    p_chat.add_argument("-m", "--model", type=str, default="deepseek-chat")
    p_chat.add_argument("-s", "--session", type=str, help="Session ID to resume")
    p_chat.add_argument("--no-save", action="store_true", help="Don't save session")

    p_resume = sub.add_parser("resume", help="Resume a session")
    p_resume.add_argument("session_id", type=str, nargs="?", default=None)
    p_resume.add_argument("-p", "--prompt", type=str, help="Additional prompt")

    sub.add_parser("list", help="List all sessions")

    p_del = sub.add_parser("delete", help="Delete a session")
    p_del.add_argument("session_id", type=str)

    p_undo = sub.add_parser("undo", help="Undo last file change")
    p_undo.add_argument("checkpoint_id", type=str, nargs="?", default=None)

    try:
        args = parser.parse_args()
    except SystemExit:
        # Catch common mistakes and suggest correct usage
        import sys as _sys
        _args = _sys.argv[1:] if len(_sys.argv) > 1 else []
        if "resume" in _args and "chat" in _args:
            print("Did you mean?  deepseek resume    (list and pick a session)")
            print("            or  deepseek chat -s <id>  (resume specific session)")
            print("            or  deepseek chat           (interactive with session picker)")
        _sys.exit(1)
        return  # unreachable

    # Determine config dir — use package directory by default
    _default_config_dir = str(Path(__file__).resolve().parent.parent)
    config_dir = os.environ.get("DEEPSEEK_CODE_DIR", _default_config_dir)
    config = load_config(config_dir)

    if args.command == "chat":
        cmd_chat(args, config)
    elif args.command == "resume":
        cmd_resume(args, config)
    elif args.command == "list":
        cmd_list(args, config)
    elif args.command == "delete":
        cmd_delete(args, config)
    elif args.command == "undo":
        cmd_undo(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
