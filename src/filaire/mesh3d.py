"""Triangle meshes: extrusions of plane regions, swept tubes, mass properties."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry.polygon import orient

from .geometry2d import polygons


@dataclass
class TriMesh:
    points: np.ndarray  # (n, 3) float
    faces: np.ndarray  # (m, 3) int, counter-clockwise seen from outside

    @staticmethod
    def empty() -> TriMesh:
        return TriMesh(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))

    def transformed(self, rotation: np.ndarray, translation) -> TriMesh:
        return TriMesh(self.points @ np.asarray(rotation).T + np.asarray(translation), self.faces.copy())

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.points.min(axis=0), self.points.max(axis=0)


def merge(meshes: list[TriMesh]) -> TriMesh:
    meshes = [m for m in meshes if len(m.faces)]
    if not meshes:
        return TriMesh.empty()
    pts, faces, n = [], [], 0
    for m in meshes:
        pts.append(m.points)
        faces.append(m.faces + n)
        n += len(m.points)
    return TriMesh(np.vstack(pts), np.vstack(faces))


def _triangulate(poly) -> list[np.ndarray]:
    """Triangles (3, 2) covering a polygon with holes, counter-clockwise."""
    out = []
    for t in shapely.constrained_delaunay_triangles(poly).geoms:
        if t.area <= 0:
            continue
        out.append(np.asarray(orient(t, 1.0).exterior.coords)[:3])
    return out


def extrude(region, z0: float, z1: float) -> TriMesh:
    """Closed prism mesh of a plane region (holes allowed) between z0 < z1."""
    meshes = []
    for poly in polygons(region):
        pts: list = []
        faces: list = []

        def add(p, pts=pts):
            pts.append(p)
            return len(pts) - 1

        for tri in _triangulate(poly):
            a, b, c = (add((x, y, z1)) for x, y in tri)
            faces.append((a, b, c))  # top, normal +z
            a, b, c = (add((x, y, z0)) for x, y in tri)
            faces.append((a, c, b))  # bottom, normal -z
        # side walls: exterior CCW and holes CW, so (p, q) with outward normal on the right
        for ring in [poly.exterior, *poly.interiors]:
            c = np.asarray(ring.coords)
            for (x0, y0), (x1, y1) in zip(c[:-1], c[1:], strict=True):
                p0, p1 = add((x0, y0, z0)), add((x1, y1, z0))
                q0, q1 = add((x0, y0, z1)), add((x1, y1, z1))
                faces += [(p0, p1, q1), (p0, q1, q0)]
        meshes.append(TriMesh(np.asarray(pts, float), np.asarray(faces, np.int64)))
    return merge(meshes)


def convex_prism_points(poly, z0: float, z1: float) -> np.ndarray:
    """Vertices of the extrusion of a convex polygon (for convex-hull collision shapes)."""
    c = np.asarray(poly.exterior.coords)[:-1]
    return np.vstack([np.c_[c, np.full(len(c), z0)], np.c_[c, np.full(len(c), z1)]])


def sweep(profile: np.ndarray, path: np.ndarray, normals: np.ndarray, caps: bool = True) -> TriMesh:
    """Tube: a closed plane profile (k, 2), counter-clockwise, swept along a path.

    path (n, 3) and normals (n, 3): at each path point the profile's u axis
    follows `normals` and its v axis tangent × normal, so the frame is
    right-handed with the tangent as third axis.
    """
    path = np.asarray(path, float)
    n, k = len(path), len(profile)
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    u = normals - (normals * t).sum(1, keepdims=True) * t
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(t, u)
    pts = (
        path[:, None, :]
        + profile[None, :, 0, None] * u[:, None, :]
        + profile[None, :, 1, None] * v[:, None, :]
    )
    pts = pts.reshape(-1, 3)
    faces = []
    for i in range(n - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            c, d = a + k, b + k
            faces += [(a, b, d), (a, d, c)]
    mesh = TriMesh(pts, np.asarray(faces, np.int64))
    if not caps:
        return mesh
    from shapely.geometry import Polygon

    tris = _triangulate(orient(Polygon(profile), 1.0))
    extra_pts, extra_faces = [], []
    base = len(pts)
    for end, sign in ((0, -1.0), (n - 1, 1.0)):
        for tri in tris:
            ids = []
            for x, y in tri:
                extra_pts.append(path[end] + x * u[end] + y * v[end])
                ids.append(base + len(extra_pts) - 1)
            extra_faces.append(tuple(ids) if sign > 0 else (ids[0], ids[2], ids[1]))
    return TriMesh(np.vstack([pts, extra_pts]), np.vstack([mesh.faces, np.asarray(extra_faces, np.int64)]))


def mass_properties(mesh: TriMesh, density: float) -> dict:
    """Mass, centre of mass and inertia tensor (about the centre) of a closed mesh.

    Signed tetrahedra from the origin (divergence theorem); the mesh must be
    closed and consistently oriented outwards. Several closed shells may
    overlap slightly (layers of a connector): their volumes add up.
    """
    p = mesh.points[mesh.faces]  # (m, 3, 3)
    a, b, c = p[:, 0], p[:, 1], p[:, 2]
    det = np.einsum("ij,ij->i", a, np.cross(b, c))  # 6 × signed volume
    vol = det.sum() / 6
    if vol <= 0:
        raise ValueError("mesh has no positive volume (open or inverted?)")
    com = (det[:, None] * (a + b + c)).sum(0) / 24 / vol
    # second moments ∫ x_i x_j dV of each tetrahedron (origin, a, b, c)
    s = a + b + c
    cov = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            term = a[:, i] * a[:, j] + b[:, i] * b[:, j] + c[:, i] * c[:, j] + s[:, i] * s[:, j]
            cov[i, j] = (det * term).sum() / 120
    mass = density * vol
    cov_c = density * cov - mass * np.outer(com, com)
    inertia = np.trace(cov_c) * np.eye(3) - cov_c
    return {"mass": mass, "volume": vol, "com": com, "inertia": inertia}


def principal_inertia(inertia: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Principal moments and rotation matrix (columns = principal axes, det +1)."""
    w, vecs = np.linalg.eigh(inertia)
    if np.linalg.det(vecs) < 0:
        vecs[:, 2] *= -1
    return np.maximum(w, 1e-18), vecs


