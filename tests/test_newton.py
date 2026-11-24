"""What Newton needs and cannot guess is a layer over each file, not part of the file."""

import pytest
from pxr import Sdf, Usd, UsdPhysics

from filaire import contract, newton
from filaire.cli import main
from filaire.generator import generate_scene, write_outputs
from filaire.validate import validate

CABLE = "/World/Cables/usb_c_000"


def _pack(tmp_path, **kw):
    return write_outputs(generate_scene("usb_c", count=1, length=0.3, seed=1), tmp_path, **kw)


def test_each_file_has_its_newton_layer(tmp_path):
    out = _pack(tmp_path)
    for name in ("filaire_usb_c", "sockets"):
        layer = out / f"{name}_newton.usda"
        assert newton.overlay_path(out / f"{name}.usdc") == layer and layer.exists()
        assert list(Sdf.Layer.FindOrOpen(str(layer)).subLayerPaths) == [f"./{name}.usdc"]
        assert newton.check(layer) == []
        assert validate(layer) == []
        assert contract.check(layer) == []
    assert newton.main([str(out)]) == 0
    for name in ("filaire_usb_c.usdc", "sockets.usdc"):  # the files themselves are unchanged
        assert contract.engine_data(Usd.Stage.Open(str(out / name))) == []


def test_every_rotation_between_segments_is_free_up_to_a_wide_limit(tmp_path):
    out = _pack(tmp_path)
    base = Usd.Stage.Open(str(out / "filaire_usb_c.usdc"))
    stage = Usd.Stage.Open(str(out / "filaire_usb_c_newton.usda"))
    joints = [p for p in stage.Traverse() if p.GetTypeName() == "PhysicsJoint"]
    assert len(joints) > 40
    for j in joints:
        assert not base.GetPrimAtPath(j.GetPath()).HasAPI(UsdPhysics.LimitAPI, "rotX")
        for axis in newton.ROTATIONS:
            limit = UsdPhysics.LimitAPI(j, axis)
            assert (limit.GetLowAttr().Get(), limit.GetHighAttr().Get()) == (-newton.LIMIT, newton.LIMIT)
            drive = UsdPhysics.DriveAPI(j, axis)  # the file's springs, untouched
            assert (
                drive.GetStiffnessAttr().Get()
                == UsdPhysics.DriveAPI(base.GetPrimAtPath(j.GetPath()), axis).GetStiffnessAttr().Get()
            )


def test_every_collider_gets_a_contact_gap(tmp_path):
    out = _pack(tmp_path)
    stage = Usd.Stage.Open(str(out / "filaire_usb_c_newton.usda"))
    cable = stage.GetPrimAtPath(CABLE)
    for end in ("usb_c_plug", "cut"):  # opinions follow the variant of each end
        cable.GetVariantSet("end_b").SetVariantSelection(end)
        for p in stage.Traverse():
            if p.HasAPI(UsdPhysics.CollisionAPI) and p.GetPath() != newton.GROUND:
                assert p.GetAttribute(newton.GAP).Get() == pytest.approx(newton.physx.CONTACT_OFFSET), p


def test_a_joint_left_without_a_limit_is_refused(tmp_path):
    out = _pack(tmp_path)
    layer = out / "filaire_usb_c_newton.usda"
    text = layer.read_text()
    layer.write_text(
        text.replace('"PhysicsLimitAPI:rotX", ', "", 1).replace(', "PhysicsLimitAPI:rotX"', "", 1)
    )
    assert any("without a limit" in p for p in newton.check(layer))


@pytest.mark.parametrize(("engines", "physx", "newton_"), [("none", 0, 0), ("physx", 2, 0), ("newton", 0, 2)])
def test_engines_chooses_the_layers(tmp_path, engines, physx, newton_):
    args = ["generate", "--preset", "usb_c", "--count", "1", "--out", str(tmp_path), "--engines", engines]
    assert main(args) == 0
    assert len(list(tmp_path.rglob("*_physx.usda"))) == physx
    assert len(list(tmp_path.rglob("*_newton.usda"))) == newton_


def test_no_layer_without_physics(tmp_path):
    _pack(tmp_path)
    out = _pack(tmp_path, physics=False)
    assert not list(out.glob("*_newton.usda"))
