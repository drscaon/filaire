"""The presets CI's engine jobs run: every preset before a release, a sample on a commit.

    python .github/ci_presets.py granulaire.presets

prints the preset names, space-separated. With FULL=true (the release checks and the
"Run workflow" button), every preset. Otherwise two: the first preset, the reference, and
one picked from the commit's hash (GITHUB_SHA), so that every commit runs the same pair
when it is run again and the commits, one after the other, go through all the presets.
"""

import importlib
import os
import sys

presets = list(importlib.import_module(sys.argv[1]).PRESETS)
if os.environ.get("FULL") == "true":
    chosen = presets
else:
    picked = int(os.environ.get("GITHUB_SHA", "0")[:8] or "0", 16) % len(presets)
    chosen = list(dict.fromkeys([presets[0], presets[picked]]))
level = "all" if len(chosen) == len(presets) else "a sample"
print(f"presets: {' '.join(chosen)} ({level})", file=sys.stderr)
print(" ".join(chosen))
