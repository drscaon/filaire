"""Filaire physics for Blender: rigid bodies and constraints from the UsdPhysics description.

Blender's USD importer reads geometry and materials but not UsdPhysics: imported as is, a cable is
a pile of loose tube pieces and its connectors fall off. Installed as an add-on, this file hooks
into File > Import > Universal Scene Description: every imported file that describes rigid bodies
gets them in Blender, ready to play, with nothing to set by hand (the approach of Quincaillerie's
add-on, extended to Filaire's cable joints):

  * one rigid body per UsdPhysics body (a cable segment, a connector, a stripped end), on its
    visual mesh, whose origin is moved to the USD centre of mass (Blender uses the origin as the
    centre of mass); USD mass, friction of its physics material;
  * its collision shape: a compound of the USD collision shapes (capsules, boxes, convex hulls),
    rebuilt from the file (whether or not "Guides" was ticked), hidden in renders;
  * colliders outside any body (the ground) -> passive;
  * the joints between segments (translations locked, rotX/rotY/rotZ drives) -> Generic Spring
    constraints with the drives' stiffness and damping; a coiled cord's free transX with its axial
    spring; fixed joints (a connector on its end segment) -> Fixed constraints. Bullet takes a
    spring's rest position from the first frame, so in Blender a cable keeps the shape it was
    generated in (coiled, slack) as its rest shape, where MuJoCo and the file say straight;
  * the rigid body world: small collision margins and enough substeps for light segments.

Install once: Edit > Preferences > Get Extensions > Install from Disk > the .zip from
`filaire blender-addon` (or Add-ons > Install for this .py). Without installing: open this file in
the Scripting workspace, set USD_FILE below and Run Script; or headless:
    blender -b -P filaire_physics.py -- file.usdc
Needs Blender 4.4 or later (its Python ships bpy and the OpenUSD module, pxr).
"""

import math
import re
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

bl_info = {
    "name": "Filaire physics",
    "author": "Daniel Régis Sarmento Caon",
    "version": (0, 1, 0),
    "blender": (4, 4, 0),
    "location": "File > Import > Universal Scene Description",
    "description": "Rigid bodies and constraints from UsdPhysics when importing a Filaire USD file",
    "category": "Import-Export",
}

USD_FILE = ""  # when run as a script from Blender's text editor
SUBSTEP_HZ = 4000  # physics rate (substeps per second): segments weigh a fraction of a gram
MARGIN = 0.0001  # collision margin (m); a tenth of the PhysX contact offset when the file gives one
ITERATIONS = 80
FIXED_ITERATIONS = 200
ANG_DAMPING = 0.1
LIN_DAMPING = 0.05
CAPSULE_SIDES = 16


def _usd():
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

    return Usd, UsdGeom, UsdPhysics, UsdShade


def _base(name):
    return re.sub(r"\.\d{3}$", "", name)


def _gf(M):
    """Gf.Matrix4d (row vectors) -> mathutils Matrix (column vectors)."""
    return Matrix([[M[j][i] for j in range(4)] for i in range(4)])


def _quat(q):
    return Quaternion((q.GetReal(), *q.GetImaginary()))


def _friction(prim):
    _, _, UsdPhysics, UsdShade = _usd()
    mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    if mat:
        api = UsdPhysics.MaterialAPI(mat.GetPrim())
        v = api.GetDynamicFrictionAttr().Get() if api else None
        if v is not None:
            return float(v)
    return 0.5


def _keep_world(o, parent):
    M = o.matrix_world.copy()
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    o.matrix_world = M


class _NameMap:
    """USD prim path -> imported object, by names, when the importer gives no prim map."""

    def __init__(self, objs):
        self.by_name = {}
        for o in objs:
            self.by_name.setdefault(_base(o.name), []).append(o)

    def objects(self, path):
        comps = [c for c in str(path).split("/") if c]

        def chain(o):
            out = []
            while o is not None:
                out.append(_base(o.name))
                o = o.parent
            return out[::-1]

        def subseq(small, big):
            it = iter(big)
            return all(any(x == y for y in it) for x in small)

        cands = [o for o in self.by_name.get(comps[-1], []) if subseq(chain(o), comps)]
        return sorted(cands, key=lambda o: -len(chain(o)))[:1]


