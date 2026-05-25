# agent-scratchpad

Keyed working memory for LLM agents — set, append, increment, with optional JSONL logging.

Zero dependencies. Python 3.10+. MIT.

## Install

```bash
pip install agent-scratchpad
```

## Usage

```python
from agent_scratchpad import Scratchpad

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
```

## Inject into system prompt

```python
context = pad.to_text(title="Agent working memory")
messages = [
    {"role": "system", "content": f"You are helpful.\n\n{context}"},
    ...
]
```

## Persistence

```python
# JSONL log — every operation appended
pad = Scratchpad("logs/scratchpad.jsonl")
pad.set("key", "value")  # appended to log

# Save/load full snapshot
pad.save("state.json")
pad2 = Scratchpad.load("state.json")
```

## All operations

```python
pad.set("key", value)          # set scalar
pad.get("key", default=None)   # get (deep copy)
pad.delete("key")              # remove
pad.has("key")                 # bool
pad.append("list_key", item)   # append to list
pad.prepend("list_key", item)  # prepend to list
pad.extend_list("list", items) # extend list
pad.increment("counter", by=1) # add to number
pad.decrement("counter", by=1) # subtract
pad.update({"a": 1, "b": 2})  # set multiple
pad.clear()                    # remove all
pad.keys()                     # sorted key list
pad.snapshot()                 # deep copy of data
```

## License

MIT
