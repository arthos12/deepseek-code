"""Glob file pattern matching tool."""

import os
import glob as glob_mod
from deepseek_code.tools.base import BaseTool, ToolResult


class GlobTool(BaseTool):
    name = "Glob"
    description = "Find files by glob pattern. Returns sorted paths."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern, e.g. '**/*.py' or 'src/**/*.ts'",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in. Defaults to current working directory.",
            },
        },
        "required": ["pattern"],
    }

    def execute(self, params: dict) -> ToolResult:
        pattern = params.get("pattern", "*")
        search_path = params.get("path") or os.getcwd()

        try:
            full_pattern = os.path.join(search_path, pattern)
            matches = glob_mod.glob(full_pattern, recursive=True)
            matches = sorted(matches, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)

            if not matches:
                return ToolResult(content=f"No files matched: {pattern}")
            return ToolResult(content="\n".join(matches[:200]))
        except Exception as e:
            return ToolResult(content=f"Glob error: {e}", is_error=True)
