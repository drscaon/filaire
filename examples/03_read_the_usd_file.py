"""Read what Filaire wrote, with OpenUSD alone.

You do not need Filaire to use a pack. Everything is in the OpenUSD file,
under the attribute namespace of the Primvaria contract:

    primvaria:generator, primvaria:preset, primvaria:seed   what made this asset
    primvaria:variation:<name>                              what was drawn for it
    primvaria:measured:<name>                               what was measured on it

This script generates a small pack, then opens it with pxr only, as a
simulator or a data pipeline would.

    python examples/03_read_the_usd_file.py
"""

import sys
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics

from filaire import generate_scene, write_outputs

out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"
folder = write_outputs(generate_scene("power_c13", count=2, length=1.0, seed=7), out)
usd_file = next(Path(folder).glob("filaire_*.usdc"))

# ---- from here on, no Filaire: only OpenUSD ----
stage = Usd.Stage.Open(str(usd_file))
units, up = UsdGeom.GetStageMetersPerUnit(stage), UsdGeom.GetStageUpAxis(stage)
print(f"{usd_file.name}: {units} m per unit, up axis {up}")

# An asset of the contract says which generator made it and which aspects varied.
cables = [p for p in stage.Traverse() if p.HasAttribute("primvaria:variation:aspects")]
aspects = cables[0].GetAttribute("primvaria:variation:aspects").Get()
made_by = cables[0].GetAttribute("primvaria:generator").Get()
print(f"{len(cables)} cables made by {made_by}, aspects that varied: {', '.join(aspects)}")

for prim in cables:
    length = prim.GetAttribute("primvaria:variation:length_m").Get()
    stiffness = prim.GetAttribute("primvaria:measured:bending_stiffness_y_nm2").Get()
    # The physics is standard UsdPhysics: rigid bodies linked by joints, which
    # any engine that reads OpenUSD finds.
    inside = list(Usd.PrimRange(prim))
    bodies = sum(1 for p in inside if p.HasAPI(UsdPhysics.RigidBodyAPI))
    joints = sum(1 for p in inside if p.IsA(UsdPhysics.Joint))
    print(f"  {prim.GetPath()}  {length:.2f} m, E.I {stiffness:.1e} N.m2, {bodies} bodies, {joints} joints")