def weld(mesh: TriMesh, tol: float = 1e-7) -> TriMesh:
    """Merge coincident vertices (within tol), so that neighbouring faces share them."""
    if not len(mesh.points):
        return mesh
    key = np.round(mesh.points / tol).astype(np.int64)
    _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    faces = inverse.reshape(-1)[mesh.faces]
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    return TriMesh(mesh.points[first], faces[keep])


def split_normals(points: np.ndarray, faces: np.ndarray, crease_deg: float = 35.0) -> np.ndarray:
    """Face-varying normals: each corner averages the normals of the faces around its vertex that
    are within crease_deg of its own face, so tubes shade smoothly and connector edges stay sharp."""
    V = np.asarray(points, float)
    F = np.asarray(faces)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])  # area-weighted
    fu = fn / np.clip(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30, None)
    cosc = np.cos(np.radians(crease_deg))
    corners_v = F.ravel()
    corners_f = np.repeat(np.arange(len(F)), 3)
    order = np.argsort(corners_v, kind="stable")
    sv, sf = corners_v[order], corners_f[order]
    starts = np.r_[0, np.nonzero(np.diff(sv))[0] + 1, len(sv)]
    out = np.zeros((len(corners_v), 3))
    for a, b in zip(starts[:-1], starts[1:], strict=True):
        f = sf[a:b]
        U = fu[f]
        acc = ((U @ U.T) > cosc).astype(float) @ fn[f]
        acc /= np.clip(np.linalg.norm(acc, axis=1, keepdims=True), 1e-30, None)
        out[order[a:b]] = acc
    return out
