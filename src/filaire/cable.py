"""One cable: cross-section, physical properties, rigid segments, ends.

Physics model (engine-neutral, written to OpenUSD with UsdPhysics):

- the cable is a chain of N rigid segments of length L along its centre
  line; segment frames have x along the cable, y across its width (the
  profile's u axis, horizontal when the cable lies flat) and z = x × y;
- consecutive segments are linked by a joint at their common end point,
  with three rotational springs: twist about x (G·J / L), bending about y
  (E·I_y / L) and about z (E·I_z / L), the discrete form of a Kirchhoff rod;
  the rest shape is straight;
- the springs have a damping of stiffness × `DAMPING_TIME`;
- a coiled cord is modelled along its axis (the coil is in the visual
  mesh only): the springs are those of a helical spring seen as a rod
  (Wahl's close-coiled spring formulas), plus an axial spring per joint that
  lets the coil stretch.

All lengths in metres, masses in kilograms, stiffness in SI units.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import centerline as cl
from . import geometry2d as g2
from .catalog import POISSON, PRESETS, end_connector
from .connectors import CONNECTORS, MM, Part, part_mesh, plug_parts, receptacle_parts
from .mesh3d import TriMesh, mass_properties, merge, sweep

DAMPING_TIME = 0.01  # s: joint damping = stiffness × DAMPING_TIME
UP = np.array([0.0, 0.0, 1.0])
COPPER = "#c47a3d"
STRIP_INSULATION = 0.012  # m of insulated core out of the jacket
STRIP_COPPER = 0.006  # m of bare copper after it


# ------------------------------------------------------------- cross-section


def profile_region(profile: tuple):
    """Cross-section in metres: x across the width, y across the height."""
    kind = profile[0]
    if kind == "round":
        return g2.circle(profile[1] * MM)
    if kind == "figure8":
        d = profile[1] * MM
        return g2.union(g2.circle(d, -d / 2), g2.circle(d, d / 2), g2.rect(d, 0.55 * d))
    if kind == "flat":
        n, pitch, t = profile[1:]
        return g2.stadium(n * pitch * MM, t * MM)
    raise ValueError(f"unknown profile {kind!r}")


def section(profile: tuple) -> dict:
    """Area, second moments and torsion constant of the cross-section (m², m⁴)."""
    region = profile_region(profile)
    s = g2.section_properties(region)
    kind = profile[0]
    if kind == "round":
        r = profile[1] * MM / 2
        j = math.pi * r**4 / 2
    elif kind == "figure8":
        r = profile[1] * MM / 2
        j = 2 * math.pi * r**4 / 2  # two cores twisting side by side, order of magnitude
    else:
        b, t = s["width"], s["height"]
        j = b * t**3 / 3 * (1 - 0.63 * t / b)  # thin rectangle (Roark)
    return {
        "area": s["area"],
        "Iy": s["Iuu"],  # bending about the width axis (the soft axis of a flat cable)
        "Iz": s["Ivv"],
        "J": j,
        "width": s["width"],
        "height": s["height"],
    }


def _ring(profile: tuple, segments: int = 16) -> np.ndarray:
    """Profile outline for the visual tube, counter-clockwise (m)."""
    kind = profile[0]
    if kind == "round":
        r = profile[1] * MM / 2
        a = np.linspace(0, 2 * math.pi, segments, endpoint=False)
        return np.c_[r * np.cos(a), r * np.sin(a)]
    region = profile_region(profile).simplify(0.02 * profile_region(profile).bounds[3])
    return g2.ring_points(region)


# ----------------------------------------------------------------- the cable


@dataclass
class End:
    """One variant of one end of the cable, in its own frame."""

    variant: str
    connector: str | None
    role: str  # plug | inline | cut | stripped
    rotation: np.ndarray  # frame in cable coordinates (columns = axes)
    origin: np.ndarray
    visuals: list = field(default_factory=list)  # [(TriMesh, colour, kind)]
    hulls: list = field(default_factory=list)  # convex point sets (frame coordinates)
    mass: float = 0.0
    com: np.ndarray = field(default_factory=lambda: np.zeros(3))
    inertia: np.ndarray = field(default_factory=lambda: np.zeros((3, 3)))


@dataclass
class Segment:
    center: np.ndarray
    rotation: np.ndarray  # columns: x along the cable, y across, z up-ish
    length: float
    visual: TriMesh


@dataclass
class Cable:
    name: str
    preset_key: str
    index: int
    length: float  # m, of the cable between its ends (axis length for a coiled cord)
    nominal_length: float
    layout: str
    color: str
    jacket: str
    profile: tuple
    section: dict
    youngs_modulus: float  # Pa, effective
    shear_modulus: float
    linear_density: float  # kg/m along the axis
    bending_stiffness: tuple  # (E·I_y, E·I_z) N·m², of the rod model
    torsional_stiffness: float  # N·m²
    axial_stiffness: float | None  # N/m of the whole coil (coiled cords), else None
    coil: dict | None
    segments: list
    ends: dict  # {"a": {variant: End}, "b": {...}}
    selected: dict  # {"a": variant, "b": variant}
    position: tuple = (0.0, 0.0, 0.0)

    @property
    def segment_length(self) -> float:
        return self.segments[0].length

    @property
    def joint_stiffness(self) -> dict:
        """Per-joint spring constants: twist, bend_y, bend_z (N·m/rad), axial (N/m)."""
        L = self.segment_length
        out = {
            "twist": self.torsional_stiffness / L,
            "bend_y": self.bending_stiffness[0] / L,
            "bend_z": self.bending_stiffness[1] / L,
        }
        if self.axial_stiffness is not None:
            out["axial"] = self.axial_stiffness * (len(self.segments) - 1)
        return out

    @property
    def mass(self) -> float:
        return self.linear_density * self.length

    def end_mass(self, end: str) -> float:
        return self.ends[end][self.selected[end]].mass


def _segment_length(width: float, length: float, max_segments: int) -> float:
    L = min(max(1.5 * width, 0.004), 0.02)
    return max(L, length / max_segments)


def _height_profile(s: np.ndarray, length: float, r: float, h_a: float, h_b: float) -> np.ndarray:
    """Cable centre height: on the ground, rising smoothly to the connectors' axes at the ends."""
    ramp = min(0.08, length / 3)

    def smooth(x):
        x = np.clip(x, 0.0, 1.0)
        return x * x * (3 - 2 * x)

    return r + (h_a - r) * smooth(1 - s / ramp) + (h_b - r) * smooth(1 - (length - s) / ramp)


