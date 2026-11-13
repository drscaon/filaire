"""Change one thing and nothing else: the aspects of Filaire.

What varies from one cable to the next is split into aspects (length, layout,
ends, color, stiffness, density), each with its own random stream. Turning one
aspect off leaves the draws of the others as they were. With the same seed you
get the same cables with a single difference, which is what you want when you
study what a robot is sensitive to.

Here: the same Ethernet cables twice, the second time with the stiffness
fixed at the middle of the preset's range. Layouts, ends and colours stay the
same, cable for cable.

    python examples/02_one_aspect_at_a_time.py
"""

from filaire import Variations, generate_scene

SEED = 4

varied = generate_scene("ethernet", count=5, seed=SEED)
fixed = generate_scene("ethernet", count=5, seed=SEED, variations=Variations(stiffness=False))

print(f"{'cable':13s} {'modulus (MPa)':>22s} {'E.I (N.m2)':>22s}  layout, colour")
print(f"{'':13s} {'varied':>10s} {'fixed':>11s} {'varied':>10s} {'fixed':>11s}")
for a, b in zip(varied.cables, fixed.cables, strict=True):
    print(
        f"{a.name:13s} {a.youngs_modulus / 1e6:10.1f} {b.youngs_modulus / 1e6:11.1f} "
        f"{a.bending_stiffness[0]:10.2e} {b.bending_stiffness[0]:11.2e}  {a.layout}, {a.color}"
    )

# The stiffness changed; the rest did not.
assert len({c.youngs_modulus for c in fixed.cables}) == 1
for name in ("layout", "color", "length", "linear_density"):
    assert [getattr(c, name) for c in varied.cables] == [getattr(c, name) for c in fixed.cables], name
print("\nsame seed, stiffness switched off: one modulus for all, same layouts, colours and masses")
