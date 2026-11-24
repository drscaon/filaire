"""The presets CI's engine jobs run: every preset before a release, a sample on a commit.

    python .github/ci_presets.py granulaire.presets [PRESET ...]

prints the preset names, space-separated. With FULL=true (the release checks and the
"Run workflow" button), every preset. Otherwise the first preset, the reference, one
picked from the commit's hash (GITHUB_SHA), so that every commit runs the same ones when
it is run again and the commits, one after the other, go through all the presets, and
the presets named after the module, which a step needs whatever the sample (a deformable
preset for the OmniPhysics layers, say).
"""

import importlib
import os
import sys

presets = list(importlib.import_module(sys.argv[1]).PRESETS)
if os.environ.get("FULL") == "true":
    chosen = presets
else:
    picked = int(os.environ.get("GITHUB_SHA", "0")[:8] or "0", 16) % len(presets)
    chosen = list(dict.fromkeys([presets[0], presets[picked], *sys.argv[2:]]))
level = "all" if len(chosen) == len(presets) else "a sample"
print(f"presets: {' '.join(chosen)} ({level})", file=sys.stderr)
print(" ".join(chosen))
