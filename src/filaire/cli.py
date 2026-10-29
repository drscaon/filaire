"""Command-line interface.

filaire list
filaire ends
filaire generate --preset usb_c [--count 6] [--seed 1] [--length 1 | --length preset]
                 [--end-a usb_c_plug] [--end-b stripped] [--layout straight|slack|coil]
                 [--color "#1c1c1c"] [--modulus 60] [--max-segments 400]
                 [--no-vary-layout] [--no-vary-ends] [--no-vary-color] [--no-vary-stiffness]
                 [--no-vary-density] [--out output]
filaire preview output/usb_c
filaire connectors [--out connectors.png]
filaire sim-test output/usb_c [--cables 2] [--seconds 3]
filaire blender-test output/usb_c [--cables 1] [--mode setup|naive] [--blender /path/to/blender]
filaire blender-addon [--out filaire_physics.zip]
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from . import __version__
from .catalog import CATEGORIES, JACKETS, PRESETS
from .centerline import LAYOUTS
from .connectors import CONNECTORS, keying_of
from .generator import DEFAULT_LENGTH, Variations, all_end_variants, generate_scene, summarize, write_outputs

VARIATION_HELP = {
    "length": "with --length preset: retail length drawn, ± tolerance (off: first length, exact)",
    "layout": "layout drawn from the preset (off: first layout)",
    "ends": "end variants drawn from the preset (off: first variant of each end)",
    "color": "jacket colour drawn (off: first colour)",
    "stiffness": "Young's modulus drawn in the preset's range (off: middle)",
    "density": "linear density drawn in the preset's range (off: middle)",
}


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be positive, got {value}")
    return value


def _length(text: str):
    if text.strip().lower() == "preset":
        return None
    try:
        return _positive_float(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"a length in metres or 'preset', got {text!r}") from e


def _end(text: str) -> str:
    if text not in all_end_variants():
        raise argparse.ArgumentTypeError(f"unknown end {text!r}; see `filaire ends`")
    return text


def _color(text: str) -> str:
    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", text):
        raise argparse.ArgumentTypeError(f"a hex colour such as #1c1c1c, got {text!r}")
    return "#" + text.lstrip("#").lower()


def _cmd_list(_args) -> int:
    for cat in CATEGORIES:
        print(cat)
        for k, p in PRESETS.items():
            if p["category"] != cat:
                continue
            ends = " | ".join(" / ".join(p["ends"][e]) for e in ("a", "b"))
            print(f"  {k:<15} {p['label']:<45} {ends}")
    print("Jackets")
    for k, j in JACKETS.items():
        print(f"  {k:<15} {j['label']:<8} friction {j['friction']}")
    return 0


def _cmd_ends(_args) -> int:
    print("Connector ends (any of them can go on either end of any cable):")
    for key, spec in CONNECTORS.items():
        inline = f"{key}_inline ({spec.inline_name})" if spec.inline else ""
        print(f"  {key + '_plug':<16} {spec.plug_name:<24} {spec.gender:<6} {keying_of(spec):<10} {inline}")
    print("Other ends:")
    print("  cut              clean cut")
    print("  stripped         jacket removed, cores out with bare copper tips")
    return 0


def _cmd_generate(args) -> int:
    var = Variations(**{k: getattr(args, f"vary_{k}") for k in VARIATION_HELP})
    ends = {k: v for k, v in (("a", args.end_a), ("b", args.end_b)) if v}
    scene = generate_scene(
        args.preset,
        args.count,
        args.seed,
        var,
        layout=args.layout,
        ends=ends,
        length=args.length,
        max_segments=args.max_segments,
        color=args.color,
        youngs_modulus=args.modulus,
    )
    out = write_outputs(scene, args.out, physics=args.physics)
    print(json.dumps(summarize(scene), indent=2, ensure_ascii=False))
    print(f"written to {out}")
    return 0


def _cmd_preview(args) -> int:
    from . import render

    for folder in args.folders:
        print(render.sheet(folder))
    return 0


def _cmd_connectors(args) -> int:
    from . import render

    print(render.connectors_sheet(args.out))
    return 0


def _cmd_sim_test(args) -> int:
    try:
        import mujoco  # noqa: F401
    except ImportError:
        print("the simulation test needs MuJoCo: pip install 'filaire[sim]'", file=sys.stderr)
        return 2
    from .sim.checks import run_folder

    report = run_folder(args.folder, cables=args.cables, seconds=args.seconds, out=args.out)
    return 0 if report["passed"] else 1


def _cmd_blender_test(args) -> int:
    from .blender.checks import blender_test

    try:
        report = blender_test(args.folder, args.cables, args.seconds, args.mode, args.blender)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{report['passed']}/{report['total']} passed (Blender, {args.mode})")
    if args.mode == "naive":
        return 0  # a comparison: rigid bodies set by hand are expected to come apart
    return 0 if report["passed"] == report["total"] else 1


def _cmd_blender_addon(args) -> int:
    from .blender import write_addon

    path = write_addon(args.out)
    print(path)
    print("Blender 4.4+: Edit > Preferences > Get Extensions > Install from Disk, then File > Import > USD")
    print("or run it without installing: blender -b -P <the .py> -- file.usdc")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="filaire",
        description="Standard cable assets generator for Physical AI, exporting to OpenUSD.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list cable presets and jackets").set_defaults(func=_cmd_list)
    sub.add_parser("ends", help="list the end variants (connectors, cut, stripped)").set_defaults(
        func=_cmd_ends
    )

    g = sub.add_parser("generate", help="generate cables and an OpenUSD scene")
    g.add_argument("--preset", default="usb_c", choices=sorted(PRESETS))
    g.add_argument("--count", type=_positive_int, default=6, help="number of cables (default: 6)")
    g.add_argument("--seed", type=int, default=1, help="random seed (default: 1)")
    g.add_argument(
        "--length",
        type=_length,
        default=DEFAULT_LENGTH,
        help="cable length in m (default: 1); 'preset' draws the preset's retail lengths",
    )
    g.add_argument("--end-a", type=_end, default=None, help="end A of every cable (default: preset's draw)")
    g.add_argument("--end-b", type=_end, default=None, help="end B of every cable, independent of end A")
    g.add_argument(
        "--layout", choices=LAYOUTS, default=None, help="how the cables lie (default: preset's draw)"
    )
    g.add_argument("--color", type=_color, default=None, help="jacket colour for every cable, e.g. #1c1c1c")
    g.add_argument("--modulus", type=_positive_float, default=None, help="effective Young's modulus in MPa")
    g.add_argument(
        "--max-segments",
        type=_positive_int,
        default=400,
        help="maximum rigid segments per cable (default: 400)",
    )
    g.add_argument("--out", default="output", help="output root folder (default: output)")
    g.add_argument(
        "--no-physics",
        dest="physics",
        action="store_false",
        help="visual assets only: no rigid bodies, colliders, joints, physics scene or ground",
    )
    for name, text in VARIATION_HELP.items():
        g.add_argument(
            f"--vary-{name}",
            dest=f"vary_{name}",
            action=argparse.BooleanOptionalAction,
            default=True,
            help=text,
        )
    g.set_defaults(func=_cmd_generate)

    p = sub.add_parser("preview", help="top view of generated cables (needs matplotlib)")
    p.add_argument("folders", nargs="+")
    p.set_defaults(func=_cmd_preview)

    c = sub.add_parser("connectors", help="sheet of every plug face and its receptacle (needs matplotlib)")
    c.add_argument("--out", default="connectors.png")
    c.set_defaults(func=_cmd_connectors)

    s = sub.add_parser("sim-test", help="check the generated assets in MuJoCo (needs mujoco)")
    s.add_argument("folder", help="a generated folder, output/<preset>")
    s.add_argument(
        "--cables", type=_positive_int, default=2, help="cables dropped on the ground (default: 2)"
    )
    s.add_argument(
        "--seconds", type=_positive_float, default=3.0, help="simulated time of the drop (default: 3)"
    )
    s.add_argument("--out", default=None, help="report folder (default: <folder>/sim_test)")
    s.set_defaults(func=_cmd_sim_test)

    b = sub.add_parser(
        "blender-test", help="the drop check in Blender, through the add-on (needs bpy or Blender)"
    )
    b.add_argument("folder", help="a generated folder, output/<preset>")
    b.add_argument("--cables", type=_positive_int, default=1, help="cables dropped (default: 1)")
    b.add_argument("--seconds", type=_positive_float, default=1.5, help="simulated time (default: 1.5)")
    b.add_argument(
        "--mode",
        choices=("setup", "naive"),
        default="setup",
        help="setup: imported through the add-on (default); naive: every mesh a rigid body by hand",
    )
    b.add_argument("--blender", default=None, help="Blender executable (default: the bpy module, then PATH)")
    b.set_defaults(func=_cmd_blender_test)

    a = sub.add_parser("blender-addon", help="write the Blender add-on (physics set up on USD import)")
    a.add_argument("--out", default="filaire_physics.zip", help=".zip (extension) or .py (add-on or script)")
    a.set_defaults(func=_cmd_blender_addon)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
