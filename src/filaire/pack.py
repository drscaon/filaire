"""The pack of this generator: ``instances.csv`` and ``manifest.json``, the same in the four
generators of the suite.

The code is in primvaria-contract (``primvaria_contract.pack``); this module gives every name
of it, as before, and fills in this generator's name and version in the manifest. The same
file in the four generators::

    write_pack(folder, pack="beach_sand", seed=1, aspects=("size", "shape"), summary={...})
    check_pack(folder)        # [] when the table still says what the files say
"""

from __future__ import annotations

from pathlib import Path

from primvaria_contract import pack as _shared
from primvaria_contract.pack import *  # noqa: F403 (the pack's names, as before)

from . import __version__
from .contract import GENERATOR


def write_pack(folder, pack, seed, aspects=(), summary=None, extra=None) -> Path:
    """Write ``instances.csv`` and ``manifest.json`` for the OpenUSD files already in ``folder``
    (``primvaria_contract.pack.write_pack``), as this generator's pack."""
    identity = {"generator": GENERATOR, "version": __version__}
    return _shared.write_pack(folder, pack, seed, aspects, summary, extra, **identity)


def __getattr__(name: str):  # the module's other names too, as before
    return getattr(_shared, name)
