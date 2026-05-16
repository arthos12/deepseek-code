"""Tool registry: register, lookup, list, get schemas."""

from deepseek_code.tools.base import BaseTool, ToolResult


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_openai_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def get_subset(self, names: list[str]) -> "ToolRegistry":
        subset = ToolRegistry()
        for name in names:
            tool = self._tools.get(name)
            if tool:
                subset.register(tool)
        return subset

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def execute(self, name: str, params: dict) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                content=f"Tool '{name}' not found. Available: {', '.join(self.list_names())}",
                is_error=True,
            )
        return tool.execute(params)
