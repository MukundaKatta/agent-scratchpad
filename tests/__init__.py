"""Test package for agent-scratchpad.

This project uses a ``src/`` layout, so the package is not importable from the
repository root unless it has been installed. To keep the test suite runnable
with the standard library alone (``python3 -m unittest discover -s tests``,
with no ``pip install`` required), we add ``src/`` to ``sys.path`` here. This
module is imported by ``unittest`` before any test module, so the path is set
up before ``import agent_scratchpad`` runs.

If the package is already installed (e.g. via ``pip install -e .``), the
installed copy still takes precedence for normal imports; this only provides a
fallback for an uninstalled checkout.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
