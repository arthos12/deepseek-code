"""Lightweight file checkpoint — save before edit, restore on undo."""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path


class Checkpoint:
    def __init__(self, base_dir: str = "./sessions"):
        self.dir = Path(base_dir) / "checkpoints"
        self.history: list[dict] = []  # [{id, file, original, timestamp}]

    def save(self, filepath: str) -> str | None:
        """Save file state before modification. Returns checkpoint ID."""
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None

        cid = uuid.uuid4().hex[:8]
        ts = datetime.now().isoformat()
        self.dir.mkdir(parents=True, exist_ok=True)

        record = {
            "id": cid,
            "file": os.path.abspath(filepath),
            "content": content,
            "timestamp": ts,
        }
        record_path = self.dir / f"{cid}.json"
        record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        self.history.append(record)
        return cid

    def undo(self, checkpoint_id: str | None = None) -> dict | None:
        """Restore file from checkpoint. If no ID given, restore latest."""
        if not self.dir.is_dir():
            return None

        if checkpoint_id:
            record_path = self.dir / f"{checkpoint_id}.json"
            if not record_path.exists():
                return None
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self._restore(record)
            record_path.unlink()
            return record

        # Undo latest
        records = sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not records:
            return None
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self._restore(record)
        records[0].unlink()
        return record

    def _restore(self, record: dict) -> None:
        """Write original content back to file."""
        filepath = record["file"]
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(record["content"])

    def list_checkpoints(self) -> list[dict]:
        """List all saved checkpoints."""
        if not self.dir.is_dir():
            return []
        result = []
        for p in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            r = json.loads(p.read_text(encoding="utf-8"))
            result.append({"id": r["id"], "file": r["file"], "timestamp": r["timestamp"]})
        return result

    def clear(self) -> None:
        """Remove all checkpoints."""
        if self.dir.is_dir():
            for p in self.dir.glob("*.json"):
                p.unlink()
