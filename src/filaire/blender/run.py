"""Simulate one OpenUSD scene with Blender's rigid bodies (Bullet), headless; runs inside Blender.

Modes:

* ``setup``: import with ``physics.import_with_physics`` (the UsdPhysics description rebuilt);
* ``naive``: what one does by hand: File > Import > USD, then every imported mesh an active rigid
  body with Blender's default settings, the ground passive.

Writes a JSON file: for every rigid-body mesh its first and last world matrix (setup: of the USD
body frame, the centre-of-mass offset taken back out), origin trajectory (every 0.1 s), lowest
vertex at the end, the USD body it stands for (setup) and its parent chain (naive).

usage (pip-installed bpy):  python -m filaire.blender.run scene.usda out.json setup 1.0
usage (Blender):            blender -b -P run.py -- scene.usda out.json setup 1.0
"""

import json
import os
import re
import sys

import bpy
from mathutils import Matrix, Vector

FPS = 120


def _blender_pxr():
    """With the bpy module from pip, put Blender's own OpenUSD bindings first: the importer's hooks
    hand over its stage, which only that build of pxr can read (Blender itself needs nothing)."""
    import glob

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(bpy.__file__))))
    for d in glob.glob(os.path.join(root, "python", "lib", "python3*", "site-packages")):
        if os.path.isdir(os.path.join(d, "pxr")) and d not in sys.path:
            sys.path.insert(0, d)
            for m in [m for m in sys.modules if m == "pxr" or m.startswith("pxr.")]:
                del sys.modules[m]


_blender_pxr()


def _base(name):
    return re.sub(r"\.\d{3}$", "", name)


def _chain(o):
    out = []
    while o is not None:
        out.append(_base(o.name))
        o = o.parent
    return out[::-1]


def simulate(scene_path, out, mode="setup", seconds=1.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    nframes = int(seconds * FPS)
    sc.frame_start, sc.frame_end = 1, nframes + 1
    if mode == "naive":
        bpy.ops.wm.usd_import(filepath=scene_path, import_guide=False)
        chains = {o.name: _chain(o) for o in sc.objects}
        bpy.ops.rigidbody.world_add()
        for o in list(sc.objects):
            if o.type != "MESH":
                continue
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                bpy.ops.rigidbody.object_add(type="PASSIVE" if _base(o.name) == "Ground" else "ACTIVE")
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from physics import import_with_physics

        chains = {}
        import_with_physics(scene_path)
    rw = sc.rigidbody_world
    rw.point_cache.frame_start, rw.point_cache.frame_end = 1, nframes + 1

    def bodies():
        return [
            o
            for o in sc.objects
            if o.type == "MESH"
            and o.rigid_body
            and o.rigid_body.type == "ACTIVE"
            and (mode == "naive" or "usd_rigid_body" in o)
        ]

    def frame(o):
        M = o.matrix_world.copy()
        if "usd_center_of_mass" in o:  # back to the USD body frame
            M = M @ Matrix.Translation(-Vector(o["usd_center_of_mass"]))
        return [list(r) for r in M]

    first, traj = {}, {}
    for f in range(1, nframes + 2):
        sc.frame_set(f)
        if f == 1:
            first = {o.name: frame(o) for o in bodies()}
        if f % 12 == 1:
            for o in bodies():
                traj.setdefault(o.name, []).append(list(o.matrix_world.translation))
    rows = {}
    for o in bodies():
        M = o.matrix_world
        low = min((M @ v.co).z for v in o.data.vertices) if len(o.data.vertices) else None
        rows[o.name] = dict(
            usd=o.get("usd_rigid_body"),
            chain=chains.get(o.name, [_base(o.name)]),
            first=first[o.name],
            last=frame(o),
            traj=traj.get(o.name, []),
            lowest=low,
        )
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(mode=mode, fps=FPS, seconds=seconds, bodies=rows), f)
    return rows


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    simulate(
        argv[0], argv[1], argv[2] if len(argv) > 2 else "setup", float(argv[3]) if len(argv) > 3 else 1.0
    )
