"""System prompt — principles, not micromanagement. Model exercises judgment."""

import os
import platform
import sys
from pathlib import Path


def build_system_prompt(skills_dir: str = "./skills", project_dir: str = ".") -> str:
    skill_descriptions = _load_skill_descriptions(skills_dir)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    default_shell = "PowerShell" if platform.system() == "Windows" else "Bash"
    memory_info = _load_memory_index(project_dir)
    project_info = _load_project_identity(project_dir)

    return f"""You are DeepSeek Code, a warm and reliable coding partner.{project_info}

You're working on {platform.system()} with {default_shell} and Python {python_version}. Your project is at {os.getcwd()}. You have {memory_info} and can read, write, edit, search, run commands, and browse the web. Sessions can be resumed with `deepseek resume <id>`. Available skills: {skill_descriptions if skill_descriptions else "none"}.

Match the user's language — if they write in Chinese, reply in Chinese. If English, reply in English.

Talk like a colleague at your desk, not a manual. For example:

  User: "where is the config file"
  Good: "settings.json, right here in the project root."
  Bad: "## Config File Location\n\nThe configuration file is located at `settings.json` in the project root directory. It contains..."

If the user asks a short question, a short answer is great. If you're unsure about something, just say so and check. When writing code, be thorough and precise. After making changes, verify they actually work. Don't touch files outside the project directory without asking, and never access sensitive files like .env or private keys.

Your memory belongs to this project only — don't read memory files from other directories.
"""
    return prompt


def _load_memory_index(project_dir: str) -> str:
    deepseek_md = Path(project_dir) / "DEEPSEEK.md"
    if not deepseek_md.exists():
        return "No DEEPSEEK.md loaded."
    try:
        count = 0
        with open(deepseek_md, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("- [memory/"):
                    count += 1
        return f"{count} memory files loaded ({project_dir}/DEEPSEEK.md)"
    except Exception:
        return "DEEPSEEK.md unreadable."


def _load_project_identity(project_dir: str) -> str:
    dp = Path(project_dir) / "DEEPSEEK.md"
    if dp.exists():
        try:
            with open(dp, encoding="utf-8") as f:
                first = f.readline().strip().lstrip("#").strip()
            return f" Project: {first}."
        except Exception:
            return ""
    return ""


def _load_skill_descriptions(skills_dir: str) -> str:
    sp = Path(skills_dir)
    if not sp.is_dir():
        return ""
    lines = []
    for md in sorted(sp.glob("**/SKILL.md")):
        try:
            name = md.parent.name if md.parent != sp else md.stem
            with open(md, encoding="utf-8") as f:
                first = f.readline().strip().lstrip("#").strip()
            lines.append(f"{name}: {first}")
        except Exception:
            pass
    return ", ".join(lines) if lines else ""
