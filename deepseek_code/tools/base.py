"""Base classes for all tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from deepseek_code.types import ToolDefinition


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


class BaseTool(ABC):
    """Abstract base for all tools. Each tool defines its name, description,
    JSON Schema parameters, and an execute() method."""

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema

    @abstractmethod
    def execute(self, params: dict) -> ToolResult:
        """Execute the tool with the given parameters. Must not raise."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def to_openai_schema(self) -> dict:
        return self.get_definition().to_openai_schema()
