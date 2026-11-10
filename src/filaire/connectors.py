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

import math
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
    keying: str  # declared: none (any angle) | square (quarter turns) | reversible (0°, 180°) | keyed
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
    # looks of the receptacles and plugs (visual only: the collision geometry does not change)
    socket_shell: str = ""  # wall around the cavity, SHELL_WALL thick; "" = the receptacle's body colour
    socket_insert: str = "#1d1f22"  # what stands inside the cavity: tongue, pins, contact insert
    insert_metal: bool = False  # ... in metal (pins) rather than plastic (tongue, insert)
    panel_color: str = "#2b2d31"  # the device face around a panel receptacle
    clear: bool = False  # mating part of the plug in clear plastic (modular plugs)
    # [(t0, t1, colour)], mm from the plug tip: insulator rings, insulated pin sleeves
    bands: list = field(default_factory=list)
    pin_layers: tuple = ()  # indices of mating layers that are bare metal pins (power plugs)
    plug_insert: str = ""  # plug face: colour of the insert inside a metal rim (XLR, M12)
    plug_rim: float = 1.0  # mm, width of that metal rim, from the outer boundary
    approximate: list = field(default_factory=list)  # dimensions that are not from a source
    sources: list = field(default_factory=list)
    # bayonet: once fully in, the plug is turned by this angle (degrees, counter-clockwise seen
    # from the receptacle) to lock; its receptacle then keeps clear of everything the plug sweeps
    twist: float = 0.0

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


_METAL = "#b8bcc2"  # nickel-plated steel
_BLACK = "#1b1c1e"  # black thermoplastic (inlets, jacks, headers)
_WALL = "#ecebe6"  # white wiring-device plastic (wall sockets)
_GOLD = "#c9a13b"  # gold-plated contacts
SHELL_WALL = 0.6  # mm, visible wall of a metal receptacle shell around its cavity
METALS = {_METAL, _GOLD}

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
# Micro-B: trapezoid shell (chamfered lower corners), cavity for the receptacle's tongue near the top
_MICRO_B_PLUG = g2.chamfered_rect(6.80, 1.75, bottom=0.75).difference(g2.rect(5.6, 0.62, 0.0, 0.32))

# 0.1 in (2.54 mm) pin headers: 0.64 mm square posts; a socket's entry is the post plus the clearance
_PITCH = 2.54
_POST = 0.64
_ENTRY = _POST + 2 * 0.1


def _entries(xs, size=_ENTRY, y=0.0):
    return [g2.rect(size, size, x, y) for x in xs]


# servo lead: 3-way housing, polarised by a rib along one long side
_SERVO_HOUSING = g2.union(g2.rect(7.6, 2.6, 0.0, -0.3), g2.rect(1.6, 0.6, 0.0, 1.3))
_SERVO_SOCKET = _holes(_SERVO_HOUSING, *_entries([-_PITCH, 0.0, _PITCH], y=-0.3))
# jumper wire: one 2.54 mm square housing
_JUMPER_HOUSING = g2.rect(2.5, 2.5)
# battery plug (60 A class): two Ø3.5 mm bullets 7.2 mm apart, housing with two chamfered corners
_BATT_FRONT = g2.chamfered_rect(13.6, 6.4, top=1.6)
_BATT_SOCKET = _holes(_BATT_FRONT, g2.circle(3.7, -3.6), g2.circle(3.7, 3.6))
_BATT_OUTER = g2.chamfered_rect(15.8, 8.2, top=2.0)
# balance plug, 5-way 2.5 mm pitch: housing with two locking ribs on one side
_BAL_N, _BAL_PITCH = 5, 2.5
_BAL_W = _BAL_PITCH * (_BAL_N - 1) + 2.9
_BAL_HOUSING = g2.union(
    g2.rect(_BAL_W, 4.2, 0.0, -0.25),
    g2.rect(1.2, 0.6, -(_BAL_W / 2 - 1.8), 2.1),
    g2.rect(1.2, 0.6, _BAL_W / 2 - 1.8, 2.1),
)
_BAL_SOCKET = _holes(
    _BAL_HOUSING, *_entries([(k - (_BAL_N - 1) / 2) * _BAL_PITCH for k in range(_BAL_N)], y=-0.25)
)
# D-sub 9 (shell size E): the female insert goes into the male's D shell; 5 + 4 contacts
_DSUB_D = g2.trapezoid(16.30, 7.80, 10.0, r=1.0)
_DSUB_ROWS = [(x, 1.42) for x in (-5.54, -2.77, 0.0, 2.77, 5.54)]
_DSUB_ROWS += [(x, -1.42) for x in (-4.155, -1.385, 1.385, 4.155)]
_DSUB_SOCKET = _holes(_DSUB_D, *(g2.circle(1.2, x, y) for x, y in _DSUB_ROWS))
_DSUB_FLANGE = g2.rrect(30.81, 12.55, 1.0)
_DSUB_HOOD = g2.rrect(31.5, 15.5, 3.0)

