"""PhysX settings (Isaac Sim), as an OpenUSD layer over a file.

The main files hold plain OpenUSD: `UsdGeom`, `UsdShade` and the standard `UsdPhysics`
schemas, which every engine reads. What only PhysX reads is kept out of them and written
here, in `<file>_physx.usda`: a layer whose only sublayer is the main file and which adds,
as `over`s, the PhysX schemas and attributes:

* every rigid body: `PhysxRigidBodyAPI` with the solver iteration counts light links need
  and a cap on the depenetration velocity;
* every collider but the shared ground: `PhysxCollisionAPI` with the contact and rest offsets.

Open the layer instead of the file to get both (Isaac Sim: File > Open). Opinions on what
lives inside a variant are written inside the same variant, so they follow the selection.

    python -m filaire.physx output/usb_c            # check the layers of a pack

Not simulated here: PhysX needs Isaac Sim and an NVIDIA RTX GPU. The check is structural.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdPhysics

SUFFIX = "_physx"
GROUND = "/World/Ground"  # the shared ground carries no engine data (ground.py)
CONTACT_OFFSET = 0.0005  # m: contacts are generated from this distance on
REST_OFFSET = 0.0  # m
POSITION_ITERATIONS = 32  # light links on stiff joints need many
VELOCITY_ITERATIONS = 4
MAX_DEPENETRATION_VELOCITY = 1.0  # m/s
_F = Sdf.ValueTypeNames


def overlay_path(usd: Path) -> Path:
    return Path(usd).with_name(f"{Path(usd).stem}{SUFFIX}.usda")


def is_overlay(path: Path) -> bool:
    return Path(path).stem.endswith(SUFFIX)


def _tune(prim) -> None:
    """The PhysX opinions of one prim, written at the current edit target."""
    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
        prim.AddAppliedSchema("PhysxRigidBodyAPI")
        prim.CreateAttribute("physxRigidBody:solverPositionIterationCount", _F.Int).Set(POSITION_ITERATIONS)
        prim.CreateAttribute("physxRigidBody:solverVelocityIterationCount", _F.Int).Set(VELOCITY_ITERATIONS)
        prim.CreateAttribute("physxRigidBody:maxDepenetrationVelocity", _F.Float).Set(
            MAX_DEPENETRATION_VELOCITY
        )
        prim.CreateAttribute("physxRigidBody:enableCCD", _F.Bool).Set(False)
    if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND:
        prim.AddAppliedSchema("PhysxCollisionAPI")
        prim.CreateAttribute("physxCollision:contactOffset", _F.Float).Set(CONTACT_OFFSET)
        prim.CreateAttribute("physxCollision:restOffset", _F.Float).Set(REST_OFFSET)


def _in_variant(prim, selection: str = "") -> bool:
    """Whether a prim is defined inside a variant (and so exists only when it is selected);
    with a selection such as "{end_a=usb_c_plug}", inside that very variant."""
    paths = [spec.path for spec in prim.GetPrimStack()]
    return any(p.ContainsPrimVariantSelection() and selection in str(p) for p in paths)


def write_overlay(usd) -> Path:
    """Write `<file>_physx.usda` beside an OpenUSD file and return its path."""
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
    # what exists whatever the variants: written on the prims themselves
    holders = []
    for prim in stage.Traverse():
        if prim.HasVariantSets():
            holders.append(prim)
        if not _in_variant(prim):
            _tune(prim)
    # what a variant brings: written inside that variant, one selection at a time (the
    # selections are tried in the session layer, which is not saved)
    session = stage.GetSessionLayer()
    for holder in holders:
        sets = holder.GetVariantSets()
        for name in sets.GetNames():
            vset = sets.GetVariantSet(name)
            for variant in vset.GetVariantNames():
                with Usd.EditContext(stage, session):
                    vset.SetVariantSelection(variant)
                with Usd.EditContext(stage, vset.GetVariantEditTarget(layer)):
                    for prim in Usd.PrimRange(holder):
                        if _in_variant(prim, f"{{{name}={variant}}}"):
                            _tune(prim)
    session.Clear()
    layer.Save()
    return out


def _authored(prim) -> set[str]:
    """API schemas as authored: the PhysX ones are not registered without Isaac Sim's plug-ins."""
    names: set[str] = set()
    for spec in prim.GetPrimStack():
        listed = spec.GetInfo("apiSchemas") if spec.HasInfo("apiSchemas") else None
        if listed:
            names.update(listed.GetAppliedItems())
    return names


