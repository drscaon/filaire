"""Plane shapes for cable cross-sections and connector faces.

All functions take and return millimetres or metres consistently (they are
unit-free); the catalogue is written in millimetres and converted once.

Shapes are shapely geometries in the connector's face plane: x across the
width, y across the height, the insertion axis being z.
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

QUAD_SEGS = 8  # segments per quarter circle (32 per full circle)


def circle(d: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    return Point(cx, cy).buffer(d / 2, quad_segs=QUAD_SEGS)


def rect(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    return box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def rrect(w: float, h: float, r: float = 0.0, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    """Rectangle w × h with corner radius r (clipped to half the shorter side)."""
    r = min(max(r, 0.0), min(w, h) / 2 - 1e-9)
    if r <= 0:
        return rect(w, h, cx, cy)
    return rect(w - 2 * r, h - 2 * r, cx, cy).buffer(r, quad_segs=QUAD_SEGS, join_style="round")


def stadium(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    return rrect(w, h, h / 2, cx, cy)


def chamfered_rect(w: float, h: float, bottom: float = 0.0, top: float = 0.0) -> Polygon:
    """Rectangle with 45° chamfers on its two bottom and/or two top corners."""
    x, y = w / 2, h / 2
    pts = [(-x + bottom, -y), (x - bottom, -y), (x, -y + bottom), (x, y - top), (x - top, y), (-x + top, y)]
    pts += [(-x, y - top), (-x, -y + bottom)]
    return Polygon(_dedupe(pts))


def _dedupe(pts):
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 1e-9:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-9:
        out.pop()
    return out


def union(*geoms):
    return unary_union([g for g in geoms if g is not None and not g.is_empty])


def rotate(geom, angle_deg: float):
    return affinity.rotate(geom, angle_deg, origin=(0, 0))


def polygons(geom) -> list[Polygon]:
    """The polygons of a geometry (Polygon, MultiPolygon or collection), oriented CCW."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [orient(geom, 1.0)]
    if isinstance(geom, MultiPolygon):
        return [orient(p, 1.0) for p in geom.geoms]
    out = []
    for g in getattr(geom, "geoms", []):
        out += polygons(g)
    return out


# ------------------------------------------------------------ convex parts


def _is_convex(poly: Polygon, tol: float) -> bool:
    return poly.convex_hull.area - poly.area <= tol * max(poly.area, 1e-18)


def convex_parts(geom, tol: float = 1e-6) -> list[Polygon]:
    """Split a region (holes allowed) into convex polygons.

    Constrained Delaunay triangulation, then greedy merging of neighbouring
    pieces while their union stays convex (Hertel–Mehlhorn style). Every
    returned polygon is convex, the pieces do not overlap and they cover the
    region; extruded, each is a valid convex collision shape.
    """
    parts: list[Polygon] = []
    for poly in polygons(geom):
        if not poly.interiors and _is_convex(poly, tol):
            parts.append(poly)
            continue
        tris = [orient(t, 1.0) for t in shapely.constrained_delaunay_triangles(poly).geoms if t.area > 0]
        pieces = list(tris)
        merged = True
        while merged:
            merged = False
            # largest first: big convex pieces absorb their small neighbours
            pieces.sort(key=lambda p: -p.area)
            for i in range(len(pieces)):
                for j in range(i + 1, len(pieces)):
                    a, b = pieces[i], pieces[j]
                    shared = a.boundary.intersection(b.boundary)
                    if shared.length <= 1e-12:
                        continue
                    u = a.union(b)
                    if isinstance(u, Polygon) and not u.interiors and _is_convex(u, tol):
                        pieces[i] = orient(shapely.simplify(u, 0.0), 1.0)
                        pieces.pop(j)
                        merged = True
                        break
                if merged:
                    break
        parts += pieces
    return parts


# ------------------------------------------------------ section properties


def section_properties(geom) -> dict:
    """Area and second moments of a cross-section about its centroid.

    Returns area, centroid, Iuu = ∫v² dA (bending about the u axis, i.e. the
    width axis), Ivv = ∫u² dA, polar Ip = Iuu + Ivv, and the bounding size.
    """
    area = 0.0
    su = sv = 0.0
    suu = svv = 0.0
    for poly in polygons(geom):
        for ring, sign in [(poly.exterior, 1.0)] + [(r, 1.0) for r in poly.interiors]:
            c = np.asarray(ring.coords)
            x0, y0 = c[:-1, 0], c[:-1, 1]
            x1, y1 = c[1:, 0], c[1:, 1]
            cross = x0 * y1 - x1 * y0
            # oriented rings: exterior CCW, holes CW (shapely orient), so plain sums work
            area += sign * cross.sum() / 2
            su += sign * ((x0 + x1) * cross).sum() / 6
            sv += sign * ((y0 + y1) * cross).sum() / 6
            svv += sign * ((x0**2 + x0 * x1 + x1**2) * cross).sum() / 12  # ∫x² dA
            suu += sign * ((y0**2 + y0 * y1 + y1**2) * cross).sum() / 12  # ∫y² dA
    cu, cv = su / area, sv / area
    iuu = suu - area * cv**2
    ivv = svv - area * cu**2
    minx, miny, maxx, maxy = geom.bounds
    return {
        "area": area,
        "centroid": (cu, cv),
        "Iuu": iuu,
        "Ivv": ivv,
        "Ip": iuu + ivv,
        "width": maxx - minx,
        "height": maxy - miny,
    }


def ring_points(geom) -> np.ndarray:
    """Outer boundary of the largest polygon, as an (n, 2) array without the closing point."""
    polys = polygons(geom)
    poly = max(polys, key=lambda p: p.area)
    return np.asarray(poly.exterior.coords)[:-1]
