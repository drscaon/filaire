import json

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from filaire import generate_scene, write_outputs


@pytest.fixture(scope="module")
def folder(tmp_path_factory):
    scene = generate_scene("ethernet", count=2, seed=1, ends={"b": "rj45_inline"})
    return write_outputs(scene, tmp_path_factory.mktemp("out"))


def test_files_written(folder):
    assert (folder / "filaire_ethernet.usdc").exists()
    assert (folder / "sockets.usdc").exists()
    assert (folder / "cables.csv").read_text(encoding="utf-8").count("\n") == 3
    assert json.loads((folder / "summary.json").read_text(encoding="utf-8"))["count"] == 2


def test_stage_conventions(folder):
    stage = Usd.Stage.Open(str(folder / "filaire_ethernet.usdc"))
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert UsdPhysics.GetStageKilogramsPerUnit(stage) == 1.0
    assert stage.GetDefaultPrim().GetPath() == "/World"


def test_cable_physics(folder):
    stage = Usd.Stage.Open(str(folder / "filaire_ethernet.usdc"))
    cable = stage.GetPrimAtPath("/World/Cables/ethernet_000")
    assert cable.HasAPI(UsdPhysics.ArticulationRootAPI)
    segs = cable.GetChild("Segments").GetChildren()
    joints = cable.GetChild("Joints").GetChildren()
    assert len(joints) == len(segs) - 1 == cable.GetAttribute("filaire:segmentCount").Get() - 1
    seg = segs[0]
    assert seg.HasAPI(UsdPhysics.RigidBodyAPI) and seg.HasAPI(UsdPhysics.MassAPI)
    assert seg.GetChild("Collision").IsA(UsdGeom.Capsule)
    drive = UsdPhysics.DriveAPI.Get(joints[0], "rotY")
    k_deg = drive.GetStiffnessAttr().Get()
    L = cable.GetAttribute("filaire:segmentLength").Get()
    EI = cable.GetAttribute("filaire:bendingStiffness").Get()[0]
    assert k_deg * 180 / 3.141592653589793 == pytest.approx(EI / L, rel=1e-4)


def test_end_variants(folder):
    stage = Usd.Stage.Open(str(folder / "filaire_ethernet.usdc"))
    cable = stage.GetPrimAtPath("/World/Cables/ethernet_000")
    vs = cable.GetVariantSets()
    assert set(vs.GetNames()) == {"end_a", "end_b"}
    assert vs.GetVariantSet("end_b").GetVariantSelection() == "rj45_inline"
    assert {"rj45_plug", "rj45_inline", "cut", "stripped"} <= set(vs.GetVariantSet("end_b").GetVariantNames())
    mf = stage.GetPrimAtPath("/World/Cables/ethernet_000/End_B/Body/MateFrame")
    assert mf.GetAttribute("filaire:role").Get() == "receptacle"
    assert mf.GetAttribute("filaire:contactGender").Get() == "female"
    vs.GetVariantSet("end_b").SetVariantSelection("cut")
    assert not stage.GetPrimAtPath("/World/Cables/ethernet_000/End_B/Body")
    vs.GetVariantSet("end_b").SetVariantSelection("stripped")
    assert stage.GetPrimAtPath("/World/Cables/ethernet_000/End_B/Body/Collision/hull_00")


def test_sockets(folder):
    stage = Usd.Stage.Open(str(folder / "sockets.usdc"))
    sock = stage.GetPrimAtPath("/World/Sockets/rj45")
    assert sock and not sock.HasAPI(UsdPhysics.RigidBodyAPI)  # static
    hulls = sock.GetChild("Collision").GetChildren()
    assert hulls and all(h.HasAPI(UsdPhysics.CollisionAPI) for h in hulls)
    assert sock.GetChild("MateFrame").GetAttribute("filaire:keying").Get() == "keyed"


def test_one_visual_mesh_per_body(folder):
    stage = Usd.Stage.Open(str(folder / "filaire_ethernet.usdc"))
    bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    assert bodies
    for b in bodies:
        meshes = [
            p
            for p in Usd.PrimRange(b)
            if p.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(p).ComputePurpose() != UsdGeom.Tokens.guide
        ]
        assert len(meshes) == 1, b.GetPath()
        assert "PhysxRigidBodyAPI" in _authored_schemas(b)
    colliders = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)]
    assert all("PhysxCollisionAPI" in _authored_schemas(p) for p in colliders)


def _authored_schemas(prim):
    """API schemas as authored: the PhysX ones are not registered without Isaac Sim's plug-ins, so
    GetAppliedSchemas() may leave them out; the files still carry them for Isaac Sim."""
    names = []
    for spec in prim.GetPrimStack():
        op = spec.GetInfo("apiSchemas")
        if op:
            names += list(op.prependedItems) + list(op.explicitItems) + list(op.appendedItems)
    return names


def test_joint_anchors_meet(folder):
    """Both bodies of every joint put its anchor at the same point (cables curve: chords, not arcs)."""
    import numpy as np

    stage = Usd.Stage.Open(str(folder / "filaire_ethernet.usdc"))
    cache = UsdGeom.XformCache()

    def world(path, local):
        M = np.array(cache.GetLocalToWorldTransform(stage.GetPrimAtPath(path)))
        return np.append(np.array(local), 1.0) @ M

    n = 0
    for p in stage.Traverse():
        if p.IsA(UsdPhysics.Joint):
            j = UsdPhysics.Joint(p)
            a = world(j.GetBody0Rel().GetTargets()[0], j.GetLocalPos0Attr().Get())
            b = world(j.GetBody1Rel().GetTargets()[0], j.GetLocalPos1Attr().Get())
            assert np.linalg.norm(a[:3] - b[:3]) < 1e-6, p.GetPath()
            n += 1
    assert n > 10


def test_openusd_validators(folder):
    from filaire.validate import validate

    assert validate(folder / "filaire_ethernet.usdc") == []
    assert validate(folder / "sockets.usdc") == []


def test_no_physics(tmp_path):
    from filaire.validate import validate

    scene = generate_scene("power_c13", count=2, seed=1)
    out = write_outputs(scene, tmp_path, physics=False)
    for name in ("filaire_power_c13.usdc", "sockets.usdc"):
        stage = Usd.Stage.Open(str(out / name))
        assert stage.GetDefaultPrim().GetCustomDataByKey("filaire:physics") is False
        for p in stage.Traverse():
            assert not p.HasAPI(UsdPhysics.RigidBodyAPI) and not p.HasAPI(UsdPhysics.CollisionAPI)
            assert not p.IsA(UsdPhysics.Joint) and not p.IsA(UsdPhysics.Scene)
            assert not any(s.startswith("Physx") for s in _authored_schemas(p))
        assert validate(out / name) == []
    stage = Usd.Stage.Open(str(out / "filaire_power_c13.usdc"))
    cable = stage.GetPrimAtPath("/World/Cables/power_c13_000")
    assert cable.GetChild("Visual").IsA(UsdGeom.Mesh)  # one mesh for the whole cable
    assert stage.GetPrimAtPath("/World/Cables/power_c13_000/End_A/Body/MateFrame")
