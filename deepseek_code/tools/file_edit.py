"""File edit tool — exact string replacement."""

import os
from deepseek_code.tools.base import BaseTool, ToolResult


class EditTool(BaseTool):
    name = "Edit"
    description = "Exact string replacement in file. Use replace_all=True for all occurrences."
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "Exact text to replace",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text (must differ from old_string)",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences instead of failing on non-unique match",
                "default": False,
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    def execute(self, params: dict) -> ToolResult:
        file_path = params.get("file_path", "")
        old_string = params.get("old_string", "")
        new_string = params.get("new_string", "")
        replace_all = params.get("replace_all", False)

        if not os.path.isabs(file_path):
            return ToolResult(content=f"Path must be absolute: {file_path}", is_error=True)
        if not os.path.isfile(file_path):
            return ToolResult(content=f"File not found: {file_path}", is_error=True)
        if old_string == new_string:
            return ToolResult(content="old_string and new_string are identical", is_error=True)

        try:
            with open(file_path, encoding="utf-8") as f:
                original = f.read()
        except Exception as e:
            return ToolResult(content=f"Read error: {e}", is_error=True)

        count = original.count(old_string)
        if count == 0:
            return ToolResult(
                content=f"old_string not found in {file_path}",
                is_error=True,
            )
        if count > 1 and not replace_all:
            return ToolResult(
                content=f"old_string appears {count} times in {file_path}. "
                f"Use replace_all=True or provide more surrounding context to make it unique.",
                is_error=True,
            )

        modified = original.replace(old_string, new_string) if replace_all else original.replace(old_string, new_string, 1)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified)
            action = f"Replaced {count} occurrence(s)" if replace_all else "Replaced 1 occurrence"
            return ToolResult(content=f"{action} in {file_path}")
        except Exception as e:
            return ToolResult(content=f"Write error: {e}", is_error=True)
