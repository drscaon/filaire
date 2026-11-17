"""Every generated file follows the Primvaria OpenUSD contract.

The same file in the four generators. Each repository's ``conftest.py`` provides the
``contract_files`` fixture: OpenUSD files freshly written by the generator, one folder.
"""

import importlib
from pathlib import Path

import pytest
from pxr import Sdf, Usd

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


def test_assets_say_what_was_drawn(contract_files):
    stage = _stage_with_assets(contract_files)
    for prim in contract.asset_roots(stage):
        drawn = contract.variation(prim)
        assert isinstance(drawn["aspects"], list)
        assert all(contract.VALUE_NAME.fullmatch(name) for name in drawn)


def test_missing_aspects_are_reported(contract_files):
    stage = _stage_with_assets(contract_files)
    contract.asset_roots(stage)[0].GetAttribute(contract.ASPECTS).Block()
    assert any(f"no {contract.ASPECTS}" in p for p in contract.conformance(stage))


def test_a_variation_name_must_be_snake_case(contract_files):
    stage = _stage_with_assets(contract_files)
    prim = contract.asset_roots(stage)[0]
    with pytest.raises(ValueError, match="snake_case"):
        contract.write_variation(prim, (), {"clearanceMm": 0.1})
    contract.write_variation(prim, ("size",), {"flags": [True, False], "names": ["a", "b"], "none": None})
    drawn = contract.variation(prim)
    assert drawn["aspects"] == ["size"] and drawn["flags"] == [1.0, 0.0] and drawn["names"] == ["a", "b"]
    assert "none" not in drawn


def test_another_generator_is_reported_only_for_own_files(contract_files):
    stage = _stage_with_assets(contract_files)
    other = next(g for g in contract.GENERATORS if g != GENERATOR)
    prim = contract.asset_roots(stage)[0]
    prim.GetAttribute("primvaria:generator").Set(other)
    assert any("primvaria:generator" in p for p in contract.conformance(stage))
    # only a variant set this generator's assets carry, which section 7 gives to no other
    assert [p for p in contract.conformance(stage, own=False) if "section 7" not in p] == []


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


def test_files_hold_no_engine_data(contract_files):
    """Contract, section 9: what only one engine reads lies in an engine layer, not in the file."""
    files = [f for f in contract_files if not contract.is_engine_layer(f)]
    assert files
    for f in files:
        assert contract.engine_data(Usd.Stage.Open(str(f))) == [], f.name


def test_engine_data_in_a_file_is_reported(contract_files, tmp_path):
    files = [f for f in contract_files if not contract.is_engine_layer(f)]
    source = next(f for f in files if contract.asset_roots(Usd.Stage.Open(str(f))))
    copy = tmp_path / "copy.usda"
    Sdf.Layer.FindOrOpen(str(source)).Export(str(copy))  # the layer itself: a stage would let go of it
    stage = Usd.Stage.Open(str(copy))
    contract.asset_roots(stage)[0].AddAppliedSchema("PhysxRigidBodyAPI")
    stage.GetRootLayer().Save()
    assert any("engine data in the file" in p for p in contract.check(copy, own=False))


def test_an_engine_layer_lies_over_its_file_only(contract_files, tmp_path):
    for layer in (f for f in contract_files if contract.is_engine_layer(f)):
        assert not any("engine layer" in p for p in contract.check(layer)), layer.name
    stray = tmp_path / "nothing_physx.usda"
    Sdf.Layer.CreateNew(str(stray)).Save()
    assert any("only sublayer" in p for p in contract.check(stray, own=False))


def test_assets_say_what_they_are_with_semantic_labels(contract_files):
    """OpenUSD semantic labels: the classes, down to the preset, and the instance, the asset's name."""
    from pxr import UsdSemantics

    stage = _stage_with_assets(contract_files)
    for prim in contract.asset_roots(stage):
        classes = contract.labels(prim)
        assert len(classes) >= 2 and prim.GetAttribute("primvaria:preset").Get() in classes
        assert contract.labels(prim, "instance") == [prim.GetName()]
        query = UsdSemantics.LabelsQuery("class", Usd.TimeCode.Default())
        assert set(query.ComputeUniqueInheritedLabels(prim)) == set(classes)  # what a renderer reads


