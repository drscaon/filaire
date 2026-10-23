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
