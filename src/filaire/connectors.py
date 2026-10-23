"""Connector catalogue and geometry: plugs, receptacles on a cable, fixed receptacles.

One description per connector family gives the cross-sections of the part
that enters (the *plug*), layer by layer from its tip. The matching
receptacle is **derived** from it: in each layer, the receptacle's solid is
its outline minus the plug's cross-section grown by the clearance. So the
two always mate, the plug's holes become the receptacle's pins or tongue,
and the plug's key becomes the receptacle's keyway.

Two words, kept apart on purpose:

- *gender* is the contact gender of the standard: an IEC C13 is female
  (sockets) even though it is the part that enters the C14 inlet;
- *role* is geometric: the plug enters, the receptacle receives. A plug can
  have female contacts (C13, XLR female, M12 female, IDC socket).

Frames (metres):

- plug: origin on the mating plane (the stop face, where the plug's body
  begins); +Z is the insertion direction, out of the tip; the mating layers
  occupy 0 ≤ z ≤ depth, the body −length ≤ z ≤ 0 and the cable leaves at
  z = −length;
- receptacle: origin on its front face, +Z into the receptacle (the same
  direction as the plug's insertion); the cavity occupies 0 ≤ z ≤ depth.

When the plug is fully inserted, both origins and axes coincide (the
`mate_frame` of each part in the OpenUSD output).

Dimensions are in millimetres in this file. Values marked `approximate` are
orders of magnitude for simulation, not the drawings of the standard; the
`sources` list the published figures used where there are some.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import geometry2d as g2
from .mesh3d import TriMesh, convex_prism_points, extrude, mass_properties, merge

MM = 1e-3


@dataclass
class Layer:
    t0: float  # distance from the plug tip where the layer starts (mm)
    t1: float  # ... and ends
    region: object  # shapely geometry in the face plane (mm)


@dataclass
class ConnectorSpec:
    key: str
    label: str
    standard: str
    gender: str  # contact gender of the cable-side part: male | female
    keying: str  # declared: none (any angle) | reversible (0° and 180°) | keyed (one orientation)
    layers: list  # mating cross-sections of the plug, from its tip
    body: list  # plug body behind the mating plane: [(length mm, region), ...] from the plane back
    inline: tuple | None  # receptacle on a cable: (body length mm, outline)
    panel: tuple  # fixed receptacle: (block depth behind the cavity mm, front outline)
    clearance: float = 0.1  # mm, radial, between plug and receptacle
    density: float = 1400.0  # kg/m³, effective (plastic + metal parts)
    plug_name: str = ""  # display names (gender words of the standard)
    inline_name: str = ""
    panel_name: str = ""
    color: str = "#202020"  # body colour of the plug and inline receptacle (sRGB)
    shell: str = ""  # colour of the metal shell / mating part, "" = same as body
    approximate: list = field(default_factory=list)  # dimensions that are not from a source
    sources: list = field(default_factory=list)

    @property
    def depth(self) -> float:
        """Insertion depth (mm): length of the mating layers."""
        return max(layer.t1 for layer in self.layers)

    @property
    def body_length(self) -> float:
        return sum(length for length, _ in self.body)


# ----------------------------------------------------------------- helpers


def _pins(diameter, positions):
    return g2.union(*(g2.circle(diameter, x, y) for x, y in positions))


def _holes(region, *holes):
    for h in holes:
        region = region.difference(h)
    return region


_METAL = "#b8bcc2"

# ----------------------------------------------------------------- catalogue

_USB_C_PLUG = g2.stadium(8.25, 2.40).difference(g2.stadium(6.95, 1.00))
_USB_A_PLUG = g2.rect(12.0, 4.5).difference(g2.rect(11.2, 1.85, 0.0, 0.975))
_HDMI_PLUG = g2.chamfered_rect(13.9, 4.45, bottom=1.3).difference(g2.rect(10.9, 1.5, 0.0, 0.25))
_RJ45_PLUG = g2.union(g2.rect(11.68, 6.60), g2.rect(4.2, 1.40 + 0.2, 0.0, 3.30 + 0.6))
_RJ9_PLUG = g2.union(g2.rect(7.70, 6.60), g2.rect(3.2, 1.6, 0.0, 3.9))
_C13_FACE = g2.chamfered_rect(24.0, 15.5, top=4.5)
_C13_HOLES = [g2.rect(2.4, 4.6, x, y) for x, y in ((-7.0, -2.0), (7.0, -2.0), (0.0, 2.0))]
_C7_FACE = g2.union(g2.circle(9.2, -4.3), g2.circle(9.2, 4.3), g2.rect(8.6, 7.4))
_XLR_INSERT = _holes(
    g2.circle(19.0),
    g2.rect(2.6, 2.4, 0.0, 9.5),
    *(g2.circle(2.2, x, y) for x, y in ((-4.4, 1.6), (4.4, 1.6), (0.0, -4.6))),
)
_M12_INSERT = _holes(
    g2.circle(10.0),
    g2.rect(1.6, 2.0, 0.0, 5.0),
    *(g2.circle(1.4, 2.5 * np.cos(a), 2.5 * np.sin(a)) for a in np.radians([45, 135, 225, 315])),
)
_M12_NUT = g2.circle(15.0).difference(g2.circle(12.6))
_IDC_HOLES = [g2.rect(1.0, 1.0, x, y) for x in (-5.08, -2.54, 0.0, 2.54, 5.08) for y in (-1.27, 1.27)]
_IDC_SOCKET = _holes(g2.union(g2.rect(15.0, 6.2), g2.rect(4.6, 1.2, 0.0, 3.6)), *_IDC_HOLES)

CONNECTORS: dict[str, ConnectorSpec] = {
    "usb_c": ConnectorSpec(
        key="usb_c",
        label="USB Type-C",
        standard="USB Type-C Cable and Connector Specification",
        gender="male",
        keying="reversible",
        layers=[Layer(0.0, 6.65, _USB_C_PLUG)],
        body=[(18.0, g2.rrect(12.0, 6.5, 2.5))],
        inline=(24.0, g2.rrect(13.0, 7.5, 2.5)),
        panel=(3.0, g2.rrect(22.0, 12.0, 1.5)),
        clearance=0.05,
        plug_name="USB-C plug",
        inline_name="USB-C receptacle (extension)",
        panel_name="USB-C port",
        shell=_METAL,
        approximate=["plug inner cavity 6.95 × 1.00 (receptacle tongue)", "overmold 12 × 6.5 × 18"],
        sources=[
            "receptacle opening 8.34 × 2.56, plug insertion length ≈ 6.65: "
            "https://www.accesscomms.com.au/usb-connector-dimensions/",
        ],
    ),
    "usb_a": ConnectorSpec(
        key="usb_a",
        label="USB Type-A",
        standard="USB 2.0 Specification (Standard-A)",
        gender="male",
        keying="keyed",
        layers=[Layer(0.0, 12.0, _USB_A_PLUG)],
        body=[(20.0, g2.rrect(16.0, 8.0, 2.0))],
        inline=None,
        panel=(3.0, g2.rrect(24.0, 14.0, 1.5)),
        clearance=0.08,
        plug_name="USB-A plug",
        panel_name="USB-A port",
        shell=_METAL,
        approximate=["shell 12.0 × 4.5", "inner cavity (receptacle tongue) 11.2 × 1.85, upper half"],
        sources=["plug body length ≈ 12: https://www.accesscomms.com.au/usb-connector-dimensions/"],
    ),
    "hdmi_a": ConnectorSpec(
        key="hdmi_a",
        label="HDMI Type A",
        standard="HDMI Specification (Type A)",
        gender="male",
        keying="keyed",
        layers=[Layer(0.0, 9.5, _HDMI_PLUG)],
        body=[(22.0, g2.rrect(21.0, 11.0, 2.5))],
        inline=(30.0, g2.rrect(22.0, 12.0, 2.5)),
        panel=(3.0, g2.rrect(28.0, 14.0, 1.5)),
        clearance=0.05,
        plug_name="HDMI plug",
        inline_name="HDMI receptacle (extension)",
        panel_name="HDMI port",
        shell=_METAL,
        approximate=["bottom chamfers 1.3", "insertion depth 9.5", "inner cavity 10.9 × 1.5"],
        sources=["plug 13.9 × 4.45, receptacle 14 × 4.55: https://en.wikipedia.org/wiki/HDMI"],
    ),
    "rj45": ConnectorSpec(
        key="rj45",
        label="RJ45 (8P8C)",
        standard="IEC 60603-7 (8-way modular)",
        gender="male",
        keying="keyed",
        layers=[Layer(0.0, 14.0, _RJ45_PLUG)],
        body=[(16.0, g2.rrect(13.0, 10.0, 2.0))],
        inline=(34.0, g2.rrect(17.0, 15.0, 1.5)),
        panel=(4.0, g2.rrect(17.0, 15.0, 1.0)),
        clearance=0.1,
        plug_name="RJ45 plug",
        inline_name="RJ45 coupler (inline)",
        panel_name="RJ45 jack",
        color="#d8dde3",
        approximate=["latch 4.2 wide", "insertion depth 14", "boot 13 × 10 × 16"],
        sources=[
            "plug 11.68 wide, 8.00 high with latch, 22.48 long; insertion height 6.60: "
            "https://en.wikipedia.org/wiki/Modular_connector",
        ],
    ),
    "rj9": ConnectorSpec(
        key="rj9",
        label="RJ9 (4P4C handset)",
        standard="4-way modular (handset)",
        gender="male",
        keying="keyed",
        layers=[Layer(0.0, 10.0, _RJ9_PLUG)],
        body=[(6.0, g2.rrect(8.5, 8.0, 1.5))],
        inline=None,
        panel=(4.0, g2.rrect(13.0, 13.0, 1.0)),
        clearance=0.1,
        plug_name="RJ9 plug",
        panel_name="RJ9 handset jack",
        color="#d8dde3",
        approximate=["height 6.60 (modular insertion height)", "latch", "insertion depth 10"],
        sources=["plug width 7.7: https://en.wikipedia.org/wiki/Modular_connector"],
    ),
    "jack35": ConnectorSpec(
        key="jack35",
        label="3.5 mm jack (TRS)",
        standard="IEC 60603-11 (3.5 mm)",
        gender="male",
        keying="none",
        layers=[Layer(0.0, 15.0, g2.circle(3.5))],
        body=[(18.0, g2.circle(6.0))],
        inline=(22.0, g2.circle(7.5)),
        panel=(3.0, g2.rrect(12.0, 12.0, 1.5)),
        clearance=0.05,
        plug_name="3.5 mm plug",
        inline_name="3.5 mm socket (extension)",
        panel_name="3.5 mm socket",
        shell=_METAL,
        approximate=["overmold Ø6 × 18"],
        sources=["Ø3.5, length 15: https://en.wikipedia.org/wiki/Phone_connector_(audio)"],
    ),
    "c13": ConnectorSpec(
        key="c13",
        label="IEC 60320 C13 / C14",
        standard="IEC 60320-1",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 13.0, _holes(_C13_FACE, *_C13_HOLES))],
        body=[(35.0, g2.rrect(27.0, 19.0, 3.0))],
        inline=(30.0, g2.rrect(30.0, 22.0, 3.0)),
        panel=(4.0, g2.rrect(31.0, 23.0, 2.0)),
        clearance=0.2,
        density=1300.0,
        plug_name="C13 connector",
        inline_name="C14 plug (extension)",
        panel_name="C14 inlet",
        approximate=["face 24.0 × 15.5 with 4.5 chamfers", "blade holes 2.4 × 4.6", "depth 13"],
        sources=["pin centres 14 mm across, 4 mm vertical offset: https://en.wikipedia.org/wiki/IEC_60320"],
    ),
    "c7": ConnectorSpec(
        key="c7",
        label="IEC 60320 C7 / C8 (figure-8)",
        standard="IEC 60320-1",
        gender="female",
        keying="reversible",
        layers=[Layer(0.0, 10.0, _holes(_C7_FACE, g2.circle(2.6, -4.3), g2.circle(2.6, 4.3)))],
        body=[(26.0, g2.rrect(20.0, 11.5, 4.0))],
        inline=None,
        panel=(3.0, g2.rrect(26.0, 16.0, 2.0)),
        clearance=0.2,
        density=1300.0,
        plug_name="C7 connector",
        panel_name="C8 inlet",
        approximate=["lobes Ø9.2", "pin holes Ø2.6"],
        sources=["pin centres 8.6 mm, C8 inlet 10 mm deep: https://en.wikipedia.org/wiki/IEC_60320"],
    ),
    "cee77": ConnectorSpec(
        key="cee77",
        label="CEE 7/7 mains plug (type E/F)",
        standard="CEE 7",
        gender="male",
        keying="reversible",
        layers=[
            Layer(0.0, 19.0, _pins(4.8, [(-9.5, 0.0), (9.5, 0.0)])),
            Layer(19.0, 34.0, g2.circle(36.0)),
        ],
        body=[(30.0, g2.rrect(40.0, 38.0, 12.0))],
        inline=None,
        panel=(6.0, g2.rrect(56.0, 56.0, 6.0)),
        clearance=0.3,
        density=1200.0,
        plug_name="CEE 7/7 plug",
        panel_name="Wall socket (simplified, no earth)",
        approximate=["plug face Ø36", "socket without earth pin or clips", "grip 40 × 38 × 30"],
        sources=[
            "pins 4.8 × 19 mm, 19 mm apart; CEE 7/5 recess 15 mm deep: https://en.wikipedia.org/wiki/CEE_7",
        ],
    ),
    "cee716": ConnectorSpec(
        key="cee716",
        label="CEE 7/16 Europlug",
        standard="CEE 7",
        gender="male",
        keying="reversible",
        layers=[
            Layer(0.0, 19.0, _pins(4.0, [(-9.5, 0.0), (9.5, 0.0)])),
            Layer(19.0, 25.0, g2.stadium(35.0, 13.5)),
        ],
        body=[(24.0, g2.rrect(35.0, 15.0, 6.0))],
        inline=None,
        panel=(6.0, g2.rrect(50.0, 50.0, 6.0)),
        clearance=0.3,
        density=1200.0,
        plug_name="Europlug",
        panel_name="Europlug socket (simplified)",
        approximate=["pins Ø4.0, parallel", "body 35 × 13.5", "recess 6"],
        sources=["pin length and spacing as CEE 7/6: https://en.wikipedia.org/wiki/CEE_7"],
    ),
    "xlr3": ConnectorSpec(
        key="xlr3",
        label="XLR 3-pin",
        standard="IEC 61076-2-103",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 11.0, _XLR_INSERT)],
        body=[(42.0, g2.circle(20.5))],
        inline=(46.0, g2.circle(23.0)),
        panel=(6.0, g2.rrect(26.0, 31.0, 2.0)),
        clearance=0.2,
        density=2500.0,
        plug_name="XLR3 female (cable)",
        inline_name="XLR3 male (cable)",
        panel_name="XLR3 male (panel)",
        color="#2a2d31",
        shell=_METAL,
        approximate=["insert Ø19 with 2.6 key groove", "pin positions", "depth 11", "male shell Ø23"],
        sources=["no published dimensions found; IEC 61076-2-103 not consulted"],
    ),
    "m12a": ConnectorSpec(
        key="m12a",
        label="M12 A-coded 4-pin",
        standard="IEC 61076-2-101",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 8.0, g2.union(_M12_INSERT, _M12_NUT))],
        body=[(12.0, g2.circle(15.0)), (30.0, g2.circle(13.0))],
        inline=None,
        panel=(4.0, g2.rrect(18.0, 18.0, 2.0)),
        clearance=0.15,
        density=2500.0,
        plug_name="M12 female (cable)",
        panel_name="M12 male (panel)",
        color="#3a3f45",
        shell=_METAL,
        approximate=["insert Ø10", "key 1.6", "pins on Ø5", "nut Ø15 / bore Ø12.6"],
        sources=["thread M12 × 1 (IEC 61076-2-101, not consulted)"],
    ),
    "idc10": ConnectorSpec(
        key="idc10",
        label="IDC 2 × 5, 2.54 mm",
        standard="IDC ribbon socket, 0.1 in pitch",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 6.0, _IDC_SOCKET)],
        body=[(7.0, g2.rect(15.0, 9.0))],
        inline=None,
        panel=(3.0, g2.rect(20.3, 8.85)),
        clearance=0.1,
        density=1300.0,
        plug_name="IDC socket 2×5",
        panel_name="Box header 2×5",
        color="#2b2b2b",
        approximate=["socket 15.0 × 6.2 with key 4.6", "box header 20.3 × 8.85", "depth 6"],
        sources=["2.54 mm pin pitch (0.1 in)"],
    ),
}


# ----------------------------------------------------------- parts & meshes


@dataclass
class Part:
    """A prism: a plane region extruded along z, in the part's frame (metres)."""

    region: object  # shapely geometry, metres
    z0: float
    z1: float
    kind: str  # "mating" | "body"

    def mesh(self) -> TriMesh:
        return extrude(self.region, self.z0, self.z1)

    def convex_hulls(self) -> list[np.ndarray]:
        return [convex_prism_points(p, self.z0, self.z1) for p in g2.convex_parts(self.region)]


