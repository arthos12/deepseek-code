"""System prompt — principles, not micromanagement. Model exercises judgment."""

import os
import platform
import sys
from pathlib import Path


def build_system_prompt(skills_dir: str = "./skills", project_dir: str = ".") -> str:
    skill_descriptions = _load_skill_descriptions(skills_dir)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    default_shell = "PowerShell" if platform.system() == "Windows" else "Bash"
    memory_content = _load_memory_content(project_dir)

    return f"""You are DeepSeek Code, a warm and reliable coding partner.

{memory_content}

Working environment: {platform.system()} with {default_shell}, Python {python_version}. Project: {project_dir}. Skills: {skill_descriptions if skill_descriptions else "none"}.

Match the user's language — if they write in Chinese, reply in Chinese. If English, reply in English.

When starting any multi-step task, use TodoWrite immediately to plan and track your progress. Update it as you go. Before answering "where were we", check your TodoWrite list first.

Talk like a colleague at your desk, not a manual. If the user asks a short question, a short answer is great. When writing code, be thorough and precise. After changes, verify they work. Don't access files outside the project without asking, and never touch sensitive files like .env or private keys.
"""
    return prompt


def _load_memory_content(project_dir: str) -> str:
    """Load actual memory file contents into system prompt — like CLAUDE.md injection."""
    memory_dir = Path(project_dir) / "memory"
    deepseek_md = Path(project_dir) / "DEEPSEEK.md"
    parts = []

    # Load DEEPSEEK.md
    if deepseek_md.exists():
        try:
            content = deepseek_md.read_text(encoding="utf-8").strip()
            parts.append(f"## Project context (DEEPSEEK.md)\n{content}")
        except Exception:
            pass

    # Load all memory/*.md files
    if memory_dir.is_dir():
        for md in sorted(memory_dir.glob("*.md")):
            if md.name == "MEMORY.md":
                continue
            try:
                content = md.read_text(encoding="utf-8").strip()
                if len(content) > 800:
                    content = content[:800] + "\n...(truncated)"
                parts.append(f"## Memory: {md.stem}\n{content}")
            except Exception:
                pass

    if parts:
        return "\n\n".join(parts)
    return "No memory files loaded."


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
