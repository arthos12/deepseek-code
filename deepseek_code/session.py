"""JSONL session persistence."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


def _ensure_dir(sessions_dir: str) -> None:
    os.makedirs(sessions_dir, exist_ok=True)


def save_session(agent, config: dict) -> str:
    """Save agent messages to a JSONL file. Returns session ID."""
    sessions_dir = config.get("sessions_dir", "./sessions")
    _ensure_dir(sessions_dir)

    sid = getattr(agent, "session_id", None) or uuid.uuid4().hex[:12]
    agent.session_id = sid

    filepath = Path(sessions_dir) / f"{sid}.jsonl"
    now = datetime.now().isoformat()

    # Extract title from first user message
    title = ""
    for msg in agent.messages:
        if msg.get("role") == "user":
            title = msg.get("content", "")[:80].replace("\n", " ")
            break

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "session_header",
            "id": sid,
            "title": title,
            "model": agent.model,
            "token_usage": agent.token_usage,
            "created": getattr(agent, "created_at", now),
            "updated": now,
        }, ensure_ascii=False) + "\n")
        for msg in agent.messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    return sid


def load_session(session_id: str, sessions_dir: str) -> dict | None:
    """Load a session. Returns dict with messages, model, token_usage or None."""
    filepath = Path(sessions_dir) / f"{session_id}.jsonl"
    if not filepath.exists():
        # Try partial match
        for f in Path(sessions_dir).glob(f"{session_id[:8]}*.jsonl"):
            filepath = f
            break
    if not filepath.exists():
        return None

    messages = []
    header = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record.get("type") == "session_header":
                header = record
            else:
                messages.append(record)

    return {
        "id": header.get("id", session_id),
        "model": header.get("model", "deepseek-chat"),
        "token_usage": header.get("token_usage", {}),
        "messages": messages,
        "created": header.get("created", ""),
        "updated": header.get("updated", ""),
    }


def list_sessions(sessions_dir: str) -> list[dict]:
    """List all sessions with metadata."""
    _ensure_dir(sessions_dir)
    sessions = []
    for f in sorted(Path(sessions_dir).glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f, encoding="utf-8") as fp:
                first = json.loads(fp.readline())
            sessions.append({
                "id": first.get("id", f.stem),
                "title": first.get("title", ""),
                "model": first.get("model", "?"),
                "updated": first.get("updated", ""),
                "message_count": sum(1 for _ in open(f, encoding="utf-8")) - 1,
            })
        except Exception:
            pass
    return sessions


def delete_session(session_id: str, sessions_dir: str) -> bool:
    """Delete a session file. Returns True if deleted."""
    filepath = Path(sessions_dir) / f"{session_id}.jsonl"
    if not filepath.exists():
        for f in Path(sessions_dir).glob(f"{session_id[:8]}*.jsonl"):
            filepath = f
            break
    if filepath.exists():
        os.remove(filepath)
        return True
    return False
