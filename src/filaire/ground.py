"""The ground and physics scene of every Primvaria project (this file is the same in each).

Every OpenUSD file with physics carries the same two prims, so that assets from different
generators can share one scene and every engine gets the same floor:

    /World/PhysicsScene     UsdPhysics.Scene, gravity 9.81 m/s² along -Z
    /World/Ground           UsdGeom.Cube: a static box, its top face at z = 0, 2 cm thick,
                            covering the content with 0.5 m to spare on each side (1 m × 1 m
                            at least), grey, rendered (purpose default), CollisionAPI, no
                            PhysX attributes (engines derive their contact offsets)
    /World/GroundMaterial   UsdShade.Material with UsdPhysics.MaterialAPI: static friction 0.6,
                            dynamic friction 0.5, restitution 0.1 (a wooden or concrete floor),
                            bound to the ground for the physics purpose

The stage itself is in metres, Z up, kilograms. ``read_ground`` gives the tests the ground as
the file has it.
"""

from __future__ import annotations

from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

GRAVITY = 9.81  # m/s², along -Z
GROUND_THICKNESS = 0.02  # m
GROUND_MARGIN = 0.5  # m of floor around the content, on each side
GROUND_STATIC_FRICTION = 0.6
GROUND_DYNAMIC_FRICTION = 0.5
GROUND_RESTITUTION = 0.1
GROUND_COLOR = (0.5, 0.5, 0.5)

SCENE_PATH = "/World/PhysicsScene"
GROUND_PATH = "/World/Ground"
GROUND_MATERIAL_PATH = "/World/GroundMaterial"


def physics_scene(stage) -> UsdPhysics.Scene:
    """/World/PhysicsScene with the gravity authored (9.81 m/s² along -Z)."""
    scene = UsdPhysics.Scene.Define(stage, SCENE_PATH)
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(GRAVITY)
    return scene


def ground(stage, lo=(0.0, 0.0), hi=(0.0, 0.0)) -> UsdGeom.Cube:
    """/World/Ground: a box whose top face is z = 0, covering the content's footprint (``lo`` and
    ``hi``, its x-y corners in metres) with GROUND_MARGIN to spare on each side, and its physics
    material /World/GroundMaterial."""
    x0, y0 = lo[0] - GROUND_MARGIN, lo[1] - GROUND_MARGIN
    x1, y1 = hi[0] + GROUND_MARGIN, hi[1] + GROUND_MARGIN
    g = UsdGeom.Cube.Define(stage, GROUND_PATH)
    g.CreateSizeAttr(1.0)
    g.AddTranslateOp().Set(Gf.Vec3d((x0 + x1) / 2, (y0 + y1) / 2, -GROUND_THICKNESS / 2))
    g.AddScaleOp().Set(Gf.Vec3f(x1 - x0, y1 - y0, GROUND_THICKNESS))
    g.CreateDisplayColorAttr([Gf.Vec3f(*GROUND_COLOR)])
    UsdPhysics.CollisionAPI.Apply(g.GetPrim())
    mat = UsdShade.Material.Define(stage, GROUND_MATERIAL_PATH)
    api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api.CreateStaticFrictionAttr(GROUND_STATIC_FRICTION)
    api.CreateDynamicFrictionAttr(GROUND_DYNAMIC_FRICTION)
    api.CreateRestitutionAttr(GROUND_RESTITUTION)
    UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mat, UsdShade.Tokens.weakerThanDescendants, "physics")
    return g


def read_ground(stage) -> dict:
    """The ground as a file has it: x-y corners ``lo`` and ``hi``, height of its top face
    ``top`` (m), and its physics material (``static_friction``, ``dynamic_friction``,
    ``restitution``); None without a ground."""
    prim = stage.GetPrimAtPath(GROUND_PATH)
    if not prim or not prim.IsValid():
        return None
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(prim)
    r = box.ComputeAlignedRange()
    out = dict(lo=(r.GetMin()[0], r.GetMin()[1]), hi=(r.GetMax()[0], r.GetMax()[1]), top=r.GetMax()[2])
    mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    api = UsdPhysics.MaterialAPI(mat.GetPrim()) if mat else None
    for key, attr, default in (
        ("static_friction", "GetStaticFrictionAttr", GROUND_STATIC_FRICTION),
        ("dynamic_friction", "GetDynamicFrictionAttr", GROUND_DYNAMIC_FRICTION),
        ("restitution", "GetRestitutionAttr", GROUND_RESTITUTION),
    ):
        v = getattr(api, attr)().Get() if api else None
        out[key] = float(v if v is not None else default)
    return out


def conformance(stage) -> list[str]:
    """How a stage departs from the shared ground and physics scene (empty: it conforms)."""
    problems = []
    if UsdGeom.GetStageMetersPerUnit(stage) != 1.0 or UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        problems.append("stage not in metres with Z up")
    if UsdPhysics.GetStageKilogramsPerUnit(stage) != 1.0:
        problems.append("stage not in kilograms")
    scene = stage.GetPrimAtPath(SCENE_PATH)
    if not scene or not scene.IsA(UsdPhysics.Scene):
        problems.append(f"no {SCENE_PATH}")
    else:
        s = UsdPhysics.Scene(scene)
        if s.GetGravityDirectionAttr().Get() != Gf.Vec3f(0, 0, -1):
            problems.append("gravity direction is not -Z")
        if abs((s.GetGravityMagnitudeAttr().Get() or 0.0) - GRAVITY) > 1e-6:
            problems.append(f"gravity magnitude is not {GRAVITY}")
    g = stage.GetPrimAtPath(GROUND_PATH)
    if not g or not g.IsA(UsdGeom.Cube) or not g.HasAPI(UsdPhysics.CollisionAPI):
        problems.append(f"no {GROUND_PATH} collision box")
        return problems
    info = read_ground(stage)
    if abs(info["top"]) > 1e-9:
        problems.append("the ground's top is not at z = 0")
    r = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(g)
    if abs(r.ComputeAlignedRange().GetSize()[2] - GROUND_THICKNESS) > 1e-9:
        problems.append(f"the ground is not {GROUND_THICKNESS} m thick")
    if min(info["hi"][0] - info["lo"][0], info["hi"][1] - info["lo"][1]) < 2 * GROUND_MARGIN - 1e-9:
        problems.append("the ground is smaller than 1 m × 1 m")
    if UsdGeom.Imageable(g).ComputePurpose() != UsdGeom.Tokens.default_:
        problems.append("the ground is not rendered (purpose)")
    if any(s.startswith("Physx") for s in g.GetAppliedSchemas()):
        problems.append("the ground has PhysX attributes")
    expected = (GROUND_STATIC_FRICTION, GROUND_DYNAMIC_FRICTION, GROUND_RESTITUTION)
    got = (info["static_friction"], info["dynamic_friction"], info["restitution"])
    mat, _ = UsdShade.MaterialBindingAPI(g).ComputeBoundMaterial("physics")
    if not mat or str(mat.GetPath()) != GROUND_MATERIAL_PATH:
        problems.append(f"the ground's physics material is not {GROUND_MATERIAL_PATH}")
    elif any(abs(a - b) > 1e-6 for a, b in zip(got, expected, strict=True)):
        problems.append(f"the ground's material is {got}, not {expected}")
    return problems
