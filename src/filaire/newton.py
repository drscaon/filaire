"""Newton settings, as an OpenUSD layer over a file.

The main files hold plain OpenUSD and the standard `UsdPhysics` schemas. What Newton needs and
cannot guess from them is written here, in `<file>_newton.usda`: a layer whose only sublayer is
the main file and which adds, as `over`s:

* every collider but the shared ground: `newton:contactGap`, the distance from which contacts are
  generated, the same as the PhysX layer's contact offset. Newton's own default, 0.1 m, is meant
  for robots and floods its contact buffer with links this small;
* every joint between two segments: a limit of ±LIMIT degrees on each rotation (twist and both
  bendings). The file leaves these axes free, which UsdPhysics reads as free; Newton 1.8 gives a
  generic joint a degree of freedom only on an axis with a limit, and would make the cable rigid.
  A cable never bends that far between two neighbouring segments, so the limit is never reached
  and the motion is the file's: the drives (stiffness and damping) are read from the file;
* every segment: its rotational inertia raised by the armature Filaire's MuJoCo model gives the
  joints around it, k (dt / 0.3)² for the stiffest drive k of those joints at dt = 1 ms
  (sim/mujoco_model.py). A segment's own inertia (about 1e-10 kg m² for a USB-C cable) is so
  small that Newton's XPBD solver cannot hold a drive against it: without the armature a
  USB-C sample held flat at one end drops about 8 times more than beam theory. XPBD has no
  joint armature, so it is written as inertia; the mass is the file's.

Open the layer instead of the file to get both. Engines other than Newton ignore it.

    python -m filaire.newton output/usb_c            # check the layers of a pack

The check here is structural; Primvaria's CI opens the layers in Newton (scripts/newton_check.py).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from . import physx

SUFFIX = "_newton"
GROUND = physx.GROUND
GAP = "newton:contactGap"
LIMIT = 170.0  # degrees, either way: far beyond a bend between two neighbouring segments
ARMATURE_DT = 1e-3  # s: the timestep the armature is sized for, as in sim/mujoco_model.py
ARMATURE_PERIOD = 0.3  # the same rule: a = k (dt / 0.3)²
DEG = math.pi / 180
ROTATIONS = ("rotX", "rotY", "rotZ")
_F = Sdf.ValueTypeNames


def overlay_path(usd: Path) -> Path:
    return Path(usd).with_name(f"{Path(usd).stem}{SUFFIX}.usda")


def _free_rotations(prim) -> list[str]:
    """The rotation axes a generic joint leaves free: driven, with no limit of their own."""
    if not prim.IsA(UsdPhysics.Joint) or prim.GetTypeName() != "PhysicsJoint":
        return []
    return [
        axis
        for axis in ROTATIONS
        if prim.HasAPI(UsdPhysics.DriveAPI, axis) and not prim.HasAPI(UsdPhysics.LimitAPI, axis)
    ]


def _tune(prim) -> None:
    """The Newton opinions of one prim, written at the current edit target."""
    if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND:
        prim.CreateAttribute(GAP, _F.Float).Set(physx.CONTACT_OFFSET)
    for axis in _free_rotations(prim):
        limit = UsdPhysics.LimitAPI.Apply(prim, axis)
        limit.CreateLowAttr(-LIMIT)
        limit.CreateHighAttr(LIMIT)


def armatures(stage) -> dict:
    """{segment path: armature (kg m²)}: the stiffest drive of the joints around each segment."""
    out: dict = {}
    for joint in stage.Traverse():
        if joint.GetTypeName() != "PhysicsJoint":
            continue
        k = max(
            (UsdPhysics.DriveAPI(joint, a).GetStiffnessAttr().Get() or 0.0) / DEG
            for a in ROTATIONS
            if joint.HasAPI(UsdPhysics.DriveAPI, a)
        )
        a = k * (ARMATURE_DT / ARMATURE_PERIOD) ** 2
        j = UsdPhysics.Joint(joint)
        for rel in (j.GetBody0Rel(), j.GetBody1Rel()):
            for target in rel.GetTargets():
                if "/Segments/" in str(target):
                    out[target] = max(out.get(target, 0.0), a)
    return out


def write_overlay(usd) -> Path:
    """Write `<file>_newton.usda` beside an OpenUSD file and return its path."""
    usd = Path(usd)
    out = overlay_path(usd)
    out.unlink(missing_ok=True)
    layer = Sdf.Layer.CreateNew(str(out))
    layer.subLayerPaths.append(f"./{usd.name}")
    stage = Usd.Stage.Open(layer)
    base = Usd.Stage.Open(str(usd))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(base))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(base))
    UsdPhysics.SetStageKilogramsPerUnit(stage, UsdPhysics.GetStageKilogramsPerUnit(base))
    stage.SetDefaultPrim(stage.GetPrimAtPath(base.GetDefaultPrim().GetPath()))
    holders = []
    for prim in stage.Traverse():
        if prim.HasVariantSets():
            holders.append(prim)
        if not physx._in_variant(prim):
            _tune(prim)
    for path, a in armatures(base).items():  # segments: outside every variant
        mass = UsdPhysics.MassAPI(stage.GetPrimAtPath(path))
        inertia = mass.GetDiagonalInertiaAttr().Get()
        mass.GetDiagonalInertiaAttr().Set(type(inertia)(*(float(v) + a for v in inertia)))
    session = stage.GetSessionLayer()
    for holder in holders:  # what a variant brings: written inside that variant
        sets = holder.GetVariantSets()
        for name in sets.GetNames():
            vset = sets.GetVariantSet(name)
            for variant in vset.GetVariantNames():
                with Usd.EditContext(stage, session):
                    vset.SetVariantSelection(variant)
                with Usd.EditContext(stage, vset.GetVariantEditTarget(layer)):
                    for prim in Usd.PrimRange(holder):
                        if physx._in_variant(prim, f"{{{name}={variant}}}"):
                            _tune(prim)
    session.Clear()
    layer.Save()
    return out


def check(path) -> list[str]:
    """Structural problems of a Newton layer (empty: none)."""
    path = Path(path)
    layer = Sdf.Layer.FindOrOpen(str(path))
    main = path.with_name(path.stem.removesuffix(SUFFIX) + ".usdc")
    if list(layer.subLayerPaths) != [f"./{main.name}"]:
        return [f"its only sublayer must be ./{main.name}"]
    problems = []
    base = Usd.Stage.Open(str(main))
    if any(a.GetName().startswith("newton:") for p in base.Traverse() for a in p.GetAttributes()):
        problems.append(f"{main.name} holds Newton data itself")
    stage = Usd.Stage.Open(str(path))
    base_paths = {p.GetPath() for p in Usd.PrimRange.AllPrims(base.GetPseudoRoot())}
    extra = [
        p.GetPath() for p in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()) if p.GetPath() not in base_paths
    ]
    if extra:
        problems.append(f"defines prims the file does not have: {extra[0]}")
    for path, a in armatures(base).items():
        below = UsdPhysics.MassAPI(base.GetPrimAtPath(path)).GetDiagonalInertiaAttr().Get()
        over = UsdPhysics.MassAPI(stage.GetPrimAtPath(path)).GetDiagonalInertiaAttr().Get()
        if any(abs(o - b - a) > 1e-6 * (b + a) for o, b in zip(over, below, strict=True)):
            problems.append(f"{path}: inertia is not the file's plus the armature {a:.3g} kg m²")
    for prim in stage.Traverse():
        collider = prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND
        gap = prim.GetAttribute(GAP).Get() if prim.HasAttribute(GAP) else None
        if collider != (gap is not None):
            problems.append(f"{prim.GetPath()}: collider and {GAP} do not go together")
        if _free_rotations(prim):
            problems.append(f"{prim.GetPath()}: a driven rotation without a limit")
        for axis in ROTATIONS:
            if prim.IsA(UsdPhysics.Joint) and prim.HasAPI(UsdPhysics.LimitAPI, axis):
                lim = UsdPhysics.LimitAPI(prim, axis)
                low, high = lim.GetLowAttr().Get(), lim.GetHighAttr().Get()
                if (
                    low <= high
                    and not (low <= -LIMIT and high >= LIMIT)
                    and prim.HasAPI(UsdPhysics.DriveAPI, axis)
                ):
                    problems.append(f"{prim.GetPath()}: {axis} limited to [{low}, {high}] degrees")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the Newton layers (*_newton.usda) of packs or files.")
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    files = []
    for p in args.paths:
        files += sorted(p.rglob(f"*{SUFFIX}.usda")) if p.is_dir() else [p]
    if not files:
        print("no Newton layer found")
        return 1
    bad = 0
    for f in files:
        problems = check(f)
        bad += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {f}")
        for line in problems[:10]:
            print(f"     {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
