"""Generation of a set of cables from a preset, and of the matching fixed receptacles."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .cable import Cable, build_cable
from .catalog import PRESETS, end_connector
from .centerline import LAYOUTS
from .connectors import CONNECTORS

# independent random streams per cable, one per aspect: turning a variation off
# leaves the draws of the other aspects unchanged
_STREAMS = {"length": 0, "layout": 1, "shape": 2, "ends": 3, "color": 4, "stiffness": 5, "density": 6}


@dataclass
class Variations:
    """Which aspects vary from one cable to the next (all on by default)."""

    length: bool = True  # nominal length drawn, actual length around it (off: first length, exact)
    layout: bool = True  # layout drawn from the preset (off: first layout)
    ends: bool = True  # end variants drawn (off: the first variant of each end)
    color: bool = True  # jacket colour drawn (off: first colour)
    stiffness: bool = True  # Young's modulus drawn in the preset's range (off: middle)
    density: bool = True  # linear density drawn in the range (off: middle)


@dataclass
class Scene:
    preset_key: str
    preset: dict
    cables: list
    seed: int
    variations: Variations = field(default_factory=Variations)

    @property
    def connectors(self) -> list[str]:
        """Connector families used by the cables' ends (every authored variant)."""
        out = []
        for c in self.cables:
            for side in c.ends.values():
                for variant in side:
                    key, _ = end_connector(variant)
                    if key and key not in out:
                        out.append(key)
        return out


def _rng(seed: int, index: int, stream: str) -> np.random.Generator:
    return np.random.default_rng([seed, index, _STREAMS[stream]])


def _weighted(rng, weights: dict):
    keys = list(weights)
    p = np.asarray([weights[k] for k in keys], float)
    return keys[int(rng.choice(len(keys), p=p / p.sum()))]


DEFAULT_LENGTH = 1.0  # m


def end_variants(preset_key: str, end: str, forced: str | None = None) -> list[str]:
    """Variants authored for one end: the preset's, a forced one, then cut and stripped."""
    out = list(PRESETS[preset_key]["ends"][end])
    for v in (forced, "cut", "stripped"):
        if v is not None and v not in out:
            out.append(v)
    return out


def make_cable(
    preset_key: str,
    index: int,
    seed: int,
    var: Variations,
    layout: str | None = None,
    ends: dict | None = None,
    length: float | None = DEFAULT_LENGTH,
    max_segments: int = 400,
    color: str | None = None,
    youngs_modulus: float | None = None,
) -> Cable:
    """One cable. length in m (None: drawn from the preset's retail lengths), modulus in MPa."""
    pr = PRESETS[preset_key]
    lengths = pr["lengths"]
    if length is not None:
        if length <= 0:
            raise ValueError(f"length must be positive, got {length}")
        nominal = actual = float(length)
    elif var.length:
        rng = _rng(seed, index, "length")
        nominal = float(_weighted(rng, lengths))
        k = 1.0 + pr["tolerance"] * float(np.clip(rng.standard_normal(), -2.5, 2.5))
        actual = nominal * k
    else:
        nominal = actual = float(next(iter(lengths)))

    if layout is None:
        layout = (
            _weighted(_rng(seed, index, "layout"), pr["layouts"]) if var.layout else next(iter(pr["layouts"]))
        )
    elif layout not in LAYOUTS:
        raise ValueError(f"unknown layout {layout!r}; choose from {', '.join(LAYOUTS)}")

    selected, options = {}, {}
    rng_ends = _rng(seed, index, "ends")
    for end in ("a", "b"):
        forced = (ends or {}).get(end)
        if forced is not None:
            check_end_variant(forced)
        options[end] = end_variants(preset_key, end, forced)
        drawn = pr["ends"][end]
        pick = _weighted(rng_ends, drawn) if var.ends else next(iter(drawn))  # always drawn: same stream
        selected[end] = forced if forced is not None else pick

    if color is None:
        color = (
            pr["colors"][int(_rng(seed, index, "color").integers(len(pr["colors"])))]
            if var.color
            else pr["colors"][0]
        )
    e_lo, e_hi = pr["youngs_modulus"]
    if youngs_modulus is not None:
        E = float(youngs_modulus)
    else:
        E = _rng(seed, index, "stiffness").uniform(e_lo, e_hi) if var.stiffness else (e_lo + e_hi) / 2
    d_lo, d_hi = pr["linear_density"]
    rho = _rng(seed, index, "density").uniform(d_lo, d_hi) if var.density else (d_lo + d_hi) / 2

    return build_cable(
        name=f"{preset_key}_{index:03d}",
        preset_key=preset_key,
        index=index,
        length=actual,
        nominal_length=nominal,
        layout=layout,
        color=color,
        youngs_modulus=E * 1e6,
        linear_density=rho * 1e-3,
        selected=selected,
        end_options=options,
        rng_layout=_rng(seed, index, "shape"),
        max_segments=max_segments,
    )


def all_end_variants() -> list[str]:
    """Every end variant Filaire can build: plugs, receptacles on a cable, cut, stripped."""
    out = []
    for key, spec in CONNECTORS.items():
        out.append(f"{key}_plug")
        if spec.inline is not None:
            out.append(f"{key}_inline")
    return out + ["cut", "stripped"]


def check_end_variant(variant: str) -> str:
    if variant not in all_end_variants():
        raise ValueError(f"unknown end {variant!r}; choose from {', '.join(all_end_variants())}")
    return variant


