"""Permission manager — project-dir scoping, sensitive file protection."""

import fnmatch
import os
from pathlib import Path


# Files/patterns that are always denied, regardless of location
_SENSITIVE_GLOBS = [
    "*.pem", "*.key", "*-key.pem", "id_rsa", "id_ed25519", "id_ecdsa",
    "*.p12", "*.pfx", "*.jks", "*.keystore",
    ".env", ".env.*",
    "wallet.*", "*.wallet", "wallet.json",
    "credentials*", "*secret*", "*token*",
    "*password*", "*passwd*",
]

# Directories that are always denied
_SENSITIVE_DIRS = [
    "C:/Windows", "C:/Windows/System32", "C:/Windows/SysWOW64",
    "/etc", "/boot", "/sys", "/proc",
    "/System", "/Library/System",
    ".ssh", ".gnupg", ".aws",
]

# Shell commands that contain dangerous patterns are denied
_SHELL_DENY_PATTERNS = [
    "rm -rf /", "rm -rf --no-preserve-root",
    "mkfs.", "dd if=",
    ":(){ :|:& };:",  # fork bomb
    "> /dev/sda", "> /dev/nvme",
    "chmod 777 /", "chown -R",
    "del /f /s C:\\", "format C:",
    "diskpart", "cleanmgr",
    "shutdown", "restart-computer", "stop-computer",
    "Set-ExecutionPolicy", "icacls C:",
    "reg delete", "reg add",
]


class PermissionManager:
    def __init__(self, config: dict):
        perm_config = config.get("permissions", {})
        self.allow_patterns = list(perm_config.get("allow", []))
        self.ask_patterns = list(perm_config.get("ask", []))
        self.deny_patterns = list(perm_config.get("deny", []))
        self.project_dir = os.path.abspath(config.get("project_dir", os.getcwd()))

    # ── path checks ──

    def is_in_project(self, path: str) -> bool:
        """Check if path is inside the project directory."""
        try:
            resolved = os.path.abspath(path)
            return resolved.startswith(self.project_dir + os.sep) or resolved == self.project_dir
        except (ValueError, OSError):
            return False

    def is_sensitive_path(self, path: str) -> bool:
        """Check if a file path matches sensitive patterns."""
        basename = os.path.basename(path)
        resolved = os.path.abspath(path)

        # Check filename against sensitive globs
        for pattern in _SENSITIVE_GLOBS:
            if fnmatch.fnmatch(basename, pattern):
                return True

        # Check if inside sensitive directories
        normalized = resolved.replace("\\", "/")
        for sdir in _SENSITIVE_DIRS:
            sdir_norm = sdir.replace("\\", "/")
            if normalized.startswith(sdir_norm + "/") or normalized == sdir_norm:
                return True

        return False

    def is_sensitive_command(self, command: str) -> bool:
        """Check if a shell command contains dangerous patterns."""
        lower = command.lower()
        for pattern in _SHELL_DENY_PATTERNS:
            if pattern.lower() in lower:
                return True
        return False

    # ── permission check ──

    def check(self, tool_name: str, args: dict | None = None) -> str:
        """
        Returns 'allow', 'ask', or 'deny'.
        Priority: sensitive file deny → explicit deny → project-enforced deny → allow → ask.
        """
        key = self._make_key(tool_name, args)

        # 1. Sensitive file/command — always deny
        if self._hits_sensitive(tool_name, args):
            return "deny"

        # 2. Explicit deny patterns
        for pattern in self.deny_patterns:
            if fnmatch.fnmatch(key, pattern):
                return "deny"

        # 3. Path outside project dir → ask (unless user allows)
        if not self._is_within_scope(tool_name, args):
            return "ask"

        # 4. Explicit allow patterns
        for pattern in self.allow_patterns:
            if fnmatch.fnmatch(key, pattern):
                return "allow"

        # 5. Explicit ask patterns
        for pattern in self.ask_patterns:
            if fnmatch.fnmatch(key, pattern):
                return "ask"

        return "allow"  # within project, no rule → allow

    def _hits_sensitive(self, tool_name: str, args: dict | None) -> bool:
        """Check if args involve sensitive files or commands."""
        if not args:
            return False
        if tool_name == "Shell":
            cmd = args.get("command", "")
            return self.is_sensitive_command(cmd)
        path = args.get("file_path") or args.get("path") or ""
        if path:
            return self.is_sensitive_path(path)
        return False

    def _is_within_scope(self, tool_name: str, args: dict | None) -> bool:
        """Check if the operation stays within approved scope."""
        if not args:
            return True  # tools without path args are fine
        if tool_name in ("WebSearch", "WebFetch", "TodoWrite"):
            return True  # network/metadata tools don't have file scope
        if tool_name in ("Glob", "Grep", "Shell"):
            # Check the path/search directory
            p = args.get("path") or args.get("command") or ""
            if p and os.path.isabs(p):
                return self.is_in_project(p) if not p.upper().startswith("C:") and "/windows/" not in p.lower() else False
            return True  # relative paths assumed in project
        path = args.get("file_path") or ""
        if path and os.path.isabs(path):
            return self.is_in_project(path)
        return True  # relative path — assume in project

    def _make_key(self, tool_name: str, args: dict | None = None) -> str:
        if not args:
            return tool_name
        path = args.get("file_path") or args.get("path") or args.get("command") or ""
        if path:
            return f"{tool_name}({path})"
        return tool_name

    # ── user interaction ──

    def prompt_user(self, tool_name: str, args: dict | None = None) -> bool:
        """Ask user for permission. Returns True if allowed."""
        detail = self._format_args(tool_name, args or {})

        # Check if outside project scope — stronger warning
        tag = " (outside project)" if not self._is_within_scope(tool_name, args) else ""
        prompt = f"\n  [{tool_name}]{tag} {detail} [Y/n] "

        try:
            answer = input(prompt).strip().lower()
            if answer in ("", "y", "yes"):  # Enter = approve
                return True
            if answer in ("a", "all"):
                self.allow_patterns.append(tool_name)
                return True
            return False
        except (EOFError, KeyboardInterrupt):
            return False

    def _format_args(self, tool_name: str, args: dict) -> str:
        if tool_name == "Shell":
            desc = args.get("description", "")
            if desc:
                return desc
            cmd = args.get("command", "")
            return cmd[:77] + "..." if len(cmd) > 80 else cmd
        path = args.get("file_path", "")
        if path:
            if len(path) > 60:
                path = "..." + path[-57:]
            return path
        url = args.get("url", "")
        if url:
            return url[:57] + "..." if len(url) > 60 else url
        desc = args.get("description", "")
        if desc:
            return desc
        parts = []
        for k, v in (args or {}).items():
            s = str(v)
            if len(s) > 40:
                s = s[:37] + "..."
            parts.append(f"{k}={s}")
        return ", ".join(parts[:3])
