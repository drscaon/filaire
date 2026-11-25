"""Command line of the Primvaria contract check, for this generator's files::

    python -m <generator>.conformance output/<preset>     # files or folders; exit 1 on any issue

A folder is also searched for packs (a ``manifest.json``): their ``instances.csv`` must say
what their OpenUSD files say. The code is in primvaria-contract
(``primvaria_contract.conformance``); the same file in the four generators.
"""

from __future__ import annotations

from primvaria_contract import conformance as _shared

from . import __version__
from .contract import GENERATOR


def main(argv: list[str] | None = None) -> int:
    return _shared.main(argv, GENERATOR, __version__)


if __name__ == "__main__":
    raise SystemExit(main())