def engine_data(stage) -> list[str]:
    """What a stage holds that only PhysX reads: 'path: name' lines (empty for a main file)."""
    found = []
    for prim in stage.Traverse():
        found += [f"{prim.GetPath()}: {s}" for s in sorted(_authored(prim)) if s.startswith("Physx")]
        found += [
            f"{prim.GetPath()}: {a.GetName()}"
            for a in prim.GetAttributes()
            if a.GetName().startswith("physx")
        ]
    return found


def check(path) -> list[str]:
    """Structural problems of a PhysX layer (empty: none)."""
    path = Path(path)
    layer = Sdf.Layer.FindOrOpen(str(path))
    main = path.with_name(path.stem.removesuffix(SUFFIX) + ".usdc")
    problems = []
    if list(layer.subLayerPaths) != [f"./{main.name}"]:
        problems.append(f"its only sublayer must be ./{main.name}")
        return problems
    base = Usd.Stage.Open(str(main))
    if engine_data(base):
        problems.append(f"{main.name} holds PhysX data itself")
    stage = Usd.Stage.Open(str(path))
    base_paths = {p.GetPath() for p in Usd.PrimRange.AllPrims(base.GetPseudoRoot())}
    extra = [
        p.GetPath() for p in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()) if p.GetPath() not in base_paths
    ]
    if extra:
        problems.append(f"defines prims the file does not have: {extra[0]}")
    holders = [p for p in stage.Traverse() if p.HasVariantSets()]
    session = stage.GetSessionLayer()
    selections = [{}]  # the file's own selections, then each variant of each set in turn
    for holder in holders:
        for name in holder.GetVariantSets().GetNames():
            for variant in holder.GetVariantSet(name).GetVariantNames():
                selections.append({(holder.GetPath(), name): variant})
    for chosen in selections:
        session.Clear()
        with Usd.EditContext(stage, session):
            for (holder, name), variant in chosen.items():
                stage.GetPrimAtPath(holder).GetVariantSet(name).SetVariantSelection(variant)
        label = ", ".join(f"{n}={v}" for (_, n), v in chosen.items()) or "default"
        for prim in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()):
            if not prim.IsDefined():
                problems.append(f"[{label}] {prim.GetPath()}: an opinion on a prim that does not exist")
                continue
            body, collider = prim.HasAPI(UsdPhysics.RigidBodyAPI), prim.HasAPI(UsdPhysics.CollisionAPI)
            schemas = _authored(prim)
            if body != ("PhysxRigidBodyAPI" in schemas):
                problems.append(
                    f"[{label}] {prim.GetPath()}: rigid body and PhysxRigidBodyAPI do not go together"
                )
            if (collider and prim.GetPath() != GROUND) != ("PhysxCollisionAPI" in schemas):
                problems.append(
                    f"[{label}] {prim.GetPath()}: collider and PhysxCollisionAPI do not go together"
                )
            if "PhysxCollisionAPI" in schemas:
                off = prim.GetAttribute("physxCollision:contactOffset").Get()
                rest = prim.GetAttribute("physxCollision:restOffset").Get()
                if off is None or rest is None or not off > rest >= 0:
                    problems.append(
                        f"[{label}] {prim.GetPath()}: contact offset must be above the rest offset"
                    )
    session.Clear()
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the PhysX layers (*_physx.usda) of packs or files.")
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    files = []
    for p in args.paths:
        files += sorted(p.rglob(f"*{SUFFIX}.usda")) if p.is_dir() else [p]
    if not files:
        print("no PhysX layer found")
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