# BNC: the plug's coupling sleeve has two bayonet slots, an axial entry from its face then a
# quarter turn round; the jack's barrel carries two studs. Plug turned by +90° (seen from the
# jack) to lock. Diameters (mm): barrel 9.9, sleeve 10.1 inside, 14.5 outside, pin 1.35.
_BNC_SLOT = 2.4  # slot width, for studs of Ø2.1
_BNC_ENTRY = 90.0  # angle of the slots' entries (and of the studs)


def _annulus(d_out, d_in):
    return g2.circle(d_out).difference(g2.circle(d_in))


_BNC_SLEEVE = _annulus(14.5, 10.1)
_BNC_CROSS = g2.rotate(g2.rect(16.0, _BNC_SLOT), _BNC_ENTRY)  # both slots, across the axis
_BNC_ARC = g2.union(  # each slot's turn: from its entry, 90° clockwise in the plug's frame
    *(g2.rotate(g2.rect(16.0, _BNC_SLOT), _BNC_ENTRY - a) for a in np.linspace(0.0, 90.0, 46))
)
_BNC_INNER = g2.circle(8.0)  # outer contact fingers and insulator, inside the jack's barrel
_BNC_FRONT = g2.union(_BNC_SLEEVE.difference(_BNC_CROSS), _annulus(8.0, 7.0), g2.circle(1.35))


def _barrel(key: str, od: float, bore: float, length: float, sizes_source: str, length_source: str):
    """A coaxial DC plug: a sleeve of outer diameter od around a bore of diameter bore.

    The derived jack gets its centre pin from the bore (bore minus twice the clearance), so a
    plug with a smaller bore cannot go onto a thicker pin, while a larger bore fits loosely, as
    on real 5.5 × 2.1 and 5.5 × 2.5 mm connectors.
    """
    return ConnectorSpec(
        key=key,
        label=f"DC barrel {od:g} × {bore:g} mm",
        standard="IEC 60130-10" if od == 5.5 else "EIAJ RC-5320A",
        gender="male",
        keying="none",
        layers=[Layer(0.0, length, g2.circle(od).difference(g2.circle(bore)))],
        body=[(6.0, g2.circle(od + 2.5)), (16.0, g2.circle(od + 4.5))],
        inline=(26.0, g2.circle(od + 5.5)),
        panel=(4.0, g2.rrect(od + 7.5, od + 7.5, 1.5)),
        clearance=0.05,
        plug_name=f"DC plug {od:g} × {bore:g}",
        inline_name=f"DC jack {od:g} × {bore:g} (extension)",
        panel_name=f"DC jack {od:g} × {bore:g}",
        shell=_METAL,
        socket_shell=_BLACK,
        socket_insert=_METAL,
        insert_metal=True,
        approximate=([] if length_source else [f"plug length {length:g}"]) + ["overmold and jack body"],
        sources=[f"{od:g} × {bore:g} mm: {sizes_source}"] + ([length_source] if length_source else []),
    )


