"""Every generated file follows the Primvaria OpenUSD contract.

The same file in the four generators. Each repository's ``conftest.py`` provides the
``contract_files`` fixture: OpenUSD files freshly written by the generator, one folder.
"""

import importlib
from pathlib import Path

import pytest
from pxr import Usd

SRC = Path(__file__).parents[1] / "src"
GENERATOR = next(p.name for p in SRC.iterdir() if (p / "contract.py").exists())
contract = importlib.import_module(f"{GENERATOR}.contract")
conformance = importlib.import_module(f"{GENERATOR}.conformance")
package = importlib.import_module(GENERATOR)


def _stage_with_assets(files):
    for f in files:
        stage = Usd.Stage.Open(str(f))
        if contract.asset_roots(stage):
            stage.SetEditTarget(stage.GetSessionLayer())  # never touch the file
            return stage
    raise AssertionError("no generated file has an asset root")


def test_generated_files_conform(contract_files):
    assert contract_files
    for f in contract_files:
        assert contract.check(f) == [], f.name


def test_assets_name_their_generator(contract_files):
    stage = _stage_with_assets(contract_files)
    for prim in contract.asset_roots(stage):
        assert prim.GetAttribute("primvaria:contract").Get() == contract.CONTRACT
        assert prim.GetAttribute("primvaria:generator").Get() == GENERATOR
        assert prim.GetAttribute("primvaria:version").Get() == package.__version__
        assert prim.GetAttribute("primvaria:preset").Get()
        assert isinstance(prim.GetAttribute("primvaria:seed").Get(), int)
        info = Usd.ModelAPI(prim).GetAssetInfo()
        assert info["name"] and info["identifier"].path and info["version"] == package.__version__


@pytest.mark.parametrize("key", ["contract", "generator", "version", "preset", "seed"])
def test_a_missing_attribute_is_reported(contract_files, key):
    stage = _stage_with_assets(contract_files)
    prim = contract.asset_roots(stage)[0]
    prim.GetAttribute(f"primvaria:{key}").Block()
    assert any(f"no primvaria:{key}" in p for p in contract.conformance(stage))


def test_another_generator_is_reported_only_for_own_files(contract_files):
    stage = _stage_with_assets(contract_files)
    other = next(g for g in contract.GENERATORS if g != GENERATOR)
    prim = contract.asset_roots(stage)[0]
    prim.GetAttribute("primvaria:generator").Set(other)
    assert any("primvaria:generator" in p for p in contract.conformance(stage))
    assert contract.conformance(stage, own=False) == []


def test_a_broken_model_hierarchy_is_reported(contract_files):
    stage = _stage_with_assets(contract_files)
    prim = contract.asset_roots(stage)[0]
    parent = prim.GetParent()
    if parent.IsPseudoRoot():
        pytest.skip("the asset root is the file's root prim")
    Usd.ModelAPI(parent).SetKind("")
    assert any("not a group model" in p for p in contract.conformance(stage))


def test_no_asset_root_is_reported(contract_files):
    stage = _stage_with_assets(contract_files)
    for prim in contract.asset_roots(stage):
        Usd.ModelAPI(prim).SetKind("")
    assert any("no asset root" in p for p in contract.conformance(stage))


def test_command_line(contract_files, capsys):
    assert conformance.main([str(contract_files[0].parent)]) == 0
    assert "0 with issues" in capsys.readouterr().out
    assert conformance.main([]) == 2
