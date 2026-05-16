"""Console display — code-enforced output control."""

import re
import sys
import threading

# Filler phrases the model should not say — stripped by code, not by model compliance
_FILLER_PATTERNS = [
    r"(?i)^(great|excellent|awesome|perfect|wonderful|fantastic)[!,\s]*",
    r"(?i)^(certainly|absolutely|of course|sure thing)[!,\s]*",
    r"(?i)^(I('d| would) be (happy|glad|delighted) to)\s+",
    r"(?i)^(let me (help|assist) you with)\s+",
    r"(?i)^(good|great|excellent) question[!,\s]*",
    r"(?i)^(thank you for|thanks for)\s+",
]

_MAX_RESPONSE_CHARS = 3000


class Display:
    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich
        self._console = None
        self._lock = threading.Lock()
        if use_rich:
            try:
                from rich.console import Console
                self._console = Console()
            except ImportError:
                self.use_rich = False

    # ── streaming ──

    def thinking(self, text: str):
        """Reasoner thinking — suppressed by default to save tokens.
        Only show a brief indicator on first chunk."""
        pass  # thinking is internal; don't stream to user

    def stream_token(self, text: str):
        try:
            with self._lock:
                sys.stdout.write(text)
                sys.stdout.flush()
        except UnicodeEncodeError:
            with self._lock:
                safe = text.encode("gbk", errors="replace").decode("gbk")
                sys.stdout.write(safe)
                sys.stdout.flush()

    def stream_end(self, had_tools: bool = False):
        """End streaming. If tools were used, add a subtle separator before the response."""
        if had_tools:
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            print()

    # ── tool display ──

    def tool_call(self, step: int, name: str, args: dict) -> None:
        detail = self._tool_detail(name, args)
        line = f"  [{step}] {detail}"
        with self._lock:
            if self._console:
                self._console.print(line, style="dim cyan")
            else:
                print(line)

    def tool_result(self, step: int, name: str, result: str, is_error: bool = False) -> None:
        summary = result[:150].replace("\n", " ")
        if len(result) > 150:
            summary += f" ({len(result)} chars)"
        if is_error:
            with self._lock:
                if self._console:
                    self._console.print(f"    ! {summary}", style="red")
                else:
                    print(f"    ! {summary}")

    def tool_denied(self, name: str, args: dict) -> None:
        with self._lock:
            if self._console:
                self._console.print(f"  [{name}] blocked", style="yellow")
            else:
                print(f"  [{name}] blocked")

    def tool_group_start(self, count: int) -> None:
        if count <= 1:
            return
        with self._lock:
            if self._console:
                self._console.print(f"  (parallel {count})", style="dim")

    def _tool_detail(self, name: str, args: dict) -> str:
        if name == "Read":
            return f"Read {args.get('file_path', '')}"
        if name == "Write":
            p = args.get("file_path", "")
            return f"Write {p} ({len(args.get('content', ''))}b)"
        if name == "Edit":
            return f"Edit {args.get('file_path', '')}"
        if name == "Glob":
            return f"Glob {args.get('pattern', '')}"
        if name == "Grep":
            return f"Grep {args.get('pattern', '')}"
        if name == "Shell":
            d = args.get("description", "") or args.get("command", "")
            return f"Shell {d[:77]}"
        if name == "WebSearch":
            return f"WebSearch {args.get('query', '')}"
        if name == "WebFetch":
            return f"WebFetch {args.get('url', '')[:57]}"
        if name == "TodoWrite":
            return f"TodoWrite ({len(args.get('todos', []))} items)"
        if name == "Agent":
            return f"Agent {args.get('description', '')}"
        return name

    # ── model content output (code-enforced) ──

    def content(self, text: str) -> str:
        """Display model response. Strip filler, truncate if verbose. Returns cleaned text."""
        if not text:
            return ""
        cleaned = text.strip()
        for pat in _FILLER_PATTERNS:
            cleaned = re.sub(pat, "", cleaned)
        cleaned = cleaned.strip()
        if len(cleaned) > _MAX_RESPONSE_CHARS:
            cleaned = cleaned[:_MAX_RESPONSE_CHARS] + "\n\n[response truncated — too long]"
        print(cleaned)
        return cleaned

    # ── status ──

    def info(self, text: str) -> None:
        if self._console:
            self._console.print(text, style="bold")
        else:
            print(text)

    def warn(self, text: str) -> None:
        if self._console:
            self._console.print(f"⚠ {text}", style="yellow")
        else:
            print(f"WARN: {text}")

    def error(self, text: str) -> None:
        if self._console:
            self._console.print(f"ERROR: {text}", style="bold red")
        else:
            print(f"ERROR: {text}", file=sys.stderr)

    def diff(self, text: str) -> None:
        """Show git diff with color."""
        lines = text.split("\n")[:30]
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                if self._console:
                    self._console.print(f"  {line}", style="green")
                else:
                    print(f"  {line}")
            elif line.startswith("-") and not line.startswith("---"):
                if self._console:
                    self._console.print(f"  {line}", style="red")
                else:
                    print(f"  {line}")
            elif line.startswith("@@"):
                if self._console:
                    self._console.print(f"  {line}", style="dim cyan")
                else:
                    print(f"  {line}")
            else:
                pass  # skip context lines, only show changes
        if len(lines) > 30:
            print(f"  ... ({len(lines) - 30} more lines)")

    def separator(self) -> None:
        """Visual break between turns."""
        if self._console:
            self._console.print("  ─────────────────────────────", style="dim")
        else:
            print("  ---")

    def text(self, text: str) -> None:
        print(text)

    def blank(self) -> None:
        print()

    def token_summary(self, prompt_tokens: int, completion_tokens: int) -> None:
        total = prompt_tokens + completion_tokens
        msg = f"  tokens: {prompt_tokens:,} in  {completion_tokens:,} out  {total:,} total"
        if self._console:
            self._console.print(msg, style="dim")
        else:
            print(msg)
