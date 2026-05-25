"""Tests for agent_scratchpad."""

from __future__ import annotations

import pytest

from agent_scratchpad import AgentScratchpad, ScratchpadKeyError

# ---------------------------------------------------------------------------
# Constructor / repr / dunder
# ---------------------------------------------------------------------------


def test_repr():
    pad = AgentScratchpad()
    assert "AgentScratchpad(count=0)" == repr(pad)


def test_repr_with_entries():
    pad = AgentScratchpad()
    pad.set("a", 1)
    assert "count=1" in repr(pad)


def test_len_empty():
    assert len(AgentScratchpad()) == 0


def test_len_with_entries():
    pad = AgentScratchpad()
    pad.set("x", 1).set("y", 2)
    assert len(pad) == 2


def test_contains_present():
    pad = AgentScratchpad()
    pad.set("key", "val")
    assert "key" in pad


def test_contains_absent():
    assert "missing" not in AgentScratchpad()


# ---------------------------------------------------------------------------
# set / get / has
# ---------------------------------------------------------------------------


def test_set_returns_self():
    pad = AgentScratchpad()
    assert pad.set("k", "v") is pad


def test_get_existing():
    pad = AgentScratchpad()
    pad.set("name", "Alice")
    assert pad.get("name") == "Alice"


def test_get_missing_returns_default():
    assert AgentScratchpad().get("x") is None


def test_get_custom_default():
    assert AgentScratchpad().get("x", 42) == 42


def test_has_present():
    pad = AgentScratchpad()
    pad.set("a", 1)
    assert pad.has("a") is True


def test_has_absent():
    assert AgentScratchpad().has("nope") is False


# ---------------------------------------------------------------------------
# Deep copy semantics
# ---------------------------------------------------------------------------


def test_set_deep_copies_value():
    original = {"nested": [1, 2, 3]}
    pad = AgentScratchpad()
    pad.set("d", original)
    original["nested"].append(4)
    # Scratchpad should have the old value
    assert pad.get("d") == {"nested": [1, 2, 3]}


def test_get_deep_copies_value():
    pad = AgentScratchpad()
    pad.set("lst", [1, 2])
    result = pad.get("lst")
    result.append(3)
    # Scratchpad internal should be unchanged
    assert pad.get("lst") == [1, 2]


# ---------------------------------------------------------------------------
# require
# ---------------------------------------------------------------------------


def test_require_present():
    pad = AgentScratchpad()
    pad.set("x", 99)
    assert pad.require("x") == 99


def test_require_missing_raises():
    with pytest.raises(ScratchpadKeyError):
        AgentScratchpad().require("missing")


def test_scratchpad_key_error_is_key_error():
    assert issubclass(ScratchpadKeyError, KeyError)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_removes_key():
    pad = AgentScratchpad()
    pad.set("a", 1)
    pad.delete("a")
    assert pad.has("a") is False


def test_delete_noop_on_missing():
    pad = AgentScratchpad()
    # Should not raise
    pad.delete("nonexistent")
    assert pad.count == 0


def test_delete_returns_self():
    pad = AgentScratchpad()
    assert pad.delete("x") is pad


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all():
    pad = AgentScratchpad()
    pad.set("a", 1).set("b", 2).set("c", 3)
    pad.clear()
    assert pad.count == 0
    assert pad.is_empty is True


def test_clear_returns_self():
    pad = AgentScratchpad()
    assert pad.clear() is pad


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_merges():
    pad = AgentScratchpad()
    pad.set("existing", "keep")
    pad.update({"new1": "a", "new2": "b"})
    assert pad.get("existing") == "keep"
    assert pad.get("new1") == "a"
    assert pad.count == 3


def test_update_overwrites():
    pad = AgentScratchpad()
    pad.set("key", "old")
    pad.update({"key": "new"})
    assert pad.get("key") == "new"


def test_update_returns_self():
    pad = AgentScratchpad()
    assert pad.update({}) is pad


def test_update_deep_copies():
    src = {"lst": [1, 2]}
    pad = AgentScratchpad()
    pad.update(src)
    src["lst"].append(3)
    assert pad.get("lst") == [1, 2]


# ---------------------------------------------------------------------------
# keys / values / items
# ---------------------------------------------------------------------------


def test_keys_sorted():
    pad = AgentScratchpad()
    pad.set("z", 1).set("a", 2).set("m", 3)
    assert pad.keys() == ["a", "m", "z"]


def test_values_in_key_order():
    pad = AgentScratchpad()
    pad.set("b", 2).set("a", 1)
    assert pad.values() == [1, 2]


def test_items_sorted():
    pad = AgentScratchpad()
    pad.set("b", 2).set("a", 1)
    assert pad.items() == [("a", 1), ("b", 2)]


def test_keys_empty():
    assert AgentScratchpad().keys() == []


# ---------------------------------------------------------------------------
# snapshot / restore
# ---------------------------------------------------------------------------


def test_snapshot_deep_copy():
    pad = AgentScratchpad()
    pad.set("x", [1, 2])
    snap = pad.snapshot()
    snap["x"].append(3)
    # Internal state unchanged
    assert pad.get("x") == [1, 2]


def test_snapshot_all_keys():
    pad = AgentScratchpad()
    pad.set("a", 1).set("b", 2)
    snap = pad.snapshot()
    assert set(snap.keys()) == {"a", "b"}


def test_restore_replaces():
    pad = AgentScratchpad()
    pad.set("old", "value")
    pad.restore({"new": 99})
    assert pad.has("old") is False
    assert pad.get("new") == 99


def test_restore_returns_self():
    pad = AgentScratchpad()
    assert pad.restore({}) is pad


def test_restore_deep_copies():
    data = {"lst": [1, 2]}
    pad = AgentScratchpad()
    pad.restore(data)
    data["lst"].append(3)
    assert pad.get("lst") == [1, 2]


# ---------------------------------------------------------------------------
# count / is_empty
# ---------------------------------------------------------------------------


def test_count_empty():
    assert AgentScratchpad().count == 0


def test_count_after_sets():
    pad = AgentScratchpad()
    pad.set("a", 1).set("b", 2)
    assert pad.count == 2


def test_is_empty_true():
    assert AgentScratchpad().is_empty is True


def test_is_empty_false():
    pad = AgentScratchpad()
    pad.set("x", 1)
    assert pad.is_empty is False


def test_is_empty_after_clear():
    pad = AgentScratchpad()
    pad.set("x", 1)
    pad.clear()
    assert pad.is_empty is True
