"""
agent_scratchpad — keyed in-memory notepad for agent loops.

Store intermediate findings, inject them into prompts, search by key,
expire old notes. Zero dependencies (stdlib: time, fnmatch, dataclasses).
"""

from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

@dataclass
class ScratchpadEntry:
    """A single scratchpad note."""

    key: str
    value: str
    category: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    @property
    def ttl_remaining(self) -> float | None:
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0.0, remaining)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class KeyNotFound(KeyError):
    """Raised when a key does not exist in the scratchpad."""


class KeyAlreadyExists(KeyError):
    """Raised when trying to create a key that already exists."""


# ---------------------------------------------------------------------------
# Scratchpad
# ---------------------------------------------------------------------------

class Scratchpad:
    """
    Keyed in-memory notepad for agent loops.

    Usage::

        pad = Scratchpad()
        pad.write("search_result", "10 papers found about quantum computing")
        pad.write("summary", "Key themes: error correction, qubits", category="findings")

        # Inject into a prompt
        context = pad.to_context()
        messages.append({"role": "user", "content": f"{context}\\n\\nNow synthesize."})
    """

    def __init__(self) -> None:
        self._entries: dict[str, ScratchpadEntry] = {}

    # ------------------------------------------------------------------
    # Write / update / delete
    # ------------------------------------------------------------------

    def write(
        self,
        key: str,
        value: str,
        *,
        category: str | None = None,
        ttl_seconds: float | None = None,
        overwrite: bool = True,
    ) -> ScratchpadEntry:
        """
        Write a value to the scratchpad.

        Args:
            key: Unique identifier for this note.
            value: Text content.
            category: Optional grouping tag.
            ttl_seconds: If set, the entry expires after this many seconds.
            overwrite: If False and key exists (and not expired), raises
                       :class:`KeyAlreadyExists`.

        Returns:
            The :class:`ScratchpadEntry`.
        """
        existing = self._entries.get(key)
        if existing and not existing.expired and not overwrite:
            raise KeyAlreadyExists(f"Key {key!r} already exists")

        expires_at: float | None = None
        if ttl_seconds is not None:
            expires_at = time.time() + ttl_seconds

        entry = ScratchpadEntry(
            key=key,
            value=value,
            category=category,
            expires_at=expires_at,
        )
        self._entries[key] = entry
        return entry

    def update(self, key: str, value: str, *, ttl_seconds: float | None = None) -> ScratchpadEntry:
        """
        Update an existing entry.

        Args:
            key: Must already exist (and not be expired).
            value: New text value.
            ttl_seconds: Reset TTL if provided.

        Returns:
            Updated :class:`ScratchpadEntry`.

        Raises:
            :class:`KeyNotFound` if key doesn't exist or is expired.
        """
        entry = self._get_live(key)
        entry.value = value
        entry.updated_at = time.time()
        if ttl_seconds is not None:
            entry.expires_at = time.time() + ttl_seconds
        return entry

    def append(self, key: str, text: str, *, separator: str = "\n") -> ScratchpadEntry:
        """
        Append *text* to an existing entry (or create it if missing).

        Args:
            key: Entry key.
            text: Text to append.
            separator: Separator between old and new text.

        Returns:
            Updated :class:`ScratchpadEntry`.
        """
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            return self.write(key, text)
        entry.value = entry.value + separator + text
        entry.updated_at = time.time()
        return entry

    def delete(self, key: str) -> None:
        """
        Delete an entry by key.

        Args:
            key: Entry key.

        Raises:
            :class:`KeyNotFound` if key doesn't exist.
        """
        if key not in self._entries:
            raise KeyNotFound(key)
        del self._entries[key]

    def clear(self, category: str | None = None) -> int:
        """
        Delete all entries (or all entries in a category).

        Args:
            category: If given, only delete entries in this category.

        Returns:
            Number of entries deleted.
        """
        if category is None:
            count = len(self._entries)
            self._entries.clear()
            return count
        to_delete = [k for k, e in self._entries.items() if e.category == category]
        for k in to_delete:
            del self._entries[k]
        return len(to_delete)

    def purge_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        to_delete = [k for k, e in self._entries.items() if e.expired]
        for k in to_delete:
            del self._entries[k]
        return len(to_delete)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read(self, key: str, default: str | None = None) -> str | None:
        """
        Read a value by key.

        Args:
            key: Entry key.
            default: Value to return if key is missing or expired.

        Returns:
            Value string, or *default*.
        """
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            return default
        return entry.value

    def get_entry(self, key: str) -> ScratchpadEntry | None:
        """
        Return the full :class:`ScratchpadEntry`, or None if missing/expired.
        """
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            return None
        return entry

    def require(self, key: str) -> str:
        """
        Return a value, raising :class:`KeyNotFound` if missing or expired.
        """
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            raise KeyNotFound(key)
        return entry.value

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def keys(self, category: str | None = None) -> list[str]:
        """
        Return all live (non-expired) keys.

        Args:
            category: If given, filter to this category only.

        Returns:
            List of keys.
        """
        return [
            k for k, e in self._entries.items()
            if not e.expired and (category is None or e.category == category)
        ]

    def search(self, pattern: str, *, category: str | None = None) -> dict[str, str]:
        """
        Return entries whose key matches a glob *pattern*.

        Args:
            pattern: Glob pattern (e.g. ``"result_*"``).
            category: Optionally restrict to a category.

        Returns:
            ``{key: value}`` dict for matching live entries.
        """
        return {
            k: e.value
            for k, e in self._entries.items()
            if not e.expired
            and fnmatch.fnmatch(k, pattern)
            and (category is None or e.category == category)
        }

    def categories(self) -> list[str]:
        """Return distinct category names (live entries only)."""
        cats = {e.category for e in self._entries.values() if not e.expired and e.category}
        return sorted(cats)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Prompt injection
    # ------------------------------------------------------------------

    def to_context(
        self,
        *,
        category: str | None = None,
        header: str = "## Scratchpad Notes",
        entry_format: str = "**{key}**: {value}",
        separator: str = "\n\n",
    ) -> str:
        """
        Render all live entries as a formatted string for prompt injection.

        Args:
            category: Filter to a category.
            header: Section header (empty string to omit).
            entry_format: Python format string with ``{key}`` and ``{value}``.
            separator: Separator between entries.

        Returns:
            Formatted string.
        """
        live = [
            e for e in self._entries.values()
            if not e.expired and (category is None or e.category == category)
        ]
        if not live:
            return ""
        parts = []
        if header:
            parts.append(header)
        for e in live:
            parts.append(entry_format.format(key=e.key, value=e.value))
        return separator.join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def __contains__(self, key: str) -> bool:
        entry = self._entries.get(key)
        return entry is not None and not entry.expired

    def __len__(self) -> int:
        return sum(1 for e in self._entries.values() if not e.expired)

    def _get_live(self, key: str) -> ScratchpadEntry:
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            raise KeyNotFound(key)
        return entry