def _scale(region):
    from shapely import affinity

    return affinity.scale(region, MM, MM, origin=(0, 0))


def plug_parts(spec: ConnectorSpec) -> list[Part]:
    d = spec.depth
    parts = [
        Part(_scale(layer.region), (d - layer.t1) * MM, (d - layer.t0) * MM, "mating")
        for layer in spec.layers
    ]
    z = 0.0
    for length, region in spec.body:
        parts.append(Part(_scale(region), (z - length) * MM, z * MM, "body"))
        z -= length
    return parts


def receptacle_parts(spec: ConnectorSpec, mount: str = "panel") -> list[Part]:
    """The derived receptacle: outline minus the plug grown by the clearance, layer by layer.

    mount = "panel": a block (device face, wall socket, inlet) of depth
    cavity + spec.panel[0]; mount = "inline": a receptacle body on a cable,
    spec.inline[0] long, the cable leaving at z = length.
    """
    if mount == "panel":
        back, outline = spec.panel
        total = spec.depth + back
    elif mount == "inline":
        if spec.inline is None:
            raise ValueError(f"{spec.key} has no receptacle on a cable")
        total, outline = spec.inline
        total = max(total, spec.depth + 3.0)
    else:
        raise ValueError(f"unknown mount {mount!r}")
    d, c = spec.depth, spec.clearance
    parts = []
    for layer in spec.layers:
        solid = outline.difference(_cavity(layer.region, c))
        z0, z1 = d - layer.t1, d - layer.t0
        if layer.t0 == 0.0:
            z1 += c  # the cavity goes on past the plug tip by the clearance
        parts.append(Part(_scale(solid), z0 * MM, z1 * MM, "mating"))
    parts.append(Part(_scale(outline), (d + c) * MM, total * MM, "body"))
    return [p for p in parts if not p.region.is_empty and p.z1 > p.z0]


