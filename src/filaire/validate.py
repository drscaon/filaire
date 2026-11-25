"""OpenUSD validation of this generator's files with the validators shipped with OpenUSD::

    python -m <generator>.validate output/<preset>     # files or folders; exit 1 on any issue

Every validator of the UsdValidation registry, on each file once per variant of every variant
set. The code is in primvaria-contract (``primvaria_contract.validate``); this module gives
every name of it, as before. The same file in the four generators.
"""

from __future__ import annotations

from primvaria_contract import validate as _shared
from primvaria_contract.validate import *  # noqa: F403 (the module's names, as before)

from .contract import GENERATOR


def main(argv: list[str] | None = None) -> int:
    return _shared.main(argv, GENERATOR)


def __getattr__(name: str):  # the module's private helpers too, as before
    return getattr(_shared, name)


if __name__ == "__main__":
    raise SystemExit(main())
