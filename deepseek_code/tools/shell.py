"""Shell command execution tool."""

import subprocess
import os
from deepseek_code.tools.base import BaseTool, ToolResult


class ShellTool(BaseTool):
    name = "Shell"
    description = "Run a shell command. Include a description of what it does."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds. Default 120000 (2 min).",
            },
            "description": {
                "type": "string",
                "description": "Short description of what this command does",
            },
        },
        "required": ["command"],
    }

    def execute(self, params: dict) -> ToolResult:
        command = params.get("command", "")
        timeout_ms = params.get("timeout", 120000)
        timeout_sec = min(timeout_ms, 600000) / 1000.0

        # Defense-in-depth: block known destructive patterns
        upper_cmd = command.upper().replace("\\", "/")
        _BLOCKED = [
            "FORMAT C:", "FORMAT /", "DISKPART",
            "RM -RF /", "RM -RF --NO-PRESERVE-ROOT",
            "DEL /F /S C:\\", "DEL /F /S /Q C:",
            "> /DEV/SDA", "> /DEV/NVME",
            "MKFS.", "DD IF=",
            "CHMOD 777 /", "CHOWN -R /",
        ]
        for pat in _BLOCKED:
            if pat in upper_cmd:
                return ToolResult(
                    content=f"Destructive command blocked: {command[:100]}",
                    is_error=True,
                )

        shell_cmd = os.environ.get("DEEPSEEK_SHELL", "powershell")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout.strip()
            if result.stderr:
                err = result.stderr.strip()
                if err:
                    output = (output + "\n" + err).strip() if output else err
            if not output:
                output = f"Command completed with exit code {result.returncode}"
            return ToolResult(content=output, is_error=result.returncode != 0)
        except subprocess.TimeoutExpired:
            return ToolResult(content=f"Command timed out after {timeout_sec}s", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Shell error: {e}", is_error=True)
