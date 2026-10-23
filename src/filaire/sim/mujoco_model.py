"""MuJoCo models built from the OpenUSD data (see usd_reader.py).

A cable becomes a kinematic tree: the first segment has a free joint, each
next segment hangs from the previous one by three hinges (x: twist, y and z:
bending) at their common end point, plus a slide along x for coiled cords.
The tree is built in the rest pose (straight), so the springs' reference is
the straight cable; the authored pose is then set through the joint angles.
The connectors are welded to the end segments, with their convex parts as
mesh geoms. The drop test leaves the twist hinge out (see DOFS): a chain's
mass matrix is dense, and the cost of a step grows with the cube of its
number of joints.

Numerical additions, for the explicit integration of very stiff, very light
links only: each joint gets an armature (added inertia) that keeps its
highest frequency under 0.3 / timestep, and at least critical damping for
that armature. Neither changes a static equilibrium: the sag and coil checks
compare equilibria.
"""

from __future__ import annotations

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

DT = 1e-3
# bending only in the drop test: a chain's mass matrix is dense, so the cost of a
# step grows with the cube of the number of joints; twist (rotX) is dropped there,
# kept in the sag and coil checks
DOFS = (("rotY", [0, 1, 0]), ("rotZ", [0, 0, 1]))


def _wxyz(R: np.ndarray) -> list:
    x, y, z, w = Rotation.from_matrix(R).as_quat()
    return [w, x, y, z]


def _armature(k: float, dt: float) -> tuple[float, float]:
    a = k * (dt / 0.3) ** 2
    return a, 2 * np.sqrt(k * a)


def _inertial(body, b) -> None:
    body.explicitinertial = True
    body.mass = max(b.mass, 1e-7)
    body.ipos = list(b.com)
    body.iquat = _wxyz(b.inertia_axes)
    body.inertia = list(np.maximum(b.inertia, 1e-12))


def add_hulls(spec, body, hulls, prefix: str, friction: float, rgba=(0.2, 0.2, 0.2, 1)) -> None:
    for k, pts in enumerate(hulls):
        name = f"{prefix}_h{k}"
        m = spec.add_mesh(name=name)
        m.uservert = np.asarray(pts, float).ravel().tolist()
        body.add_geom(
            type=mujoco.mjtGeom.mjGEOM_MESH,
            meshname=name,
            friction=[friction, 0.005, 0.0001],
            rgba=list(rgba),
        )


def _segment_geom(body, seg, friction: float, rgba) -> None:
    if seg.capsule:
        r, h = seg.capsule
        body.add_geom(
            type=mujoco.mjtGeom.mjGEOM_CAPSULE,
            fromto=[-h / 2, 0, 0, h / 2, 0, 0],
            size=[r, 0, 0],
            friction=[friction, 0.005, 0.0001],
            rgba=list(rgba),
        )
    else:
        lx, ly, lz = seg.box
        body.add_geom(
            type=mujoco.mjtGeom.mjGEOM_BOX, size=[lx / 2, ly / 2, lz / 2], friction=[friction, 0.005, 0.0001]
        )