def test_missing_labels_are_reported(contract_files):
    stage = _stage_with_assets(contract_files)
    prim = contract.asset_roots(stage)[0]
    prim.GetAttribute("semantics:labels:class").Set([])
    prim.GetAttribute("semantics:labels:instance").Set(["someone_else"])
    problems = contract.conformance(stage)
    assert any("no class label" in p for p in problems) and any("instance label" in p for p in problems)


def test_class_labels_are_single_words(contract_files):
    stage = _stage_with_assets(contract_files)
    prim = contract.asset_roots(stage)[0]
    for bad in ((), ("Two Words",), ("grain", "")):
        with pytest.raises(ValueError, match="class labels"):
            contract.write_labels(prim, bad)


def _one_asset(generator=GENERATOR):
    """A stage that conforms, with one asset /World/Part, written with the contract's own helpers
    and said to be of ``generator``: the one a variant set of the test belongs to (section 7)."""
    from pxr import UsdGeom, UsdPhysics

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    contract.set_group(world, assembly=True)
    prim = UsdGeom.Xform.Define(stage, "/World/Part").GetPrim()
    contract.write_identity(prim, name="Part", preset="test", seed=1, identifier="./part.usda")
    contract.write_variation(prim, (), {})
    contract.write_labels(prim, ("part", "test"))
    prim.GetAttribute("primvaria:generator").Set(generator)
    assert contract.conformance(stage, own=False) == []
    return stage, prim


def _variant_set(prim, name, variants, selection=None):
    vset = prim.GetVariantSets().AddVariantSet(name)
    for v in variants:
        vset.AddVariant(v)
    if selection:
        vset.SetVariantSelection(selection)
    return vset


def test_generated_variant_sets_follow_section_7(contract_files):
    """Contract, section 7: snake_case names and a default selection, in every generated file."""
    for f in (f for f in contract_files if not contract.is_engine_layer(f)):
        stage = Usd.Stage.Open(str(f))
        for prim in stage.Traverse():
            for name in prim.GetVariantSets().GetNames():
                vset = prim.GetVariantSet(name)
                assert contract.VALUE_NAME.fullmatch(name), (f.name, name)
                assert all(contract.VALUE_NAME.fullmatch(v) for v in vset.GetVariantNames()), (f.name, name)
                assert vset.GetVariantSelection() in vset.GetVariantNames(), (f.name, name)


@pytest.mark.parametrize(
    "name, variants, selection, problem",
    [
        ("Moisture", ["dry", "wet"], "dry", "not lowercase snake_case"),
        ("moisture", ["dry", "Wet"], "dry", "variant 'Wet' is not lowercase snake_case"),
        ("moisture", ["dry", "wet"], None, "no default selection"),
    ],
)
def test_a_variant_set_against_section_7_is_reported(name, variants, selection, problem):
    stage, prim = _one_asset("granulaire")
    _variant_set(prim, name, variants, selection)
    assert any(problem in p for p in contract.conformance(stage, own=False))


CHANGED = "/World/Part: variant brass of finish changes the asset's identity"


def test_a_variant_that_changes_the_identity_is_reported():
    """A variant changes the asset's state, never what it is (section 5): its preset, its labels."""
    stage, prim = _one_asset("quincaillerie")
    prim.RemoveProperty("primvaria:preset")  # a local opinion is stronger than a variant's
    vset = _variant_set(prim, "finish", ["as_generated", "brass"])
    for variant, preset in (("as_generated", "test"), ("brass", "another")):
        vset.SetVariantSelection(variant)
        with vset.GetVariantEditContext():
            prim.CreateAttribute("primvaria:preset", Sdf.ValueTypeNames.String).Set(preset)
    vset.SetVariantSelection("as_generated")
    assert contract.conformance(stage, own=False) == [CHANGED]

    stage, prim = _one_asset("quincaillerie")
    prim.RemoveProperty("semantics:labels:class")
    vset = _variant_set(prim, "finish", ["as_generated", "brass"])
    for variant, classes in (("as_generated", ["part", "test"]), ("brass", ["part", "brass"])):
        vset.SetVariantSelection(variant)
        with vset.GetVariantEditContext():
            prim.CreateAttribute("semantics:labels:class", Sdf.ValueTypeNames.TokenArray).Set(classes)
            prim.CreateAttribute("test:roughness", Sdf.ValueTypeNames.Float).Set(0.3)  # a state: allowed
    vset.SetVariantSelection("as_generated")
    assert contract.conformance(stage, own=False) == [CHANGED]


