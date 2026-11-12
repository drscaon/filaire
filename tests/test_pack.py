"""Every pack has the same two files, and they say what the OpenUSD files say.

The same file in the four generators. Each repository's ``conftest.py`` provides the
``pack_folder`` fixture: a pack freshly written by the generator.
"""

import importlib
import shutil
from pathlib import Path

import pytest
from pxr import Usd

SRC = Path(__file__).parents[1] / "src"
GENERATOR = next(p.name for p in SRC.iterdir() if (p / "pack.py").exists())
pack = importlib.import_module(f"{GENERATOR}.pack")
contract = importlib.import_module(f"{GENERATOR}.contract")
conformance = importlib.import_module(f"{GENERATOR}.conformance")
package = importlib.import_module(GENERATOR)


@pytest.fixture
def copy(pack_folder, tmp_path):
    """A copy of the pack that a test may damage."""
    return Path(shutil.copytree(pack_folder, tmp_path / "pack"))


def test_the_pack_agrees_with_its_files(pack_folder):
    assert pack.check_pack(pack_folder) == []


def test_manifest(pack_folder):
    manifest = pack.read_manifest(pack_folder)
    assert manifest["contract"] == contract.CONTRACT
    assert manifest["generator"] == GENERATOR and manifest["version"] == package.__version__
    assert manifest["pack"] and isinstance(manifest["seed"], int) and isinstance(manifest["aspects"], list)
    assert manifest["table"] == pack.TABLE and manifest["assets"] == len(pack.read_table(pack_folder)) > 0
    assert all((pack_folder / f).exists() for f in manifest["files"])


def test_one_row_per_asset_with_the_common_columns_first(pack_folder):
    table = pack.read_table(pack_folder)
    assert tuple(table[0])[: len(pack.FIRST)] == pack.FIRST
    assert len({(r["file"], r["prim"]) for r in table}) == len(table)
    for row in table:
        stage = Usd.Stage.Open(str(pack_folder / row["file"]))
        prim = stage.GetPrimAtPath(row["prim"])
        assert prim.GetName() == row["name"]
        assert row["generator"] == GENERATOR and row["version"] == package.__version__
        assert row["seed"] == str(prim.GetAttribute("primvaria:seed").Get())
        for key, value in contract.variation(prim).items():
            assert row["aspects" if key == "aspects" else f"variation:{key}"] == pack.cell(value)
        for key, value in contract.measured(prim).items():
            assert row[f"measured:{key}"] == pack.cell(value)


def test_assets_carry_measurements(pack_folder):
    table = pack.read_table(pack_folder)
    assert any(key.startswith("measured:") for key in table[0])


def test_a_table_that_disagrees_is_reported(copy):
    table = pack.read_table(copy)
    lines = (copy / pack.TABLE).read_text(encoding="utf-8").splitlines()
    seed = list(table[0]).index("seed")
    cells = lines[1].split(",")
    cells[seed] = str(int(cells[seed]) + 1)
    changed = "\n".join([lines[0], ",".join(cells), *lines[2:]]) + "\n"
    (copy / pack.TABLE).write_text(changed, encoding="utf-8")
    assert any("seed is" in p for p in pack.check_pack(copy))


def test_a_missing_row_and_a_missing_file_are_reported(copy):
    lines = (copy / pack.TABLE).read_text(encoding="utf-8").splitlines()
    (copy / pack.TABLE).write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    problems = pack.check_pack(copy)
    assert any("no row for" in p for p in problems) and any("rows in" in p for p in problems)
    (copy / pack.read_manifest(copy)["files"][0]).unlink()
    assert any("missing file" in p for p in pack.check_pack(copy))
    (copy / pack.MANIFEST).unlink()
    assert pack.check_pack(copy) == [f"no {pack.MANIFEST} or no {pack.TABLE}"]


def test_command_line_checks_packs(pack_folder, copy, capsys):
    assert conformance.main([str(pack_folder)]) == 0
    assert "1 packs checked" in capsys.readouterr().out
    (copy / pack.TABLE).write_text("name\n", encoding="utf-8")
    assert conformance.main([str(copy)]) == 1
