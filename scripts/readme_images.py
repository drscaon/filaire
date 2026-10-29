"""Build the README images: hero render of every preset, a labelled sheet of every
preset and of every connector family (the plug on its cable in front of its
receptacle), connector faces, and the GitHub social preview.

The cables are written without physics (`physics=False`): one mesh per cable,
lighter to import, the same look.

Development tool, not part of the package. Needs the dev extras, Pillow and
Blender as a Python module (`pip install bpy`, Python 3.13):

    python scripts/readme_images.py [--samples 96] [--out docs/images]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from filaire import PRESETS, Variations, generate_scene, render, write_outputs
from filaire.connectors import CONNECTORS
from filaire.usd_export import export_sockets, socket_layout

HERE = Path(__file__).resolve().parent
BLENDER = [sys.executable, str(HERE / "render_blender.py")]

# a cable for each connector family, to show the plug on (the end B of a short straight piece)
PLUG_CABLE = {
    "usb_c": "usb_c",
    "usb_a": "usb_a_to_c",
    "usb_micro": "usb_micro",
    "hdmi_a": "hdmi",
    "rj45": "ethernet",
    "rj9": "coiled_handset",
    "jack35": "audio_jack",
    "c13": "power_c13",
    "c7": "power_c7",
    "cee77": "power_c13",
    "cee716": "power_c7",
    "dc5521": "dc_barrel",
    "dc5525": "dc_barrel",
    "dc4017": "dc_barrel",
    "xlr3": "xlr_mic",
    "m12a": "m12_sensor",
    "idc10": "ribbon_idc",
}
# how each preset is shown: length (m), layout
SHOW = {"coiled_handset": (0.25, "straight"), "ribbon_idc": (0.25, "straight")}
SEEDS = {"usb_c": 3, "power_c13": 5, "hdmi": 7, "audio_jack": 4, "ethernet": 2}


def _preset_scene(key: str, length: float = 0.4, seed: int | None = None):
    """One cable of a preset, with the preset's first end variants (its typical cable)."""
    length, layout = SHOW.get(key, (length, "slack"))
    return generate_scene(
        key,
        count=1,
        seed=seed or SEEDS.get(key, 1),
        layout=layout,
        length=length,
        variations=Variations(ends=False),
    )


def _bbox(usd: Path) -> tuple[np.ndarray, np.ndarray]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(usd))
    box = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]).ComputeWorldBound(
        stage.GetPrimAtPath("/World/Cables")
    )
    r = box.ComputeAlignedRange()
    return np.array(r.GetMin()), np.array(r.GetMax())


def _camera_for(lo, hi, direction=(0.25, -0.8, 0.75), lens=50.0, aspect=4 / 3, fill=1.15):
    """Camera (position, target) framing a box from the given direction, for a lens and aspect."""
    c = (lo + hi) / 2
    size = max(hi[0] - lo[0], (hi[1] - lo[1]) * aspect, 0.05)
    d = size * fill / 2 / (18.0 / lens)  # 36 mm sensor width: tan(half fov) = 18 / lens
    v = np.asarray(direction, float)
    v /= np.linalg.norm(v)
    return (*(c + d * v), *c)


def blender(*args, samples: int = 96):
    env = {**os.environ, "SAMPLES": str(samples)}
    subprocess.run([*BLENDER, *map(str, args)], check=True, stdout=subprocess.DEVNULL, env=env)


def hero(tmp: Path, out: Path, samples: int, size=(1600, 900)):
    """Every preset: one cable each, in two columns, seen from above at an angle."""
    keys = list(PRESETS)
    args, cells = [], []
    for k, key in enumerate(keys):
        folder = write_outputs(_preset_scene(key, 0.62), tmp / "hero", physics=False)
        usd = folder / f"filaire_{key}.usdc"
        lo, hi = _bbox(usd)
        col, row = divmod(k, (len(keys) + 1) // 2)
        cx, cy = 0.78 * col, -0.15 * row  # cell centre
        d = np.array([cx, cy, 0]) - (lo + hi) / 2
        args += [usd, d[0], d[1], 0, 0]
        cells.append((lo + d, hi + d))
    lo = np.min([c[0] for c in cells], axis=0)
    hi = np.max([c[1] for c in cells], axis=0)
    cam = _camera_for(lo, hi, direction=(0.0, -0.75, 1.0), lens=40, aspect=size[0] / size[1], fill=1.05)
    blender("hero", out, *size, *cam, 40, *args, samples=samples)


def _tile(tmp: Path, name: str, args: list, cam, samples: int, size=(640, 480)) -> Path:
    out = tmp / "tiles" / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    blender("hero", out, *size, *cam[0], cam[1], *args, samples=samples)
    return out


def preset_tiles(tmp: Path, samples: int) -> list[tuple[Path, str]]:
    tiles = []
    for key in PRESETS:
        folder = write_outputs(_preset_scene(key), tmp / "presets", physics=False)
        usd = folder / f"filaire_{key}.usdc"
        lo, hi = _bbox(usd)
        cam = _camera_for(lo, hi, direction=(0.2, -0.7, 0.8), fill=1.15)
        tiles.append((_tile(tmp, f"preset_{key}", [usd, 0, 0, 0, 0], (cam, 50), samples), key))
    return tiles


def connector_tiles(tmp: Path, samples: int) -> list[tuple[Path, str]]:
    """Each plug on a short straight cable, 15 mm in front of its fixed receptacle."""
    tiles = []
    rot = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])  # +90° about z: the cable's +x becomes +y
    for key, spec in CONNECTORS.items():
        sock = export_sockets(tmp / "connectors" / f"socket_{key}.usdc", [key], physics=False)
        _, _R, s_origin = socket_layout([key])[0]
        scene = generate_scene(
            PLUG_CABLE[key],
            count=1,
            seed=2,
            layout="straight",
            length=0.12,
            ends={"a": "cut", "b": f"{key}_plug"},
        )
        c = scene.cables[0]
        plug_mate = rot @ (c.ends["b"][f"{key}_plug"].origin + np.asarray(c.position))
        folder = write_outputs(scene, tmp / "connectors" / key, physics=False)
        h = float(plug_mate[2])
        gap = 0.015
        d_cable = np.array([0.0, -gap, h]) - plug_mate
        d_sock = np.array([0.0, 0.0, h]) - s_origin
        w = max(
            spec.panel[1].bounds[2] - spec.panel[1].bounds[0],
            spec.panel[1].bounds[3] - spec.panel[1].bounds[1],
        )
        w *= 1e-3
        target = np.array([0.0, -gap * 0.8, h])
        dist = 2.6 * w + 0.03
        v = np.array([0.62, -0.72, 0.42])
        v /= np.linalg.norm(v)
        cam = (*(target + dist * v), *target)
        args = [folder / f"filaire_{PLUG_CABLE[key]}.usdc", *d_cable, 90, sock, *d_sock, 0]
        label = f"{spec.plug_name}  →  {spec.panel_name}"
        tiles.append((_tile(tmp, f"connector_{key}", args, (cam, 50), samples), label))
    return tiles


