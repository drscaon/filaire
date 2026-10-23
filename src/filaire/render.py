"""Previews with matplotlib: top view of generated cables, faces of the connectors."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _rgb(hexcolor: str) -> tuple:
    c = hexcolor.lstrip("#")
    return tuple(int(c[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _world_points(prim, xf_cache) -> np.ndarray:
    from pxr import UsdGeom

    mesh = UsdGeom.Mesh(prim)
    pts = np.asarray(mesh.GetPointsAttr().Get(), float)
    M = np.asarray(xf_cache.GetLocalToWorldTransform(prim), float)
    return pts @ M[:3, :3] + M[3, :3]


def _gamma(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def sheet(folder: str | Path) -> Path:
    """Top view of every cable of a generated folder, read back from its OpenUSD file."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    from pxr import Usd, UsdGeom
    from scipy.spatial import ConvexHull

    folder = Path(folder)
    usd = next(folder.glob("filaire_*.usdc"))
    stage = Usd.Stage.Open(str(usd))
    cache = UsdGeom.XformCache()
    fig, ax = plt.subplots(figsize=(12, 9))
    lo, hi = np.full(2, np.inf), np.full(2, -np.inf)
    for cable in stage.GetPrimAtPath("/World/Cables").GetChildren():
        for prim in Usd.PrimRange(cable):
            if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.guide:
                continue
            xy = _world_points(prim, cache)[:, :2]
            if len(xy) < 3:
                continue
            try:
                hull = xy[ConvexHull(xy).vertices]
            except Exception:  # degenerate (collinear) piece
                continue
            color = UsdGeom.Mesh(prim).GetDisplayColorAttr().Get()
            rgb = _gamma(color[0]) if color else (0.3, 0.3, 0.3)
            ax.add_patch(
                MplPolygon(hull, closed=True, facecolor=rgb, edgecolor=(0, 0, 0, 0.35), linewidth=0.3)
            )
            lo, hi = np.minimum(lo, xy.min(0)), np.maximum(hi, xy.max(0))
        seg0 = cable.GetPrimAtPath("Segments/seg_000")
        p = np.asarray(cache.GetLocalToWorldTransform(seg0), float)[3, :2]
        ax.annotate(cable.GetName(), p, fontsize=7, xytext=(4, 8), textcoords="offset points")
    ax.set_xlim(lo[0] - 0.05, hi[0] + 0.05)
    ax.set_ylim(lo[1] - 0.05, hi[1] + 0.05)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_facecolor("#f4f4f2")
    ax.set_title(f"{usd.stem}: top view")
    out = folder / "sheet.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def connectors_sheet(out: str | Path, keys: list[str] | None = None) -> Path:
    """Faces of each connector family: the plug and the receptacle derived from it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    from . import geometry2d as g2
    from .connectors import CONNECTORS, _cavity, keying_of

    keys = keys or list(CONNECTORS)
    ncol = 4
    nrow = int(np.ceil(len(keys) / ncol))
    fig, axes = plt.subplots(nrow, ncol * 2, figsize=(ncol * 4.2, nrow * 2.3))
    axes = np.atleast_2d(axes)

    def draw(ax, geom, color, edge="#333333"):
        for poly in g2.polygons(geom):
            verts, codes = [], []
            for ring in [poly.exterior, *poly.interiors]:
                c = np.asarray(ring.coords)
                verts += c.tolist()
                codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(c) - 2) + [MplPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor=edge, linewidth=0.6))

    for i, key in enumerate(keys):
        spec = CONNECTORS[key]
        r, c = divmod(i, ncol)
        a_plug, a_rec = axes[r, 2 * c], axes[r, 2 * c + 1]
        outline = spec.panel[1]
        plug_color = _rgb(spec.shell or spec.color)
        # the plug seen from its tip: every mating layer, deepest drawn last
        for layer in sorted(spec.layers, key=lambda la: -la.t0):
            draw(a_plug, layer.region, plug_color)
        # the receptacle seen from the front: its opening, and the pins or tongue deeper inside
        front = max(spec.layers, key=lambda la: la.t1)
        opening = _cavity(front.region, spec.clearance)
        draw(a_rec, outline, (0.9, 0.9, 0.91))
        draw(a_rec, opening, (0.35, 0.35, 0.37))
        for layer in spec.layers:
            if layer is not front:
                inner = outline.difference(_cavity(layer.region, spec.clearance)).intersection(opening)
                draw(a_rec, inner, (0.7, 0.7, 0.72))
        for ax in (a_plug, a_rec):
            minx, miny, maxx, maxy = outline.bounds
            m = 0.08 * max(maxx - minx, maxy - miny)
            ax.set_xlim(minx - m, maxx + m)
            ax.set_ylim(miny - m, maxy + m)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
        a_plug.set_title(f"{spec.plug_name}\n{spec.gender} contacts, depth {spec.depth:g} mm", fontsize=7.5)
        a_rec.set_title(f"{spec.panel_name}\nkeying: {keying_of(spec)}", fontsize=7.5)
    for j in range(len(keys), nrow * ncol):
        r, c = divmod(j, ncol)
        axes[r, 2 * c].axis("off")
        axes[r, 2 * c + 1].axis("off")
    fig.suptitle(
        "Plug faces (left) and the receptacles derived from them (right), to scale per pair", fontsize=10
    )
    fig.tight_layout()
    out = Path(out)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out
