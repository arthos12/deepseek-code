"""Context compaction: summarize old turns to stay within token limits."""


class Compactor:
    def __init__(self, config: dict):
        self.trigger_tokens = config.get("compact_trigger_tokens", 800000)
        # Simple estimate: ~4 chars per token
        self.trigger_chars = self.trigger_tokens * 4

    def should_compact(self, messages: list[dict]) -> bool:
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        # Don't compact if we have fewer than 10 messages
        if len(messages) < 10:
            return False
        return total_chars > self.trigger_chars

    def compact(self, messages: list[dict]) -> list[dict]:
        """Keep system prompt + last 6 messages intact, summarize the middle."""
        if len(messages) <= 8:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        keep_recent = 8
        to_compact = non_system[:-keep_recent]
        recent = non_system[-keep_recent:]

        # Build compacted summary
        summary_parts = []
        for m in to_compact:
            role = m.get("role", "?")
            content = m.get("content", "")
            if content and len(content) > 500:
                content = content[:500] + "..."
            if role == "user":
                summary_parts.append(f"User: {content}")
            elif role == "assistant" and m.get("tool_calls"):
                names = [tc.get("function", {}).get("name", "?") for tc in m.get("tool_calls", [])]
                summary_parts.append(f"Assistant called tools: {', '.join(names)}")
            elif role == "tool":
                tc_id = m.get("tool_call_id", "")[:8]
                summary = content[:200] if content else ""
                summary_parts.append(f"Tool result [{tc_id}]: {summary}")

        compacted_msg = {
            "role": "system",
            "content": (
                "[Context compacted — earlier messages summarized]\n\n"
                + "\n".join(summary_parts)
            ),
        }

        return system_msgs + [compacted_msg] + recent
