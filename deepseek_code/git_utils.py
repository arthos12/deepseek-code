"""Git utilities — status, diff, branch awareness."""

import subprocess
import os
from pathlib import Path


def is_git_repo(path: str = ".") -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5,
            cwd=path,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_status(path: str = ".") -> str:
    """Get git status summary."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=path, encoding="utf-8", errors="replace",
        )
        return result.stdout.strip() or "(clean)"
    except Exception as e:
        return f"(git error: {e})"


def get_branch(path: str = ".") -> str:
    """Get current branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
            cwd=path, encoding="utf-8", errors="replace",
        )
        return result.stdout.strip() or "?"
    except Exception:
        return "?"


def diff_file(filepath: str, staged: bool = False, path: str = ".") -> str:
    """Get git diff for a specific file."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    cmd.append("--")
    cmd.append(filepath)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=10,
            cwd=path, encoding="utf-8", errors="replace",
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(diff error: {e})"


def diff_all(path: str = ".") -> str:
    """Get full git diff of working tree."""
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=15,
            cwd=path, encoding="utf-8", errors="replace",
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(diff error: {e})"


def diff_unified(filepath: str, old_content: str, new_content: str, max_lines: int = 200) -> str:
    """Generate a unified diff between two strings (no git required)."""
    import difflib
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
    )
    result = "".join(diff)
    if not result:
        return "(no changes)"
    lines = result.split("\n")
    if len(lines) > max_lines:
        result = "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    return result
