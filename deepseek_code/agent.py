"""Agentic loop — clean, minimal. Model decides. Code handles infrastructure."""

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deepseek_code.api import DeepSeekAPI
from deepseek_code.tools.registry import ToolRegistry
from deepseek_code.tools.base import ToolResult
from deepseek_code.system_prompt import build_system_prompt
from deepseek_code.permissions import PermissionManager
from deepseek_code.compaction import Compactor
from deepseek_code.display import Display
from deepseek_code.memory_hook import (
    detect_memory_candidates,
    should_auto_save,
    append_to_memory,
    update_memory_index,
)
from deepseek_code.checkpoint import Checkpoint
from deepseek_code import git_utils

_CONSECUTIVE_FAILURE_LIMIT = 3

# Keywords for model auto-routing
_REASONER_KEYWORDS = [
    "error", "bug", "crash", "traceback", "exception",
    "报错", "异常", "崩溃", "调试",
    "漏洞", "vulnerability", "security",
]


class Agent:
    def __init__(self, config: dict, registry: ToolRegistry):
        self.config = config
        self.registry = registry
        self.api = DeepSeekAPI(config)
        self.permissions = PermissionManager(config)
        self.display = Display()
        self.messages: list[dict] = []
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self.model = config.get("model", "deepseek-chat")
        self.max_turns = config.get("max_turns", 50)
        self._compactor = Compactor(config)
        self._system_prompt = None
        self._step = 0
        self._consecutive_failures = 0
        self.checkpoint = Checkpoint(config.get("sessions_dir", "./sessions"))
        self._in_git = git_utils.is_git_repo(config.get("project_dir", "."))
        self._project_dir = config.get("project_dir", ".")

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = build_system_prompt(
                self.config["skills_dir"],
                self.config.get("project_dir", "."),
            )
        return self._system_prompt

    def _choose_model(self, user_input: str) -> str:
        """Auto-route: reasoner for debug/analysis, chat otherwise."""
        lower = user_input.lower()
        for kw in _REASONER_KEYWORDS:
            if kw in lower:
                return self.config.get("reasoning_model", "deepseek-reasoner")
        return self.model

    def run(self, user_input: str, resume_messages: list[dict] | None = None) -> str:
        if resume_messages:
            self.messages = list(resume_messages)
            self.model = self.config.get("model", "deepseek-chat")
        else:
            self.messages = [{"role": "system", "content": self.system_prompt}]
            self.model = self._choose_model(user_input)

        self.messages.append({"role": "user", "content": user_input})
        tools = self.registry.get_openai_schemas()
        turn = 0

        while turn < self.max_turns:
            turn += 1

            if self._compactor.should_compact(self.messages):
                self.messages = self._compactor.compact(self.messages)

            try:
                stream = self.api.chat_stream(
                    messages=self.messages,
                    tools=tools if tools else None,
                    model=self.model,
                )
            except Exception as e:
                self.display.error(f"API call failed: {e}")
                return f"Error: {e}"

            text_parts = []
            tool_calls = []
            usage = {}

            for event in stream:
                t = event.get("type", "")
                if t == "thinking":
                    self.display.thinking(event["content"])
                elif t == "text":
                    self.display.stream_token(event["content"])
                    text_parts.append(event["content"])
                elif t == "tool_call":
                    tool_calls.append(event)
                elif t == "done":
                    usage = event.get("usage", {})
                elif t == "error":
                    self.display.error(event["content"])
                    return f"Error: {event['content']}"

            self.display.stream_end()

            self.token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            self.token_usage["completion_tokens"] += usage.get("completion_tokens", 0)

            text_content = "".join(text_parts)

            # No tool calls — done
            if not tool_calls:
                if turn > 1:
                    self.display.token_summary(
                        self.token_usage["prompt_tokens"],
                        self.token_usage["completion_tokens"],
                    )
                cleaned = self._dedup_response(text_content or "")
                cleaned = self.display.content(cleaned)
                self.messages.append({"role": "assistant", "content": cleaned})
                return cleaned

            # Execute tools
            failed_count = self._handle_tool_calls(tool_calls)

            # Memory auto-save
            if self.config.get("memory_auto_save", False) and turn > 1:
                self._auto_save_memory(user_input, text_content)

            # Consecutive failure guard
            if failed_count > 0:
                self._consecutive_failures += 1
                if self._consecutive_failures >= _CONSECUTIVE_FAILURE_LIMIT:
                    self.display.error(
                        f"{self._consecutive_failures} consecutive tool failures. "
                        "Check shell type, file paths, or permissions."
                    )
            else:
                self._consecutive_failures = 0

        return "Max turns reached."

    def _dedup_response(self, text: str) -> str:
        """Remove self-repetition in model output."""
        if len(text) < 300:
            return text

        # Method 1: half-split similarity
        half = len(text) // 2
        first = text[:half].strip()
        second = text[half:].strip()
        if first and second:
            common = sum(1 for a, b in zip(first, second) if a == b)
            if common / max(len(first), len(second)) > 0.45:
                return first

        # Method 2: deduplicate repeated paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        seen = set()
        unique = []
        for p in paragraphs:
            key = p[:80]
            if key not in seen:
                seen.add(key)
                unique.append(p)
        if len(unique) < len(paragraphs):
            return "\n\n".join(unique)

        return text

    def _auto_save_memory(self, user_input: str, assistant_response: str) -> None:
        try:
            tool_results = []
            for msg in reversed(self.messages[-10:]):
                if msg.get("role") == "tool" and msg.get("content"):
                    tool_results.append(msg["content"])

            candidates = detect_memory_candidates(
                user_input=user_input,
                assistant_response=assistant_response,
                tool_results=tool_results,
            )

            auto_save = should_auto_save(candidates, min_confidence=0.8)
            for candidate in auto_save:
                result = append_to_memory(
                    project_dir=self.config.get("project_dir", "."),
                    category=candidate["category"],
                    content=candidate["content"],
                    source="auto",
                )
                if result["status"] == "ok":
                    self.display.info(
                        f"  [memory] saved to {result['file_path']} "
                        f"({candidate['reason']})"
                    )
        except Exception:
            pass  # memory hook must never crash the agent

    def _handle_tool_calls(self, tool_calls: list[dict]) -> int:
        """Execute tool calls with parallel/serial split. Returns failure count."""
        assistant_msg: dict = {"role": "assistant", "content": None, "tool_calls": []}
        for tc in tool_calls:
            assistant_msg["tool_calls"].append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                },
            })
        self.messages.append(assistant_msg)

        resolved = []
        for tc in tool_calls:
            verdict = self.permissions.check(tc["name"], tc["arguments"])
            resolved.append((tc, verdict))

        parallel_tasks = []
        serial_tasks = []
        failed = 0

        for tc, verdict in resolved:
            if verdict == "deny":
                failed += 1
                self.display.tool_denied(tc["name"], tc["arguments"])
                serial_tasks.append((tc, ToolResult(content="Permission denied.", is_error=True)))
            elif verdict == "ask":
                allowed = self.permissions.prompt_user(tc["name"], tc["arguments"])
                if not allowed:
                    failed += 1
                    self.display.tool_denied(tc["name"], tc["arguments"])
                    serial_tasks.append((tc, ToolResult(content="User denied.", is_error=True)))
                elif tc["name"] in ("Read", "Glob", "Grep", "WebSearch", "WebFetch"):
                    parallel_tasks.append(tc)
                else:
                    serial_tasks.append((tc, None))
            elif tc["name"] in ("Read", "Glob", "Grep", "WebSearch", "WebFetch"):
                parallel_tasks.append(tc)
            else:
                serial_tasks.append((tc, None))

        results_by_id = {}

        if parallel_tasks:
            self.display.tool_group_start(len(parallel_tasks))
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = {}
                for tc in parallel_tasks:
                    self._step += 1
                    step = self._step
                    self.display.tool_call(step, tc["name"], tc["arguments"])
                    futures[pool.submit(self.registry.execute, tc["name"], tc["arguments"])] = (tc, step)

                for future in as_completed(futures):
                    tc, step = futures[future]
                    try:
                        result = future.result(timeout=60)
                    except Exception as e:
                        result = ToolResult(content=str(e), is_error=True)
                    if result.is_error:
                        failed += 1
                    results_by_id[tc["id"]] = result
                    self.display.tool_result(step, tc["name"], result.content, result.is_error)

        for tc, pre_result in serial_tasks:
            self._step += 1
            step = self._step
            if pre_result is not None:
                results_by_id[tc["id"]] = pre_result
                continue
            # P0: checkpoint before Write/Edit
            if tc["name"] in ("Write", "Edit"):
                filepath = tc["arguments"].get("file_path", "")
                if filepath:
                    self.checkpoint.save(filepath)

            self.display.tool_call(step, tc["name"], tc["arguments"])
            result = self.registry.execute(tc["name"], tc["arguments"])
            if result.is_error:
                failed += 1
            results_by_id[tc["id"]] = result
            self.display.tool_result(step, tc["name"], result.content, result.is_error)

            # P0: show diff after Write/Edit
            if tc["name"] in ("Write", "Edit") and not result.is_error:
                filepath = tc["arguments"].get("file_path", "")
                if filepath and self._in_git:
                    diff = git_utils.diff_file(filepath, path=self._project_dir)
                    if diff:
                        self.display.diff(diff)

        for tc in tool_calls:
            result = results_by_id.get(tc["id"], ToolResult(content="?", is_error=True))
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result.content,
            })

        return failed
