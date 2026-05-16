"""Task tracking tool."""

from deepseek_code.tools.base import BaseTool, ToolResult


class TodoWriteTool(BaseTool):
    name = "TodoWrite"
    description = "Track task progress. Each item: content, status (pending/in_progress/completed), activeForm."
    parameters = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "What to do (imperative)"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Present continuous, e.g. 'Fixing auth bug'",
                        },
                    },
                    "required": ["content", "status", "activeForm"],
                },
            },
        },
        "required": ["todos"],
    }

    def execute(self, params: dict) -> ToolResult:
        todos = params.get("todos", [])

        icons = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
        lines = ["Task list:"]
        for i, t in enumerate(todos, 1):
            icon = icons.get(t.get("status", "pending"), "[?]")
            content = t.get("content", "?")
            active = t.get("activeForm", "")
            line = f"  {i}. {icon} {content}"
            if t.get("status") == "in_progress" and active:
                line += f"  -- {active}"
            lines.append(line)

        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for t in todos:
            s = t.get("status", "pending")
            if s in counts:
                counts[s] += 1
        lines.append(
            f"\n{counts['completed']} done, {counts['in_progress']} active, "
            f"{counts['pending']} pending"
        )

        return ToolResult(content="\n".join(lines))