def _frame(z_axis: np.ndarray) -> np.ndarray:
    """Right-handed frame with the given z axis and y as close to up as possible."""
    z = z_axis / np.linalg.norm(z_axis)
    x = np.cross(UP, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.c_[x, y, z]


def _hex_to_rgb(color: str) -> tuple:
    c = color.lstrip("#")
    return tuple(int(c[i : i + 2], 16) / 255 for i in (0, 2, 4))


def connector_end(variant: str, cable_color: str) -> End:
    """Geometry of a connector variant in its own frame (origin on the mating plane)."""
    key, role = end_connector(variant)
    spec = CONNECTORS[key]
    parts = plug_parts(spec) if role == "plug" else receptacle_parts(spec, "inline")
    body_color = spec.color
    visuals = []
    for kind in ("mating", "body"):
        sel = [p for p in parts if p.kind == kind]
        if not sel:
            continue
        color = spec.shell if (kind == "mating" and role == "plug" and spec.shell) else body_color
        visuals.append((part_mesh(sel), color, kind))
    hulls = [h for p in parts for h in p.convex_hulls()]
    mp = mass_properties(part_mesh(parts), spec.density)
    return End(
        variant, key, role, np.eye(3), np.zeros(3), visuals, hulls, mp["mass"], mp["com"], mp["inertia"]
    )


def _core_layout(profile: tuple, n: int) -> tuple[np.ndarray, float]:
    """Positions (n, 2) and diameter of the cores in the cross-section (m)."""
    kind = profile[0]
    if kind == "flat":
        _, count, pitch, _t = profile
        x = (np.arange(count) - (count - 1) / 2) * pitch * MM
        return np.c_[x, np.zeros(count)], 0.8 * pitch * MM
    if kind == "figure8":
        d = profile[1] * MM
        return np.array([[-d / 2, 0.0], [d / 2, 0.0]]), 0.55 * d
    d = profile[1] * MM
    if n == 1:
        return np.zeros((1, 2)), 0.5 * d
    rc = 0.27 * d if n <= 4 else 0.3 * d
    a = np.linspace(0, 2 * math.pi, n, endpoint=False) + math.pi / 2
    dc = min(0.85 * 2 * rc * math.sin(math.pi / n), 0.42 * d)
    return np.c_[rc * np.cos(a), rc * np.sin(a)], dc


def stripped_end(profile: tuple, colors: list) -> End:
    pos, dc = _core_layout(profile, len(colors))
    visuals, regions = [], []
    for (x, y), color in zip(pos, colors, strict=False):
        ins = g2.circle(dc, x, y)
        cu = g2.circle(0.55 * dc, x, y)
        visuals.append((Part(ins, 0.0, STRIP_INSULATION, "body").mesh(), color, "core"))
        visuals.append(
            (Part(cu, STRIP_INSULATION, STRIP_INSULATION + STRIP_COPPER, "body").mesh(), COPPER, "copper")
        )
        regions.append(ins)
    hull_region = g2.union(*regions).convex_hull
    part = Part(hull_region, 0.0, STRIP_INSULATION + STRIP_COPPER, "body")
    mp = mass_properties(merge([v[0] for v in visuals]), 3000.0)
    return End(
        "stripped",
        None,
        "stripped",
        np.eye(3),
        np.zeros(3),
        visuals,
        part.convex_hulls(),
        mp["mass"],
        mp["com"],
        mp["inertia"],
    )


def _end_height(end: End) -> float:
    """Height of the frame origin above the ground when the end lies flat (y up)."""
    lo = min(v[0].bounds[0][1] for v in end.visuals) if end.visuals else 0.0
    return -lo + 0.0005


def build_cable(
    name: str,
    preset_key: str,
    index: int,
    length: float,
    nominal_length: float,
    layout: str,
    color: str,
    youngs_modulus: float,
    linear_density: float,
    selected: dict,
    end_options: dict,
    rng_layout: np.random.Generator,
    max_segments: int = 400,
    coil_length: float | None = None,
) -> Cable:
    pr = PRESETS[preset_key]
    profile = pr["profile"]
    sec = section(profile)
    width = sec["width"]
    E = youngs_modulus
    G = E / (2 * (1 + POISSON))
    coil_info = None

    if "coil" in pr:
        # coiled cord: the rod is the coil's axis
        d = profile[1] * MM
        D = pr["coil"]["diameter"] * MM  # mean coil diameter
        p = pr["coil"]["pitch"] * d
        axis_length = coil_length if coil_length is not None else length
        turns = axis_length / p
        Iw, Jw = sec["Iy"], sec["J"]
        bend = 2 * E * Iw * p / (math.pi * D * (2 + POISSON))
        twist = E * Iw * p / (math.pi * D)
        axial = 4 * G * Jw / (math.pi * D**3 * turns)
        wire_per_axis = math.hypot(math.pi * D, p) / p
        rho = linear_density * wire_per_axis
        wire_length = axis_length * wire_per_axis
        coil_info = {"diameter": D, "pitch": p, "turns": turns, "wire_length": wire_length, "wire": d}
        bending, torsion, axial_k = (bend, bend), twist, axial
        cable_len = axis_length
        tube_width = D + d
    else:
        bending = (E * sec["Iy"], E * sec["Iz"])
        torsion = G * sec["J"]
        axial_k = None
        rho = linear_density
        cable_len = length
        tube_width = width

    L_seg = _segment_length(tube_width, cable_len, max_segments)
    n_seg = max(2, int(round(cable_len / L_seg)))
    L_seg = cable_len / n_seg

    # ----- ends (every variant, for the variant sets)
    ends: dict = {"a": {}, "b": {}}
    for end in ("a", "b"):
        for variant in end_options[end]:
            key, role = end_connector(variant)
            if key:
                ends[end][variant] = connector_end(variant, color)
            elif role == "stripped":
                ends[end][variant] = stripped_end(profile, pr["conductors"])
            else:
                ends[end][variant] = End("cut", None, "cut", np.eye(3), np.zeros(3))

    # ----- centre line in the ground plane
    step = min(L_seg / 4, max(width / 2, 0.002))
    min_radius = max(6 * tube_width, 0.03)
    if layout == "straight":
        xy = cl.straight(cable_len, step)
    elif layout == "slack":
        xy = cl.slack(cable_len, step, rng_layout, min_radius)
    elif layout == "coil":
        end_len = max(
            (_end_extent(e) for side in ends.values() for e in side.values()),
            default=0.0,
        )
        end_w = max((_end_width(e) for side in ends.values() for e in side.values()), default=0.0)
        spacing = end_w / 2 + tube_width / 2 + 0.003  # the outer end's connector clears the loop inside
        xy = cl.coil(cable_len, step, tube_width, max(0.07, 1.3 * end_len, 2 * min_radius), spacing)
    else:
        raise ValueError(f"unknown layout {layout!r}; choose from {', '.join(cl.LAYOUTS)}")
    xy = cl.fit_length(xy, cable_len)
    s = cl.arc_length(xy)

    radius = tube_width / 2 if coil_info else sec["height"] / 2
    h_a = max(radius, *(_end_height(e) for e in ends["a"].values() if e.visuals), radius)
    h_b = max(radius, *(_end_height(e) for e in ends["b"].values() if e.visuals), radius)
    z = _height_profile(s, cable_len, radius, h_a, h_b)
    path = np.c_[xy, z]

    # ----- segments: joints at equal arc length along the path
    s_joint = np.linspace(0.0, cable_len, n_seg + 1)
    joints = np.c_[[np.interp(s_joint, s, path[:, k]) for k in range(3)]].T
    tangent = cl.tangents(path)
    normal = np.cross(UP, tangent)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)

    ring = _ring(profile)
    if coil_info:
        helix, helix_s, helix_n = _helix(path, s, coil_info)
        wire_ring = _ring(("round", coil_info["wire"] / MM), 10)

    segments = []
    for i in range(n_seg):
        p0, p1 = joints[i], joints[i + 1]
        x = (p1 - p0) / np.linalg.norm(p1 - p0)
        y = np.cross(UP, x)
        y /= np.linalg.norm(y)
        zz = np.cross(x, y)
        R = np.c_[x, y, zz]
        c = 0.5 * (p0 + p1)
        if coil_info:
            idx = np.flatnonzero((helix_s >= s_joint[i] - 1e-12) & (helix_s <= s_joint[i + 1] + 1e-12))
            idx = np.arange(max(idx[0] - 1, 0), min(idx[-1] + 2, len(helix_s)))  # overlap: no gap at joints
            pts, nrm = helix[idx], helix_n[idx]
            prof = wire_ring
        else:
            m = (s > s_joint[i] + 1e-12) & (s < s_joint[i + 1] - 1e-12)
            pts = np.vstack([p0, path[m], p1])
            # the curve's own frame at the shared joint points: neighbouring pieces meet exactly
            n0 = _interp_rows(s_joint[i], s, normal)
            n1 = _interp_rows(s_joint[i + 1], s, normal)
            nrm = np.vstack([n0, normal[m], n1])
            prof = ring
        mesh = sweep(prof, pts, nrm) if len(pts) >= 2 else TriMesh.empty()
        segments.append(Segment(c, R, L_seg, mesh.transformed(R.T, -R.T @ c)))

    # ----- place the ends: plug Z out of the cable, inline receptacle Z into it
    for end, idx, sign in (("a", 0, -1.0), ("b", -1, 1.0)):
        p = path[idx]
        t_out = sign * tangent[idx]
        t_out = t_out / np.linalg.norm(t_out)
        for e in ends[end].values():
            if e.role == "plug":
                e.rotation = _frame(t_out)
                e.origin = p + t_out * CONNECTORS[e.connector].body_length * MM
            elif e.role == "inline":
                spec = CONNECTORS[e.connector]
                total = max(spec.inline[0], spec.depth + 3.0) * MM
                e.rotation = _frame(-t_out)
                e.origin = p + t_out * total
            else:
                e.rotation = _frame(t_out)
                e.origin = p.copy()

    return Cable(
        name=name,
        preset_key=preset_key,
        index=index,
        length=cable_len,
        nominal_length=nominal_length,
        layout=layout,
        color=color,
        jacket=pr["jacket"],
        profile=profile,
        section=sec,
        youngs_modulus=E,
        shear_modulus=G,
        linear_density=rho,
        bending_stiffness=bending,
        torsional_stiffness=torsion,
        axial_stiffness=axial_k,
        coil=coil_info,
        segments=segments,
        ends=ends,
        selected=selected,
    )


