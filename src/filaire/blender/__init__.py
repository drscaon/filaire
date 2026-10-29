"""Blender support: an add-on that rebuilds the UsdPhysics description as Blender rigid bodies and
constraints whenever a USD file is imported (``physics.py``, runs inside Blender), and the checks run
through it (``checks.py`` drives ``run.py`` in a Blender process)."""

import os
import zipfile

from .. import __version__

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics.py")

MANIFEST = """schema_version = "1.0.0"
id = "filaire_physics"
version = "{version}"
name = "Filaire physics"
tagline = "Rigid bodies and constraints from UsdPhysics when importing USD"
maintainer = "Daniel Régis Sarmento Caon"
type = "add-on"
website = "https://github.com/drscaon/filaire"
tags = ["Physics", "Import-Export"]
blender_version_min = "4.4.0"
license = ["SPDX:MIT"]
"""


def write_addon(out):
    """Write the add-on: a Blender extension (.zip) or a single file (.py, legacy add-on or script)."""
    out = os.fspath(out)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if out.endswith(".zip"):
        version = __version__.split("+")[0].split("b")[0].split("a")[0].split("rc")[0]
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("blender_manifest.toml", MANIFEST.format(version=version))
            z.write(SCRIPT, "__init__.py")
    else:
        with open(SCRIPT, encoding="utf-8") as f, open(out, "w", encoding="utf-8") as g:
            g.write(f.read())
    return out
