"""Prove that a cable bends as its numbers say: two checks in MuJoCo.

Both checks build a MuJoCo model from the OpenUSD file (segments, masses and
joint stiffness are read from it).

* Sag: a short length of the cable is held by one end, horizontally, and
  bends under its own weight. The deflection of its tip must match beam
  theory for the bending stiffness the file states. This proves the file is
  consistent with the model; it does not prove the model matches a real cable
  (see "Checking a preset against a real cable" in docs/physics.md).
* Drop: the whole cable, with its connectors, falls on the ground and must
  come to rest without passing through it.

Needs MuJoCo:  pip install "filaire[sim]"

    python examples/04_sag_and_drop_in_mujoco.py
"""

import sys
from pathlib import Path

from pxr import Usd

from filaire import generate_scene, write_outputs
from filaire.sim.checks import drop_check, sag_check
from filaire.sim.usd_reader import cable_paths, read_cable

out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"
folder = write_outputs(generate_scene("usb_c", count=1, length=0.5, layout="straight", seed=1), out)

# Read the first cable of the file as the simulator sees it.
stage = Usd.Stage.Open(str(next(Path(folder).glob("filaire_*.usdc"))))
cable = read_cable(stage, cable_paths(stage)[0])

sag = sag_check(cable)
held_cm, tip_mm, theory_mm = sag["sample_length_m"] * 100, sag["tip_deflection_mm"], sag["beam_theory_mm"]
print(f"sag:  {held_cm:.1f} cm held by one end, the tip goes down {tip_mm:.2f} mm")
print(
    f"      beam theory says {theory_mm:.2f} mm ({sag['error']:+.1%}): {'PASS' if sag['passed'] else 'FAIL'}"
)

drop = drop_check(cable, seconds=2.0)
speed, depth_mm = drop["max_speed_end"], drop["max_ground_penetration_mm"]
print(f"drop: {drop['links_simulated']} links, speed at the end {speed:.3f} m/s")
print(f"      deepest point {depth_mm:.3f} mm in the ground: {'PASS' if drop['passed'] else 'FAIL'}")

sys.exit(0 if sag["passed"] and drop["passed"] else 1)