def test_the_variant_check_leaves_the_stage_as_it_was():
    stage, prim = _one_asset("granulaire")
    vset = _variant_set(prim, "moisture", ["dry", "wet"], "dry")
    with vset.GetVariantEditContext():
        prim.CreateAttribute("test:water", Sdf.ValueTypeNames.Float).Set(0.0)
    vset.SetVariantSelection("wet")
    with vset.GetVariantEditContext():
        prim.CreateAttribute("test:water", Sdf.ValueTypeNames.Float).Set(0.2)
    stage.SetEditTarget(stage.GetSessionLayer())
    vset.SetVariantSelection("dry")  # the selection of the session layer is kept as it is
    session = stage.GetSessionLayer().ExportToString()
    assert contract.conformance(stage, own=False) == []
    assert stage.GetSessionLayer().ExportToString() == session
    assert vset.GetVariantSelection() == "dry" and prim.GetAttribute("test:water").Get() == 0.0


@pytest.mark.parametrize(
    "generator, name",
    [("maillage", "state"), ("quincaillerie", "moisture"), ("granulaire", "wetness")],
)
def test_a_variant_set_the_contract_does_not_give_its_generator_is_reported(generator, name):
    """Section 7 says what each variant set means and who uses it: a new one, or one used by another
    generator, is written into the contract first, so that a name means the same everywhere."""
    stage, prim = _one_asset(generator)
    _variant_set(prim, name, ["a", "b"], "a")
    problems = contract.conformance(stage, own=False)
    assert problems == [f"/World/Part: variant set {name}: not in the contract's section 7 for {generator}"]


@pytest.mark.parametrize(
    "path, type_name, problem",
    [
        ("/World/Part/MateFrameThread", "Xform", "not named MateFrame or MateFrame_<feature>"),
        ("/World/Part/MateFrame_Thread", "Xform", "not named MateFrame or MateFrame_<feature>"),
        ("/World/Part/MateFrame_thread", "Scope", "a MateFrame is an Xform, not Scope"),
        ("/World/MateFrame", "Xform", "a MateFrame outside an asset root"),
    ],
)
def test_a_mate_frame_against_section_8_is_reported(path, type_name, problem):
    stage, _ = _one_asset()
    stage.DefinePrim(path, type_name)
    assert any(problem in p for p in contract.conformance(stage, own=False))


def test_mate_frames_are_checked_in_every_variant():
    """A MateFrame often comes with a variant (a connector on a cable end): each one is checked."""
    stage, prim = _one_asset("filaire")
    vset = _variant_set(prim, "end_a", ["cut", "plug"], "cut")
    vset.SetVariantSelection("plug")
    with vset.GetVariantEditContext():
        stage.DefinePrim("/World/Part/Plug/MateFrame_Pins", "Xform")
    vset.SetVariantSelection("cut")
    problems = contract.conformance(stage, own=False)
    assert any("MateFrame_Pins: not named" in p and "(variant plug of end_a)" in p for p in problems)


def test_common_mate_attributes_are_not_written_yet():
    """Section 8: mate attributes stay in the generator's namespace; primvaria:mate:* is not in v1."""
    stage, prim = _one_asset()
    frame = stage.DefinePrim("/World/Part/MateFrame", "Xform")
    frame.CreateAttribute("test:role", Sdf.ValueTypeNames.Token).Set("plug")
    assert contract.conformance(stage, own=False) == []
    prim.CreateAttribute("primvaria:mate:role", Sdf.ValueTypeNames.Token).Set("plug")
    problems = contract.conformance(stage, own=False)
    assert any("primvaria:mate:* attributes are not in the contract" in p for p in problems)


def test_an_asset_that_points_outside_itself_is_reported():
    """Section 4: an asset is whole on its own, so that referenced alone it keeps its materials."""
    from pxr import UsdShade

    stage, prim = _one_asset()
    outside = UsdShade.Material.Define(stage, "/World/Looks/paint")
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(outside)
    problems = contract.conformance(stage, own=False)
    assert problems == ["/World/Part: material:binding points outside its asset, to /World/Looks/paint"]
    inside = UsdShade.Material.Define(stage, "/World/Part/Looks/paint")
    UsdShade.MaterialBindingAPI(prim).Bind(inside)
    assert contract.conformance(stage, own=False) == []
