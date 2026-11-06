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

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "filaire", "blender")
)
from physics import flat_where_flat  # noqa: E402  (the add-on module, importable without the package)


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
    flat_where_flat([o.data for o in new if o.type == "MESH"])
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


# a warm, light-wood desk: black, grey, white and coloured cables all stand out on it
FLOOR_DARK, FLOOR_LIGHT = (0.16, 0.165, 0.17, 1), (0.27, 0.272, 0.275, 1)  # factory concrete


def floor(size=200.0, color=None, markings=False):
    """Factory floor: sealed grey concrete with a faint large-scale variation, fine speckle and a
    little gloss. markings: saw-cut joints every 2 m and a yellow lane line (wide shots only).
    FLOOR=r,g,b in the environment (or color) gives a plain floor instead."""
    if color is None and "FLOOR" in os.environ:
        color = tuple(float(v) for v in os.environ["FLOOR"].split(",")) + (1,)
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    p = bpy.context.object
    mat = bpy.data.materials.new("floor")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if color is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.85
        p.data.materials.append(mat)
        return
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def noise(scale, detail):
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        L(tc.outputs["Object"], n.inputs["Vector"])
        return n

    def math(op, *args):
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate(args):
            if isinstance(v, float | int):
                m.inputs[i].default_value = v
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    coarse, fine = noise(0.6, 3.0), noise(400.0, 2.0)
    # concrete value: mostly the speckle, a faint large-scale cloud (strong, it reads as fog)
    v = math("MULTIPLY_ADD", fine.outputs["Fac"], 0.6, math("MULTIPLY", coarse.outputs["Fac"], 0.4))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = FLOOR_DARK
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = FLOOR_LIGHT
    L(v, ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    rough = math("MULTIPLY_ADD", coarse.outputs["Fac"], 0.3, 0.3)
    if markings:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        L(tc.outputs["Object"], sep.inputs[0])

        def joint(axis):  # 1 on a 6 mm saw cut every 2 m
            d = math("PINGPONG", math("ADD", axis, 1.0), 1.0)  # distance to the nearest multiple of 2
            return math("LESS_THAN", d, 0.003)

        cut = math("MAXIMUM", joint(sep.outputs["X"]), joint(sep.outputs["Y"]))
        lane = math("LESS_THAN", math("ABSOLUTE", math("ADD", sep.outputs["Y"], 1.1), 0.0), 0.05)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        L(lane, mix.inputs["Factor"])
        L(col, mix.inputs[6])
        mix.inputs[7].default_value = (0.75, 0.52, 0.03, 1)  # safety yellow
        dark = nt.nodes.new("ShaderNodeMix")
        dark.data_type = "RGBA"
        L(cut, dark.inputs["Factor"])
        L(mix.outputs[2], dark.inputs[6])
        dark.inputs[7].default_value = (0.04, 0.04, 0.045, 1)
        col = dark.outputs[2]
    L(col, bsdf.inputs["Base Color"])
    L(rough, bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.03
    L(fine.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
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
    cam.data.clip_start = 0.001  # close-ups of connectors: the default 0.1 m would cut them
    cam.data.clip_end = 100.0
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def clear_plastic():
    """Blender reads UsdPreviewSurface opacity as alpha; render Filaire's clear plastic (RJ45 and
    RJ9 plugs, opacity < 1 with an ior) as transmission instead, like a path tracer would."""
    for m in bpy.data.materials:
        if "_clear" in m.name and m.node_tree:
            for n in m.node_tree.nodes:
                if n.bl_idname == "ShaderNodeBsdfPrincipled":
                    n.inputs["Alpha"].default_value = 1.0
                    n.inputs["Transmission Weight"].default_value = 0.95
                    n.inputs["Roughness"].default_value = 0.08


def render(out: str):
    clear_plastic()
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


def add_obstacle(ob: dict):
    """A static box or cylinder, with MuJoCo's size convention (half sizes; radius, half length):
    painted steel by default; an optional "color" (RGBA) and "metallic" (0-1) override it."""
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
    bsdf.inputs["Base Color"].default_value = tuple(ob.get("color", (0.55, 0.56, 0.58, 1)))
    bsdf.inputs["Metallic"].default_value = float(ob.get("metallic", 1.0))
    bsdf.inputs["Roughness"].default_value = float(ob.get("roughness", 0.35))
    o.data.materials.append(mat)


def animate(job_path: str):
    """Render the frames of an animation: one pose of every listed object per frame."""
    import json

    from mathutils import Matrix

    job = json.loads(open(job_path, encoding="utf-8").read())
    w, h = job["size"]
    reset((w, h), job["samples"])
    floor(markings=job.get("floor_markings", False))
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
    movers = []  # obstacles with a pose per frame (a gripper): their mesh has no scale, so a
    for mv in job.get("movers", []):  # world matrix places them
        add_obstacle(mv["ob"])
        movers.append((bpy.context.object, mv["track"]))
    cam = job["camera"]
    lights(cam[3:6], 1.0)
    camera(cam[:3], cam[3:6], job["lens"])
    os.makedirs(job["out_dir"], exist_ok=True)
    for f in range(job["frames"]):
        for key, obj in objects.items():
            obj.matrix_world = Matrix(job["tracks"][key][f])
        for obj, track in movers:
            obj.matrix_world = Matrix(track[f])
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
