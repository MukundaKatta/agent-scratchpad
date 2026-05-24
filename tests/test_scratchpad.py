"""Tests for agent_scratchpad.Scratchpad."""

from __future__ import annotations

import threading

import pytest

from agent_scratchpad import Scratchpad

# ---------------------------------------------------------------------------
# Basic set / get
# ---------------------------------------------------------------------------


def test_set_get_basic():
    pad = Scratchpad()
    pad.set("key", "value")
    assert pad.get("key") == "value"


def test_get_missing_returns_default():
    pad = Scratchpad()
    assert pad.get("nope") is None


def test_get_missing_custom_default():
    pad = Scratchpad()
    assert pad.get("nope", 42) == 42


def test_set_overwrites():
    pad = Scratchpad()
    pad.set("k", 1)
    pad.set("k", 2)
    assert pad.get("k") == 2


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_existing_returns_true():
    pad = Scratchpad()
    pad.set("x", 10)
    assert pad.delete("x") is True


def test_delete_existing_key_gone():
    pad = Scratchpad()
    pad.set("x", 10)
    pad.delete("x")
    assert pad.get("x") is None


def test_delete_missing_returns_false():
    pad = Scratchpad()
    assert pad.delete("ghost") is False


# ---------------------------------------------------------------------------
# has
# ---------------------------------------------------------------------------


def test_has_true():
    pad = Scratchpad()
    pad.set("present", 1)
    assert pad.has("present") is True


def test_has_false():
    pad = Scratchpad()
    assert pad.has("absent") is False


# ---------------------------------------------------------------------------
# keys / items
# ---------------------------------------------------------------------------


def test_keys_returns_list():
    pad = Scratchpad()
    pad.set("a", 1)
    pad.set("b", 2)
    assert sorted(pad.keys()) == ["a", "b"]


def test_keys_is_copy():
    pad = Scratchpad()
    pad.set("a", 1)
    k = pad.keys()
    k.append("mutated")
    assert "mutated" not in pad.keys()  # noqa: SIM118 — testing .keys() copy semantics


def test_items_returns_dict():
    pad = Scratchpad()
    pad.set("x", 99)
    assert pad.items() == {"x": 99}


def test_items_is_copy():
    pad = Scratchpad()
    pad.set("x", 99)
    d = pad.items()
    d["extra"] = "oops"
    assert "extra" not in pad.items()


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all():
    pad = Scratchpad()
    pad.set("a", 1)
    pad.set("b", 2)
    pad.clear()
    assert pad.keys() == []


# ---------------------------------------------------------------------------
# size
# ---------------------------------------------------------------------------


def test_size_property():
    pad = Scratchpad()
    assert pad.size == 0
    pad.set("k", "v")
    assert pad.size == 1
    pad.delete("k")
    assert pad.size == 0


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------


def test_append_creates_list_on_missing_key():
    pad = Scratchpad()
    pad.append("items", "first")
    assert pad.get("items") == ["first"]


def test_append_to_existing_list():
    pad = Scratchpad()
    pad.set("items", [1, 2])
    pad.append("items", 3)
    assert pad.get("items") == [1, 2, 3]


def test_append_to_non_list_raises():
    pad = Scratchpad()
    pad.set("items", "not a list")
    with pytest.raises(TypeError):
        pad.append("items", "value")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_case_insensitive_key():
    pad = Scratchpad()
    pad.set("FooBar", 1)
    result = pad.search("foobar")
    assert "FooBar" in result


def test_search_case_insensitive_value():
    pad = Scratchpad()
    pad.set("note", "Hello World")
    result = pad.search("hello")
    assert "note" in result


def test_search_no_match_empty_dict():
    pad = Scratchpad()
    pad.set("alpha", "beta")
    assert pad.search("xyz") == {}


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def test_snapshot_is_copy():
    pad = Scratchpad()
    pad.set("a", 1)
    snap = pad.snapshot()
    snap["b"] = 2
    assert "b" not in pad.items()


def test_snapshot_reflects_state():
    pad = Scratchpad()
    pad.set("x", 42)
    assert pad.snapshot() == {"x": 42}


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_thread_safety_no_data_loss():
    pad = Scratchpad()
    n_threads = 10
    keys_per_thread = 100

    def writer(thread_id: int):
        for i in range(keys_per_thread):
            pad.set(f"t{thread_id}_k{i}", i)

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert pad.size == n_threads * keys_per_thread


# ---------------------------------------------------------------------------
# JSONL persistence
# ---------------------------------------------------------------------------


def test_persist_set_get_roundtrip(tmp_path):
    path = str(tmp_path / "pad.jsonl")
    pad = Scratchpad(persist_path=path)
    pad.set("result", {"score": 0.9})
    pad2 = Scratchpad(persist_path=path)
    assert pad2.get("result") == {"score": 0.9}


def test_persist_reload_recovers_state(tmp_path):
    path = str(tmp_path / "pad.jsonl")
    pad = Scratchpad(persist_path=path)
    pad.set("step1", "done")
    pad.set("step2", 42)
    pad2 = Scratchpad(persist_path=path)
    assert pad2.get("step1") == "done"
    assert pad2.get("step2") == 42


def test_persist_clear_writes_marker(tmp_path):
    path = str(tmp_path / "pad.jsonl")
    pad = Scratchpad(persist_path=path)
    pad.set("a", 1)
    pad.clear()
    pad2 = Scratchpad(persist_path=path)
    assert pad2.size == 0


def test_persist_deleted_key_not_present_after_reload(tmp_path):
    path = str(tmp_path / "pad.jsonl")
    pad = Scratchpad(persist_path=path)
    pad.set("gone", "bye")
    pad.delete("gone")
    pad2 = Scratchpad(persist_path=path)
    assert not pad2.has("gone")


def test_persist_tilde_expansion(tmp_path, monkeypatch):
    # Redirect ~ to tmp_path so we don't pollute home dir
    monkeypatch.setenv("HOME", str(tmp_path))
    path = "~/agent_test.jsonl"
    pad = Scratchpad(persist_path=path)
    pad.set("k", "v")
    pad2 = Scratchpad(persist_path=path)
    assert pad2.get("k") == "v"


def test_persist_none_no_file_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pad = Scratchpad(persist_path=None)
    pad.set("k", "v")
    assert list(tmp_path.iterdir()) == []


def test_persist_delete_roundtrip(tmp_path):
    path = str(tmp_path / "pad.jsonl")
    pad = Scratchpad(persist_path=path)
    pad.set("keep", 1)
    pad.set("drop", 2)
    pad.delete("drop")
    pad2 = Scratchpad(persist_path=path)
    assert pad2.has("keep")
    assert not pad2.has("drop")
