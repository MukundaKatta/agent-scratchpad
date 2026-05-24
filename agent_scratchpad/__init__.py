"""agent_scratchpad: keyed in-memory notepad for multi-step agent reasoning.

Supports optional JSONL persistence so a crashed run can resume with context.
Thread-safe via threading.RLock. Zero runtime dependencies.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any


class Scratchpad:
    """Keyed in-memory notepad with optional JSONL persistence.

    Usage::

        pad = Scratchpad()
        pad.set("step1_result", {"score": 0.9})
        print(pad.get("step1_result"))

        # Persist to disk so a crash doesn't lose context
        pad = Scratchpad(persist_path="~/.agent/run42.jsonl")
    """

    def __init__(self, persist_path: str | None = None) -> None:
        """Create a scratchpad.

        Args:
            persist_path: Optional path to a JSONL file. Tilde (~) is expanded.
                          If the file exists, state is replayed from it on init.
                          Every mutation appends one line to the file.
        """
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        self._path: str | None = None

        if persist_path is not None:
            self._path = os.path.expanduser(persist_path)
            self._load()

    # ------------------------------------------------------------------
    # Internal persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Replay the JSONL file into _data. Last writer per key wins."""
        if not self._path or not os.path.exists(self._path):
            return
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip malformed lines
                if entry.get("cleared"):
                    self._data = {}
                elif entry.get("deleted"):
                    self._data.pop(entry.get("key", ""), None)
                elif "key" in entry and "value" in entry:
                    self._data[entry["key"]] = entry["value"]

    def _append(self, record: dict) -> None:
        """Append one JSON line to the persist file (if configured)."""
        if self._path is None:
            return
        line = json.dumps(record, ensure_ascii=False)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*, overwriting any prior value."""
        with self._lock:
            self._data[key] = value
            self._append({"key": key, "value": value})

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if not present."""
        with self._lock:
            return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        """Remove *key* from the scratchpad.

        Returns:
            True if the key existed and was removed, False otherwise.
        """
        with self._lock:
            if key not in self._data:
                return False
            del self._data[key]
            self._append({"key": key, "deleted": True})
            return True

    def has(self, key: str) -> bool:
        """Return True if *key* is present."""
        with self._lock:
            return key in self._data

    def keys(self) -> list[str]:
        """Return a list copy of all current keys."""
        with self._lock:
            return list(self._data.keys())

    def items(self) -> dict:
        """Return a shallow copy of the current key-value mapping."""
        with self._lock:
            return dict(self._data)

    def clear(self) -> None:
        """Remove all entries. Persists a 'cleared' marker if path is set."""
        with self._lock:
            self._data = {}
            self._append({"cleared": True})

    @property
    def size(self) -> int:
        """Number of entries currently in the scratchpad."""
        with self._lock:
            return len(self._data)

    def append(self, key: str, value: Any) -> None:
        """Append *value* to the list stored at *key*.

        - If *key* does not exist: creates a new list ``[value]``.
        - If *key* exists and holds a list: appends *value* in place.
        - If *key* exists and holds a non-list: raises ``TypeError``.
        """
        with self._lock:
            if key not in self._data:
                self._data[key] = [value]
                self._append({"key": key, "value": [value]})
                return
            existing = self._data[key]
            if not isinstance(existing, list):
                kind = type(existing).__name__
                raise TypeError(
                    f"Cannot append to key '{key}': existing value is {kind}, not list"
                )
            existing.append(value)
            # Persist the full updated list so reload is correct
            self._append({"key": key, "value": existing})

    def search(self, query: str) -> dict:
        """Return entries whose key or value contain *query* (case-insensitive).

        Matching is performed on ``str(key)`` and ``str(value)``.

        Args:
            query: Substring to search for.

        Returns:
            ``{key: value}`` dict of matching entries.
        """
        q = query.lower()
        with self._lock:
            return {
                k: v
                for k, v in self._data.items()
                if q in str(k).lower() or q in str(v).lower()
            }

    def snapshot(self) -> dict:
        """Return a shallow copy of the entire scratchpad state."""
        with self._lock:
            return dict(self._data)


__all__ = ["Scratchpad"]