def _interp_rows(x: float, xs: np.ndarray, rows: np.ndarray) -> np.ndarray:
    v = np.array([np.interp(x, xs, rows[:, k]) for k in range(rows.shape[1])])
    return v / np.linalg.norm(v)


def _end_width(end: End) -> float:
    if not end.visuals:
        return 0.0
    return max(v[0].bounds[1][0] for v in end.visuals) - min(v[0].bounds[0][0] for v in end.visuals)


def _end_extent(end: End) -> float:
    if not end.visuals:
        return 0.0
    lo = min(v[0].bounds[0][2] for v in end.visuals)
    hi = max(v[0].bounds[1][2] for v in end.visuals)
    return hi - lo


def _helix(path: np.ndarray, s: np.ndarray, coil: dict):
    """Wire centre line of a coiled cord around its axis path, with arc length along the axis."""
    R = coil["diameter"] / 2
    p = coil["pitch"]
    per_turn = 24
    n = max(int(s[-1] / p * per_turn), 8)
    sa = np.linspace(0.0, s[-1], n + 1)
    axis = np.c_[[np.interp(sa, s, path[:, k]) for k in range(3)]].T
    t = cl.tangents(axis)
    u = np.cross(UP, t)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(t, u)
    phi = 2 * math.pi * sa / p
    radial = np.cos(phi)[:, None] * u + np.sin(phi)[:, None] * v
    pts = axis + R * radial
    return pts, sa, radial


def cable_color_rgb(color: str) -> tuple:
    return _hex_to_rgb(color)
