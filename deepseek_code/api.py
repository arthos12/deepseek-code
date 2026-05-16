"""DeepSeek API wrapper via OpenAI SDK — supports streaming and regular calls."""

import json
import time
from typing import Iterator
from openai import OpenAI


class DeepSeekAPI:
    def __init__(self, config: dict):
        api_key = config.get("api_key", "")
        if not api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY not set. Set the environment variable "
                "or add 'api_key' to settings.local.json"
            )
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self.config = config

    def _timeout_for(self, model: str) -> int:
        if model == self.config.get("reasoning_model", "deepseek-reasoner"):
            return self.config.get("reasoning_timeout", 120)
        return self.config.get("timeout", 60)

    def _temperature_for(self, model: str) -> float:
        if model == self.config.get("reasoning_model", "deepseek-reasoner"):
            return self.config.get("analysis_temperature", 0.3)
        return self.config.get("temperature", 0.0)

    def _max_tokens_for(self, model: str) -> int:
        if model == self.config.get("reasoning_model", "deepseek-reasoner"):
            return self.config.get("reasoning_max_tokens", 8192)
        return self.config.get("max_tokens", 4096)

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> dict:
        """
        Send chat completion request. Returns parsed response dict:
        {"content": str|None, "tool_calls": list|None, "finish_reason": str, "usage": dict}
        """
        model = model or self.config.get("model", "deepseek-chat")

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": self._temperature_for(model),
            "max_tokens": self._max_tokens_for(model),
            "timeout": self._timeout_for(model),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        last_error = None
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return self._parse_response(response)
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                if attempt == 0 and ("timeout" in msg or "connection" in msg):
                    time.sleep(2)
                    continue
                break

        raise RuntimeError(
            f"DeepSeek API call failed: {last_error}"
        )

    def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> Iterator[dict]:
        """
        Stream chat completion. Yields dicts:
        {"type": "text", "content": "..."}  — text chunk
        {"type": "tool_call", "id": ..., "name": ..., "arguments": ...} — accumulated tool call
        {"type": "done", "usage": {...}} — stream complete
        """
        model = model or self.config.get("model", "deepseek-chat")

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": self._temperature_for(model),
            "max_tokens": self._max_tokens_for(model),
            "timeout": self._timeout_for(model),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            return

        tool_calls_acc: dict[int, dict] = {}  # index -> {id, name, args_str}
        usage = {}

        for chunk in stream:
            # Track usage
            if chunk.usage:
                usage = {
                    "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(chunk.usage, "completion_tokens", 0),
                }

            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Reasoning content (deepseek-reasoner only)
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                yield {"type": "thinking", "content": delta.reasoning_content}

            # Text content
            if delta.content:
                yield {"type": "text", "content": delta.content}

            # Tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": tc_delta.id or "",
                            "name": tc_delta.function.name or "",
                            "arguments": "",
                        }
                    acc = tool_calls_acc[idx]
                    if tc_delta.id:
                        acc["id"] = tc_delta.id
                    if tc_delta.function.name:
                        acc["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        acc["arguments"] += tc_delta.function.arguments

        # Emit accumulated tool calls
        for idx in sorted(tool_calls_acc.keys()):
            acc = tool_calls_acc[idx]
            try:
                args = json.loads(acc["arguments"])
            except json.JSONDecodeError:
                args = {}
            yield {
                "type": "tool_call",
                "id": acc["id"],
                "name": acc["name"],
                "arguments": args,
            }

        yield {"type": "done", "usage": usage}

    def _parse_response(self, response) -> dict:
        choice = response.choices[0]
        msg = choice.message

        result: dict = {
            "content": msg.content or "",
            "finish_reason": choice.finish_reason or "stop",
            "usage": {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            },
            "tool_calls": None,
        }

        if msg.tool_calls:
            parsed = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                parsed.append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    },
                })
            result["tool_calls"] = parsed

        return result