def part_mesh(parts: list[Part]) -> TriMesh:
    return merge([p.mesh() for p in parts])


def mass_of(parts: list[Part], density: float) -> dict:
    return mass_properties(part_mesh(parts), density)


def fits(spec: ConnectorSpec, angle_deg: float, mount: str = "panel", tol: float = 1e-9) -> bool:
    """Does the plug, turned by angle about the insertion axis, enter the receptacle fully?

    Plane test, layer by layer: the turned plug cross-section must not overlap
    the receptacle's solid at any depth it goes through.
    """
    outline = spec.panel[1] if mount == "panel" else spec.inline[1]
    solids = [outline.difference(_cavity(other.region, spec.clearance)) for other in spec.layers]
    for layer in spec.layers:
        turned = g2.rotate(layer.region, angle_deg)
        # every receptacle layer the turned plug layer passes through on its way in
        for other, solid in zip(spec.layers, solids, strict=True):
            if other.t1 <= layer.t0 + 1e-12:
                continue
            if turned.intersection(solid).area > tol:
                return False
    return True


def _cavity(region, clearance: float):
    return region.buffer(clearance, quad_segs=g2.QUAD_SEGS, join_style="mitre")


def admissible_angles(spec: ConnectorSpec, step: float = 15.0) -> list[float]:
    return [a for a in np.arange(0.0, 360.0, step) if fits(spec, float(a))]


def keying_of(spec: ConnectorSpec) -> str:
    """Keying found from the geometry: none, reversible or keyed."""
    angles = admissible_angles(spec)
    if len(angles) == int(360 / 15):
        return "none"
    if 180.0 in angles:
        return "reversible"
    return "keyed"
