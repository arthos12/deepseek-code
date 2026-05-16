"""Pydantic models for DeepSeek Code CLI."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

    def to_api_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": str(self.arguments),  # OpenAI format wants JSON string
            },
        }


@dataclass
class Message:
    role: Role
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_api_dict(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [tc.to_api_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class SessionRecord:
    id: str
    model: str
    messages: list[dict] = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)
    created: str = ""
    updated: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.updated:
            self.updated = self.created
