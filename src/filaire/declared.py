"""What every cable draws, declared once: the tables of docs/variation.md are written from this
module and from the presets (catalog.PRESETS), and tests/test_distributions.py checks that the
generator follows them.

Every drawn value of a cable follows one rule, applied to its preset's own numbers:

* ("weights", field): one of the keys of the preset's field, with the field's values as weights;
* ("pick", field): one of the items of the preset's list, each as likely;
* ("uniform", field, scale): uniform between the two numbers of the preset's field, times scale;
* ("tolerance",): the nominal length times 1 + tolerance × e, e a normal draw kept within ±2.5;
* ("opening",): a receptacle's opening, width and height each uniform over the tolerance its source
  publishes (connectors.py, docs/sources.md), not a preset's field.

Each row is (column, aspect, rule, note); a dotted field is a field of a field (ends.a).
"""

from __future__ import annotations

from .catalog import PRESETS

CLIP = 2.5  # the length's normal draw is kept within ±2.5 standard deviations

DECLARED = [
    (
        "nominal_length_m",
        "length",
        ("weights", "lengths"),
        "with `--length preset`; else the length given (1 m)",
    ),
    ("length_m", "length", ("tolerance",), "with `--length preset`; else the length given, exact"),
    ("layout", "layout", ("weights", "layouts"), ""),
    ("end_a", "ends", ("weights", "ends.a"), ""),
    ("end_b", "ends", ("weights", "ends.b"), ""),
    ("color", "color", ("pick", "colors"), ""),
    ("youngs_modulus_pa", "stiffness", ("uniform", "youngs_modulus", 1e6), "the preset gives MPa"),
    ("linear_density_kg_per_m", "density", ("uniform", "linear_density", 1e-3), "the preset gives g/m"),
    (
        "coil_leads_m",
        "length",
        ("uniform", "coil.leads", 1e-3),
        "coiled cords only, one per end, in mm in the preset; recorded as built: rounded to whole segments",
    ),
    (
        "end_a_opening_m",
        "clearance",
        ("opening",),
        "width and height of a receptacle on the cable whose opening is published with a tolerance",
    ),
    ("end_b_opening_m", "clearance", ("opening",), "the same at end b (the `usb_c` extension)"),
    ("opening_m", "clearance", ("opening",), "the fixed receptacles of `sockets.usdc` (USB-C, USB-A ports)"),
]


def field(preset: dict, name: str):
    """A preset's field, or a field of a field (``ends.a``); None when the preset has none."""
    value = preset
    for part in name.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def rule_text(rule) -> str:
    kind, *args = rule
    if kind == "weights":
        return f"one of the preset's `{args[0]}`, with its weights"
    if kind == "pick":
        return f"one of the preset's `{args[0]}`, each as likely"
    if kind == "uniform":
        return f"uniform over the preset's `{args[0]}`" + (f", × {args[1]:g}" if args[1] != 1 else "")
    if kind == "tolerance":
        return f"nominal × (1 + `tolerance` × e), e normal, kept within ±{CLIP:g}"
    if kind == "opening":
        return "uniform over the opening's published tolerance, width and height each ([Sources](sources.md))"
    raise ValueError(f"unknown rule {kind!r}")


def _weights(d: dict) -> str:
    total = sum(d.values())
    return ", ".join(f"{k} {100 * v / total:g} %" for k, v in d.items())


def table() -> str:
    """The Markdown of docs/variation.md between its markers: the rules, then the presets' numbers."""
    out = ["### Rules", "", "| Column | Aspect | Drawn as | Note |", "|---|---|---|---|"]
    for column, aspect, rule, note in DECLARED:
        out.append(f"| `variation:{column}` | {aspect} | {rule_text(rule)} | {note} |")
    out += [
        "",
        "### The presets' numbers",
        "",
        "| Preset | `lengths` (m) | `tolerance` | `layouts` | `ends.a` | `ends.b` | `colors` "
        "| `youngs_modulus` (MPa) | `linear_density` (g/m) | `coil.leads` (mm) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, p in PRESETS.items():
        leads = field(p, "coil.leads")
        out.append(
            f"| `{key}` | {_weights(p['lengths'])} | {p['tolerance']:g} | {_weights(p['layouts'])} "
            f"| {_weights(p['ends']['a'])} | {_weights(p['ends']['b'])} | {len(p['colors'])} "
            f"| {p['youngs_modulus'][0]:g} to {p['youngs_modulus'][1]:g} "
            f"| {p['linear_density'][0]:g} to {p['linear_density'][1]:g} "
            f"| {f'{leads[0]:g} to {leads[1]:g}' if leads else ''} |"
        )
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(table())
