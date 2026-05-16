"""File write tool."""

import os
from deepseek_code.tools.base import BaseTool, ToolResult


class WriteTool(BaseTool):
    name = "Write"
    description = "Create or overwrite a file. Creates parent dirs."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    }

    def execute(self, params: dict) -> ToolResult:
        file_path = params.get("file_path", "")
        content = params.get("content", "")

        if not os.path.isabs(file_path):
            return ToolResult(content=f"Path must be absolute: {file_path}", is_error=True)

        try:
            parent = os.path.dirname(file_path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            size = os.path.getsize(file_path)
            return ToolResult(content=f"File written: {file_path} ({size} bytes)")
        except PermissionError as e:
            return ToolResult(content=f"Permission denied: {e}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Write error: {e}", is_error=True)