def _collider_geometry(prim, M):
    """Vertices (transformed by M, a mathutils Matrix) and faces of a USD collider."""
    _, UsdGeom, _, _ = _usd()
    if prim.IsA(UsdGeom.Cube):
        s = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2
        V = [(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
        F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    elif prim.IsA(UsdGeom.Capsule):
        cap = UsdGeom.Capsule(prim)
        r, h, ax = cap.GetRadiusAttr().Get(), cap.GetHeightAttr().Get(), cap.GetAxisAttr().Get()
        n, rings = CAPSULE_SIDES, 4
        V = []
        # two hemispheres along the axis; the convex hull of these points is the capsule
        for side in (-1, 1):
            for k in range(rings + 1):
                phi = math.pi / 2 * k / rings
                z = side * (h / 2 + r * math.sin(phi))
                rr = r * math.cos(phi)
                for i in range(n if k < rings else 1):
                    a = 2 * math.pi * i / n
                    a_, b_ = rr * math.cos(a), rr * math.sin(a)
                    V.append({"X": (z, a_, b_), "Y": (b_, z, a_), "Z": (a_, b_, z)}[ax])
        F = []  # a point cloud: Bullet's convex hull shape needs only the vertices
    elif prim.IsA(UsdGeom.Mesh):
        m = UsdGeom.Mesh(prim)
        V = [tuple(p) for p in m.GetPointsAttr().Get()]
        counts, idx = m.GetFaceVertexCountsAttr().Get(), m.GetFaceVertexIndicesAttr().Get()
        F, k = [], 0
        for c in counts:
            F.append(tuple(idx[k : k + c]))
            k += c
    else:
        return None, None
    return [tuple(M @ Vector(v)) for v in V], F


def _drive(UsdPhysics, jp, dof):
    d = UsdPhysics.DriveAPI.Get(jp, dof)
    if not d or not d.GetStiffnessAttr().HasAuthoredValue():
        return None
    return float(d.GetStiffnessAttr().Get() or 0.0), float(d.GetDampingAttr().Get() or 0.0)


def _locked(UsdPhysics, jp, dof):
    lim = UsdPhysics.LimitAPI.Get(jp, dof)
    if not lim or not lim.GetLowAttr().HasAuthoredValue():
        return False
    return lim.GetLowAttr().Get() > lim.GetHighAttr().Get()


def setup_physics(stage, prim_map=None, scene=None):
    """Build Blender rigid bodies and constraints for the UsdPhysics bodies of an imported stage.

    prim_map: {prim path: [Blender data]} from the importer; without it, objects are found by name.
    Returns {USD body path: Blender object}."""
    Usd, UsdGeom, UsdPhysics, _ = _usd()
    sc = scene or bpy.context.scene
    bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    if not bodies:
        return {}
    body_set = {p.GetPath() for p in bodies}
    if prim_map is None:
        names = _NameMap(list(bpy.data.objects))

        def objs_of(path):
            return names.objects(path)

    else:
        # the importer merges an Xform and its only Mesh child into one object: the object is mapped
        # to the Xform, its mesh data to the Mesh prim
        users = {}
        for o in bpy.data.objects:
            if o.data is not None:
                users.setdefault(o.data.as_pointer(), []).append(o)
        pmap = {}
        for k, v in prim_map.items():
            objs = [o for o in v if isinstance(o, bpy.types.Object)]
            for d in v:
                if isinstance(d, bpy.types.Mesh) and not any(o.data == d for o in objs):
                    objs += users.get(d.as_pointer(), [])
            pmap[str(k)] = objs

        def objs_of(path):
            return [o for o in pmap.get(str(path), []) if o.name in bpy.data.objects]

    cache = UsdGeom.XformCache()
    done = [
        o for b in bodies for q in Usd.PrimRange(b) for o in objs_of(q.GetPath()) if "usd_rigid_body" in o
    ]
    if done:  # already set up (two hooks registered: the add-on and a script)
        return {}

    def owner(p):
        q = p.GetParent()
        while q and not q.IsPseudoRoot():
            if q.GetPath() in body_set:
                return q
            q = q.GetParent()
        return None

    bpy.context.view_layer.update()  # world matrices of the objects just imported
    # correction from stage world to Blender world (import scale, parent objects)
    C = Matrix.Identity(4)
    for p in stage.Traverse():
        obs = [o for o in objs_of(p.GetPath()) if o.type == "MESH"]
        if p.IsA(UsdGeom.Mesh) and obs and not p.HasAPI(UsdPhysics.CollisionAPI):
            C = obs[0].matrix_world @ _gf(cache.GetLocalToWorldTransform(p)).inverted()
            break

    def world(prim):
        return C @ _gf(cache.GetLocalToWorldTransform(prim))

    # imported collision guides are replaced by colliders rebuilt from the file
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.CollisionAPI):
            for o in objs_of(p.GetPath()):
                bpy.data.objects.remove(o, do_unlink=True)

    if sc.rigidbody_world is None:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = max(10, math.ceil(SUBSTEP_HZ / sc.render.fps))
    rw.solver_iterations = ITERATIONS
    rw.use_split_impulse = True
    if rw.collection is None:
        rw.collection = bpy.data.collections.new("RigidBodyWorld")
    if rw.constraints is None:
        rw.constraints = bpy.data.collections.new("RigidBodyConstraints")
    rw.point_cache.frame_end = max(rw.point_cache.frame_end, sc.frame_end)
    target = sc.collection

    def add_rb(o, rtype, margin=MARGIN):
        if o.name not in rw.collection.objects:
            rw.collection.objects.link(o)
        if o.rigid_body is None:
            with bpy.context.temp_override(scene=sc, object=o, active_object=o, selected_objects=[o]):
                bpy.ops.rigidbody.object_add(type=rtype)
        rb = o.rigid_body
        rb.type = rtype
        rb.use_margin = True
        rb.collision_margin = margin
        rb.restitution = 0.0
        rb.use_deactivation = False
        rb.linear_damping = LIN_DAMPING
        rb.angular_damping = ANG_DAMPING
        return rb

    def new_object(name, V, F, M_world):
        me = bpy.data.meshes.new(name)
        me.from_pydata(V, [], F)
        me.update()
        o = bpy.data.objects.new(name, me)
        target.objects.link(o)
        o.matrix_world = M_world
        return o

    # bodies
    out = {}
    for b in bodies:
        kin = bool(UsdPhysics.RigidBodyAPI(b).GetKinematicEnabledAttr().Get())
        meshes, cols = [], []
        for p in Usd.PrimRange(b):
            if p != b and (p.GetPath() in body_set or owner(p) != b):
                continue
            if p.HasAPI(UsdPhysics.CollisionAPI):
                cols.append(p)
            elif p.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(p).ComputePurpose() != UsdGeom.Tokens.guide:
                meshes.append(p)
        Wb = world(b)
        ma = UsdPhysics.MassAPI(b)
        com_w = Wb @ Vector(ma.GetCenterOfMassAttr().Get() or (0, 0, 0))
        M_body = Matrix.Translation(com_w) @ Wb.to_3x3().normalized().to_4x4()
        vis = next((o for p in meshes for o in objs_of(p.GetPath()) if o.type == "MESH"), None)
        if vis is None:  # no visual mesh: an empty mesh object carries the body
            vis = new_object(f"{b.GetName()}_body", [], [], M_body)
        else:
            if vis.data.users > 1:
                vis.data = vis.data.copy()
            vis.data.transform(M_body.inverted() @ vis.matrix_world)  # origin at the centre of mass
            _keep_world(vis, None)
            vis.matrix_world = M_body
        bpy.context.view_layer.update()
        rb = add_rb(vis, "PASSIVE" if kin else "ACTIVE")
        rb.kinematic = kin
        rb.mass = float(ma.GetMassAttr().Get() or 0.001)
        rb.collision_shape = "COMPOUND"
        rb.collision_margin = 0.0
        fr = []
        inv = M_body.inverted()
        for c in cols:
            V, F = _collider_geometry(c, inv @ world(c))
            if V is None:
                continue
            co = new_object(f"{vis.name}_col_{c.GetName()}", V, F, M_body)
            _keep_world(co, vis)
            off = c.GetAttribute("physxCollision:contactOffset")
            margin = min(MARGIN, off.Get() / 10) if off and off.Get() else MARGIN
            crb = add_rb(co, "ACTIVE", margin)
            crb.collision_shape = "CONVEX_HULL"
            crb.mass = 1e-7
            co.display_type, co.hide_render = "WIRE", True
            fr.append(_friction(c))
        rb.friction = min(fr) if fr else 0.5
        vis["usd_rigid_body"] = str(b.GetPath())
        vis["usd_center_of_mass"] = list(ma.GetCenterOfMassAttr().Get() or (0, 0, 0))
        out[b.GetPath()] = vis

    # colliders outside any body (the ground): passive
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.CollisionAPI) and owner(p) is None and p.GetPath() not in body_set:
            V, F = _collider_geometry(p, Matrix.Identity(4))
            if V is None:
                continue
            o = new_object(p.GetName(), V, F, world(p))
            rb = add_rb(o, "PASSIVE")
            rb.collision_shape = "BOX" if p.IsA(UsdGeom.Cube) else "CONVEX_HULL"
            rb.friction = _friction(p)
            o.hide_render, o.display_type = True, "WIRE"

    # joints -> constraints
    rad = 180.0 / math.pi  # USD angular drives are per degree, Blender's springs per radian
    for jp in stage.Traverse():
        if not jp.IsA(UsdPhysics.Joint):
            continue
        J = UsdPhysics.Joint(jp)
        b0, b1 = J.GetBody0Rel().GetTargets(), J.GetBody1Rel().GetTargets()
        o0, o1 = (out.get(b0[0]) if b0 else None), (out.get(b1[0]) if b1 else None)
        if o1 is None:
            continue
        W0 = world(stage.GetPrimAtPath(b0[0])) if b0 else C.copy()
        frame = (
            W0
            @ Matrix.Translation(Vector(J.GetLocalPos0Attr().Get()))
            @ _quat(J.GetLocalRot0Attr().Get()).to_matrix().to_4x4()
        )
        e = bpy.data.objects.new(f"joint_{jp.GetParent().GetParent().GetName()}_{jp.GetName()}", None)
        target.objects.link(e)
        e.empty_display_size = 0.002
        e.matrix_world = Matrix.Translation(frame.translation) @ frame.to_3x3().normalized().to_4x4()
        fixed = jp.IsA(UsdPhysics.FixedJoint)
        with bpy.context.temp_override(scene=sc, object=e, active_object=e, selected_objects=[e]):
            bpy.ops.rigidbody.constraint_add(type="FIXED" if fixed else "GENERIC_SPRING")
        c = e.rigid_body_constraint
        c.object1, c.object2 = o0, o1
        c.disable_collisions = True
        if fixed:  # a connector can weigh as much as 30 cm of cable: hold it firmly
            c.use_override_solver_iterations = True
            c.solver_iterations = FIXED_ITERATIONS
        if not fixed:
            c.spring_type = "SPRING2"
            for dof, kind, a in (
                ("transX", "lin", "x"),
                ("transY", "lin", "y"),
                ("transZ", "lin", "z"),
                ("rotX", "ang", "x"),
                ("rotY", "ang", "y"),
                ("rotZ", "ang", "z"),
            ):
                if _locked(UsdPhysics, jp, dof):
                    setattr(c, f"use_limit_{kind}_{a}", True)
                    setattr(c, f"limit_{kind}_{a}_lower", 0.0)
                    setattr(c, f"limit_{kind}_{a}_upper", 0.0)
                drive = _drive(UsdPhysics, jp, dof)
                if drive is None:
                    continue
                k, d = drive
                scale = rad if kind == "ang" else 1.0
                suffix = a if kind == "lin" else f"ang_{a}"
                setattr(c, f"use_spring_{suffix}", True)
                setattr(c, f"spring_stiffness_{suffix}", k * scale)
                setattr(c, f"spring_damping_{suffix}", d * scale)
        if o0 is not None:
            _keep_world(e, o0)  # the joint marker follows its first body in the viewport
        e["usd_joint"] = str(jp.GetPath())
    return out


# ------------------------------------------------------------------ add-on: hook into the importer
_registered = False


class FILAIRE_USDHook(bpy.types.USDHook):
    bl_idname = "filaire_physics"
    bl_label = "Filaire physics"
    bl_description = "Rigid bodies and constraints from UsdPhysics"

    @staticmethod
    def on_import(context):
        stage = context.get_stage()
        if stage is None:
            return False
        try:
            prim_map = context.get_prim_map()
        except AttributeError:  # Blender before 4.4
            prim_map = None
        setup_physics(stage, prim_map)
        return True


def register():
    global _registered
    if not _registered:
        bpy.utils.register_class(FILAIRE_USDHook)
        _registered = True


def unregister():
    global _registered
    if _registered:
        bpy.utils.unregister_class(FILAIRE_USDHook)
        _registered = False


def import_with_physics(path):
    """File > Import > USD with the physics set up (registers the import hook if needed)."""
    register()
    bpy.ops.wm.usd_import(filepath=path)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    f = argv[0] if argv else USD_FILE
    if f:
        import_with_physics(f)
    else:
        register()  # run from the text editor: every USD import of this session gets its physics
