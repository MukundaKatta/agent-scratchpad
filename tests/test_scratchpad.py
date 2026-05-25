import time
import pytest
from agent_scratchpad import Scratchpad, ScratchpadEntry, KeyNotFound, KeyAlreadyExists


# ---------------------------------------------------------------------------
# write / read
# ---------------------------------------------------------------------------

def test_write_and_read():
    pad = Scratchpad()
    pad.write("key1", "value1")
    assert pad.read("key1") == "value1"

def test_read_missing_returns_none():
    pad = Scratchpad()
    assert pad.read("missing") is None

def test_read_missing_returns_default():
    pad = Scratchpad()
    assert pad.read("missing", default="fallback") == "fallback"

def test_write_returns_entry():
    pad = Scratchpad()
    e = pad.write("k", "v")
    assert isinstance(e, ScratchpadEntry)

def test_write_overwrites_by_default():
    pad = Scratchpad()
    pad.write("k", "v1")
    pad.write("k", "v2")
    assert pad.read("k") == "v2"

def test_write_no_overwrite_raises():
    pad = Scratchpad()
    pad.write("k", "v1")
    with pytest.raises(KeyAlreadyExists):
        pad.write("k", "v2", overwrite=False)

def test_write_category():
    pad = Scratchpad()
    e = pad.write("k", "v", category="findings")
    assert e.category == "findings"


# ---------------------------------------------------------------------------
# update / append
# ---------------------------------------------------------------------------

def test_update_existing():
    pad = Scratchpad()
    pad.write("k", "old")
    pad.update("k", "new")
    assert pad.read("k") == "new"

def test_update_missing_raises():
    pad = Scratchpad()
    with pytest.raises(KeyNotFound):
        pad.update("k", "v")

def test_update_sets_updated_at():
    pad = Scratchpad()
    pad.write("k", "v")
    before = time.time()
    pad.update("k", "v2")
    e = pad.get_entry("k")
    assert e.updated_at >= before

def test_append_to_existing():
    pad = Scratchpad()
    pad.write("notes", "first")
    pad.append("notes", "second")
    assert "first" in pad.read("notes")
    assert "second" in pad.read("notes")

def test_append_to_missing_creates():
    pad = Scratchpad()
    pad.append("notes", "first")
    assert pad.read("notes") == "first"

def test_append_separator():
    pad = Scratchpad()
    pad.write("k", "a")
    pad.append("k", "b", separator=" | ")
    assert pad.read("k") == "a | b"


# ---------------------------------------------------------------------------
# delete / clear
# ---------------------------------------------------------------------------

def test_delete():
    pad = Scratchpad()
    pad.write("k", "v")
    pad.delete("k")
    assert pad.read("k") is None

def test_delete_missing_raises():
    pad = Scratchpad()
    with pytest.raises(KeyNotFound):
        pad.delete("nope")

def test_clear_all():
    pad = Scratchpad()
    pad.write("a", "1")
    pad.write("b", "2")
    n = pad.clear()
    assert n == 2
    assert len(pad) == 0

def test_clear_by_category():
    pad = Scratchpad()
    pad.write("a", "1", category="facts")
    pad.write("b", "2", category="notes")
    pad.clear(category="facts")
    assert "a" not in pad
    assert "b" in pad


# ---------------------------------------------------------------------------
# require / contains / len
# ---------------------------------------------------------------------------

def test_require_existing():
    pad = Scratchpad()
    pad.write("k", "v")
    assert pad.require("k") == "v"

def test_require_missing_raises():
    pad = Scratchpad()
    with pytest.raises(KeyNotFound):
        pad.require("missing")

def test_contains():
    pad = Scratchpad()
    pad.write("k", "v")
    assert "k" in pad
    assert "missing" not in pad

def test_len():
    pad = Scratchpad()
    pad.write("a", "1")
    pad.write("b", "2")
    assert len(pad) == 2


# ---------------------------------------------------------------------------
# TTL / expiry
# ---------------------------------------------------------------------------

def test_entry_not_expired_by_default():
    pad = Scratchpad()
    e = pad.write("k", "v")
    assert not e.expired

def test_entry_expires():
    pad = Scratchpad()
    pad.write("k", "v", ttl_seconds=0.01)
    time.sleep(0.02)
    assert pad.read("k") is None

def test_expired_not_in_contains():
    pad = Scratchpad()
    pad.write("k", "v", ttl_seconds=0.01)
    time.sleep(0.02)
    assert "k" not in pad

def test_expired_not_counted_in_len():
    pad = Scratchpad()
    pad.write("live", "v")
    pad.write("dead", "v", ttl_seconds=0.01)
    time.sleep(0.02)
    assert len(pad) == 1

def test_purge_expired():
    pad = Scratchpad()
    pad.write("live", "v")
    pad.write("dead", "v", ttl_seconds=0.01)
    time.sleep(0.02)
    n = pad.purge_expired()
    assert n == 1
    assert len(pad._entries) == 1

def test_ttl_remaining():
    pad = Scratchpad()
    e = pad.write("k", "v", ttl_seconds=60)
    assert e.ttl_remaining > 59


# ---------------------------------------------------------------------------
# keys / search / categories
# ---------------------------------------------------------------------------

def test_keys():
    pad = Scratchpad()
    pad.write("a", "1")
    pad.write("b", "2")
    assert set(pad.keys()) == {"a", "b"}

def test_keys_by_category():
    pad = Scratchpad()
    pad.write("a", "1", category="x")
    pad.write("b", "2", category="y")
    assert pad.keys(category="x") == ["a"]

def test_search_glob():
    pad = Scratchpad()
    pad.write("result_1", "r1")
    pad.write("result_2", "r2")
    pad.write("other", "o")
    matches = pad.search("result_*")
    assert set(matches.keys()) == {"result_1", "result_2"}

def test_search_exact():
    pad = Scratchpad()
    pad.write("abc", "v")
    assert pad.search("abc") == {"abc": "v"}

def test_search_no_match():
    pad = Scratchpad()
    pad.write("abc", "v")
    assert pad.search("xyz") == {}

def test_categories():
    pad = Scratchpad()
    pad.write("a", "1", category="facts")
    pad.write("b", "2", category="notes")
    assert set(pad.categories()) == {"facts", "notes"}


# ---------------------------------------------------------------------------
# to_context
# ---------------------------------------------------------------------------

def test_to_context_empty():
    pad = Scratchpad()
    assert pad.to_context() == ""

def test_to_context_includes_keys():
    pad = Scratchpad()
    pad.write("result", "10 papers found")
    ctx = pad.to_context()
    assert "result" in ctx
    assert "10 papers found" in ctx

def test_to_context_has_header():
    pad = Scratchpad()
    pad.write("k", "v")
    ctx = pad.to_context()
    assert "Scratchpad Notes" in ctx

def test_to_context_no_header():
    pad = Scratchpad()
    pad.write("k", "v")
    ctx = pad.to_context(header="")
    assert "Scratchpad Notes" not in ctx

def test_to_context_category_filter():
    pad = Scratchpad()
    pad.write("a", "v1", category="facts")
    pad.write("b", "v2", category="notes")
    ctx = pad.to_context(category="facts")
    assert "v1" in ctx
    assert "v2" not in ctx

def test_to_context_custom_format():
    pad = Scratchpad()
    pad.write("mykey", "myval")
    ctx = pad.to_context(header="", entry_format="{key}={value}")
    assert "mykey=myval" in ctx
