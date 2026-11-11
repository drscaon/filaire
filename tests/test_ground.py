"""The ground and physics scene shared by every Primvaria project (filaire/ground.py)."""

import pytest
from pxr import Usd

from filaire.generator import generate_scene, write_outputs
from filaire.ground import conformance, read_ground


def test_ground_and_physics_scene_follow_the_shared_convention(tmp_path):
    folder = write_outputs(generate_scene("usb_c", 2, 1), tmp_path)
    files = sorted(folder.glob("*.usdc"))
    assert {f.name for f in files} >= {"filaire_usb_c.usdc", "sockets.usdc"}
    for f in files:
        stage = Usd.Stage.Open(str(f))
        assert conformance(stage) == [], f
        g = read_ground(stage)
        assert g["top"] == pytest.approx(0.0, abs=1e-9)
        assert g["dynamic_friction"] == pytest.approx(0.5)


def test_no_ground_without_physics(tmp_path):
    folder = write_outputs(generate_scene("usb_c", 1, 1), tmp_path, physics=False)
    stage = Usd.Stage.Open(str(folder / "filaire_usb_c.usdc"))
    assert read_ground(stage) is None and not stage.GetPrimAtPath("/World/PhysicsScene")