def coarsen(cable, max_links: int):
    """The same cable with at most max_links links: groups of g consecutive segments merged.

    Each link is straight along the chord of its group, carries the group's
    mass and length, and its joints have the springs of g joints in series
    (stiffness / g), so the bending stiffness E·I of the rod is unchanged.
    Ends keep their world pose.
    """
    import copy

    n = len(cable.segments)
    g = int(np.ceil(n / max_links))
    if g <= 1:
        return cable
    out = copy.copy(cable)
    segs, links = cable.segments, []
    for start in range(0, n, g):
        grp = segs[start : start + g]
        Ls = [s.capsule[1] if s.capsule else s.box[0] for s in grp]
        p0 = grp[0].position - grp[0].rotation[:, 0] * Ls[0] / 2
        p1 = grp[-1].position + grp[-1].rotation[:, 0] * Ls[-1] / 2
        x = (p1 - p0) / np.linalg.norm(p1 - p0)
        y = grp[len(grp) // 2].rotation[:, 1]
        y = y - x * (x @ y)
        y /= np.linalg.norm(y)
        R = np.c_[x, y, np.cross(x, y)]
        L = float(sum(Ls))
        m = sum(s.mass for s in grp)
        b = copy.copy(grp[0])
        b.rotation, b.position, b.mass, b.com = R, 0.5 * (p0 + p1), m, np.zeros(3)
        r = b.capsule[0] if b.capsule else b.box[2] / 2
        I_end = m * (r * r / 4 + L * L / 12)
        b.inertia, b.inertia_axes = np.array([m * r * r / 2, I_end, I_end]), np.eye(3)
        b.capsule = (b.capsule[0], L) if b.capsule else None
        b.box = (L, *grp[0].box[1:]) if grp[0].box else None
        links.append(b)
    out.segments = links
    joints = []
    for j in cable.joints[: len(links) - 1]:
        jj = copy.copy(j)
        jj.stiffness = {k: v / g for k, v in j.stiffness.items()}
        jj.damping = {k: v / g for k, v in j.damping.items()}
        joints.append(jj)
    out.joints = joints
    ends = {}
    for side, (old, new) in (("a", (segs[0], links[0])), ("b", (segs[-1], links[-1]))):
        if cable.ends.get(side) is None:
            ends[side] = None
            continue
        body, lp, lr = cable.ends[side]
        wp = old.position + old.rotation @ lp
        wr = old.rotation @ lr
        ends[side] = (body, new.rotation.T @ (wp - new.position), new.rotation.T @ wr)
    out.ends = ends
    return out


def cable_model(cable, dt: float = DT, lift: float = 0.01, floor: bool = True):
    """(model, init) — init(data) sets the authored pose, lifted by `lift`."""
    spec = mujoco.MjSpec()
    spec.option.timestep = dt
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    fr = float(cable.attrs.get("filaire:friction", 0.5))
    if floor:
        spec.worldbody.add_geom(
            type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 1], friction=[fr, 0.005, 0.0001]
        )
    segs, joints = cable.segments, cable.joints
    lengths = [s.capsule[1] if s.capsule else s.box[0] for s in segs]
    bodies = []
    parent = spec.worldbody
    for i, seg in enumerate(segs):
        if i == 0:
            b = parent.add_body(name="seg0", pos=list(seg.position), quat=_wxyz(seg.rotation))
            b.add_freejoint(name="root")
        else:
            b = parent.add_body(
                name=f"seg{i}", pos=[lengths[i - 1] / 2 + lengths[i] / 2, 0, 0], quat=[1, 0, 0, 0]
            )
            j = joints[i - 1]
            anchor = [-lengths[i] / 2, 0, 0]
            for dof, axis in DOFS:
                k = j.stiffness[dof]
                a, c = _armature(k, dt)
                b.add_joint(
                    name=f"j{i}_{dof}",
                    type=mujoco.mjtJoint.mjJNT_HINGE,
                    axis=axis,
                    pos=anchor,
                    stiffness=k,
                    damping=max(j.damping[dof], c),
                    armature=a,
                )
            if j.free_axial:
                k = j.stiffness["transX"]
                b.add_joint(
                    name=f"j{i}_transX",
                    type=mujoco.mjtJoint.mjJNT_SLIDE,
                    axis=[1, 0, 0],
                    pos=anchor,
                    stiffness=k,
                    damping=max(j.damping["transX"], 2 * np.sqrt(k * seg.mass)),
                )
        _inertial(b, seg)
        _segment_geom(b, seg, fr, (0.15, 0.15, 0.15, 1))
        bodies.append(b)
        parent = b
    for i in range(len(bodies) - 2):
        spec.add_exclude(bodyname1=f"seg{i}", bodyname2=f"seg{i + 2}")
    for side, idx in (("a", 0), ("b", len(segs) - 1)):
        end = cable.ends.get(side)
        if end is None:
            continue
        body, lp, lr = end
        e = bodies[idx].add_body(name=f"end_{side}", pos=list(lp), quat=_wxyz(lr))
        _inertial(e, body)
        add_hulls(spec, e, body.hulls, f"end_{side}", 0.4)
        for k in (1, 2, 3):
            if 0 <= idx + (k if side == "a" else -k) < len(segs):
                spec.add_exclude(bodyname1=f"end_{side}", bodyname2=f"seg{idx + (k if side == 'a' else -k)}")
    model = spec.compile()

    def init(data):
        root = model.joint("root").qposadr[0]
        data.qpos[root : root + 3] = segs[0].position + np.array([0, 0, lift])
        data.qpos[root + 3 : root + 7] = _wxyz(segs[0].rotation)
        for i in range(1, len(segs)):
            rel = segs[i - 1].rotation.T @ segs[i].rotation
            angles = dict(
                zip(("rotX", "rotY", "rotZ"), Rotation.from_matrix(rel).as_euler("XYZ"), strict=True)
            )
            for dof, _axis in DOFS:
                data.qpos[model.joint(f"j{i}_{dof}").qposadr[0]] = angles[dof]
        mujoco.mj_forward(model, data)

    return model, init


