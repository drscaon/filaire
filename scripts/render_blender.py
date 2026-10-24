"""Render the README images with Blender (Cycles, CPU) from Filaire's OpenUSD output.

Development tool, not part of the package. Needs the `bpy` module
(`pip install bpy`, Python 3.13) or Blender's own Python:

    python scripts/render_blender.py hero out.jpg W H camx camy camz tx ty tz lens \
        usd1 dx dy dz rotz  usd2 dx dy dz rotz ...
    python scripts/render_blender.py anim job.json      # frames of an animation (drop_gif.py)

Each USD file is imported (selected variants only, no collision guides),
turned by rotz degrees about z, then moved by (dx, dy, dz) metres.
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector


def reset(resolution=(1600, 900), samples=64):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = resolution
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.92, 0.93, 0.95, 1)
    bg.inputs[1].default_value = 0.25


def import_usd(path: str, dx=0.0, dy=0.0, dz=0.0, rotz=0.0, merge: bool = True) -> list:
    before = set(bpy.data.objects)
    bpy.ops.wm.usd_import(
        filepath=path, import_guide=False, import_proxy=False, import_render=True, merge_parent_xform=merge
    )
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.name.startswith("Ground") or o.name.startswith("PhysicsScene"):
            o.hide_render = True
            o.hide_viewport = True
    roots = [o for o in new if o.parent is None]
    pivot = bpy.data.objects.new("pivot", None)
    bpy.context.scene.collection.objects.link(pivot)
    for o in roots:
        o.parent = pivot
    pivot.location = (dx, dy, dz)
    pivot.rotation_euler = (0, 0, math.radians(rotz))
    return new


def floor(size=200.0, color=(0.36, 0.37, 0.39, 1)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    p = bpy.context.object
    mat = bpy.data.materials.new("floor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.85
    p.data.materials.append(mat)


def lights(target=(0, 0, 0), scale=1.0):
    t = Vector(target)
    for loc, energy, size in (((-2, -2.5, 3.5), 420, 3.0), ((3, -1, 2.5), 140, 2.0), ((0, 3, 3), 160, 3.0)):
        bpy.ops.object.light_add(type="AREA", location=t + Vector(loc) * scale)
        lamp = bpy.context.object
        lamp.data.energy = energy * scale * scale
        lamp.data.size = size * scale
        d = t - lamp.location
        lamp.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(location, target, lens=50.0):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.data.lens = lens
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def render(out: str):
    settings = bpy.context.scene.render.image_settings
    if out.lower().endswith((".jpg", ".jpeg")):
        settings.file_format = "JPEG"
        settings.quality = 90
    else:
        settings.file_format = "PNG"
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)


def _strip(name: str) -> str:
    """'seg_012.003' -> 'seg_012' (Blender's suffix for duplicate names)."""
    head, _, tail = name.rpartition(".")
    return head if head and tail.isdigit() else name


def _find(obj, path: list[str]):
    """Follow a USD path below obj; a missing level (a Scope not imported as an empty) is skipped."""
    for part in path:
        child = next((c for c in obj.children if _strip(c.name) == part), None)
        if child is None and part != path[-1]:
            continue
        if child is None:
            return None
        obj = child
    return obj


def add_obstacle(ob: dict, color=(0.32, 0.22, 0.14, 1)):
    """A static box or cylinder, with MuJoCo's size convention (half sizes; radius, half length)."""
    from math import radians

    if ob["type"] == "box":
        bpy.ops.mesh.primitive_cube_add(size=2, location=ob["pos"])
        bpy.context.object.scale = ob["size"]
    else:
        r, half = ob["size"][:2]
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=2 * half, location=ob["pos"])
        bpy.ops.object.shade_smooth()
    o = bpy.context.object
    o.rotation_euler = [radians(a) for a in ob.get("euler", [0, 0, 0])]
    mat = bpy.data.materials.new("obstacle")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.6
    o.data.materials.append(mat)


def animate(job_path: str):
    """Render the frames of an animation: one pose of every listed object per frame."""
    import json

    from mathutils import Matrix

    job = json.loads(open(job_path, encoding="utf-8").read())
    w, h = job["size"]
    reset((w, h), job["samples"])
    floor()
    objects = {}
    for k, cable in enumerate(job["cables"]):
        new = import_usd(cable["usd"], merge=False)  # keep one object per USD Xform, to move it
        root = next(o for o in new if _strip(o.name) == cable["name"])
        for key in job["tracks"]:
            idx, *path = key.split("/")
            if int(idx) == k:
                obj = _find(root, path)
                if obj is not None:
                    objects[key] = obj
    for ob in job.get("obstacles", []):
        add_obstacle(ob)
    cam = job["camera"]
    lights(cam[3:6], 1.0)
    camera(cam[:3], cam[3:6], job["lens"])
    os.makedirs(job["out_dir"], exist_ok=True)
    for f in range(job["frames"]):
        for key, obj in objects.items():
            obj.matrix_world = Matrix(job["tracks"][key][f])
        bpy.context.view_layer.update()
        render(os.path.join(job["out_dir"], f"frame_{f:04d}.png"))


def main(argv):
    mode = argv[0]
    if mode == "anim":
        animate(argv[1])
        return
    out = argv[1]
    if mode == "hero":
        res = (int(argv[2]), int(argv[3]))
        cam = [float(v) for v in argv[4:10]]
        lens = float(argv[10])
        rest = argv[11:]
        reset(res, int(os.environ.get("SAMPLES", "96")))
        floor()
        for i in range(0, len(rest), 5):
            import_usd(rest[i], *(float(v) for v in rest[i + 1 : i + 5]))
        lights(cam[3:6], 1.0)
        camera(cam[:3], cam[3:6], lens)
        render(out)
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    main(args)
