"""OpenUSD export.

Cable stage (Z up, metres, kilograms), `/World` the default prim:

    /World
      /PhysicsScene                   gravity
      /Looks/<colour>                 UsdPreviewSurface materials
      /PhysicsMaterials/<name>        UsdPhysics materials (friction, restitution)
      /Cables/<cable>                 Xform, PhysicsArticulationRootAPI, filaire:* attributes,
                                      variant sets "end_a" and "end_b"
        /Segments/seg_000 …           rigid bodies (RigidBodyAPI, MassAPI, PhysxRigidBodyAPI)
          /Visual                     ONE mesh: the piece of tube this segment carries
          /Collision                  Capsule along x (round cables) or Cube (flat, figure-8), guide
        /Joints/joint_000 …           PhysicsJoint between neighbouring segments: translations
                                      locked, rotX/rotY/rotZ drives (twist, bending)
        /End_A, /End_B                filled by the selected variant:
          /Body                       rigid body of the connector or stripped end
            /Visual                   ONE mesh, a GeomSubset per material (shell, body, cores…)
            /Collision/hull_00 …      convex parts (MeshCollisionAPI convexHull, purpose guide)
            /MateFrame                origin on the mating plane, +Z = insertion direction
          /Attach                     PhysicsFixedJoint to the end segment
      /Ground                         collision box, its top face at z = 0

One visual mesh per rigid body, as in Quincaillerie: every DCC imports one
object per body, so a rigid body set on it (by hand, or by the Blender add-on)
moves the whole part. Every body carries `PhysxRigidBodyAPI` and every
collider `PhysxCollisionAPI` (contact and rest offsets), read by Isaac Sim
and ignored by other engines.

Angular drives use UsdPhysics units: stiffness per degree, damping per
degree per second. The same values in SI units (per radian) and the rod's
stiffness (E·I, G·J) are kept as `filaire:*` attributes, engine-neutral.

Without physics (`physics=False`, `--no-physics`), the same layout carries
visuals only: each cable is one mesh (`/World/Cables/<cable>/Visual`), each
end a Body Xform with its Visual and MateFrame, and there are no rigid
bodies, colliders, joints, physics materials, physics scene or ground.

Socket stage (`sockets.usdc`): one fixed receptacle block per connector
family under /World/Sockets, static colliders standing on the ground with the
insertion axis horizontal, each with its MateFrame.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt
from scipy.spatial import ConvexHull

from . import __version__
from .cable import DAMPING_TIME, Cable, End, cable_color_rgb
from .catalog import CONNECTOR_FRICTION, JACKETS, PRESETS
from .connectors import CONNECTORS, MM, keying_of, part_mesh, receptacle_parts
from .mesh3d import TriMesh, mass_properties, merge, principal_inertia, split_normals, weld

_F = Sdf.ValueTypeNames
DEG = math.pi / 180
CONTACT_OFFSET = 0.0005  # m, PhysX contact offset of every collider (a tenth is Blender's margin)
CREASE = 35.0  # degrees: sharper edges between faces keep their own normals


def _attr(prim, name, type_name, value):
    prim.CreateAttribute(name, type_name, custom=True).Set(value)


def _srgb_to_linear(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _quat(R: np.ndarray) -> Gf.Quatf:
    m = Gf.Matrix3d(*np.asarray(R, float).T.flatten().tolist())  # Gf is row-vector: rows = axes
    q = m.ExtractRotation().GetQuat()
    return Gf.Quatf(q)


def _xform(prim_xf: UsdGeom.Xformable, R: np.ndarray, t) -> None:
    prim_xf.AddTranslateOp().Set(Gf.Vec3d(*map(float, t)))
    prim_xf.AddOrientOp().Set(_quat(R))


class _Looks:
    def __init__(self, stage):
        self.stage = stage
        self.cache: dict = {}
        UsdGeom.Scope.Define(stage, "/World/Looks")

    def get(self, color: str, roughness: float = 0.5, metallic: float = 0.0) -> UsdShade.Material:
        key = (color, round(roughness, 2), round(metallic, 2))
        if key in self.cache:
            return self.cache[key]
        name = f"m_{color.lstrip('#')}_{int(roughness * 100)}_{int(metallic * 100)}"
        path = f"/World/Looks/{name}"
        mat = UsdShade.Material.Define(self.stage, path)
        sh = UsdShade.Shader.Define(self.stage, f"{path}/Surface")
        sh.CreateIdAttr("UsdPreviewSurface")
        rgb = _srgb_to_linear(cable_color_rgb(color))
        sh.CreateInput("diffuseColor", _F.Color3f).Set(Gf.Vec3f(*map(float, rgb)))
        sh.CreateInput("roughness", _F.Float).Set(float(roughness))
        sh.CreateInput("metallic", _F.Float).Set(float(metallic))
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        self.cache[key] = mat
        return mat


def _physics_material(stage, name: str, friction: float, restitution: float) -> UsdShade.Material:
    path = f"/World/PhysicsMaterials/{name}"
    mat = UsdShade.Material.Define(stage, path)
    api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api.CreateStaticFrictionAttr(float(friction))
    api.CreateDynamicFrictionAttr(float(friction))
    api.CreateRestitutionAttr(float(restitution))
    return mat


def _bind(prim, material, physics: bool = False) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim)
    api = UsdShade.MaterialBindingAPI(prim)
    if physics:
        api.Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")
    else:
        api.Bind(material)


def _geometry(m: UsdGeom.Mesh, mesh: TriMesh, normals: bool) -> None:
    pts = mesh.points.astype(np.float32)
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(pts))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(mesh.faces), 3, np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(mesh.faces.astype(np.int32).ravel()))
    m.CreateExtentAttr([Gf.Vec3f(*map(float, pts.min(0))), Gf.Vec3f(*map(float, pts.max(0)))])
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    if normals:
        n = split_normals(mesh.points, mesh.faces, CREASE).astype(np.float32)
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(n))
        m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)


def _linear(color: str) -> Gf.Vec3f:
    return Gf.Vec3f(*map(float, _srgb_to_linear(cable_color_rgb(color))))


def _mesh(stage, path: str, mesh: TriMesh, color: str | None = None, normals: bool = False) -> UsdGeom.Mesh:
    m = UsdGeom.Mesh.Define(stage, path)
    _geometry(m, weld(mesh) if normals else mesh, normals)
    if color:
        m.CreateDisplayColorAttr([_linear(color)])
    return m


def _visual(stage, looks, path: str, parts: list) -> UsdGeom.Mesh:
    """ONE mesh for all the visual parts of a body: [(TriMesh, colour, roughness, metallic), …].

    Each material gets a GeomSubset (family materialBind, partition) bound to its material, and
    displayColor is set per face, so viewers without materials show the colours too.
    """
    meshes = [weld(t[0]) for t in parts]
    mesh = merge(meshes)
    m = UsdGeom.Mesh.Define(stage, path)
    _geometry(m, mesh, normals=False)
    normals = np.vstack([split_normals(x.points, x.faces, CREASE) for x in meshes if len(x.faces)])
    m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals.astype(np.float32)))
    m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    keys = []
    for x, (_t, color, rough, metal) in zip(meshes, parts, strict=True):
        keys += [(color, round(rough, 2), round(metal, 2))] * len(x.faces)
    pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("displayColor", _F.Color3fArray, UsdGeom.Tokens.uniform)
    pv.Set([_linear(k[0]) for k in keys])
    distinct = list(dict.fromkeys(keys))
    bapi = UsdShade.MaterialBindingAPI.Apply(m.GetPrim())
    if len(distinct) == 1:
        bapi.Bind(looks.get(*distinct[0]))
        return m
    idx = np.array([distinct.index(k) for k in keys])
    for i, (color, rough, metal) in enumerate(distinct):
        faces = np.nonzero(idx == i)[0]
        name = f"m_{color.lstrip('#')}_{int(rough * 100)}_{int(metal * 100)}"
        sub = bapi.CreateMaterialBindSubset(name, Vt.IntArray(faces.tolist()), UsdGeom.Tokens.face)
        UsdShade.MaterialBindingAPI.Apply(sub.GetPrim()).Bind(looks.get(color, rough, metal))
    bapi.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)
    return m


def _physx_body(prim, position_iterations: int = 32) -> None:
    """PhysxRigidBodyAPI (read by Isaac Sim, ignored elsewhere): solver iterations for light links."""
    prim.AddAppliedSchema("PhysxRigidBodyAPI")
    prim.CreateAttribute("physxRigidBody:solverPositionIterationCount", _F.Int).Set(position_iterations)
    prim.CreateAttribute("physxRigidBody:solverVelocityIterationCount", _F.Int).Set(4)
    prim.CreateAttribute("physxRigidBody:maxDepenetrationVelocity", _F.Float).Set(1.0)
    prim.CreateAttribute("physxRigidBody:enableCCD", _F.Bool).Set(False)


def _physx_collision(prim, offset: float = CONTACT_OFFSET) -> None:
    """PhysxCollisionAPI contact and rest offsets (Isaac Sim; the Blender add-on reads its margin)."""
    prim.AddAppliedSchema("PhysxCollisionAPI")
    prim.CreateAttribute("physxCollision:contactOffset", _F.Float).Set(float(offset))
    prim.CreateAttribute("physxCollision:restOffset", _F.Float).Set(0.0)


def _collider(prim, physics_mat) -> None:
    UsdPhysics.CollisionAPI.Apply(prim)
    _physx_collision(prim)
    _bind(prim, physics_mat, physics=True)


def _hull_mesh(points: np.ndarray) -> TriMesh:
    h = ConvexHull(points)
    faces = h.simplices.copy()
    # orient outwards
    c = points[h.vertices].mean(0)
    for f in faces:
        a, b, d = points[f]
        if np.dot(np.cross(b - a, d - a), a - c) < 0:
            f[1], f[2] = f[2], f[1]
    return TriMesh(points, faces)


def _collision_hulls(stage, path: str, hulls: list, physics_mat) -> None:
    UsdGeom.Scope.Define(stage, path)
    for k, pts in enumerate(hulls):
        m = _mesh(stage, f"{path}/hull_{k:02d}", _hull_mesh(np.asarray(pts, float)))
        m.CreatePurposeAttr(UsdGeom.Tokens.guide)
        _collider(m.GetPrim(), physics_mat)
        UsdPhysics.MeshCollisionAPI.Apply(m.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)


def _mass(prim, mass: float, com, inertia: np.ndarray) -> None:
    api = UsdPhysics.MassAPI.Apply(prim)
    api.CreateMassAttr(float(mass))
    api.CreateCenterOfMassAttr(Gf.Vec3f(*map(float, com)))
    moments, axes = principal_inertia(inertia)
    api.CreateDiagonalInertiaAttr(Gf.Vec3f(*map(float, moments)))
    api.CreatePrincipalAxesAttr(_quat(axes))


def _mate_frame(stage, path: str, spec_key: str, role: str, mount: str) -> None:
    spec = CONNECTORS[spec_key]
    mf = UsdGeom.Xform.Define(stage, path)
    p = mf.GetPrim()
    _attr(p, "filaire:connector", _F.String, spec.key)
    _attr(p, "filaire:connectorLabel", _F.String, spec.label)
    _attr(p, "filaire:role", _F.Token, role)  # plug | receptacle
    _attr(p, "filaire:mount", _F.Token, mount)  # cable | panel
    _attr(p, "filaire:contactGender", _F.Token, spec.gender if role == "plug" else _other(spec.gender))
    _attr(p, "filaire:insertionDepth", _F.Float, float(spec.depth * MM))
    _attr(p, "filaire:clearance", _F.Float, float(spec.clearance * MM))
    _attr(p, "filaire:keying", _F.Token, spec.keying)
    _attr(p, "filaire:standard", _F.String, spec.standard)
    name = spec.plug_name if role == "plug" else (spec.inline_name if mount == "cable" else spec.panel_name)
    _attr(p, "filaire:name", _F.String, name)


def _other(gender: str) -> str:
    return {"male": "female", "female": "male"}.get(gender, gender)


def _end_parts(end: End) -> list:
    parts = []
    for mesh, color, kind in end.visuals:
        metal = kind == "mating" and end.role == "plug" and CONNECTORS[end.connector].shell == color
        metal = metal or kind == "copper"
        parts.append((mesh, color, 0.3 if metal else 0.45, 0.9 if metal else 0.0))
    return parts


def _end_variant(
    stage, looks, cable_path: str, side: str, end: End, last_seg, seg_path: str, mats, physics: bool = True
) -> None:
    base = f"{cable_path}/End_{side.upper()}"
    UsdGeom.Xform.Define(stage, base)
    _attr(stage.GetPrimAtPath(base), "filaire:end", _F.String, end.variant)
    if end.role == "cut":
        return
    body = UsdGeom.Xform.Define(stage, f"{base}/Body")
    _xform(body, end.rotation, end.origin)
    bp = body.GetPrim()
    _visual(stage, looks, f"{base}/Body/Visual", _end_parts(end))
    if end.connector:
        role = "plug" if end.role == "plug" else "receptacle"
        _mate_frame(stage, f"{base}/Body/MateFrame", end.connector, role, "cable")
    if not physics:
        return
    UsdPhysics.RigidBodyAPI.Apply(bp)
    _physx_body(bp)
    _mass(bp, end.mass, end.com, end.inertia)
    _collision_hulls(stage, f"{base}/Body/Collision", end.hulls, mats["connector"])
    j = UsdPhysics.FixedJoint.Define(stage, f"{base}/Attach")
    j.CreateBody0Rel().SetTargets([Sdf.Path(seg_path)])
    j.CreateBody1Rel().SetTargets([bp.GetPath()])
    Rs, cs = last_seg.rotation, last_seg.center
    j.CreateLocalPos0Attr(Gf.Vec3f(*map(float, Rs.T @ (end.origin - cs))))
    j.CreateLocalRot0Attr(_quat(Rs.T @ end.rotation))
    j.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
    j.CreateLocalRot1Attr(Gf.Quatf(1, 0, 0, 0))


def _segment(stage, looks, path: str, cable: Cable, seg, mats) -> None:
    x = UsdGeom.Xform.Define(stage, path)
    _xform(x, seg.rotation, seg.center)
    p = x.GetPrim()
    if len(seg.visual.faces):
        _visual(
            stage,
            looks,
            f"{path}/Visual",
            [(seg.visual, cable.color, JACKETS[cable.jacket]["roughness"], 0.0)],
        )
    UsdPhysics.RigidBodyAPI.Apply(p)
    _physx_body(p)
    L = seg.length
    m = cable.linear_density * cable.segment_length  # the arc it stands for: total mass kept
    if cable.coil:
        r2 = (cable.coil["diameter"] / 2) ** 2
        inertia = np.diag([m * r2, m * (r2 / 2 + L * L / 12), m * (r2 / 2 + L * L / 12)])
    else:
        sec = cable.section
        A = sec["area"]
        inertia = np.diag(
            [
                m * (sec["Iy"] + sec["Iz"]) / A,
                m * (sec["Iy"] / A + L * L / 12),
                m * (sec["Iz"] / A + L * L / 12),
            ]
        )
    _mass(p, m, (0, 0, 0), inertia)
    if cable.coil or cable.profile[0] == "round":
        r = (cable.coil["diameter"] + cable.coil["wire"]) / 2 if cable.coil else cable.section["width"] / 2
        col = UsdGeom.Capsule.Define(stage, f"{path}/Collision")
        col.CreateAxisAttr(UsdGeom.Tokens.x)
        col.CreateRadiusAttr(float(r))
        col.CreateHeightAttr(float(L))
    else:
        col = UsdGeom.Cube.Define(stage, f"{path}/Collision")
        col.CreateSizeAttr(1.0)
        col.AddScaleOp().Set(
            Gf.Vec3f(float(L), float(cable.section["width"]), float(cable.section["height"]))
        )
    col.CreatePurposeAttr(UsdGeom.Tokens.guide)
    _collider(col.GetPrim(), mats["jacket"])


def _joint(stage, path: str, s0: str, s1: str, L0: float, L1: float, cable: Cable) -> None:
    j = UsdPhysics.Joint.Define(stage, path)
    j.CreateBody0Rel().SetTargets([Sdf.Path(s0)])
    j.CreateBody1Rel().SetTargets([Sdf.Path(s1)])
    j.CreateLocalPos0Attr(Gf.Vec3f(float(L0 / 2), 0, 0))
    j.CreateLocalPos1Attr(Gf.Vec3f(float(-L1 / 2), 0, 0))
    j.CreateLocalRot0Attr(Gf.Quatf(1, 0, 0, 0))
    j.CreateLocalRot1Attr(Gf.Quatf(1, 0, 0, 0))
    p = j.GetPrim()
    k = cable.joint_stiffness
    free_axial = "axial" in k
    for dof in ("transX", "transY", "transZ"):
        if dof == "transX" and free_axial:
            continue
        lim = UsdPhysics.LimitAPI.Apply(p, dof)
        lim.CreateLowAttr(1.0)  # low > high: locked
        lim.CreateHighAttr(-1.0)
    for dof, key in (("rotX", "twist"), ("rotY", "bend_y"), ("rotZ", "bend_z")):
        d = UsdPhysics.DriveAPI.Apply(p, dof)
        d.CreateTypeAttr("force")
        d.CreateTargetPositionAttr(0.0)
        d.CreateTargetVelocityAttr(0.0)
        d.CreateStiffnessAttr(float(k[key] * DEG))
        d.CreateDampingAttr(float(k[key] * DAMPING_TIME * DEG))
    if free_axial:
        d = UsdPhysics.DriveAPI.Apply(p, "transX")
        d.CreateTypeAttr("force")
        d.CreateTargetPositionAttr(0.0)
        d.CreateStiffnessAttr(float(k["axial"]))
        d.CreateDampingAttr(float(k["axial"] * DAMPING_TIME))


def _cable_attrs(prim, c: Cable) -> None:
    k = c.joint_stiffness
    _attr(prim, "filaire:preset", _F.String, c.preset_key)
    _attr(prim, "filaire:layout", _F.Token, c.layout)
    _attr(prim, "filaire:length", _F.Float, float(c.length))
    _attr(prim, "filaire:nominalLength", _F.Float, float(c.nominal_length))
    _attr(prim, "filaire:profile", _F.String, " ".join(str(v) for v in c.profile))
    _attr(prim, "filaire:width", _F.Float, float(c.section["width"]))
    _attr(prim, "filaire:height", _F.Float, float(c.section["height"]))
    _attr(prim, "filaire:jacket", _F.String, c.jacket)
    _attr(prim, "filaire:color", _F.String, c.color)
    _attr(prim, "filaire:youngsModulus", _F.Float, float(c.youngs_modulus))
    _attr(prim, "filaire:shearModulus", _F.Float, float(c.shear_modulus))
    _attr(prim, "filaire:linearDensity", _F.Float, float(c.linear_density))
    _attr(prim, "filaire:bendingStiffness", _F.Float2, Gf.Vec2f(*map(float, c.bending_stiffness)))
    _attr(prim, "filaire:torsionalStiffness", _F.Float, float(c.torsional_stiffness))
    _attr(prim, "filaire:segmentLength", _F.Float, float(c.segment_length))
    _attr(prim, "filaire:segmentCount", _F.Int, len(c.segments))
    _attr(prim, "filaire:jointStiffness", _F.Float3, Gf.Vec3f(k["twist"], k["bend_y"], k["bend_z"]))
    _attr(prim, "filaire:dampingTime", _F.Float, float(DAMPING_TIME))
    _attr(prim, "filaire:restShape", _F.Token, "straight")
    _attr(prim, "filaire:friction", _F.Float, float(JACKETS[c.jacket]["friction"]))
    if c.coil:
        _attr(prim, "filaire:axialStiffness", _F.Float, float(c.axial_stiffness))
        _attr(prim, "filaire:jointAxialStiffness", _F.Float, float(k["axial"]))
        _attr(prim, "filaire:coil:diameter", _F.Float, float(c.coil["diameter"]))
        _attr(prim, "filaire:coil:pitch", _F.Float, float(c.coil["pitch"]))
        _attr(prim, "filaire:coil:turns", _F.Float, float(c.coil["turns"]))
        _attr(prim, "filaire:coil:wireLength", _F.Float, float(c.coil["wire_length"]))
        _attr(prim, "filaire:coil:wireDiameter", _F.Float, float(c.coil["wire"]))


def _ground(stage, size: float, lo=(0.0, 0.0), hi=(0.0, 0.0), thickness: float = 0.02) -> None:
    """A collision box whose top face is the floor, z = 0 (a box rather than a plane: every engine
    and Blender's Bullet collide robustly with it)."""
    x0, y0, x1, y1 = lo[0] - size, lo[1] - size, hi[0] + size, hi[1] + size
    g = UsdGeom.Cube.Define(stage, "/World/Ground")
    g.CreateSizeAttr(1.0)
    g.AddTranslateOp().Set(Gf.Vec3d((x0 + x1) / 2, (y0 + y1) / 2, -thickness / 2))
    g.AddScaleOp().Set(Gf.Vec3f(x1 - x0, y1 - y0, thickness))
    g.CreateDisplayColorAttr([Gf.Vec3f(0.5, 0.5, 0.5)])
    UsdPhysics.CollisionAPI.Apply(g.GetPrim())
    _physx_collision(g.GetPrim())


def _new_stage(path: Path, physics: bool = True):
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.Find(str(path.resolve()))
    if layer is not None:  # still open in this process (a previous export): start from an empty layer
        layer.Clear()
        stage = Usd.Stage.Open(layer)
    else:
        stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetCustomDataByKey("filaire:version", __version__)
    world.GetPrim().SetCustomDataByKey("filaire:physics", bool(physics))
    if physics:
        scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
        scene.CreateGravityMagnitudeAttr(9.81)
    return stage, world


def _cable_visual(stage, looks, cp: str, c: Cable) -> None:
    """Visual-only cable: every segment's piece of tube in one mesh, in the cable's frame."""
    pieces = [s.visual.transformed(s.rotation, s.center) for s in c.segments if len(s.visual.faces)]
    _visual(stage, looks, f"{cp}/Visual", [(merge(pieces), c.color, JACKETS[c.jacket]["roughness"], 0.0)])


def export_cables(path: str | Path, scene, physics: bool = True) -> Path:
    path = Path(path)
    stage, world = _new_stage(path, physics)
    world.GetPrim().SetCustomDataByKey("filaire:preset", scene.preset["label"])
    world.GetPrim().SetCustomDataByKey("filaire:seed", int(scene.seed))
    looks = _Looks(stage)
    mats = None
    if physics:
        UsdGeom.Scope.Define(stage, "/World/PhysicsMaterials")
        jacket = JACKETS[PRESETS[scene.preset_key]["jacket"]]
        mats = {
            "jacket": _physics_material(stage, "jacket", jacket["friction"], jacket["restitution"]),
            "connector": _physics_material(stage, "connector", CONNECTOR_FRICTION, 0.2),
        }
    UsdGeom.Scope.Define(stage, "/World/Cables")
    xs, ys = [], []
    for c in scene.cables:
        cp = f"/World/Cables/{c.name}"
        cx = UsdGeom.Xform.Define(stage, cp)
        cx.AddTranslateOp().Set(Gf.Vec3d(*c.position))
        prim = cx.GetPrim()
        _cable_attrs(prim, c)
        segs = [f"{cp}/Segments/seg_{i:03d}" for i in range(len(c.segments))]
        if physics:
            UsdPhysics.ArticulationRootAPI.Apply(prim)
            UsdGeom.Scope.Define(stage, f"{cp}/Segments")
            UsdGeom.Scope.Define(stage, f"{cp}/Joints")
            for sp, seg in zip(segs, c.segments, strict=True):
                _segment(stage, looks, sp, c, seg, mats)
            for i in range(len(segs) - 1):
                L0, L1 = c.segments[i].length, c.segments[i + 1].length
                _joint(stage, f"{cp}/Joints/joint_{i:03d}", segs[i], segs[i + 1], L0, L1, c)
        else:
            _cable_visual(stage, looks, cp, c)
        for side, seg_idx in (("a", 0), ("b", -1)):
            vset = prim.GetVariantSets().AddVariantSet(f"end_{side}")
            for variant, end in c.ends[side].items():
                vset.AddVariant(variant)
                vset.SetVariantSelection(variant)
                with vset.GetVariantEditContext():
                    _end_variant(
                        stage, looks, cp, side, end, c.segments[seg_idx], segs[seg_idx], mats, physics
                    )
            vset.SetVariantSelection(c.selected[side])
        for s in c.segments:
            xs.append(s.center[0] + c.position[0])
            ys.append(s.center[1] + c.position[1])
    if physics:
        _ground(stage, 1.0, (min(xs), min(ys)), (max(xs), max(ys)))
    stage.GetRootLayer().Save()
    return path


def socket_layout(keys: list[str]) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """(key, rotation, origin) of each fixed receptacle, standing in a row, insertion along +y."""
    out, x = [], 0.0
    R = np.c_[[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]  # X = -x, Y = up, Z = +y
    for key in keys:
        spec = CONNECTORS[key]
        parts = receptacle_parts(spec, "panel")
        lo, hi = part_mesh(parts).bounds
        w = hi[0] - lo[0]
        x += w / 2
        out.append((key, R, np.array([x, 0.0, -lo[1] + 0.0005])))
        x += w / 2 + 0.03
    return out


def export_sockets(path: str | Path, keys: list[str], physics: bool = True) -> Path:
    """Fixed receptacles (device ports, inlets, wall sockets) of the given connector families."""
    path = Path(path)
    stage, _world = _new_stage(path, physics)
    looks = _Looks(stage)
    if physics:
        UsdGeom.Scope.Define(stage, "/World/PhysicsMaterials")
        mat = _physics_material(stage, "connector", CONNECTOR_FRICTION, 0.2)
    UsdGeom.Scope.Define(stage, "/World/Sockets")
    layout = socket_layout(keys)
    for key, R, origin in layout:
        spec = CONNECTORS[key]
        parts = receptacle_parts(spec, "panel")
        sp = f"/World/Sockets/{key}"
        x = UsdGeom.Xform.Define(stage, sp)
        _xform(x, R, origin)
        mesh = part_mesh(parts)
        color = "#e4e6e8" if spec.key not in ("idc10",) else "#2b2b2b"
        _visual(stage, looks, f"{sp}/Visual", [(mesh, color, 0.5, 0.0)])
        if physics:
            _collision_hulls(stage, f"{sp}/Collision", [h for p in parts for h in p.convex_hulls()], mat)
        mp = mass_properties(mesh, spec.density)
        _attr(x.GetPrim(), "filaire:mass", _F.Float, float(mp["mass"]))
        _attr(x.GetPrim(), "filaire:geometricKeying", _F.Token, keying_of(spec))
        _mate_frame(stage, f"{sp}/MateFrame", key, "receptacle", "panel")
    if physics:
        _ground(stage, 0.3, (0, 0), (max(o[2][0] for o in layout), 0))
    stage.GetRootLayer().Save()
    return path
