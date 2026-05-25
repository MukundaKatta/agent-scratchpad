# agent-scratchpad

Keyed in-memory notepad for agent loops. Zero dependencies.

```python
from agent_scratchpad import Scratchpad

pad = Scratchpad()
pad.write("search_result", "10 papers on quantum computing found")
pad.write("theme", "error correction dominates", category="findings")

context = pad.to_context()
# Inject into next prompt
messages.append({"role": "user", "content": f"{context}\n\nSynthesize."})
```

## Install

```bash
pip install agent-scratchpad
```
