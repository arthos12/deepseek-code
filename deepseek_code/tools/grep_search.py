"""Regex search tool — uses ripgrep if available, falls back to Python."""

import subprocess
import os
import re
import fnmatch
from pathlib import Path
from deepseek_code.tools.base import BaseTool, ToolResult


class GrepTool(BaseTool):
    name = "Grep"
    description = "Search files by regex. Uses rg or Python re fallback."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in",
            },
            "glob": {
                "type": "string",
                "description": "Glob pattern to filter files, e.g. '*.py'",
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
                "description": "Output mode",
            },
            "-i": {
                "type": "boolean",
                "description": "Case insensitive search",
            },
            "head_limit": {
                "type": "integer",
                "description": "Limit output lines",
            },
        },
        "required": ["pattern"],
    }

    def execute(self, params: dict) -> ToolResult:
        pattern = params.get("pattern", "")
        search_path = params.get("path") or os.getcwd()
        glob_filter = params.get("glob")
        ignore_case = params.get("-i", False)
        output_mode = params.get("output_mode", "content")
        head_limit = params.get("head_limit", 250)

        # Try ripgrep first
        try:
            return self._rg_search(pattern, search_path, glob_filter, ignore_case, output_mode, head_limit)
        except FileNotFoundError:
            # rg not installed — use Python fallback
            try:
                return self._py_search(pattern, search_path, glob_filter, ignore_case, output_mode, head_limit)
            except Exception as e:
                return ToolResult(content=f"Grep error: {e}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Grep error: {e}", is_error=True)

    def _rg_search(self, pattern, search_path, glob_filter, ignore_case, output_mode, head_limit):
        cmd = ["rg", "--no-heading", "--with-filename", "--line-number", "--color=never"]
        if ignore_case:
            cmd.append("-i")
        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")
        if glob_filter:
            cmd.extend(["--glob", glob_filter])
        cmd.append(pattern)
        if os.path.isdir(search_path) or os.path.isfile(search_path):
            cmd.append(search_path)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        return self._format_output(result.stdout.strip(), head_limit, pattern)

    def _py_search(self, pattern, search_path, glob_filter, ignore_case, output_mode, head_limit):
        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(content=f"Invalid regex pattern: {e}", is_error=True)

        # Collect files to search
        if os.path.isfile(search_path):
            files = [search_path]
        elif os.path.isdir(search_path):
            files = []
            for root, _dirs, filenames in os.walk(search_path):
                for fname in filenames:
                    if glob_filter and not fnmatch.fnmatch(fname, glob_filter):
                        continue
                    files.append(os.path.join(root, fname))
                if len(files) > 5000:
                    break  # safety limit
        else:
            return ToolResult(content=f"Path not found: {search_path}", is_error=True)

        results = []
        for filepath in files:
            # Skip binary/common non-text files
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {'.exe', '.dll', '.pdb', '.pyc', '.pyo', '.zip', '.png', '.jpg', '.gif', '.ico'}:
                continue
            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        match = regex.search(line)
                        if match:
                            if output_mode == "files_with_matches":
                                results.append(filepath)
                                break
                            elif output_mode == "count":
                                pass  # handled after
                            else:
                                results.append(f"{filepath}:{lineno}:{line.rstrip()}")
            except (PermissionError, OSError):
                continue

        if output_mode == "count":
            counts = {}
            for r in results:
                fpath = r.split(":")[0]
                counts[fpath] = counts.get(fpath, 0) + 1
            results = [f"{p}:{c}" for p, c in counts.items()]

        # Deduplicate files_with_matches
        if output_mode == "files_with_matches":
            results = sorted(set(results))

        return self._format_output("\n".join(results), head_limit, pattern)

    def _format_output(self, output: str, head_limit: int, pattern: str) -> ToolResult:
        if not output:
            return ToolResult(content=f"No matches for: {pattern}")
        lines = output.split("\n")
        if len(lines) > head_limit:
            output = "\n".join(lines[:head_limit]) + f"\n\n[Truncated: {len(lines)} total, showing {head_limit}]"
        return ToolResult(content=output)
