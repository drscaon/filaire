"""The Primvaria OpenUSD contract, version 0, bound to this generator.

The code is in primvaria-contract (``primvaria_contract.contract``), shared by the four
generators of the suite; the contract itself is
https://github.com/drscaon/primvaria/blob/main/docs/contract.md. This module gives every name
of it, as before, and fills in this generator's name and version: they are written in the
identity of its assets (``write_identity``) and checked in its own files (``conformance``,
``check``). The same file in the four generators.
"""

from __future__ import annotations

from pathlib import Path

from primvaria_contract import contract as _shared
from primvaria_contract.contract import *  # noqa: F403 (the contract's names, as before)

from . import __version__

GENERATOR = __package__


def write_identity(prim, name: str, preset: str, seed: int, identifier: str) -> None:
    """Mark ``prim`` as an asset root of this generator: kind, assetInfo and the primvaria:*
    attributes (``primvaria_contract.contract.write_identity``)."""
    identity = {"generator": GENERATOR, "version": __version__}
    _shared.write_identity(prim, name, preset, seed, identifier, **identity)


def conformance(stage, own: bool = True) -> list[str]:
    """How a stage departs from the contract (empty: it conforms).

    own: the stage was written by this generator, so its assets name it and its version."""
    return _shared.conformance(stage, *((GENERATOR, __version__) if own else ()))


def check(path: str | Path, own: bool = True) -> list[str]:
    """``conformance`` of a file, and the rule of engine layers (contract, section 9)."""
    return _shared.check(path, *((GENERATOR, __version__) if own else ()))


def __getattr__(name: str):  # the contract's private helpers too, as before
    return getattr(_shared, name)
