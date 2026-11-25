"""The ground and physics scene of every Primvaria project, from primvaria-contract
(``primvaria_contract.ground``), where the floor every generator writes is described. The same
file in the four generators.
"""

from primvaria_contract import ground as _shared
from primvaria_contract.ground import *  # noqa: F403 (the ground's names, as before)


def __getattr__(name: str):  # the module's other names too, as before
    return getattr(_shared, name)
