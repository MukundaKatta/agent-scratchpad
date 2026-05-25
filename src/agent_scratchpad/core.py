"""Keyed in-memory notepad for LLM agent runs.

A lightweight, serialisable key-value store that an agent can use to
accumulate named pieces of information across turns.

Example::

    from agent_scratchpad import AgentScratchpad

    pad = AgentScratchpad()
    pad.set("user_goal", "Write a poem about the sea")
    pad.set("draft", "Waves crash against the shore...")

    print(pad.get("user_goal"))
    print(pad.snapshot())    # {"user_goal": "...", "draft": "..."}
    pad.delete("draft")
    pad.clear()
"""

from __future__ import annotations

import copy
from typing import Any


class ScratchpadKeyError(KeyError):
    """Raised when :meth:`AgentScratchpad.require` is called for a missing key."""


class AgentScratchpad:
    """A keyed in-memory notepad for a single agent run.

    All values are stored and returned as deep copies so callers cannot
    accidentally share mutable state with the scratchpad's internals.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> AgentScratchpad:
        """Store *value* under *key* (deep copy).

        Args:
            key:   String key.
            value: Any picklable/copyable value.

        Returns:
            ``self`` for chaining.
        """
        self._store[key] = copy.deepcopy(value)
        return self

    def update(self, data: dict[str, Any]) -> AgentScratchpad:
        """Merge *data* into the scratchpad (deep copy of each value).

        Args:
            data: Mapping of key/value pairs to set.

        Returns:
            ``self`` for chaining.
        """
        for k, v in data.items():
            self._store[k] = copy.deepcopy(v)
        return self

    def delete(self, key: str) -> AgentScratchpad:
        """Remove *key* from the scratchpad.

        No-op if *key* does not exist.

        Args:
            key: Key to remove.

        Returns:
            ``self`` for chaining.
        """
        self._store.pop(key, None)
        return self

    def clear(self) -> AgentScratchpad:
        """Remove all entries.

        Returns:
            ``self`` for chaining.
        """
        self._store.clear()
        return self

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return a deep copy of the value stored under *key*.

        Args:
            key:     Key to look up.
            default: Value to return when *key* is absent.

        Returns:
            Deep copy of the stored value, or *default*.
        """
        if key not in self._store:
            return default
        return copy.deepcopy(self._store[key])

    def require(self, key: str) -> Any:
        """Return the value under *key* or raise if absent.

        Args:
            key: Key to look up.

        Returns:
            Deep copy of the stored value.

        Raises:
            ScratchpadKeyError: If *key* is not in the scratchpad.
        """
        if key not in self._store:
            raise ScratchpadKeyError(key)
        return copy.deepcopy(self._store[key])

    def has(self, key: str) -> bool:
        """Return ``True`` if *key* is present in the scratchpad."""
        return key in self._store

    # ------------------------------------------------------------------
    # Bulk views
    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return a sorted list of all keys."""
        return sorted(self._store.keys())

    def values(self) -> list[Any]:
        """Return deep copies of all values, in key-sorted order."""
        return [copy.deepcopy(self._store[k]) for k in sorted(self._store)]

    def items(self) -> list[tuple[str, Any]]:
        """Return ``(key, value)`` tuples in key-sorted order (deep copies)."""
        return [(k, copy.deepcopy(self._store[k])) for k in sorted(self._store)]

    def snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the entire scratchpad as a plain dict."""
        return copy.deepcopy(self._store)

    def restore(self, data: dict[str, Any]) -> AgentScratchpad:
        """Replace the entire scratchpad with *data* (deep copy).

        Args:
            data: New scratchpad state.

        Returns:
            ``self`` for chaining.
        """
        self._store = copy.deepcopy(data)
        return self

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of entries currently in the scratchpad."""
        return len(self._store)

    @property
    def is_empty(self) -> bool:
        """``True`` if the scratchpad has no entries."""
        return len(self._store) == 0

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store

    def __repr__(self) -> str:
        return f"AgentScratchpad(count={self.count})"
