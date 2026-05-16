"""MemorySaveTool — explicit user-triggered memory persistence.

Triggered when user says: "记住", "记一下", "record this", "save this", "存一下", etc.
The AI calls this tool to persist important information to the appropriate memory file.
"""

from pathlib import Path
from deepseek_code.tools.base import BaseTool, ToolResult
from deepseek_code.memory_hook import (
    classify_memory,
    append_to_memory,
    update_memory_index,
)


class MemorySaveTool(BaseTool):
    name = "MemorySave"
    description = (
        "Save important information to project memory. "
        "Use when the user says '记住', '记一下', 'record this', 'save this', "
        "or when you discover a new rule, pattern, or preference worth remembering. "
        "The content will be classified and saved to the appropriate memory file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The information to remember. Be specific: what, why, how to use it.",
            },
            "category": {
                "type": "string",
                "enum": [
                    "coding",
                    "investment",
                    "valuation",
                    "workflow",
                    "accuracy",
                    "lessons",
                    "tasks",
                    "general",
                ],
                "description": (
                    "Memory category. Auto-detected if not specified:\n"
                    "- coding: 编码偏好、踩坑记录、用户习惯 → memory/feedback.md\n"
                    "- investment: 投资排除原则、判断框架 → memory/project_investment_philosophy.md\n"
                    "- valuation: 估值逻辑、PEG阈值 → memory/project_valuation_framework.md\n"
                    "- workflow: 分析流程、工具能力 → memory/workflow.md\n"
                    "- accuracy: 可验证的投资判断 → docs/accuracy_log.md\n"
                    "- lessons: 分析方法论教训 → docs/analysis_lessons.md\n"
                    "- tasks: 跨会话任务清单 → memory/project_tasks.md\n"
                    "- general: 通用记忆 → memory/feedback.md"
                ),
            },
            "source": {
                "type": "string",
                "enum": ["manual", "auto"],
                "description": "manual = user explicitly asked to save. auto = AI detected worth saving.",
                "default": "manual",
            },
        },
        "required": ["content"],
    }

    def __init__(self, project_dir: str | None = None):
        super().__init__()
        self.project_dir = project_dir

    def execute(self, params: dict) -> ToolResult:
        content = params.get("content", "")
        if not content or not content.strip():
            return ToolResult(content="Nothing to save — content is empty.", is_error=True)

        category = params.get("category")
        if not category:
            category = classify_memory(content)

        source = params.get("source", "manual")
        project_dir = self.project_dir or "."

        result = append_to_memory(
            project_dir=project_dir,
            category=category,
            content=content,
            source=source,
        )

        if result["status"] == "error":
            return ToolResult(
                content=f"Failed to save memory: {result.get('error', 'unknown error')}",
                is_error=True,
            )

        # Update memory index so system prompt stays aware
        index_result = update_memory_index(project_dir)

        summary = (
            f"Saved to {result['file_path']} (category: {result['category']})\n"
            f"Content: {content[:200]}{'...' if len(content) > 200 else ''}"
        )
        if index_result.get("status") == "ok":
            summary += f"\nMemory index updated ({index_result.get('file_count', 0)} files tracked)"

        return ToolResult(content=summary)
