"""Sub-agent spawning tool."""

from deepseek_code.tools.base import BaseTool, ToolResult
from deepseek_code.sub_agent import run_sub_agent


class AgentTool(BaseTool):
    name = "Agent"
    description = (
        "Launch a sub-agent to handle complex, multi-step tasks independently. "
        "The sub-agent has its own context window and tool access. "
        "Use for research, exploration, or tasks that would bloat the main context."
    )
    parameters = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Short (3-5 word) description of the task",
            },
            "prompt": {
                "type": "string",
                "description": "The task for the agent to perform",
            },
            "allowed_tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tool names the sub-agent can use. Defaults to Read, Glob, Grep.",
            },
        },
        "required": ["description", "prompt"],
    }

    def __init__(self, main_registry=None, config: dict | None = None):
        super().__init__()
        self.main_registry = main_registry
        self.config = config or {}

    def execute(self, params: dict) -> ToolResult:
        task = params.get("prompt", "")
        description = params.get("description", "sub-agent task")
        allowed_names = params.get("allowed_tools", ["Read", "Glob", "Grep", "WebFetch"])

        if not self.main_registry:
            return ToolResult(
                content="Agent tool not initialized with tool registry.",
                is_error=True,
            )

        sub_registry = self.main_registry.get_subset(allowed_names)
        system_prompt = (
            "You are a sub-agent performing a research task. "
            "Use the available tools to gather information and return a concise summary. "
            "Be thorough but concise. Report findings, not process."
        )

        try:
            result = run_sub_agent(
                system_prompt=system_prompt,
                task=task,
                registry=sub_registry,
                config=self.config,
                max_turns=8,
            )
            return ToolResult(content=result)
        except Exception as e:
            return ToolResult(content=f"Sub-agent error: {e}", is_error=True)