_BARREL_SOURCE = "https://en.wikipedia.org/wiki/Coaxial_power_connector"

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
        socket_shell=_METAL,
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
        socket_shell=_METAL,
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
        socket_shell=_METAL,
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
        socket_shell=_METAL,
        clear=True,
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
        clear=True,
        panel_color="#e6e6e2",
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
        socket_shell=_BLACK,
        bands=[(4.0, 5.5, _BLACK), (7.7, 9.2, _BLACK)],
        shell=_METAL,
        approximate=["overmold Ø6 × 18", "insulator rings at 4.0–5.5 and 7.7–9.2 from the tip"],
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
        panel_color=_BLACK,
        socket_insert=_METAL,
        insert_metal=True,
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
        panel_color=_BLACK,
        socket_insert=_METAL,
        insert_metal=True,
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
        pin_layers=(0,),
        panel_color=_WALL,
        socket_insert=_METAL,
        insert_metal=True,
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
        pin_layers=(0,),
        bands=[(9.0, 19.0, _BLACK)],
        panel_color=_WALL,
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
        socket_insert=_METAL,
        insert_metal=True,
        plug_insert=_BLACK,
        plug_rim=1.0,
        socket_shell=_METAL,
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
        socket_insert=_METAL,
        insert_metal=True,
        plug_insert=_BLACK,
        plug_rim=1.2,
        socket_shell=_METAL,
        color="#3a3f45",
        shell=_METAL,
        approximate=["insert Ø10", "key 1.6", "pins on Ø5", "nut Ø15 / bore Ø12.6"],
        sources=["thread M12 × 1 (IEC 61076-2-101, not consulted)"],
    ),
    "usb_micro": ConnectorSpec(
        key="usb_micro",
        label="USB Micro-B",
        standard="USB 2.0 Specification (Micro-B)",
        gender="male",
        keying="keyed",
        layers=[Layer(0.0, 5.6, _MICRO_B_PLUG)],
        body=[(16.0, g2.rrect(10.5, 6.5, 2.0))],
        inline=None,
        panel=(3.0, g2.rrect(16.0, 10.0, 1.5)),
        clearance=0.05,
        plug_name="Micro-B plug",
        panel_name="Micro-B port",
        socket_shell=_METAL,
        shell=_METAL,
        approximate=[
            "plug 6.80 × 1.75 with 0.75 chamfers",
            "tongue cavity 5.6 × 0.62",
            "insertion depth 5.6",
        ],
        sources=["receptacle opening 6.85 × 1.8: https://www.accesscomms.com.au/usb-connector-dimensions/"],
    ),
    "dc5521": _barrel("dc5521", 5.5, 2.1, 9.5, f"IEC 60130-10 Type A, {_BARREL_SOURCE}", ""),
    "dc5525": _barrel("dc5525", 5.5, 2.5, 9.5, f"IEC 60130-10 Type A, {_BARREL_SOURCE}", ""),
    "dc4017": _barrel(
        "dc4017",
        4.0,
        1.7,
        9.5,
        f"EIAJ-02, {_BARREL_SOURCE}",
        f"barrel length 9.5 (EIAJ-02): {_BARREL_SOURCE}",
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
        socket_shell=_BLACK,
        socket_insert=_GOLD,
        insert_metal=True,
        color="#2b2b2b",
        approximate=["socket 15.0 × 6.2 with key 4.6", "box header 20.3 × 8.85", "depth 6"],
        sources=["2.54 mm pin pitch (0.1 in)"],
    ),
    # ------------------------------------------------------------ robotics
    "servo3": ConnectorSpec(
        key="servo3",
        label="Servo connector, 3-pin 2.54 mm",
        standard="3-way crimp housing, 0.1 in pitch (hobby servo)",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 6.0, _SERVO_SOCKET)],
        body=[(8.5, _SERVO_HOUSING)],
        inline=(14.5, g2.rect(8.8, 4.2)),
        panel=(3.0, g2.rect(10.0, 5.0)),
        clearance=0.1,
        density=1300.0,
        plug_name="Servo plug (3 sockets)",
        inline_name="Servo extension (3 pins)",
        panel_name="Servo port (3 pins in a slot)",
        socket_insert=_GOLD,
        insert_metal=True,
        panel_color=_BLACK,
        color=_BLACK,
        approximate=["housing 7.6 × 2.6 with a 1.6 × 0.6 rib, 14.5 long", "receiver slot 10 × 5", "depth 6"],
        sources=[
            "2.54 mm (0.1 in) pitch, 1 × 3: https://www.pololu.com/product/1902/specs",
            "0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf",
        ],
    ),
    "pin_m": ConnectorSpec(
        key="pin_m",
        label="Jumper pin, 2.54 mm (male)",
        standard="0.1 in pitch jumper wire",
        gender="male",
        keying="square",
        layers=[Layer(0.0, 6.0, g2.rect(_POST, _POST))],
        body=[(14.0, _JUMPER_HOUSING)],
        inline=(14.0, g2.rect(2.5, 2.5)),
        panel=(3.0, g2.rect(7.62, 7.62)),
        clearance=0.1,
        density=2500.0,
        plug_name="Jumper pin (male)",
        inline_name="Jumper socket (female)",
        panel_name="Breadboard contact",
        pin_layers=(0,),
        socket_insert=_GOLD,
        insert_metal=True,
        panel_color="#efefea",
        color=_BLACK,
        approximate=["housing 2.5 × 2.5 × 14", "pin 6 long", "breadboard block 7.62 square"],
        sources=["2.54 mm pitch, 0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf"],
    ),
    "pin_f": ConnectorSpec(
        key="pin_f",
        label="Jumper socket, 2.54 mm (female)",
        standard="0.1 in pitch jumper wire",
        gender="female",
        keying="square",
        layers=[Layer(0.0, 6.0, _holes(_JUMPER_HOUSING, g2.rect(_ENTRY, _ENTRY)))],
        body=[(8.0, _JUMPER_HOUSING)],
        inline=None,
        # the header's plastic base: the socket covers it, only the post stands in the cavity
        panel=(2.5, g2.rect(2.54, 2.54)),
        clearance=0.1,
        density=1300.0,
        plug_name="Jumper socket (female)",
        panel_name="Header pin",
        socket_insert=_GOLD,
        insert_metal=True,
        panel_color=_BLACK,
        color=_BLACK,
        approximate=["housing 2.5 × 2.5 × 14", "post 6 above a 2.5 base"],
        sources=["2.54 mm pitch, 0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf"],
    ),
    "batt35": ConnectorSpec(
        key="batt35",
        label="High-current DC plug, 3.5 mm bullets (60 A class)",
        standard="2-pole battery connector, 3.5 mm bullets, 7.2 mm pitch",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 8.0, _BATT_SOCKET)],
        body=[(8.0, _BATT_OUTER)],
        inline=(17.0, _BATT_OUTER),
        panel=(4.0, g2.rrect(20.0, 12.0, 1.5)),
        clearance=0.1,
        density=2200.0,
        plug_name="Battery plug (female)",
        inline_name="Battery plug (male, lead)",
        panel_name="Battery plug (male, board)",
        socket_insert=_GOLD,
        insert_metal=True,
        panel_color=_BLACK,
        color="#e3b21f",
        approximate=[
            "front 13.6 × 6.4 with 1.6 chamfers, body 15.8 × 8.2 with 2.0 chamfers",
            "insertion depth 8",
        ],
        sources=["7.2 mm pitch: https://altronics.cl/uploads/XT-60.pdf", "3.5 mm bullets"],
    ),
    "bal5": ConnectorSpec(
        key="bal5",
        label="Balance connector, 5-pin 2.5 mm (4S)",
        standard="5-way wire-to-board housing, 2.5 mm pitch",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 6.0, _BAL_SOCKET)],
        body=[(2.0, g2.rect(_BAL_W, 4.7, 0.0, 0.0))],
        inline=None,
        panel=(3.0, g2.rect(_BAL_PITCH * (_BAL_N - 1) + 4.9, 6.0)),
        clearance=0.1,
        density=1300.0,
        plug_name="Balance plug 5-pin",
        panel_name="Balance header 5-pin",
        socket_insert=_METAL,
        insert_metal=True,
        panel_color="#efe9d8",
        color="#efe9d8",
        approximate=[f"housing {_BAL_W:g} × 4.2 with two 1.2 ribs", "header depth 6", "insertion depth 6"],
        sources=[
            "header width 2.5 (n − 1) + 4.9, 0.64 mm posts: https://mantech.co.za/datasheets/products/XH-JST.pdf",
        ],
    ),
    "dsub9": ConnectorSpec(
        key="dsub9",
        label="D-sub 9 (DE-9)",
        standard="IEC 60807-3 / MIL-DTL-24308, shell size E",
        gender="female",
        keying="keyed",
        layers=[Layer(0.0, 6.0, _DSUB_SOCKET)],
        body=[(1.0, _DSUB_FLANGE), (32.0, _DSUB_HOOD)],
        inline=(35.0, _DSUB_HOOD),
        panel=(4.0, _DSUB_FLANGE),
        clearance=0.1,
        density=2200.0,
        plug_name="DE-9 female (cable)",
        inline_name="DE-9 male (cable)",
        panel_name="DE-9 male (panel)",
        shell=_METAL,
        plug_insert=_BLACK,
        plug_rim=0.4,
        socket_shell=_METAL,
        socket_insert=_GOLD,
        insert_metal=True,
        color="#4a4d52",
        approximate=[
            "female D 16.30 × 7.80 (male shell 16.92 × 8.36 less its wall)",
            "row spacing 2.84",
            "hood 31.5 × 15.5 × 32",
            "engagement 6",
        ],
        sources=[
            "male shell 16.92 × 8.36, flange 30.81 × 12.55: https://www.farnell.com/datasheets/2722993.pdf",
            "2.77 mm pitch: https://uk.rs-online.com/p/d-sub-connectors/2411334",
        ],
    ),
    # ------------------------------------------------------------ lab bench
    "bnc": ConnectorSpec(
        key="bnc",
        label="BNC (bayonet, 50 Ω)",
        standard="IEC 61169-8",
        gender="male",
        keying="reversible",
        twist=90.0,
        layers=[
            Layer(0.0, 4.95, _BNC_FRONT),  # slot entries; pin and outer contact
            Layer(4.95, 7.05, g2.union(_BNC_SLEEVE.difference(_BNC_ARC), _BNC_INNER)),  # the turn
            Layer(7.05, 9.2, g2.union(_BNC_SLEEVE, _BNC_INNER)),
            Layer(9.2, 9.8, g2.union(_annulus(15.2, 10.1), _BNC_INNER)),  # grip ridges
            Layer(9.8, 10.4, g2.union(_BNC_SLEEVE, _BNC_INNER)),
            Layer(10.4, 11.0, g2.union(_annulus(15.2, 10.1), _BNC_INNER)),
            Layer(11.0, 11.5, g2.union(_BNC_SLEEVE, _BNC_INNER)),
        ],
        body=[(8.0, g2.circle(8.6)), (14.0, g2.circle(7.2))],  # crimp ferrule, boot
        inline=(22.0, g2.circle(12.6)),
        panel=(3.0, g2.circle(12.6)),
        clearance=0.1,
        density=4500.0,
        plug_name="BNC plug (male)",
        inline_name="BNC jack (female, cable)",
        panel_name="BNC jack (female, panel)",
        shell=_METAL,
        socket_shell=_METAL,
        socket_insert=_METAL,
        insert_metal=True,
        panel_color=_METAL,
        color=_BLACK,
        approximate=[
            "studs Ø2.1, 5.5 from the jack's front, out to Ø12.6",
            "slot 2.4 wide, entry 4.95 deep",
            "barrel 9.9 × 11.5",
            "crimp ferrule Ø8.6 × 8, boot Ø7.2 × 14",
        ],
        sources=[
            "interface (barrel 9.78–9.91, sleeve ≥ 10.52 inside, pin 1.32–1.37, 1/4 turn): "
            "https://www.chipfind.net/static/pdf/amphenol/bnc_coaxial_connectors.pdf",
            "coupling nut Ø14.50: https://www.milestek.com/media/descriptions/productspecs/MTCN0001.pdf",
        ],
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


TWIST_STEP = 2.0  # degrees between the sampled positions of a bayonet's turn


def _receptacle_cavity(spec: ConnectorSpec, layer) -> object:
    """The cavity a receptacle keeps clear at the depth of one plug layer: the layer grown by the
    clearance and, for a bayonet, swept through the locking turn made at full depth."""
    if not spec.twist:
        return _cavity(layer.region, spec.clearance)
    key = (spec.key, layer.t0, layer.t1, spec.twist, spec.clearance)
    if key not in _SWEPT:
        steps = max(2, int(math.ceil(abs(spec.twist) / TWIST_STEP)) + 1)
        region = g2.union(*(g2.rotate(layer.region, a) for a in np.linspace(0.0, spec.twist, steps)))
        # simplified: the turned copies of a round outline leave many near-duplicate vertices
        _SWEPT[key] = _cavity(region.simplify(0.01), spec.clearance)
    return _SWEPT[key]


_SWEPT: dict = {}  # swept cavities of the bayonets, computed once


def receptacle_parts(spec: ConnectorSpec, mount: str = "panel") -> list[Part]:
    """The derived receptacle: outline minus the plug grown by the clearance, layer by layer.
    A bayonet's studs come out of it: what its plug never sweeps, pushed in and turned.

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
        solid = outline.difference(_receptacle_cavity(spec, layer))
        z0, z1 = d - layer.t1, d - layer.t0
        if layer.t0 == 0.0:
            z1 += c  # the cavity goes on past the plug tip by the clearance
        parts.append(Part(_scale(solid), z0 * MM, z1 * MM, "mating"))
    parts.append(Part(_scale(outline), (d + c) * MM, total * MM, "body"))
    return [p for p in parts if not p.region.is_empty and p.z1 > p.z0]


def _split_cavity_region(solid, cavity, outline, wall):
    """A receptacle layer (outline minus cavity) in three: the shell wall around the cavity, the
    face beyond it, and the islands standing inside the cavity (tongue, pins, insert)."""
    from shapely.geometry import MultiPolygon

    polys = list(solid.geoms) if isinstance(solid, MultiPolygon) else [solid]
    rim = outline.exterior
    outer = [q for q in polys if q.distance(rim) < 1e-6]
    inner = [q for q in polys if q.distance(rim) >= 1e-6]
    outer = g2.union(*outer) if outer else None
    ring = outer.intersection(cavity.buffer(wall)) if outer is not None else None
    face = outer.difference(cavity.buffer(wall)) if outer is not None else None
    islands = g2.union(*inner) if inner else None
    return ring, face, islands


def receptacle_looks(spec: ConnectorSpec, mount: str = "panel") -> list[tuple]:
    """Visual pieces of a receptacle, [(Part, colour, look)], look in {"metal", "plastic"}.

    Visual only: the same solid as receptacle_parts, cut by colour (shell wall, device face,
    tongue or pins, body). The colliders come from receptacle_parts.
    """
    body_color = spec.panel_color if mount == "panel" else spec.color
    shell = spec.socket_shell or body_color
    _, outline = spec.panel if mount == "panel" else spec.inline
    d = spec.depth
    out = []

    def add(region, z0, z1, color, look):
        if region is not None and not region.is_empty and z1 > z0:
            out.append((Part(_scale(region), z0 * MM, z1 * MM, "look"), color, look))

    for p in receptacle_parts(spec, mount):
        z0, z1 = p.z0 / MM, p.z1 / MM
        if p.kind == "body":
            add(outline, z0, z1, body_color, "plastic")
            continue
        layer = next(la for la in spec.layers if abs((d - la.t1) - z0) < 1e-9)
        cavity = _receptacle_cavity(spec, layer)
        solid = outline.difference(cavity)
        ring, face, islands = _split_cavity_region(solid, cavity, outline, SHELL_WALL)
        add(ring, z0, z1, shell, "metal" if shell in METALS else "plastic")
        add(face, z0, z1, body_color, "plastic")
        add(islands, z0, z1, spec.socket_insert, "metal" if spec.insert_metal else "plastic")
    return out


def plug_looks(spec: ConnectorSpec) -> list[tuple]:
    """Visual pieces of a plug, [(Part, colour, look)], look in {"metal", "plastic", "clear"}.

    The mating part in the shell colour (metal) or clear plastic, cut into bands where the
    spec has some (the insulator rings of a jack plug); the body behind in the body colour.
    """
    d = spec.depth
    mating = spec.shell or spec.color
    look = "clear" if spec.clear else ("metal" if mating in METALS else "plastic")
    out = []
    mating_parts = [p for p in plug_parts(spec) if p.kind != "body"]
    for p in plug_parts(spec):
        if p.kind == "body":
            out.append((p, spec.color, "plastic"))
            continue
        index = mating_parts.index(p)
        color0, look0 = (_METAL, "metal") if index in spec.pin_layers else (mating, look)
        if index in spec.pin_layers or not spec.plug_insert:
            pieces = [(p.region, color0, look0)]
        else:  # a metal rim around an insulating insert
            from shapely.geometry import Polygon

            envelope = g2.union(*[Polygon(q.exterior) for q in _polygons(p.region)])
            core = envelope.buffer(-spec.plug_rim * MM)
            pieces = [
                (p.region.difference(core), color0, look0),
                (p.region.intersection(core), spec.plug_insert, "plastic"),
            ]
        # p spans tip distances t in [d - z1, d - z0]; cut it at the bands
        t_lo, t_hi = d - p.z1 / MM, d - p.z0 / MM
        cuts = sorted({t_lo, t_hi, *[t for b in spec.bands for t in b[:2] if t_lo < t < t_hi]})
        for a, b in zip(cuts, cuts[1:], strict=False):
            band = next((bd for bd in spec.bands if bd[0] <= a and b <= bd[1]), None)
            for region, color, lk in pieces:
                if region.is_empty:
                    continue
                if band:
                    color, lk = band[2], "plastic"
                out.append((Part(region, (d - b) * MM, (d - a) * MM, "look"), color, lk))
    return out


def _polygons(region):
    from shapely.geometry import MultiPolygon

    return list(region.geoms) if isinstance(region, MultiPolygon) else [region]


def part_mesh(parts: list[Part]) -> TriMesh:
    return merge([p.mesh() for p in parts])


def mass_of(parts: list[Part], density: float) -> dict:
    return mass_properties(part_mesh(parts), density)


def fits(
    spec: ConnectorSpec,
    angle_deg: float,
    mount: str = "panel",
    tol: float = 1e-9,
    socket: ConnectorSpec | None = None,
) -> bool:
    """Does the plug, turned by angle about the insertion axis, enter the receptacle fully?

    Plane test, layer by layer: the turned plug cross-section must not overlap
    the receptacle's solid at any depth it goes through. `socket` tests the plug
    of `spec` against the receptacle of another family (a 5.5 × 2.5 plug in a
    5.5 × 2.1 jack); by default the receptacle is the plug's own.
    """
    socket = socket or spec
    outline = socket.panel[1] if mount == "panel" else socket.inline[1]
    solids = [outline.difference(_receptacle_cavity(socket, other)) for other in socket.layers]
    for layer in spec.layers:
        turned = g2.rotate(layer.region, angle_deg)
        # every receptacle layer the turned plug layer passes through on its way in
        for other, solid in zip(socket.layers, solids, strict=True):
            if other.t1 <= layer.t0 + 1e-12:
                continue
            if turned.intersection(solid).area > tol:
                return False
    return True


def locked(spec: ConnectorSpec, mount: str = "panel", tol: float = 1e-9) -> bool:
    """A bayonet, pushed in and turned: can it no longer come straight out? Each plug layer,
    turned by the twist, meets the receptacle's solid at some depth it would pass on its way out."""
    if not spec.twist:
        return False
    outline = spec.panel[1] if mount == "panel" else spec.inline[1]
    for layer in spec.layers:
        turned = g2.rotate(layer.region, spec.twist)
        for other in spec.layers:
            if other.t0 < layer.t1 - 1e-12:
                continue  # on the way out a layer only passes the depths nearer the front
            solid = outline.difference(_receptacle_cavity(spec, other))
            if turned.intersection(solid).area > tol:
                return True
    return False


def _cavity(region, clearance: float):
    return region.buffer(clearance, quad_segs=g2.QUAD_SEGS, join_style="mitre")


def admissible_angles(spec: ConnectorSpec, step: float = 15.0) -> list[float]:
    return [a for a in np.arange(0.0, 360.0, step) if fits(spec, float(a))]


def keying_of(spec: ConnectorSpec) -> str:
    """Keying found from the geometry: none (any angle), square (every quarter turn),
    reversible (0° and 180°) or keyed (one orientation)."""
    angles = admissible_angles(spec)
    if len(angles) == int(360 / 15):
        return "none"
    if 90.0 in angles and 180.0 in angles:
        return "square"
    if 180.0 in angles:
        return "reversible"
    return "keyed"
