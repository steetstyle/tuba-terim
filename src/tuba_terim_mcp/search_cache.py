"""Disk üzerinde arama sonucu önbelleği."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class SearchCache:
    def __init__(self, server: str, ttl_s: int = 7 * 24 * 60 * 60) -> None:
        self.root = Path.home() / ".cache" / f"{server}-mcp" / "searches"
        self.ttl_s = ttl_s

    def key(self, *parts: Any) -> str:
        blob = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        path = self.root / f"{key}.json"
        if not path.is_file():
            return None
        if time.time() - path.stat().st_mtime > self.ttl_s:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or "result" not in payload:
            return None
        result = payload["result"]
        if isinstance(result, dict):
            result = {**result, "cache": "hit"}
        return result

    def set(self, key: str, result: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f"{key}.json.tmp"
        temporary.write_text(
            json.dumps({"saved_at": time.time(), "result": result}, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.root / f"{key}.json")
