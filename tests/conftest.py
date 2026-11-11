"""Fixtures shared by the tests."""

import pytest

from filaire import generate_scene, write_outputs
from filaire.contract import usd_files


@pytest.fixture(scope="session")
def contract_files(tmp_path_factory):
    """OpenUSD files freshly generated: the cables and their sockets."""
    out = tmp_path_factory.mktemp("contract")
    folder = write_outputs(generate_scene("ethernet", count=2, seed=1, ends={"b": "rj45_inline"}), out)
    return usd_files([folder])