def sheet(tiles: list[tuple[Path, str]], out: Path, columns: int = 4, font_size: int = 22):
    """Tiles in a grid, each with its label under it."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = Image.open(tiles[0][0]).size
    band = font_size * 2
    rows = (len(tiles) + columns - 1) // columns
    img = Image.new("RGB", (columns * w, rows * (h + band)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    for i, (path, label) in enumerate(tiles):
        r, c = divmod(i, columns)
        x, y = c * w, r * (h + band)
        img.paste(Image.open(path).convert("RGB"), (x, y))
        tw = d.textlength(label, font=font)
        d.text((x + (w - tw) / 2, y + h + band / 2 - font_size / 2 - 2), label, fill=(22, 25, 29), font=font)
    img.save(out, quality=88)


SOCIAL = [
    # preset, options: short cables close to the camera, connectors in view
    ("power_c13", dict(seed=5, ends={"a": "c13_plug", "b": "cee77_plug"})),
    ("ethernet", dict(seed=2, color="#2a6fbf", ends={"b": "rj45_plug"})),
    ("usb_c", dict(seed=3, color="#f0f0ee", ends={"b": "usb_c_plug"})),
    ("audio_jack", dict(seed=4, color="#c0392b", ends={"b": "jack35_plug"})),
    ("m12_sensor", dict(seed=2, color="#e88a2a", ends={"b": "stripped"})),
    ("hdmi", dict(seed=7, ends={"b": "hdmi_a_plug"})),
]


def social_render(tmp: Path, out: Path, samples: int, size=(2560, 900)):
    """Six short cables in two columns, seen from above, for the social preview."""
    args = []
    for k, (preset, opts) in enumerate(SOCIAL):
        scene = generate_scene(preset, count=1, layout="slack", length=0.55, **opts)
        folder = write_outputs(scene, tmp / "social", physics=False)
        col, row = divmod(k, 3)  # two columns of three
        args += [folder / f"filaire_{preset}.usdc", 0.64 * col - 0.02, 0.16 * row + 0.12, 0, 0]
    cam = (0.62, -0.18, 1.2, 0.62, 0.2, 0.0)
    blender("hero", out, *size, *cam, 31, *args, samples=samples)


def social(hero_png: Path, logo_png: Path, out: Path):
    from PIL import Image, ImageDraw, ImageFont

    W, H, band_h = 1280, 640, 190
    img = Image.open(hero_png).convert("RGB")
    top_h = H - band_h  # the render fills the top, the band holds logo and tagline below it
    s = max(W / img.width, top_h / img.height)
    img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - top_h) // 2
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    canvas.paste(img.crop((left, top, left + W, top + top_h)), (0, 0))
    img = canvas
    logo = Image.open(logo_png).convert("RGBA")
    k = 92 / logo.height
    logo = logo.resize((int(logo.width * k), 92), Image.LANCZOS)
    img.paste(logo, (56, H - 172), logo)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    d.text(
        (62, H - 66),
        "Standard cable assets generator for Physical AI · OpenUSD · MuJoCo",
        fill=(22, 25, 29),
        font=font,
    )
    img.save(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--tile-samples", type=int, default=48)
    ap.add_argument("--out", default="docs/images")
    ap.add_argument("--only", default="hero,presets,plugs,connectors,social")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(","))
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if "hero" in only:
            hero(tmp, out / "hero.jpg", args.samples)
        if "presets" in only:
            sheet(preset_tiles(tmp, args.tile_samples), out / "presets.jpg")
        if "plugs" in only:
            sheet(connector_tiles(tmp, args.tile_samples), out / "plugs.jpg", font_size=19)
        if "social" in only:
            social_render(tmp, tmp / "social.png", args.samples)
            social(tmp / "social.png", out / "logo.png", out / "social_preview.png")
    if "connectors" in only:
        render.connectors_sheet(out / "connectors.png")


if __name__ == "__main__":
    main()
