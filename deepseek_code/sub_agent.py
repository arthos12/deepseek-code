"""Sub-agent: independent API loop with restricted tools, returns summary."""

from deepseek_code.api import DeepSeekAPI
from deepseek_code.tools.registry import ToolRegistry


def run_sub_agent(
    system_prompt: str,
    task: str,
    registry: ToolRegistry,
    config: dict,
    max_turns: int = 10,
    model: str | None = None,
) -> str:
    """
    Run a sub-agent with limited context and tools.
    Returns a text summary of the result.
    """
    model = model or config.get("model", "deepseek-chat")
    api = DeepSeekAPI(config)
    tools = registry.get_openai_schemas()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    for _ in range(max_turns):
        try:
            response = api.chat(messages=messages, tools=tools if tools else None, model=model)
        except Exception as e:
            return f"Sub-agent API error: {e}"

        tool_calls = response.get("tool_calls")

        if not tool_calls:
            return response.get("content", "Sub-agent completed with no output.")

        # Build assistant message with tool_calls
        import json
        assistant_msg = {"role": "assistant", "content": None, "tool_calls": []}
        for tc in tool_calls:
            assistant_msg["tool_calls"].append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": json.dumps(tc["function"]["arguments"], ensure_ascii=False),
                },
            })
        messages.append(assistant_msg)

        # Execute tools
        for tc in tool_calls:
            result = registry.execute(tc["function"]["name"], tc["function"]["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result.content,
            })

    return "Sub-agent: max turns reached."
