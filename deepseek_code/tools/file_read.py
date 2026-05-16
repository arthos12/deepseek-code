"""File read tool."""

import os
from deepseek_code.tools.base import BaseTool, ToolResult


class ReadTool(BaseTool):
    name = "Read"
    description = "Read file. Optional offset/limit for partial reads."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-indexed)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, params: dict) -> ToolResult:
        file_path = params.get("file_path", "")
        offset = params.get("offset", 0)
        limit = params.get("limit")

        if not os.path.isabs(file_path):
            return ToolResult(content=f"Path must be absolute: {file_path}", is_error=True)
        if not os.path.isfile(file_path):
            return ToolResult(content=f"File not found: {file_path}", is_error=True)

        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except PermissionError as e:
            return ToolResult(content=f"Permission denied: {e}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Read error: {e}", is_error=True)

        total = len(lines)
        if limit is not None:
            chunk = lines[offset : offset + limit]
        else:
            chunk = lines[offset:]

        output = "".join(chunk)
        if len(chunk) < total:
            output += f"\n\n[Showing lines {offset}-{offset + len(chunk)} of {total}]"

        return ToolResult(content=output)
