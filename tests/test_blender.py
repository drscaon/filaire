import importlib.util
import zipfile

import pytest

from filaire import generate_scene, write_outputs
from filaire.blender import write_addon


def test_addon_package(tmp_path):
    z = write_addon(tmp_path / "filaire_physics.zip")
    names = zipfile.ZipFile(z).namelist()
    assert set(names) == {"blender_manifest.toml", "__init__.py"}
    manifest = zipfile.ZipFile(z).read("blender_manifest.toml").decode()
    assert 'id = "filaire_physics"' in manifest and "blender_version_min" in manifest
    py = write_addon(tmp_path / "filaire_physics.py")
    assert "def setup_physics" in open(py, encoding="utf-8").read()


@pytest.mark.skipif(importlib.util.find_spec("bpy") is None, reason="needs Blender as a Python module (bpy)")
def test_blender_drop_holds_together(tmp_path):
    from filaire.blender.checks import blender_test

    folder = write_outputs(generate_scene("usb_c", count=1, length=0.3, layout="slack"), tmp_path)
    report = blender_test(folder, cables=1, seconds=0.8, verbose=False)
    assert report["passed"] == 1, report
    naive = blender_test(folder, cables=1, seconds=0.8, mode="naive", verbose=False)
    assert naive["tests"][0]["separated_mm"] > 5  # by hand, nothing holds the pieces together