def _footprint(c: Cable) -> tuple[np.ndarray, np.ndarray]:
    pts = [s.center for s in c.segments]
    for end in c.ends.values():
        for e in end.values():
            pts.append(e.origin)
    pts = np.asarray(pts)
    m = 0.06
    return pts.min(0)[:2] - m, pts.max(0)[:2] + m


def _layout_rows(cables: list[Cable], row_width: float = 3.0) -> None:
    """Place the cables side by side in rows on the ground, without overlap."""
    x = y = row_h = 0.0
    for c in cables:
        lo, hi = _footprint(c)
        w, h = hi - lo
        if x > 0 and x + w > max(row_width, w):
            x, y, row_h = 0.0, y - row_h, 0.0
        c.position = (float(x - lo[0]), float(y - hi[1]), 0.0)
        x += w
        row_h = max(row_h, h)


def generate_scene(
    preset_key: str,
    count: int = 8,
    seed: int = 1,
    variations: Variations | None = None,
    layout: str | None = None,
    ends: dict | None = None,
    length: float | None = DEFAULT_LENGTH,
    max_segments: int = 400,
    color: str | None = None,
    youngs_modulus: float | None = None,
) -> Scene:
    """count cables of a preset, laid out side by side.

    length: m, 1 m by default; None draws the preset's retail lengths.
    ends: {"a": variant, "b": variant}, each end independently; any variant of
    `all_end_variants()`, not only the preset's.
    """
    if preset_key not in PRESETS:
        raise ValueError(f"unknown preset {preset_key!r}; choose from {', '.join(PRESETS)}")
    var = variations or Variations()
    cables = [
        make_cable(preset_key, i, seed, var, layout, ends, length, max_segments, color, youngs_modulus)
        for i in range(count)
    ]
    _layout_rows(cables)
    return Scene(preset_key, PRESETS[preset_key], cables, seed, var)


# ------------------------------------------------------------------ outputs


def cable_row(c: Cable) -> dict:
    k = c.joint_stiffness
    row = {
        "name": c.name,
        "layout": c.layout,
        "nominal_length_m": round(c.nominal_length, 3),
        "length_m": round(c.length, 4),
        "color": c.color,
        "jacket": c.jacket,
        "end_a": c.selected["a"],
        "end_b": c.selected["b"],
        "youngs_modulus_mpa": round(c.youngs_modulus / 1e6, 2),
        "linear_density_g_per_m": round(c.linear_density * 1e3, 2),
        "bending_stiffness_y_nm2": f"{c.bending_stiffness[0]:.4g}",
        "bending_stiffness_z_nm2": f"{c.bending_stiffness[1]:.4g}",
        "torsional_stiffness_nm2": f"{c.torsional_stiffness:.4g}",
        "axial_stiffness_n_per_m": f"{c.axial_stiffness:.4g}" if c.axial_stiffness else "",
        "segments": len(c.segments),
        "segment_length_mm": round(c.segment_length * 1e3, 2),
        "joint_bend_y_nm_per_rad": f"{k['bend_y']:.4g}",
        "cable_mass_g": round(c.mass * 1e3, 2),
        "end_a_mass_g": round(c.end_mass("a") * 1e3, 2),
        "end_b_mass_g": round(c.end_mass("b") * 1e3, 2),
    }
    if c.coil:
        row["coil_turns"] = round(c.coil["turns"], 1)
        row["wire_length_m"] = round(c.coil["wire_length"], 3)
    return row


def summarize(scene: Scene) -> dict:
    cs = scene.cables
    masses = np.array([c.mass + c.end_mass("a") + c.end_mass("b") for c in cs])
    ei = np.array([c.bending_stiffness[0] for c in cs])
    return {
        "preset": scene.preset_key,
        "label": scene.preset["label"],
        "count": len(cs),
        "seed": scene.seed,
        "variations": asdict(scene.variations),
        "layouts": dict(Counter(c.layout for c in cs)),
        "end_a": dict(Counter(c.selected["a"] for c in cs)),
        "end_b": dict(Counter(c.selected["b"] for c in cs)),
        "colors": dict(Counter(c.color for c in cs)),
        "length_m": {
            "min": round(float(min(c.length for c in cs)), 3),
            "max": round(float(max(c.length for c in cs)), 3),
        },
        "mass_g": {"min": round(float(masses.min()) * 1e3, 1), "max": round(float(masses.max()) * 1e3, 1)},
        "bending_stiffness_nm2": {"min": float(f"{ei.min():.4g}"), "max": float(f"{ei.max():.4g}")},
        "segments": {"min": min(len(c.segments) for c in cs), "max": max(len(c.segments) for c in cs)},
        "connectors": scene.connectors,
    }


def write_outputs(scene: Scene, out_root: str | Path = "output", physics: bool = True) -> Path:
    """Write the OpenUSD files, cables.csv and summary.json under out_root/<preset>.

    physics=False writes visual assets only: no rigid bodies, colliders, joints, physics
    materials, physics scene or ground (the cables keep their filaire:* attributes)."""
    from .usd_export import export_cables, export_sockets

    out = Path(out_root) / scene.preset_key
    out.mkdir(parents=True, exist_ok=True)
    export_cables(out / f"filaire_{scene.preset_key}.usdc", scene, physics=physics)
    if scene.connectors:
        export_sockets(out / "sockets.usdc", scene.connectors, physics=physics)
    rows = [cable_row(c) for c in scene.cables]
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out / "cables.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    (out / "summary.json").write_text(
        json.dumps(summarize(scene), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out
