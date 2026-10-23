"""Render the README images with Blender (Cycles, CPU) from Filaire's OpenUSD output.

Development tool, not part of the package. Needs the `bpy` module
(`pip install bpy`, Python 3.13) or Blender's own Python:

    python scripts/render_blender.py hero out.jpg W H camx camy camz tx ty tz lens \
        usd1 dx dy dz rotz  usd2 dx dy dz rotz ...

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


def import_usd(path: str, dx=0.0, dy=0.0, dz=0.0, rotz=0.0) -> list:
    before = set(bpy.data.objects)
    bpy.ops.wm.usd_import(filepath=path, import_guide=False, import_proxy=False, import_render=True)
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


def floor(size=20.0, color=(0.36, 0.37, 0.39, 1)):
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


def main(argv):
    mode, out = argv[0], argv[1]
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
