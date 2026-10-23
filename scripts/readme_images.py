"""Build the README images: hero render, plugs in front of their receptacles,
connector faces, logo and GitHub social preview.

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

from filaire import generate_scene, render, write_outputs
from filaire.connectors import CONNECTORS
from filaire.usd_export import export_sockets, socket_layout

HERE = Path(__file__).resolve().parent
BLENDER = [sys.executable, str(HERE / "render_blender.py")]

HERO = [
    # preset, options, (dx, dy)
    ("power_c13", dict(seed=5, layout="slack", ends={"b": "cee77_plug"}, length=1.2), (-0.04, 1.16)),
    ("ethernet", dict(seed=2, layout="coil", color="#2a6fbf", length=1.5), (1.14, 1.11)),
    ("hdmi", dict(seed=7, layout="slack"), (-0.05, 0.79)),
    ("usb_c", dict(seed=3, layout="slack", ends={"b": "usb_c_plug"}), (0.75, 0.77)),
    ("audio_jack", dict(seed=4, layout="slack", color="#c0392b"), (-0.06, 0.40)),
    ("m12_sensor", dict(seed=2, layout="slack", ends={"b": "stripped"}, color="#e88a2a"), (0.6, 0.39)),
    ("coiled_handset", dict(seed=1, layout="slack", length=0.35, color="#e9e4d8"), (0.05, 0.02)),
    ("ribbon_idc", dict(seed=1, layout="straight", length=0.35), (0.65, 0.02)),
]

PLUGS = ["usb_c", "usb_a", "hdmi_a", "rj45", "jack35", "c13", "xlr3", "m12a"]
PLUG_CABLE = {
    "usb_c": "usb_c",
    "usb_a": "usb_a_to_c",
    "hdmi_a": "hdmi",
    "rj45": "ethernet",
    "jack35": "audio_jack",
    "c13": "power_c13",
    "xlr3": "xlr_mic",
    "m12a": "m12_sensor",
}


def blender(*args, samples: int = 96):
    env = {**os.environ, "SAMPLES": str(samples)}
    subprocess.run([*BLENDER, *map(str, args)], check=True, stdout=subprocess.DEVNULL, env=env)


def hero(tmp: Path, out: Path, samples: int, size=(1600, 900)):
    args = []
    for preset, opts, (dx, dy) in HERO:
        scene = generate_scene(preset, count=1, **opts)
        folder = write_outputs(scene, tmp / "hero")
        args += [folder / f"filaire_{preset}.usdc", dx, dy, 0, 0]
    cam = (0.7, -0.78, 1.0, 0.68, 0.42, 0.0)
    blender("hero", out, *size, *cam, 32, *args, samples=samples)


def plugs(tmp: Path, out: Path, samples: int):
    """Each plug 2 cm in front of its receptacle, cables running towards the camera."""
    args, x = [], 0.0
    for key in PLUGS:
        spec = CONNECTORS[key]
        sock = export_sockets(tmp / "plugs" / f"socket_{key}.usdc", [key])
        _, _R, s_origin = socket_layout([key])[0]
        width = max(spec.panel[1].bounds[2] - spec.panel[1].bounds[0], 20) * 1e-3
        x += width / 2 + 0.02
        # the socket's mate frame: socket origin + (0, 0, 0) in its frame (front face, insertion +y)
        socket_mate = s_origin
        scene = generate_scene(
            PLUG_CABLE[key],
            count=1,
            seed=2,
            layout="straight",
            length=0.25,
            ends={"a": "cut", "b": f"{key}_plug"},
        )
        c = scene.cables[0]
        end = c.ends["b"][f"{key}_plug"]
        plug_mate = end.origin + np.asarray(c.position)  # cable lies along +x before turning
        folder = write_outputs(scene, tmp / "plugs" / key)
        # turn the cable by +90° about z: +x becomes +y, the plug points into the socket
        rot = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
        pm = rot @ plug_mate
        gap = 0.02
        target = np.array([x, -gap, plug_mate[2]])  # plug mate frame, just in front of the socket
        d_cable = target - pm
        # socket: mate frame at (x, 0, plug height); sunk into the floor if taller than the plug
        d_sock = np.array([x, 0.0, plug_mate[2]]) - socket_mate
        args += [folder / f"filaire_{PLUG_CABLE[key]}.usdc", *d_cable, 90, sock, *d_sock, 0]
        x += width / 2 + 0.02
    mid = x / 2
    cam = (mid + 0.32, -0.36, 0.2, mid + 0.03, 0.0, 0.0)
    blender("hero", out, 1600, 760, *cam, 34, *args, samples=samples)


def social(hero_png: Path, logo_png: Path, out: Path):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1280, 640
    img = Image.open(hero_png).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))
    band = Image.new("RGBA", (W, 190), (255, 255, 255, 228))
    img.paste(band, (0, H - 190), band)
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
    ap.add_argument("--out", default="docs/images")
    ap.add_argument("--only", default="hero,plugs,connectors,social")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(","))
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if "hero" in only:
            hero(tmp, out / "hero.jpg", args.samples)
        if "plugs" in only:
            plugs(tmp, out / "plugs.jpg", args.samples)
    if "connectors" in only:
        render.connectors_sheet(out / "connectors.png")
    if "social" in only:
        social(out / "hero.jpg", out / "logo.png", out / "social_preview.png")


if __name__ == "__main__":
    main()
