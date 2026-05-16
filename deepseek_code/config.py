"""Config loader: settings.json + local overrides + env vars."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "model": "deepseek-chat",
    "reasoning_model": "deepseek-reasoner",
    "temperature": 0.0,
    "analysis_temperature": 0.3,
    "max_tokens": 4096,
    "reasoning_max_tokens": 8192,
    "timeout": 60,
    "reasoning_timeout": 120,
    "max_turns": 50,
    "compact_trigger_tokens": 800000,
    "sessions_dir": "./sessions",
    "skills_dir": "./skills",
    "default_shell": "powershell",
    "project_dir": "",  # empty = use cwd
    "permissions": {
        "allow": [
            "Read",
            "Glob",
            "Grep",
            "TodoWrite",
        ],
        "ask": [
            "Write",
            "Edit",
            "Shell",
            "WebFetch",
            "WebSearch",
        ],
        "deny": [
            "Write(C:*)",
            "Edit(C:*)",
            "Read(C:\\Users\\*)",
        ],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(config_dir: str = ".") -> dict:
    config = dict(DEFAULT_CONFIG)
    config["api_key"] = os.environ.get("DEEPSEEK_API_KEY", "")

    settings_path = Path(config_dir) / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, encoding="utf-8") as f:
                overrides = json.load(f)
            _deep_merge(config, overrides)
        except (json.JSONDecodeError, OSError):
            pass

    local_path = Path(config_dir) / "settings.local.json"
    if local_path.exists():
        try:
            with open(local_path, encoding="utf-8") as f:
                overrides = json.load(f)
            _deep_merge(config, overrides)
        except (json.JSONDecodeError, OSError):
            pass

    config["sessions_dir"] = str(Path(config_dir) / config["sessions_dir"])
    config["skills_dir"] = str(Path(config_dir) / config["skills_dir"])

    # Project dir: env var > config > deepseek-code install dir
    if not config.get("project_dir"):
        config["project_dir"] = os.environ.get(
            "DEEPSEEK_PROJECT_DIR",
            str(Path(__file__).resolve().parent.parent)  # deepseek-code package root
        )

    return config
