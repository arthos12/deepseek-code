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
        """Preserve system prompt + last 12 messages. Summarize middle with task awareness."""
        if len(messages) <= 20:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        keep_recent = 20  # keep more context before compacting
        to_compact = non_system[:-keep_recent]
        recent = non_system[-keep_recent:]

        # Extract user tasks and key decisions
        tasks = []
        decisions = []
        for m in to_compact:
            role = m.get("role", "?")
            content = m.get("content", "")
            if role == "user" and content:
                tasks.append(content[:200])
            elif role == "assistant" and not m.get("tool_calls"):
                # Capture non-tool responses as potential decisions
                if len(content) > 50:
                    decisions.append(content[:300])

        summary_parts = [f"Tasks worked on ({len(tasks)}):"]
        for t in tasks[-5:]:  # last 5 tasks
            summary_parts.append(f"  - {t}")
        if decisions:
            summary_parts.append(f"\nKey outcomes:")
            for d in decisions[-3:]:  # last 3 decisions
                summary_parts.append(f"  - {d[:150]}")

        compacted_msg = {
            "role": "system",
            "content": (
                "[Earlier context summarized]\n\n"
                + "\n".join(summary_parts)
            ),
        }

        return system_msgs + [compacted_msg] + recent
