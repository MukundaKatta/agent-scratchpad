"""Tests for agent-scratchpad."""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from agent_scratchpad import Scratchpad, ScratchpadError


def test_empty():
    pad = Scratchpad()
    assert len(pad) == 0
    assert pad.keys() == []

def test_set_get():
    pad = Scratchpad()
    pad.set("topic", "quantum")
    assert pad.get("topic") == "quantum"

def test_set_replaces():
    pad = Scratchpad()
    pad.set("x", 1)
    pad.set("x", 2)
    assert pad.get("x") == 2

def test_get_default():
    pad = Scratchpad()
    assert pad.get("missing") is None
    assert pad.get("missing", "fallback") == "fallback"

def test_get_deep_copy():
    pad = Scratchpad()
    pad.set("data", {"a": 1})
    result = pad.get("data")
    result["a"] = 99
    assert pad.get("data") == {"a": 1}

def test_has():
    pad = Scratchpad()
    pad.set("x", 1)
    assert pad.has("x") is True
    assert pad.has("y") is False

def test_contains():
    pad = Scratchpad()
    pad.set("k", "v")
    assert "k" in pad
    assert "z" not in pad

def test_set_returns_self():
    pad = Scratchpad()
    assert pad.set("k", "v") is pad

def test_delete():
    pad = Scratchpad()
    pad.set("x", 1)
    pad.delete("x")
    assert pad.has("x") is False

def test_delete_missing_no_error():
    pad = Scratchpad()
    pad.delete("nonexistent")

def test_append_creates_list():
    pad = Scratchpad()
    pad.append("items", "a")
    assert pad.get("items") == ["a"]

def test_append_grows_list():
    pad = Scratchpad()
    pad.append("items", "a")
    pad.append("items", "b")
    assert pad.get("items") == ["a", "b"]

def test_append_to_non_list_raises():
    pad = Scratchpad()
    pad.set("key", "string_value")
    with pytest.raises(ScratchpadError):
        pad.append("key", "x")

def test_prepend():
    pad = Scratchpad()
    pad.append("items", "b")
    pad.prepend("items", "a")
    assert pad.get("items") == ["a", "b"]

def test_prepend_creates_list():
    pad = Scratchpad()
    pad.prepend("items", "x")
    assert pad.get("items") == ["x"]

def test_extend_list():
    pad = Scratchpad()
    pad.extend_list("nums", [1, 2, 3])
    assert pad.get("nums") == [1, 2, 3]

def test_extend_list_grows():
    pad = Scratchpad()
    pad.extend_list("nums", [1, 2])
    pad.extend_list("nums", [3, 4])
    assert pad.get("nums") == [1, 2, 3, 4]

def test_extend_non_list_raises():
    pad = Scratchpad()
    pad.set("k", "string")
    with pytest.raises(ScratchpadError):
        pad.extend_list("k", [1])

def test_increment_default():
    pad = Scratchpad()
    pad.increment("count")
    assert pad.get("count") == 1

def test_increment_by():
    pad = Scratchpad()
    pad.increment("count", 5)
    assert pad.get("count") == 5

def test_increment_multiple():
    pad = Scratchpad()
    pad.increment("count")
    pad.increment("count")
    pad.increment("count")
    assert pad.get("count") == 3

def test_decrement():
    pad = Scratchpad()
    pad.set("count", 10)
    pad.decrement("count", 3)
    assert pad.get("count") == 7

def test_increment_non_numeric_raises():
    pad = Scratchpad()
    pad.set("x", "string")
    with pytest.raises(ScratchpadError):
        pad.increment("x")

def test_update():
    pad = Scratchpad()
    pad.update({"a": 1, "b": 2, "c": 3})
    assert pad.get("a") == 1
    assert pad.get("b") == 2
    assert pad.get("c") == 3

def test_clear():
    pad = Scratchpad()
    pad.set("x", 1).set("y", 2)
    pad.clear()
    assert len(pad) == 0

def test_clear_returns_self():
    pad = Scratchpad()
    assert pad.clear() is pad

def test_keys_sorted():
    pad = Scratchpad()
    pad.set("z", 1).set("a", 2).set("m", 3)
    assert pad.keys() == ["a", "m", "z"]

def test_len():
    pad = Scratchpad()
    pad.set("a", 1).set("b", 2)
    assert len(pad) == 2

def test_snapshot():
    pad = Scratchpad()
    pad.set("x", 1)
    snap = pad.snapshot()
    snap["x"] = 99
    assert pad.get("x") == 1

def test_to_text_empty():
    assert Scratchpad().to_text() == ""

def test_to_text_scalar():
    pad = Scratchpad()
    pad.set("topic", "ML")
    text = pad.to_text()
    assert "topic: ML" in text

def test_to_text_list():
    pad = Scratchpad()
    pad.append("papers", "Turing 1950")
    pad.append("papers", "Shannon 1948")
    text = pad.to_text()
    assert "papers:" in text
    assert "- Turing 1950" in text
    assert "- Shannon 1948" in text

def test_to_text_with_title():
    pad = Scratchpad()
    pad.set("x", 1)
    text = pad.to_text(title="Notes")
    assert text.startswith("Notes:")

def test_to_json():
    pad = Scratchpad()
    pad.set("x", 1)
    data = json.loads(pad.to_json())
    assert data["x"] == 1

def test_from_json():
    pad = Scratchpad.from_json('{"k": "v", "n": 42}')
    assert pad.get("k") == "v"
    assert pad.get("n") == 42

def test_save_load():
    pad = Scratchpad()
    pad.set("a", 1).append("items", "x")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        pad.save(path)
        loaded = Scratchpad.load(path)
        assert loaded.get("a") == 1
        assert loaded.get("items") == ["x"]
    finally:
        Path(path).unlink(missing_ok=True)

def test_jsonl_logging():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        pad = Scratchpad(path)
        pad.set("k", "v")
        pad.append("list", "item")
        pad.increment("count")
        lines = Path(path).read_text().strip().splitlines()
        assert len(lines) == 3
        ops = [json.loads(l)["op"] for l in lines]
        assert ops == ["set", "append", "increment"]
    finally:
        Path(path).unlink(missing_ok=True)

def test_no_logging_without_path():
    pad = Scratchpad()
    pad.set("x", 1)  # no exception

def test_repr():
    pad = Scratchpad()
    pad.set("x", 1)
    assert "Scratchpad" in repr(pad)
    assert "x" in repr(pad)

def test_chaining():
    pad = (
        Scratchpad()
        .set("a", 1)
        .set("b", 2)
        .increment("c")
        .append("items", "x")
    )
    assert pad.get("a") == 1
    assert pad.get("c") == 1
    assert pad.get("items") == ["x"]
