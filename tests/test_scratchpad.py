"""Unit tests for agent_scratchpad.

These tests use only the Python standard library (``unittest``) so they run
with no third-party dependencies::

    python3 -m unittest discover -s tests
"""

import os
import sys
import time
import unittest

# Support a ``src/`` layout without requiring installation: ensure ``src/`` is
# importable so ``python3 -m unittest discover -s tests`` works on a bare
# checkout with no ``pip install`` step.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from agent_scratchpad import (  # noqa: E402  (path setup must run first)
    KeyAlreadyExists,
    KeyNotFound,
    Scratchpad,
    ScratchpadEntry,
)


class WriteReadTests(unittest.TestCase):
    def test_write_and_read(self):
        pad = Scratchpad()
        pad.write("key1", "value1")
        self.assertEqual(pad.read("key1"), "value1")

    def test_read_missing_returns_none(self):
        pad = Scratchpad()
        self.assertIsNone(pad.read("missing"))

    def test_read_missing_returns_default(self):
        pad = Scratchpad()
        self.assertEqual(pad.read("missing", default="fallback"), "fallback")

    def test_write_returns_entry(self):
        pad = Scratchpad()
        entry = pad.write("k", "v")
        self.assertIsInstance(entry, ScratchpadEntry)
        self.assertEqual(entry.key, "k")
        self.assertEqual(entry.value, "v")

    def test_write_overwrites_by_default(self):
        pad = Scratchpad()
        pad.write("k", "v1")
        pad.write("k", "v2")
        self.assertEqual(pad.read("k"), "v2")

    def test_write_no_overwrite_raises(self):
        pad = Scratchpad()
        pad.write("k", "v1")
        with self.assertRaises(KeyAlreadyExists):
            pad.write("k", "v2", overwrite=False)

    def test_write_no_overwrite_allows_replacing_expired(self):
        # An expired key should not block a no-overwrite write.
        pad = Scratchpad()
        pad.write("k", "old", ttl_seconds=0.01)
        time.sleep(0.02)
        pad.write("k", "new", overwrite=False)
        self.assertEqual(pad.read("k"), "new")

    def test_write_category(self):
        pad = Scratchpad()
        entry = pad.write("k", "v", category="findings")
        self.assertEqual(entry.category, "findings")

    def test_get_entry_returns_entry(self):
        pad = Scratchpad()
        pad.write("k", "v", category="c")
        entry = pad.get_entry("k")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.category, "c")

    def test_get_entry_missing_returns_none(self):
        pad = Scratchpad()
        self.assertIsNone(pad.get_entry("nope"))

    def test_get_entry_expired_returns_none(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertIsNone(pad.get_entry("k"))


class UpdateAppendTests(unittest.TestCase):
    def test_update_existing(self):
        pad = Scratchpad()
        pad.write("k", "old")
        pad.update("k", "new")
        self.assertEqual(pad.read("k"), "new")

    def test_update_missing_raises(self):
        pad = Scratchpad()
        with self.assertRaises(KeyNotFound):
            pad.update("k", "v")

    def test_update_expired_raises(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        with self.assertRaises(KeyNotFound):
            pad.update("k", "v2")

    def test_update_sets_updated_at(self):
        pad = Scratchpad()
        pad.write("k", "v")
        before = time.time()
        pad.update("k", "v2")
        entry = pad.get_entry("k")
        self.assertGreaterEqual(entry.updated_at, before)

    def test_update_resets_ttl(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.5)
        pad.update("k", "v2", ttl_seconds=60)
        entry = pad.get_entry("k")
        self.assertGreater(entry.ttl_remaining, 59)

    def test_append_to_existing(self):
        pad = Scratchpad()
        pad.write("notes", "first")
        pad.append("notes", "second")
        value = pad.read("notes")
        self.assertIn("first", value)
        self.assertIn("second", value)

    def test_append_to_missing_creates(self):
        pad = Scratchpad()
        pad.append("notes", "first")
        self.assertEqual(pad.read("notes"), "first")

    def test_append_to_expired_creates_fresh(self):
        pad = Scratchpad()
        pad.write("notes", "stale", ttl_seconds=0.01)
        time.sleep(0.02)
        pad.append("notes", "fresh")
        self.assertEqual(pad.read("notes"), "fresh")

    def test_append_separator(self):
        pad = Scratchpad()
        pad.write("k", "a")
        pad.append("k", "b", separator=" | ")
        self.assertEqual(pad.read("k"), "a | b")

    def test_append_default_separator_is_newline(self):
        pad = Scratchpad()
        pad.write("k", "a")
        pad.append("k", "b")
        self.assertEqual(pad.read("k"), "a\nb")


class DeleteClearTests(unittest.TestCase):
    def test_delete(self):
        pad = Scratchpad()
        pad.write("k", "v")
        pad.delete("k")
        self.assertIsNone(pad.read("k"))

    def test_delete_missing_raises(self):
        pad = Scratchpad()
        with self.assertRaises(KeyNotFound):
            pad.delete("nope")

    def test_clear_all(self):
        pad = Scratchpad()
        pad.write("a", "1")
        pad.write("b", "2")
        self.assertEqual(pad.clear(), 2)
        self.assertEqual(len(pad), 0)

    def test_clear_by_category(self):
        pad = Scratchpad()
        pad.write("a", "1", category="facts")
        pad.write("b", "2", category="notes")
        removed = pad.clear(category="facts")
        self.assertEqual(removed, 1)
        self.assertNotIn("a", pad)
        self.assertIn("b", pad)

    def test_clear_unknown_category_removes_nothing(self):
        pad = Scratchpad()
        pad.write("a", "1", category="facts")
        self.assertEqual(pad.clear(category="ghost"), 0)
        self.assertIn("a", pad)


class RequireContainsLenTests(unittest.TestCase):
    def test_require_existing(self):
        pad = Scratchpad()
        pad.write("k", "v")
        self.assertEqual(pad.require("k"), "v")

    def test_require_missing_raises(self):
        pad = Scratchpad()
        with self.assertRaises(KeyNotFound):
            pad.require("missing")

    def test_require_expired_raises(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        with self.assertRaises(KeyNotFound):
            pad.require("k")

    def test_contains(self):
        pad = Scratchpad()
        pad.write("k", "v")
        self.assertIn("k", pad)
        self.assertNotIn("missing", pad)

    def test_len(self):
        pad = Scratchpad()
        pad.write("a", "1")
        pad.write("b", "2")
        self.assertEqual(len(pad), 2)


class TTLTests(unittest.TestCase):
    def test_entry_not_expired_by_default(self):
        pad = Scratchpad()
        entry = pad.write("k", "v")
        self.assertFalse(entry.expired)

    def test_ttl_remaining_none_without_ttl(self):
        pad = Scratchpad()
        entry = pad.write("k", "v")
        self.assertIsNone(entry.ttl_remaining)

    def test_entry_expires(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertIsNone(pad.read("k"))

    def test_expired_not_in_contains(self):
        pad = Scratchpad()
        pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertNotIn("k", pad)

    def test_expired_not_counted_in_len(self):
        pad = Scratchpad()
        pad.write("live", "v")
        pad.write("dead", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertEqual(len(pad), 1)

    def test_purge_expired(self):
        pad = Scratchpad()
        pad.write("live", "v")
        pad.write("dead", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        removed = pad.purge_expired()
        self.assertEqual(removed, 1)
        # purge actually removes the backing entry, not just hides it.
        self.assertEqual(len(pad._entries), 1)

    def test_ttl_remaining_value(self):
        pad = Scratchpad()
        entry = pad.write("k", "v", ttl_seconds=60)
        self.assertGreater(entry.ttl_remaining, 59)

    def test_ttl_remaining_clamps_to_zero(self):
        pad = Scratchpad()
        entry = pad.write("k", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertEqual(entry.ttl_remaining, 0.0)


class QueryTests(unittest.TestCase):
    def test_keys(self):
        pad = Scratchpad()
        pad.write("a", "1")
        pad.write("b", "2")
        self.assertEqual(set(pad.keys()), {"a", "b"})

    def test_keys_excludes_expired(self):
        pad = Scratchpad()
        pad.write("live", "1")
        pad.write("dead", "2", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertEqual(pad.keys(), ["live"])

    def test_keys_by_category(self):
        pad = Scratchpad()
        pad.write("a", "1", category="x")
        pad.write("b", "2", category="y")
        self.assertEqual(pad.keys(category="x"), ["a"])

    def test_search_glob(self):
        pad = Scratchpad()
        pad.write("result_1", "r1")
        pad.write("result_2", "r2")
        pad.write("other", "o")
        matches = pad.search("result_*")
        self.assertEqual(set(matches.keys()), {"result_1", "result_2"})

    def test_search_exact(self):
        pad = Scratchpad()
        pad.write("abc", "v")
        self.assertEqual(pad.search("abc"), {"abc": "v"})

    def test_search_no_match(self):
        pad = Scratchpad()
        pad.write("abc", "v")
        self.assertEqual(pad.search("xyz"), {})

    def test_search_category_filter(self):
        pad = Scratchpad()
        pad.write("res_1", "1", category="a")
        pad.write("res_2", "2", category="b")
        matches = pad.search("res_*", category="a")
        self.assertEqual(matches, {"res_1": "1"})

    def test_search_excludes_expired(self):
        pad = Scratchpad()
        pad.write("res_live", "1")
        pad.write("res_dead", "2", ttl_seconds=0.01)
        time.sleep(0.02)
        self.assertEqual(pad.search("res_*"), {"res_live": "1"})

    def test_categories(self):
        pad = Scratchpad()
        pad.write("a", "1", category="facts")
        pad.write("b", "2", category="notes")
        self.assertEqual(set(pad.categories()), {"facts", "notes"})

    def test_categories_sorted_and_unique(self):
        pad = Scratchpad()
        pad.write("a", "1", category="z")
        pad.write("b", "2", category="a")
        pad.write("c", "3", category="a")
        pad.write("d", "4")  # no category -> excluded
        self.assertEqual(pad.categories(), ["a", "z"])


class ToContextTests(unittest.TestCase):
    def test_to_context_empty(self):
        pad = Scratchpad()
        self.assertEqual(pad.to_context(), "")

    def test_to_context_includes_keys(self):
        pad = Scratchpad()
        pad.write("result", "10 papers found")
        ctx = pad.to_context()
        self.assertIn("result", ctx)
        self.assertIn("10 papers found", ctx)

    def test_to_context_has_header(self):
        pad = Scratchpad()
        pad.write("k", "v")
        self.assertIn("Scratchpad Notes", pad.to_context())

    def test_to_context_no_header(self):
        pad = Scratchpad()
        pad.write("k", "v")
        self.assertNotIn("Scratchpad Notes", pad.to_context(header=""))

    def test_to_context_category_filter(self):
        pad = Scratchpad()
        pad.write("a", "v1", category="facts")
        pad.write("b", "v2", category="notes")
        ctx = pad.to_context(category="facts")
        self.assertIn("v1", ctx)
        self.assertNotIn("v2", ctx)

    def test_to_context_custom_format(self):
        pad = Scratchpad()
        pad.write("mykey", "myval")
        ctx = pad.to_context(header="", entry_format="{key}={value}")
        self.assertIn("mykey=myval", ctx)

    def test_to_context_custom_separator(self):
        pad = Scratchpad()
        pad.write("a", "1")
        pad.write("b", "2")
        ctx = pad.to_context(header="", separator=" ;; ")
        self.assertIn(" ;; ", ctx)

    def test_to_context_excludes_expired(self):
        pad = Scratchpad()
        pad.write("live", "here")
        pad.write("dead", "gone", ttl_seconds=0.01)
        time.sleep(0.02)
        ctx = pad.to_context()
        self.assertIn("here", ctx)
        self.assertNotIn("gone", ctx)


if __name__ == "__main__":
    unittest.main()
