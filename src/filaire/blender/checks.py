"""The drop check in Blender, through the add-on, and the same import with rigid bodies set by hand.

For each tested cable of a generated folder, a small scene references the cable file, keeps that
cable only (with its selected ends), lifts it by 2 cm and lets it fall on the ground. Each scene is
simulated in its own Blender process (``run.py``), either through the bpy module of this Python
(``pip install bpy``) or through a Blender executable (``--blender /path/to/blender``).

Pass when (setup mode):

* every joint holds: the two bodies of each joint meet within 0.5 mm at its anchor, and the
  connectors stay on their end segments (fixed joints, also within 0.5 mm);
* the cable rests on the ground: no point more than 0.5 mm under it, every body slower than
  5 cm/s at the end.

The naive mode (File > Import > USD, every mesh an active rigid body) reports how far apart the
neighbouring pieces end up: there is nothing to hold them together.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

MM = 1e-3
LIFT = 0.02
RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py")


def blender_command(blender=None):
    """How to run run.py: [python, run.py] when bpy is importable here, else [blender, -b, -P, run.py, --]."""
    if blender:
        return [blender, "-b", "--factory-startup", "-P", RUN, "--"]
    import importlib.util

    if importlib.util.find_spec("bpy") is not None:
        return [sys.executable, RUN]
    exe = shutil.which("blender")
    if exe:
        return [exe, "-b", "--factory-startup", "-P", RUN, "--"]
    raise RuntimeError("Blender not found: pip install bpy (Python 3.13), or pass --blender /path/to/blender")


def build_scene(cable_file: Path, cable_name: str, out: Path, lift: float = LIFT) -> Path:
    """A scene with one cable of a file, lifted: /World references the file's /World (its looks,
    physics materials, ground and physics scene come along), the other cables deactivated."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    layer = Sdf.Layer.Find(str(out.resolve()))
    stage = Usd.Stage.Open(layer) if layer else Usd.Stage.CreateNew(str(out))
    if layer:
        layer.Clear()
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = stage.DefinePrim("/World", "Xform")
    stage.SetDefaultPrim(world)
    world.GetReferences().AddReference(os.path.relpath(cable_file, out.parent))
    for c in stage.GetPrimAtPath("/World/Cables").GetChildren():
        if c.GetName() != cable_name:
            c.SetActive(False)
    cable = stage.GetPrimAtPath(f"/World/Cables/{cable_name}")
    op = UsdGeom.Xformable(cable).GetOrderedXformOps()[0]  # the cable's translate
    t = op.Get()
    op.Set(Gf.Vec3d(t[0], t[1], t[2] + lift))
    stage.GetRootLayer().Save()
    return out


def _joints(scene: Path) -> list[tuple]:
    """(body0 path, body1 path, anchor in body0, anchor in body1) of every joint of a scene."""
    stage = Usd.Stage.Open(str(scene))
    out = []
    for p in stage.Traverse():
        if p.IsA(UsdPhysics.Joint):
            j = UsdPhysics.Joint(p)
            b0, b1 = j.GetBody0Rel().GetTargets(), j.GetBody1Rel().GetTargets()
            if b0 and b1:
                out.append(
                    (
                        str(b0[0]),
                        str(b1[0]),
                        np.array(j.GetLocalPos0Attr().Get()),
                        np.array(j.GetLocalPos1Attr().Get()),
                    )
                )
    return out


def _speed(b, fps):
    t = b["traj"]
    if len(t) < 2:
        return 0.0
    return float(np.linalg.norm(np.array(t[-1]) - np.array(t[-2]))) / (12 / fps)


def evaluate(D: dict, joints: list) -> tuple[bool, str, dict]:
    bodies = D["bodies"]
    lowest = min(b["lowest"] for b in bodies.values() if b["lowest"] is not None)
    speed = max(_speed(b, D["fps"]) for b in bodies.values())
    if D["mode"] == "naive":
        # neighbouring imported meshes: how far their relative pose moved
        names = sorted(bodies)
        sep = 0.0
        for a, b in zip(names[:-1], names[1:], strict=True):
            A, B = bodies[a], bodies[b]
            r0 = np.linalg.inv(np.array(A["first"])) @ np.array(B["first"])
            r1 = np.linalg.inv(np.array(A["last"])) @ np.array(B["last"])
            sep = max(sep, float(np.linalg.norm(r1[:3, 3] - r0[:3, 3])))
        info = dict(pieces=len(bodies), separated_mm=round(sep / MM, 1), lowest_mm=round(lowest / MM, 2))
        return (
            sep < 0.5 * MM,
            f"{len(bodies)} loose pieces, neighbours drifted apart up to {sep / MM:.1f} mm",
            info,
        )
    by_usd = {b["usd"]: np.array(b["last"]) for b in bodies.values()}
    gap = 0.0
    for p0, p1, a0, a1 in joints:
        if p0 in by_usd and p1 in by_usd:
            w0 = by_usd[p0][:3, :3] @ a0 + by_usd[p0][:3, 3]
            w1 = by_usd[p1][:3, :3] @ a1 + by_usd[p1][:3, 3]
            gap = max(gap, float(np.linalg.norm(w0 - w1)))
    ok = gap < 0.5 * MM and lowest > -0.5 * MM and speed < 0.05
    info = dict(
        bodies=len(bodies),
        joints=len(joints),
        max_joint_gap_mm=round(gap / MM, 3),
        lowest_mm=round(lowest / MM, 2),
        max_speed=round(speed, 4),
    )
    msg = (
        f"{len(joints)} joints, widest gap {gap / MM:.3f} mm, "
        f"lowest point {lowest / MM:+.2f} mm, speed {speed:.3f} m/s"
    )
    return ok, msg, info


def blender_test(
    folder, cables: int = 1, seconds: float = 1.5, mode: str = "setup", blender=None, verbose=True
):
    folder = Path(folder)
    usd = next(folder.glob("filaire_*.usdc"))
    stage = Usd.Stage.Open(str(usd))
    names = [p.GetName() for p in stage.GetPrimAtPath("/World/Cables").GetChildren()]
    cmd = blender_command(blender)
    work = folder / "sim_test" / f"blender_{mode}"
    rows = []
    for name in names[:cables]:
        scene = build_scene(usd, name, work / f"scene_{name}.usda")
        out = work / f"{name}.json"
        t0 = time.time()
        p = subprocess.run(
            cmd + [str(scene), str(out), mode, str(seconds)], capture_output=True, text=True, timeout=3600
        )
        wall = time.time() - t0
        if p.returncode != 0 or not out.exists():
            ok, msg, info = False, "Blender run failed: " + (p.stderr.strip().splitlines() or ["?"])[-1], {}
        else:
            D = json.loads(out.read_text(encoding="utf-8"))
            finite = all(np.isfinite(np.array(b["last"])).all() for b in D["bodies"].values())
            ok, msg, info = evaluate(D, _joints(scene)) if finite else (False, "diverged", {})
        rows.append(dict(cable=name, ok=bool(ok), info=msg, wall=round(wall, 1), **info))
        if verbose:
            word = "pass" if ok else ("FAIL" if mode == "setup" else "apart")
            print(f"blender   {name:<20} {word}  {msg}  ({wall:.0f} s)", flush=True)
    report = dict(engine="blender", mode=mode, passed=sum(r["ok"] for r in rows), total=len(rows), tests=rows)
    (folder / "sim_test").mkdir(exist_ok=True)
    (folder / "sim_test" / f"blender_{mode}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report
