"""What only PhysX reads is a layer over each file, not part of the file."""

import pytest
from pxr import Sdf, Usd, UsdPhysics

from filaire import generate_scene, physx, write_outputs
from filaire.validate import validate

CABLE = "/World/Cables/usb_c_000"


def _pack(tmp_path, **kw):
    return write_outputs(generate_scene("usb_c", count=2, seed=1), tmp_path, **kw)


def test_the_files_hold_no_engine_data(tmp_path):
    out = _pack(tmp_path)
    for name in ("filaire_usb_c.usdc", "sockets.usdc"):
        assert physx.engine_data(Usd.Stage.Open(str(out / name))) == []


def test_each_file_has_its_physx_layer(tmp_path):
    out = _pack(tmp_path)
    for name in ("filaire_usb_c", "sockets"):
        layer = out / f"{name}_physx.usda"
        assert physx.overlay_path(out / f"{name}.usdc") == layer and layer.exists()
        assert list(Sdf.Layer.FindOrOpen(str(layer)).subLayerPaths) == [f"./{name}.usdc"]
        assert physx.check(layer) == []
        assert validate(layer) == []  # the OpenUSD validators
    assert physx.main([str(out)]) == 0


def test_the_layer_tunes_every_body_and_collider(tmp_path):
    out = _pack(tmp_path)
    stage = Usd.Stage.Open(str(out / "filaire_usb_c_physx.usda"))
    bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    colliders = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)]
    assert len(bodies) > 100 and len(colliders) > 100
    for b in bodies:
        assert (
            b.GetAttribute("physxRigidBody:solverPositionIterationCount").Get() == physx.POSITION_ITERATIONS
        )
        assert b.GetAttribute("physxRigidBody:maxDepenetrationVelocity").Get() == 1.0
    for c in colliders:
        offset = c.GetAttribute("physxCollision:contactOffset")
        if c.GetPath() == physx.GROUND:  # the shared ground carries no engine data
            assert not offset
        else:
            assert offset.Get() == pytest.approx(physx.CONTACT_OFFSET)


def test_opinions_follow_the_variant_of_each_end(tmp_path):
    """A connector exists in its own variant only: its PhysX settings are written there, and
    leave nothing behind when the end is a clean cut."""
    out = _pack(tmp_path)
    stage = Usd.Stage.Open(str(out / "filaire_usb_c_physx.usda"))
    cable = stage.GetPrimAtPath(CABLE)
    ends = cable.GetVariantSet("end_b")
    assert {"usb_c_plug", "cut"} <= set(ends.GetVariantNames())
    ends.SetVariantSelection("usb_c_plug")
    body = stage.GetPrimAtPath(f"{CABLE}/End_B/Body")
    assert "PhysxRigidBodyAPI" in physx._authored(body)
    ends.SetVariantSelection("cut")
    assert not stage.GetPrimAtPath(f"{CABLE}/End_B/Body")  # not even an empty `over`


def test_a_layer_that_leaves_a_body_out_is_refused(tmp_path):
    out = _pack(tmp_path)
    layer = out / "sockets_physx.usda"
    assert physx.check(layer) == []
    text = layer.read_text().replace(
        "physxCollision:contactOffset = 0.0005", "physxCollision:contactOffset = 0"
    )
    layer.write_text(text)
    assert any("contact offset" in p for p in physx.check(layer))


def test_no_layer_without_physics(tmp_path):
    out = _pack(tmp_path)
    assert (out / "sockets_physx.usda").exists()
    out = _pack(tmp_path, physics=False)  # the same folder, written again without physics
    assert not list(out.glob("*_physx.usda"))
