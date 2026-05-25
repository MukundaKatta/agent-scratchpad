# agent-scratchpad

A keyed in-memory notepad for LLM agent runs.

Store, retrieve, snapshot, and restore named pieces of information across turns — without leaking mutable state.

## Install

```bash
pip install agent-scratchpad
```

## Usage

```python
from agent_scratchpad import AgentScratchpad

pad = AgentScratchpad()
pad.set("user_goal", "Write a poem about the sea")
pad.set("draft", "Waves crash against the shore...")

print(pad.get("user_goal"))     # "Write a poem about the sea"
print(pad.count)                # 2
print(pad.keys())               # ["draft", "user_goal"]

snap = pad.snapshot()           # plain dict, deep copy
pad.delete("draft")
pad.clear()
pad.restore(snap)               # brings everything back
```

## API

### `AgentScratchpad()`

No constructor arguments.

### Writes (all chainable)

| Method | Description |
|--------|-------------|
| `set(key, value)` | Store a value (deep copy). |
| `update(data)` | Merge a dict into the scratchpad (deep copy). |
| `delete(key)` | Remove a key. No-op if missing. |
| `clear()` | Remove all entries. |
| `restore(data)` | Replace the entire scratchpad with a dict (deep copy). |

### Reads

| Method/Property | Description |
|-----------------|-------------|
| `get(key, default=None)` | Return a deep copy of the value, or `default`. |
| `require(key)` | Like `get()` but raises `ScratchpadKeyError` if absent. |
| `has(key)` | `True` if key exists. |
| `keys()` | Sorted list of all keys. |
| `values()` | Deep copies in key-sorted order. |
| `items()` | `(key, value)` tuples in key-sorted order. |
| `snapshot()` | Deep copy of the entire scratchpad as a dict. |
| `count` | Number of entries. |
| `is_empty` | `True` when empty. |

### Exceptions

| Exception | When |
|-----------|------|
| `ScratchpadKeyError` | `require()` called for a missing key. |

## License

MIT
