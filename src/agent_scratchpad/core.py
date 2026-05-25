"""Keyed working memory scratchpad for LLM agents.

Supports string values, list appends, counters, and optional JSONL persistence.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any


class ScratchpadError(Exception):
    """Raised on invalid scratchpad operations."""


class Scratchpad:
    """Keyed working memory for an agent.

    Values can be strings, lists, numbers, or any JSON-serializable type.
    Use append() for list values; set() for scalars.

    Optionally persist every change to a JSONL log file so you can
    replay or inspect what the agent was thinking.

    Example::

        pad = Scratchpad()
        pad.set("topic", "quantum computing")
        pad.append("papers", "Shor 1994")
        pad.append("papers", "Grover 1996")
        pad.increment("search_count")

        print(pad.to_text())
        # topic: quantum computing
        # papers:
        #   - Shor 1994
        #   - Grover 1996
        # search_count: 1
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._data: dict[str, Any] = {}
        self._path: Path | None = Path(path) if path else None

    # ------------------------------------------------------------------
    # Set / get
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> "Scratchpad":
        """Set a key to a value (replaces any existing value)."""
        self._data[key] = value
        self._log("set", key, value)
        return self

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key, or default if not set."""
        return copy.deepcopy(self._data.get(key, default))

    def delete(self, key: str) -> "Scratchpad":
        """Remove a key. No-op if key does not exist."""
        self._data.pop(key, None)
        self._log("delete", key, None)
        return self

    def has(self, key: str) -> bool:
        """Return True if key exists."""
        return key in self._data

    # ------------------------------------------------------------------
    # List operations
    # ------------------------------------------------------------------

    def append(self, key: str, value: Any) -> "Scratchpad":
        """Append value to a list at key; creates the list if not present.

        Raises:
            ScratchpadError: if the existing value at key is not a list.
        """
        existing = self._data.get(key)
        if existing is None:
            self._data[key] = [value]
        elif isinstance(existing, list):
            existing.append(value)
        else:
            raise ScratchpadError(
                f"key {key!r} already holds a non-list value {type(existing).__name__!r}; "
                "use set() to replace it"
            )
        self._log("append", key, value)
        return self

    def prepend(self, key: str, value: Any) -> "Scratchpad":
        """Prepend value to a list at key; creates the list if not present.

        Raises:
            ScratchpadError: if the existing value at key is not a list.
        """
        existing = self._data.get(key)
        if existing is None:
            self._data[key] = [value]
        elif isinstance(existing, list):
            existing.insert(0, value)
        else:
            raise ScratchpadError(
                f"key {key!r} is not a list"
            )
        self._log("prepend", key, value)
        return self

    def extend_list(self, key: str, values: list[Any]) -> "Scratchpad":
        """Extend a list at key with multiple values."""
        existing = self._data.get(key)
        if existing is None:
            self._data[key] = list(values)
        elif isinstance(existing, list):
            existing.extend(values)
        else:
            raise ScratchpadError(f"key {key!r} is not a list")
        self._log("extend", key, values)
        return self

    # ------------------------------------------------------------------
    # Counter operations
    # ------------------------------------------------------------------

    def increment(self, key: str, by: int | float = 1) -> "Scratchpad":
        """Increment a numeric value at key; initialises to 0 if missing.

        Raises:
            ScratchpadError: if the existing value is not numeric.
        """
        existing = self._data.get(key, 0)
        if not isinstance(existing, (int, float)):
            raise ScratchpadError(f"key {key!r} is not numeric")
        self._data[key] = existing + by
        self._log("increment", key, by)
        return self

    def decrement(self, key: str, by: int | float = 1) -> "Scratchpad":
        """Decrement a numeric value at key."""
        return self.increment(key, -by)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def update(self, mapping: dict[str, Any]) -> "Scratchpad":
        """Set multiple keys at once."""
        for k, v in mapping.items():
            self.set(k, v)
        return self

    def clear(self) -> "Scratchpad":
        """Remove all keys."""
        self._data.clear()
        self._log("clear", "", None)
        return self

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return a sorted list of all keys."""
        return sorted(self._data)

    def snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the current data dict."""
        return copy.deepcopy(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    # ------------------------------------------------------------------
    # Text representation (for prompt injection)
    # ------------------------------------------------------------------

    def to_text(self, title: str | None = None) -> str:
        """Render the scratchpad as human-readable text for prompt injection.

        Lists are rendered as bullet items. Other values as ``key: value``.

        Example::

            pad.to_text(title="Agent notes")
            # Agent notes:
            # topic: quantum computing
            # papers:
            #   - Shor 1994
            #   - Grover 1996
        """
        if not self._data:
            return ""
        lines: list[str] = []
        if title:
            lines.append(f"{title}:")
        for key in sorted(self._data):
            value = self._data[key]
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Return the scratchpad data as a JSON string."""
        return json.dumps(self._data, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str, path: str | Path | None = None) -> "Scratchpad":
        """Create a Scratchpad from a JSON string."""
        pad = cls(path)
        pad._data = json.loads(text)
        return pad

    def save(self, path: str | Path) -> None:
        """Save the current snapshot to a JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Scratchpad":
        """Load a scratchpad from a JSON file."""
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_json(text, path)

    # ------------------------------------------------------------------
    # JSONL logging
    # ------------------------------------------------------------------

    def _log(self, op: str, key: str, value: Any) -> None:
        if self._path is None:
            return
        entry = {"ts": time.time(), "op": op, "key": key, "value": value}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def __repr__(self) -> str:
        return f"Scratchpad(keys={self.keys()})"
