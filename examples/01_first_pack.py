"""Generate a first pack of cables and read its ground truth.

A pack is the folder Filaire writes for one preset: an OpenUSD file with the
cables (each one a chain of rigid segments with joints as stiff as the real
cable, and a connector on each end), a second file with the matching sockets,
and a table (instances.csv) with one row per asset. The table is read back
from the OpenUSD files, so they cannot disagree.

Run it:

    python examples/01_first_pack.py            # writes under output/examples/
    python examples/01_first_pack.py some/dir   # or under a folder of your choice
"""

import sys

from filaire import CONNECTORS, PRESETS, generate_scene, write_outputs
from filaire.pack import read_manifest, read_table

out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"

# Presets are kinds of cables (USB, Ethernet, power cords...); connectors are
# what goes on their ends.
print(f"{len(PRESETS)} presets, for example: {', '.join(list(PRESETS)[:5])}")
print(f"{len(CONNECTORS)} connectors, for example: {', '.join(list(CONNECTORS)[:5])}")

# Three USB-C cables. The seed fixes every random draw: the same call always
# gives the same cables.
scene = generate_scene("usb_c", count=3, seed=1)
folder = write_outputs(scene, out)
print(f"pack written to {folder}")

# manifest.json says what the pack is; its summary counts layouts and ends.
summary = read_manifest(folder)["summary"]
print(f"layouts: {summary['layouts']}, far ends: {summary['end_b']}")

# instances.csv is the ground truth of each asset: what was drawn for it
# (variation:*) and what was measured once generated (measured:*). The sockets
# are in the table too; they draw nothing, so only the cables are shown here.
cables = [row for row in read_table(folder) if row["variation:layout"]]
print(f"\n{'cable':10s} {'layout':>9s} {'far end':>13s} {'E (MPa)':>8s} {'E.I (N.m2)':>11s} {'mass':>7s}")
for row in cables:
    modulus_mpa = float(row["variation:youngs_modulus_pa"]) / 1e6
    stiffness = float(row["measured:bending_stiffness_y_nm2"])
    mass_g = float(row["measured:cable_mass_kg"]) * 1000
    layout, end_b = row["variation:layout"], row["variation:end_b"]
    print(f"{row['name']:10s} {layout:>9s} {end_b:>13s} {modulus_mpa:8.1f} {stiffness:11.2e} {mass_g:5.1f} g")