def chain_model(
    n: int,
    seg_len: float,
    seg_mass: float,
    radius: float,
    k_bend: float,
    k_twist: float,
    vertical: bool = False,
    k_axial: float | None = None,
    dt: float = DT,
    offset: float = 0.0,
):
    """A cantilever (horizontal) or a hanging chain (vertical) of n links from a fixed support.

    The first hinge is `offset` away from the support (half a link for the
    cantilever: each hinge then stands for the curvature of the link length
    around it, the midpoint rule).
    """
    spec = mujoco.MjSpec()
    spec.option.timestep = dt
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    # links along +x; for the hanging chain the whole tree is turned to point down
    q0 = _wxyz(Rotation.from_euler("y", 90, degrees=True).as_matrix()) if vertical else [1, 0, 0, 0]
    parent = spec.worldbody.add_body(name="base", pos=[0, 0, 0], quat=q0)
    I_end = seg_mass * (radius**2 / 4 + seg_len**2 / 12)
    for i in range(n):
        b = parent.add_body(name=f"l{i}", pos=[offset + seg_len / 2 if i == 0 else seg_len, 0, 0])
        anchor = [-seg_len / 2, 0, 0]
        for axis, k in (([1, 0, 0], k_twist), ([0, 1, 0], k_bend), ([0, 0, 1], k_bend)):
            a, c = _armature(k, dt)
            b.add_joint(
                type=mujoco.mjtJoint.mjJNT_HINGE, axis=axis, pos=anchor, stiffness=k, damping=c, armature=a
            )
        if k_axial is not None:
            b.add_joint(
                name=f"s{i}",
                type=mujoco.mjtJoint.mjJNT_SLIDE,
                axis=[1, 0, 0],
                pos=anchor,
                stiffness=k_axial,
                damping=2 * n * np.sqrt(k_axial * seg_mass),  # critical for the chain's first mode
            )
        b.explicitinertial = True
        b.mass = seg_mass
        b.ipos = [0, 0, 0]  # set explicitly: left unset, it is not the body origin
        b.iquat = [1, 0, 0, 0]
        b.inertia = [seg_mass * radius**2 / 2, I_end, I_end]
        b.add_geom(
            type=mujoco.mjtGeom.mjGEOM_CAPSULE,
            fromto=[-seg_len / 2, 0, 0, seg_len / 2, 0, 0],
            size=[radius, 0, 0],
            contype=0,
            conaffinity=0,
        )
        parent = b
    return spec.compile()
