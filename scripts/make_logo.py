"""Draw the Filaire logo (SVG, light and dark, plus a PNG) from DejaVu Sans Bold outlines.

The dots of the two i are small plugs joined by a cable. Development tool:

    python scripts/make_logo.py docs/images
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.textpath import TextPath

INK, INK_DARK = "#16191D", "#E8EAED"
COPPER = "#C47A3D"
SCALE = 1.0


def _d(path: MPath, dx: float, dy: float, s: float, height: float) -> str:
    out = []
    verts, codes = path.vertices, path.codes
    i = 0
    while i < len(verts):
        c = codes[i]
        x, y = verts[i]
        X, Y = dx + x * s, height - (dy + y * s)
        if c == MPath.MOVETO:
            out.append(f"M{X:.2f},{Y:.2f}")
            i += 1
        elif c == MPath.LINETO:
            out.append(f"L{X:.2f},{Y:.2f}")
            i += 1
        elif c == MPath.CURVE3:
            (x2, y2) = verts[i + 1]
            out.append(f"Q{X:.2f},{Y:.2f} {dx + x2 * s:.2f},{height - (dy + y2 * s):.2f}")
            i += 2
        elif c == MPath.CURVE4:
            (x2, y2), (x3, y3) = verts[i + 1], verts[i + 2]
            out.append(
                f"C{X:.2f},{Y:.2f} {dx + x2 * s:.2f},{height - (dy + y2 * s):.2f} "
                f"{dx + x3 * s:.2f},{height - (dy + y3 * s):.2f}"
            )
            i += 3
        elif c == MPath.CLOSEPOLY:
            out.append("Z")
            i += 1
        else:
            i += 1
    return "".join(out)


def logo(ink: str) -> str:
    from matplotlib.font_manager import findfont, get_font

    fp = FontProperties(family="DejaVu Sans", weight="bold")
    word = "F\u0131la\u0131re"  # dotless i: the dots are drawn as plugs
    font = get_font(findfont(fp))
    font.set_size(100, 72)
    pen, glyphs, xs = 0.0, [], []
    for ch in word:
        glyphs.append((pen, TextPath((0, 0), ch, size=100, prop=fp)))
        adv = font.load_char(ord(ch)).linearHoriAdvance / 65536
        if ch == "\u0131":
            ext = glyphs[-1][1].get_extents()
            xs.append(pen + (ext.x0 + ext.x1) / 2)
        pen += adv
    pad = 24
    s = SCALE
    x0 = min(g.get_extents().x0 + p for p, g in glyphs)
    x1 = max(g.get_extents().x1 + p for p, g in glyphs)
    width = (x1 - x0) * s + 2 * pad
    height = 172.0
    base = 30.0  # baseline height from the bottom
    dx, dy = pad - x0 * s, base
    xs = [dx + x * s for x in xs]
    top = height - (dy + 76 * s)  # just above the x-height
    plug_w, plug_h = 15.0, 18.0
    parts = [f'<path fill="{ink}" d="{"".join(_d(g, dx + p * s, dy, s, height) for p, g in glyphs)}"/>']
    # cable between the two plugs, arching over "la"
    (x1, x2) = xs
    y0 = top - plug_h - 4
    parts.append(
        f'<path fill="none" stroke="{COPPER}" stroke-width="5" stroke-linecap="round" '
        f'd="M{x1:.2f},{y0:.2f} C{x1:.2f},{y0 - 34:.2f} {x2:.2f},{y0 - 34:.2f} {x2:.2f},{y0:.2f}"/>'
    )
    for x in xs:
        parts.append(
            f'<rect x="{x - plug_w / 2:.2f}" y="{top - plug_h - 4:.2f}" width="{plug_w}" height="{plug_h}" '
            f'rx="3" fill="{COPPER}"/>'
        )
        for px in (-3.5, 3.5):  # the pins
            parts.append(
                f'<rect x="{x + px - 1.5:.2f}" y="{top - 4:.2f}" width="3" height="7" fill="{COPPER}"/>'
            )
    w = int(np.ceil(width))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {int(height)}" width="{w}" '
        f'height="{int(height)}" role="img" aria-label="Filaire"><title>Filaire</title>'
        + "".join(parts)
        + "</svg>\n"
    )


def main(out: str = "docs/images"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "logo.svg").write_text(logo(INK), encoding="utf-8")
    (out / "logo-dark.svg").write_text(logo(INK_DARK), encoding="utf-8")
    # PNG for the social preview, through matplotlib's SVG-free path: rasterise with cairosvg if present
    try:
        import cairosvg

        cairosvg.svg2png(url=str(out / "logo.svg"), write_to=str(out / "logo.png"), output_height=300)
    except ImportError:
        print("cairosvg not installed: logo.png not written", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
