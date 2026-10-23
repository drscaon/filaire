"""Read Filaire's OpenUSD output back into plain data for the simulation checks.

The checks read the files, not the generator's objects, so that what is
tested is what was exported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

DEG = math.pi / 180


def _rt(prim, cache) -> tuple[np.ndarray, np.ndarray]:
    M = np.asarray(cache.GetLocalToWorldTransform(prim), float)
    return M[:3, :3].T, M[3, :3]  # Gf rows are axes: transpose to columns


def quat_to_matrix(q) -> np.ndarray:
    w, x, y, z = q.GetReal(), *q.GetImaginary()
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


@dataclass
class Body:
    name: str
    rotation: np.ndarray  # world, columns = axes
    position: np.ndarray
    mass: float
    com: np.ndarray
    inertia: np.ndarray  # principal moments
    inertia_axes: np.ndarray  # rotation of the principal axes in the body frame
    capsule: tuple | None = None  # (radius, height) along x
    box: tuple | None = None  # (lx, ly, lz)
    hulls: list = field(default_factory=list)  # point arrays in the body frame
    attrs: dict = field(default_factory=dict)


def _body(prim, cache) -> Body:
    R, t = _rt(prim, cache)
    m = UsdPhysics.MassAPI(prim)
    pa = m.GetPrincipalAxesAttr().Get()
    b = Body(
        name=prim.GetName(),
        rotation=R,
        position=t,
        mass=float(m.GetMassAttr().Get()),
        com=np.asarray(m.GetCenterOfMassAttr().Get(), float),
        inertia=np.asarray(m.GetDiagonalInertiaAttr().Get(), float),
        inertia_axes=quat_to_matrix(pa) if pa is not None else np.eye(3),
    )
    col = prim.GetChild("Collision")
    if col and col.IsA(UsdGeom.Capsule):
        cap = UsdGeom.Capsule(col)
        b.capsule = (float(cap.GetRadiusAttr().Get()), float(cap.GetHeightAttr().Get()))
    elif col and col.IsA(UsdGeom.Cube):
        ops = UsdGeom.Xformable(col).GetOrderedXformOps()
        b.box = tuple(float(v) for v in ops[0].Get())
    elif col:
        for hull in col.GetChildren():
            b.hulls.append(np.asarray(UsdGeom.Mesh(hull).GetPointsAttr().Get(), float))
    mf = prim.GetChild("MateFrame")
    if mf:
        b.attrs = {a.GetName(): a.Get() for a in mf.GetAttributes() if a.GetName().startswith("filaire:")}
    return b


@dataclass
class Joint:
    stiffness: dict  # dof -> SI (rad or m)
    damping: dict
    free_axial: bool


@dataclass
class CableData:
    name: str
    attrs: dict
    segments: list
    joints: list
    ends: dict  # "a"/"b" -> (Body, local pos in end segment, local rotation) or None
    variants: dict


def _joint(prim) -> Joint:
    k, c = {}, {}
    for dof in ("rotX", "rotY", "rotZ", "transX"):
        d = UsdPhysics.DriveAPI.Get(prim, dof)
        if d and d.GetStiffnessAttr().HasValue():
            f = 1 / DEG if dof.startswith("rot") else 1.0  # per degree -> per radian
            k[dof] = float(d.GetStiffnessAttr().Get()) * f
            c[dof] = float(d.GetDampingAttr().Get()) * f
    return Joint(k, c, "transX" in k)


def read_cable(stage: Usd.Stage, path: str, variants: dict | None = None) -> CableData:
    prim = stage.GetPrimAtPath(path)
    vsets = prim.GetVariantSets()
    for side, v in (variants or {}).items():
        vsets.GetVariantSet(f"end_{side}").SetVariantSelection(v)
    cache = UsdGeom.XformCache()
    attrs = {a.GetName(): a.Get() for a in prim.GetAttributes() if a.GetName().startswith("filaire:")}
    segs = [_body(p, cache) for p in prim.GetChild("Segments").GetChildren()]
    joints = [_joint(p) for p in prim.GetChild("Joints").GetChildren()]
    ends = {}
    for side in ("a", "b"):
        body = prim.GetPrimAtPath(f"End_{side.upper()}/Body")
        if not body:
            ends[side] = None
            continue
        attach = UsdPhysics.FixedJoint(prim.GetPrimAtPath(f"End_{side.upper()}/Attach"))
        lp = np.asarray(attach.GetLocalPos0Attr().Get(), float)
        lr = quat_to_matrix(attach.GetLocalRot0Attr().Get())
        ends[side] = (_body(body, cache), lp, lr)
    sel = {s: vsets.GetVariantSet(f"end_{s}").GetVariantSelection() for s in ("a", "b")}
    return CableData(prim.GetName(), attrs, segs, joints, ends, sel)


def cable_paths(stage: Usd.Stage) -> list[str]:
    return [str(p.GetPath()) for p in stage.GetPrimAtPath("/World/Cables").GetChildren()]


def end_options(stage: Usd.Stage, path: str, side: str) -> list[str]:
    return list(stage.GetPrimAtPath(path).GetVariantSets().GetVariantSet(f"end_{side}").GetVariantNames())


def read_sockets(path: str | Path) -> dict:
    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.XformCache()
    out = {}
    for prim in stage.GetPrimAtPath("/World/Sockets").GetChildren():
        R, t = _rt(prim, cache)
        hulls = [
            np.asarray(UsdGeom.Mesh(h).GetPointsAttr().Get(), float)
            for h in prim.GetChild("Collision").GetChildren()
        ]
        mf = prim.GetChild("MateFrame")
        attrs = {a.GetName(): a.Get() for a in mf.GetAttributes() if a.GetName().startswith("filaire:")}
        out[prim.GetName()] = {"rotation": R, "position": t, "hulls": hulls, "attrs": attrs}
    return out
