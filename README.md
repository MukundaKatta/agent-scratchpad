# agent-scratchpad

[![CI](https://github.com/MukundaKatta/agent-scratchpad/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/agent-scratchpad/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A keyed, in-memory notepad for agent loops. Store intermediate findings across
the steps of a multi-turn agent, search them by key, expire stale notes with a
TTL, and render everything into a string you can drop straight into the next
prompt.

**Zero dependencies** — pure standard library (`time`, `fnmatch`,
`dataclasses`). Fully type-hinted and ships a PEP 561 `py.typed` marker.

## Why

Agent loops accumulate state: a search result here, a summary there, a running
list of observations. Stuffing all of that back into a model context manually
is fiddly. `Scratchpad` gives you a tiny key/value store designed for exactly
that pattern — including time-to-live so transient notes clean themselves up,
and a one-call `to_context()` for prompt injection.

## Install

```bash
pip install agent-scratchpad
```

Or from a checkout:

```bash
pip install .
```

## Quick start

```python
from agent_scratchpad import Scratchpad

pad = Scratchpad()
pad.write("search_result", "10 papers on quantum computing found")
pad.write("theme", "error correction dominates", category="findings")

context = pad.to_context()
# Inject into the next prompt:
messages.append({"role": "user", "content": f"{context}\n\nSynthesize."})
```

`to_context()` renders something like:

```text
## Scratchpad Notes

**search_result**: 10 papers on quantum computing found

**theme**: error correction dominates
```

## Usage

### TTL / expiry

Give a note a lifetime; it disappears once the TTL elapses. Reads,
`len()`, `in`, `keys()`, `search()`, and `to_context()` all ignore expired
entries automatically.

```python
pad.write("rate_limit_note", "back off until 12:05", ttl_seconds=300)

# ...5 minutes later...
pad.read("rate_limit_note")        # -> None (expired)
"rate_limit_note" in pad           # -> False

# Expired entries are skipped lazily; call purge_expired() to reclaim memory.
removed = pad.purge_expired()      # -> count of entries actually deleted
```

### Appending and updating

```python
pad.append("trace", "step 1: searched")
pad.append("trace", "step 2: summarized")   # newline-separated by default
pad.read("trace")                           # "step 1: searched\nstep 2: summarized"

pad.update("trace", "reset", ttl_seconds=60)  # raises KeyNotFound if absent
```

### Categories and search

```python
pad.write("res_1", "alpha", category="results")
pad.write("res_2", "beta", category="results")
pad.write("note", "scratch")

pad.keys(category="results")     # ["res_1", "res_2"]
pad.search("res_*")              # {"res_1": "alpha", "res_2": "beta"}
pad.categories()                 # ["results"]

# Filter prompt injection to a single category:
pad.to_context(category="results")
```

### Strict reads

```python
pad.read("missing")              # -> None
pad.read("missing", default="")  # -> ""
pad.require("missing")           # raises KeyNotFound
```

## API reference

### `Scratchpad`

| Method | Description |
| --- | --- |
| `write(key, value, *, category=None, ttl_seconds=None, overwrite=True)` | Create or replace a note. With `overwrite=False`, raises `KeyAlreadyExists` if a live key already exists. Returns the `ScratchpadEntry`. |
| `update(key, value, *, ttl_seconds=None)` | Update an existing live entry's value (and optionally reset its TTL). Raises `KeyNotFound` if missing or expired. |
| `append(key, text, *, separator="\n")` | Append text to a live entry, or create it if absent/expired. |
| `delete(key)` | Remove an entry. Raises `KeyNotFound` if absent. |
| `clear(category=None)` | Remove all entries (or all in a category). Returns the count removed. |
| `purge_expired()` | Drop expired entries from the backing store. Returns the count removed. |
| `read(key, default=None)` | Return a value, or `default` if missing/expired. |
| `get_entry(key)` | Return the full `ScratchpadEntry`, or `None` if missing/expired. |
| `require(key)` | Return a value, raising `KeyNotFound` if missing/expired. |
| `keys(category=None)` | List live keys, optionally filtered by category. |
| `search(pattern, *, category=None)` | Return `{key: value}` for live keys matching a glob `pattern`. |
| `categories()` | Sorted list of distinct categories among live entries. |
| `to_context(*, category=None, header="## Scratchpad Notes", entry_format="**{key}**: {value}", separator="\n\n")` | Render live entries as a string for prompt injection. Returns `""` if empty. |
| `key in pad` | `True` if the key exists and is not expired. |
| `len(pad)` | Number of live (non-expired) entries. |

### `ScratchpadEntry`

A dataclass describing a single note.

| Field / property | Description |
| --- | --- |
| `key: str` | The note's key. |
| `value: str` | The stored text. |
| `category: str \| None` | Optional grouping tag. |
| `created_at: float` | Unix timestamp set on creation. |
| `updated_at: float` | Unix timestamp of the last `update`/`append`. |
| `expires_at: float \| None` | Absolute expiry time, or `None` for no TTL. |
| `expired` *(property)* | `True` once `expires_at` has passed. |
| `ttl_remaining` *(property)* | Seconds until expiry (clamped at `0.0`), or `None` if no TTL. |

### Exceptions

- `KeyNotFound` — subclass of `KeyError`; raised by `update`, `delete`, and `require`.
- `KeyAlreadyExists` — subclass of `KeyError`; raised by `write(..., overwrite=False)`.

## Development

Run the test suite with the standard library only — no third-party packages
required:

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
