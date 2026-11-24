"""Where every physical value of Filaire comes from (PRV-33).

Each value that describes the real world (a cable's diameter and weight, a stiffness, a friction, a
connector's dimensions) names its source: a manufacturer's datasheet of a cable of that kind, an
engineering table, or, where none was found, an estimate with what it rests on. Where the source gives
a range, the value and what the generator draws around it must lie within it; tests/test_sources.py
checks both, and that no value is left without a source.

A preset is a kind of cable, not a product: its source is the datasheet of one or two common cables of
that kind (an H05VV-F 3G0.75 mm² cord for the C13 power cord, an RG-58 C/U for the BNC lead). Where a
datasheet gives a single, approximate weight, the range it allows is read as that weight ± 10 %
(APPROXIMATE).

The connector families keep their dimensions in connectors.py, each with the published figures it uses
(`sources`) and what is not from a source (`approximate`); the second table of docs/sources.md lists them.

    python -m filaire.sources     # the tables of docs/sources.md
"""

from __future__ import annotations

from dataclasses import dataclass

from . import cable
from .catalog import CONNECTOR_FRICTION, CONNECTOR_RESTITUTION, JACKETS, POISSON, PRESETS
from .connectors import CONNECTORS

KINDS = ("standard table", "datasheet", "handbook", "estimate")
APPROXIMATE = 0.10  # a datasheet's "approx." weight, read as this relative range


@dataclass(frozen=True)
class Source:
    kind: str  # one of KINDS
    title: str
    urls: tuple = ()
    note: str = ""  # for an estimate: what it rests on


SOURCES = {
    "h05vvf": Source(
        "datasheet",
        "H05VV-F 3G0.75 mm² (EN 50525-2-11), the cord of a C13 power lead: Helukabel 29453, outer Ø 6.0 to "
        "7.6 mm, approx. 60 kg/km; Klaus Faber 030016, outer Ø approx. 6.50 mm, 70 kg/km",
        (
            "https://shop.helukabel.com/cz-en/h05vv-f-05vv-f-m29450/29453",
            "https://shop.faberkabel.de/en/Flexible-wires/Insulated-Cords/H05VV-F/030016.html",
        ),
    ),
    "h03vvh2f": Source(
        "datasheet",
        "H03VVH2-F 2 × 0.75 mm², the flat figure-8 cord of a C7 lead: Sonepar sheet 3.2 × 5.2 to 3.8 × 6.3 "
        "mm, "
        "37 kg/km; Klaus Faber 031049, 6.4 × 3.9 mm, 39 kg/km; Böhm, 32 kg/km; Letronic, 4.0 / 5.6 mm, "
        "40 kg/km. Filaire's figure-8 is d high and 2 d wide",
        (
            "https://res.cloudinary.com/sonepar-fr/raw/upload/s--s3hkfwIM--/v1/documents/49/H03VVH2-F.pdf",
            "https://shop.faberkabel.de/out/downloads/uploads/EN/dbl_h03vvh2.pdf",
            "https://www.icsgroup.ru/boehm-kabel/files/H03VVH2-F.pdf",
            "https://letronic.de/en/produkte/datenblatt/679/h03vvh2-f",
        ),
    ),
    "usb_c_cable": Source(
        "datasheet",
        "USB-C to USB-C cables: Delock 83867, cable diameter approx. 4.0 mm; Tripp Lite U040-C1M-C-5A, 3.8 "
        "mm; "
        "Eaton U420-01M-G25ARA, 5.2 mm",
        (
            "https://www.tme.eu/Document/56902cdf7b045b7ebe7c3a5ed13f06f3/DELOCK-83867_EN.pdf",
            "https://www.mouser.com/datasheet/2/411/u040c1mc5a-1717239.pdf",
            "https://www.eaton.com/us/en-us/skuPage.U420-01M-G25ARA.html",
        ),
    ),
    "telegaertner_cat6": Source(
        "datasheet",
        "Telegärtner Cat.6 U/UTP patch cable 4 × 2 × AWG24/7, PVC: outer diameter 5.4 ± 0.2 mm, weight 33 "
        "kg/km",
        ("https://www.telegaertner.com/fileadmin/pdms_files/100013078_DST_EN.pdf",),
    ),
    "hdmi_cable": Source(
        "datasheet",
        "High Speed HDMI cables, 28 AWG: Delock 82583, cable diameter approx. 7.3 mm; Secomp 11.99.5740, "
        "OD 7.3 ± 0.2 mm",
        (
            "https://www.tme.eu/Document/80c86638e858ac17d0910e7811f372ea/DELOCK-82583_EN.pdf",
            "https://www.secomp.de/media/pdf/s11/11995740_en_data_scmp.pdf",
        ),
    ),
    "mic_cable": Source(
        "datasheet",
        "2 × 0.22 mm² microphone cables: Klotz MY206, Ø 6.0 mm, 0.04 kg/m; Sommer Stage 22 Highflex, Ø 6.40 "
        "mm, "
        "47 g/m; Cordial CMK 222, 6.4 ± 0.2 mm, 53 g/m; Sommer Stage 22 Highflex VT, 6.5 mm, 56 g/m",
        (
            "https://www.bax-shop.fr/downloads/products/9000-0143-3209/my206_e.pdf",
            "https://cdn.shopify.com/s/files/1/0460/9785/8718/files/200-0001.pdf",
            "https://www.thomann.de/be/cordial_cmk_222_sw.htm",
            "https://www.thomann.de/be/sommer_cable_sc_stage_22_highflex_vt.htm",
        ),
    ),
    "speaker_cable": Source(
        "datasheet",
        "2 × 1.5 mm² flat speaker cables: Helukabel 40025, 5.5 × 2.6 mm, approx. 37 kg/km; Prysmian (Draka) "
        "Speaker 2 × 1.5 mm² flat, 3.0 × 6.5 mm. Filaire's figure-8 is d high and 2 d wide",
        (
            "https://shop.helukabel.com/at-en/speaker-cable-m40180/40025",
            "https://mrcable.ru/upload/iblock/f5a/0lynreubljpvhg1e13rdt12gr7ekv1wz.pdf",
        ),
    ),
    "murr_m12": Source(
        "datasheet",
        "Murrelektronik M12 sensor cables, PUR 4 × 0.34 mm²: outer diameter 4.5 mm ± 5 %, cable weight "
        "27.6, 33 "
        "and 36.3 g/m (cable types 3 and 634)",
        (
            "https://www.mouser.lt/datasheet/3/5927/2/7004_12341_6342500_Product_PDF_en.pdf",
            "https://www.mouser.lt/datasheet/3/5927/1/7000_40021_0340500_Product_PDF_en.pdf",
            "https://static.chipdip.ru/lib/045/DOC045045007.pdf",
        ),
    ),
    "3m_3365": Source(
        "datasheet",
        "3M 3365/10 round-conductor flat cable: 10 conductors 28 AWG (7/36), pitch 1.27 mm, ribbon thickness "
        "0.89 mm (0.035 in), width 12.70 mm",
        ("https://azcus.digikey.com/en/products/detail/3m/3365-10-100/1107680",),
    ),
    "can_cable": Source(
        "datasheet",
        "CAN bus cables 2 × 2 × 0.25 mm², PUR: Helukabel 801982, Ø 8.4 ± 0.3 mm, approx. 80 kg/km; Klaus "
        "Faber "
        "101632, Ø 8.4 mm, 68 kg/km",
        (
            "https://assets-cdn.helukabel.com/suppliers/Helukabel/documents/db/HELUKABEL_M801982_EN_GB.pdf",
            "https://www.icsgroup.ru/faber/files/dbl_bus_can_pur.pdf",
        ),
    ),
    "silicone_wire": Source(
        "datasheet",
        "Lapp ÖLFLEX HEAT 180 SiF A, single silicone wire: 14 AWG Ø 3.5 mm, approx. 22 lbs/mft (32.7 kg/km); "
        "12 AWG Ø 4.1 mm, approx. 33 lbs/mft (49.1 kg/km). A battery lead is two of them, of 14 or 12 AWG",
        (
            "https://advantageelectricsupplystoragepublic.s3-us-west-1.amazonaws.com/PartAttachment/2093214/"
            "Datasheet.pdf",
        ),
    ),
    "rg58": Source(
        "datasheet",
        "RG 58 C/U coaxial cable: Lapp 2170000, outer diameter 4.95 ± 0.12 mm, approx. 36 kg/km; "
        "Huber+Suhner "
        "RG_58_C/U, ø 4.95 mm, approx. 37 g/m; RG58 C/U LSF (RS), 4.95 ± 0.2 mm, 40 kg/km",
        (
            "https://static.rapidonline.com/pdf/67-5860_v1.pdf",
            "https://www.mouser.com/datasheet/3/1498/1/H_S_RG_58_CU_EN.PDF",
            "https://nonprod.docs.rs-online.com/024f/0900766b80626139.pdf",
        ),
    ),
    "friction_table": Source(
        "handbook",
        "University of Florida, design lab: static friction on dry concrete and dry wood, soft rubber 0.85 "
        "and "
        "0.95, soft plastic 0.6 and 0.7, hard plastic 0.3 and 0.4 (after Engineering ToolBox)",
        (
            "https://web.mae.ufl.edu/designlab/Class%20Projects/Background%20Information/Friction%20coefficients.htm",
        ),
    ),
    # ------------------------------------------------------------------ estimates
    "thin_cord": Source(
        "estimate",
        "diameter and weight of the thin cords no datasheet was found for (DC barrel, USB micro-B and "
        "A-to-C, "
        "3.5 mm audio, coiled handset)",
        note="the weight is that of the cross-section: its copper (8.96 g/cm³, the cores and shield of the "
        "cable's kind) plus the rest in PVC or TPE (1.0 to 1.4 g/cm³); a DC cord lies under H03VVH2-F 2 × "
        "0.5 mm² "
        "(3.0 × 4.9 mm, 28 kg/km); a USB 2.0 cable's diameter is that of USB-C cables of 3.5 to 4 mm",
    ),
    "cable_weights": Source(
        "estimate",
        "weight of USB-C and HDMI cables, whose datasheets give the diameter only",
        (
            "https://manuals.plus/m/dbbe6d8b0576cc227de6880275c7590ad513fa6616d5b2a5825dc9dfaac89c4e",
            "https://www.farnell.com/datasheets/4813596.pdf",
        ),
        note="the weight of whole cables with their plugs bounds it from above: StarTech USB2CC4MBKE, a 4 m "
        "USB-C cable of 143 g (≤ 36 g/m), StarTech HDMM3MHS, a 3 m 28 AWG HDMI cable of 227 g (≤ 76 g/m); "
        "the lower end is the copper and PVC of the cross-section",
    ),
    "hookup_wire": Source(
        "estimate",
        "diameter and weight of the hobby leads (servo, jumper, balance) and of a ribbon cable's PVC",
        ("https://ibselectronics.in/products/3m/3365-10-100",),
        note="from the cross-section: 26 AWG cores in a 1.05 mm servo wire, 26 to 28 AWG in a 1.3 mm jumper "
        "wire, 22 AWG in a 1.2 mm balance wire, with copper (8.96 g/cm³) and PVC or silicone (1.1 to 1.4 "
        "g/cm³); "
        "for the ribbon, 22 g/m for its full section against 17.9 g/m (544 g per 30.48 m roll) from a dealer",
    ),
    "stiffness": Source(
        "estimate",
        "the effective Young's modulus of a whole cable (jacket, insulation, stranded copper)",
        note="no datasheet gives a cable's bending stiffness; set by kind (soft leads 10 to 25 MPa, cords "
        "20 to "
        "160 MPa, coax and ribbon 150 to 300 MPa) to the orders of magnitude of the published E·I "
        "(docs/physics.md, Checking a preset against a real cable). Not calibrated",
    ),
    "poisson": Source(
        "estimate",
        "the Poisson ratio that gives a cable's torsional stiffness from its modulus",
        note="close to 0.5, as for the rubbery polymers of jackets; the stranded copper inside does not "
        "carry "
        "torsion as a solid would",
    ),
    "pur_friction": Source(
        "estimate",
        "friction of a PUR jacket",
        ("https://komplekt-a.ru/image/catalog/pdf/cfbus.pur.pdf",),
        note="under soft plastic's 0.6: PUR jackets are made low-adhesion for cable tracks (igus CFBUS.PUR)",
    ),
    "restitution": Source(
        "estimate",
        "restitution of a jacket or a connector on the floor",
        note="cables barely bounce: 0.1 for jackets, 0.15 for TPE, 0.2 for the harder connector bodies",
    ),
    "length_tolerance": Source(
        "estimate",
        "spread of a cable's length around its nominal length (relative standard deviation)",
        (
            "https://cdn.iceshop.nl/objects/mmo_114675195_1694772804_3444_50.pdf",
            "https://www.secomp.de/media/pdf/s11/11995740_en_data_scmp.pdf",
        ),
        note="cable datasheets give length tolerances of 0.4 % to 2.5 % (USB-C 4000 ± 15 mm and 500 ± 15 mm, "
        "HDMI 7500 ± 80 mm); 0.5 % to 3 % of standard deviation, wider for hand-made hobby leads",
    ),
    "retail_lengths": Source(
        "estimate",
        "nominal lengths of each kind of cable",
        note="the lengths cables of the kind are commonly sold in; their weights are a choice, not a "
        "statistic",
    ),
    "coiled_cord": Source(
        "estimate",
        "coil diameter, pitch and straight leads of a coiled handset cord",
        note="measured on photographs of handset cords: close-wound, about 8 to 9 mm across, 4 to 8 cm of "
        "straight cord at each end",
    ),
    "usb_c_receptacle": Source(
        "datasheet",
        "USB Type-C receptacle opening 8.34 +0.06/−0.02 × 2.56 ± 0.04 mm (GCT USB4900); the plug's shell "
        "8.25 × 2.40 mm. One manufacturer's tolerance: the plug's own is not included",
        ("https://www.mouser.lt/datasheet/3/1507/1/usb4900.pdf",),
    ),
    "usb_a_interface": Source(
        "datasheet",
        "USB 2.0 Standard-A receptacle opening 12.50 ± 0.10 × 5.12 ± 0.10 mm (TE Connectivity 108-1586), "
        "plug shell 12.00 × 4.50 mm (Adam Tech). The receptacle's spring tabs, which take up part of this "
        "play on a real port, are not modelled",
        (
            "https://en.eeworld.com.cn/datasheet/view/3886042.html",
            "https://dtsheet.com/doc/1419227/usb-connector",
        ),
    ),
    "hdmi_interface": Source(
        "handbook",
        "HDMI Type A plug 13.9 × 4.45 mm, receptacle 14 × 4.55 mm (nominal, no tolerance given)",
        (
            "https://en.wikipedia.org/wiki/HDMI",
            "https://uk.rs-online.com/web/content/product-knowledge/computing-networking/display-video-technology/hdmi-connectors-guide",  # noqa: E501
        ),
    ),
    "jack35_socket": Source(
        "datasheet",
        "3.5 mm socket bore Ø3.60 mm (Same Sky SJ3-35083D, Adam Tech ASJ series) for a Ø3.5 mm plug "
        "(nominal, no tolerance given)",
        (
            "https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/SJ3-35083D-TR/24627981",
            "https://zenode.ai/parts/pxm2n5epom",
        ),
    ),
    "connector_body": Source(
        "estimate",
        "effective density of a connector (plastic body with metal parts) and its clearance in its "
        "receptacle (where no opening is published: around the outline; else inside and at the tip)",
        note="between plastic (1.0 to 1.4 g/cm³) and brass or steel, by the share of metal: 1.2 to 1.4 "
        "g/cm³ for "
        "moulded plugs, 2.2 to 2.5 for metal-shelled ones, 4.5 for a BNC; clearances of 0.05 to 0.3 mm, "
        "tighter for the small precise connectors",
    ),
    "strip": Source(
        "estimate",
        "length of insulated core and of bare copper at a stripped end",
        note="12 mm of core out of the jacket and 6 mm of bare copper, as for a screw terminal",
    ),
}

DIAMETER = {  # preset: (source, range the source gives, mm) for the profile's diameter (height of a figure-8)
    "power_c13": ("h05vvf", 6.0, 7.6),
    "power_c7": ("h03vvh2f", 3.2, 3.9),
    "dc_barrel": ("thin_cord", None, None),
    "usb_c": ("usb_c_cable", 3.8, 5.2),
    "usb_micro": ("thin_cord", None, None),
    "usb_a_to_c": ("thin_cord", None, None),
    "ethernet": ("telegaertner_cat6", 5.2, 5.6),
    "hdmi": ("hdmi_cable", 7.1, 7.5),
    "audio_jack": ("thin_cord", None, None),
    "xlr_mic": ("mic_cable", 6.0, 6.6),
    "speaker_wire": ("speaker_cable", 2.6, 3.0),
    "m12_sensor": ("murr_m12", 4.275, 4.725),
    "ribbon_idc": ("3m_3365", 0.89, 0.89),  # the thickness; the pitch is the source's too
    "can_bus": ("can_cable", 8.1, 8.7),
    "servo_lead": ("hookup_wire", None, None),
    "jumper_wire": ("hookup_wire", None, None),
    "battery_lead": ("silicone_wire", 3.5, 4.1),
    "balance_lead": ("hookup_wire", None, None),
    "bnc_coax": ("rg58", 4.83, 5.07),
    "coiled_handset": ("thin_cord", None, None),
}

_PAIR = 2 * 32.7, 2 * 49.1  # two silicone wires, 14 or 12 AWG
WEIGHT = {  # preset: (source, range the source gives, g/m) for the linear density
    "power_c13": ("h05vvf", 60.0, 70.0),
    "power_c7": ("h03vvh2f", 32.0, 40.0),
    "dc_barrel": ("thin_cord", None, 28.0),  # under H03VVH2-F 2 × 0.5 mm²
    "usb_c": ("cable_weights", None, 143.0 / 4),
    "usb_micro": ("thin_cord", None, None),
    "usb_a_to_c": ("thin_cord", None, None),
    "ethernet": ("telegaertner_cat6", 33.0 * (1 - APPROXIMATE), 33.0 * (1 + APPROXIMATE)),
    "hdmi": ("cable_weights", None, 227.0 / 3),
    "audio_jack": ("thin_cord", None, None),
    "xlr_mic": ("mic_cable", 40.0, 56.0),
    "speaker_wire": ("speaker_cable", 37.0 * (1 - APPROXIMATE), 37.0 * (1 + APPROXIMATE)),
    "m12_sensor": ("murr_m12", 27.6, 36.3),
    "ribbon_idc": ("hookup_wire", 17.0, 22.0),
    "can_bus": ("can_cable", 68.0, 80.0),
    "servo_lead": ("hookup_wire", None, None),
    "jumper_wire": ("hookup_wire", None, None),
    "battery_lead": ("silicone_wire", *_PAIR),
    "balance_lead": ("hookup_wire", None, None),
    "bnc_coax": ("rg58", 36.0, 40.0),
    "coiled_handset": ("thin_cord", None, None),
}

FRICTION = {  # jacket: (source, range the source gives)
    "pvc": ("friction_table", 0.6, 0.7),  # soft plastic
    "tpe": ("friction_table", 0.6, 0.7),
    "lszh": ("friction_table", 0.6, 0.7),
    "silicone": ("friction_table", 0.85, 0.95),  # soft rubber
    "pur": ("pur_friction", None, 0.6),
}


@dataclass(frozen=True)
class Value:
    path: str  # where it is in the code: PRESETS.usb_c.linear_density.min
    value: float
    unit: str
    source: str  # a key of SOURCES
    low: float | None = None  # the range the source gives, when it gives one
    high: float | None = None


def _presets() -> list[Value]:
    out = []
    for key, p in PRESETS.items():
        kind, *dims = p["profile"]
        src, lo, hi = DIAMETER[key]
        name = f"PRESETS.{key}.profile"
        if kind == "flat":
            n, pitch, thickness = dims
            out.append(Value(f"{name}.pitch", pitch, "mm", src))
            out.append(Value(f"{name}.thickness", thickness, "mm", src, lo, hi))
        else:
            out.append(Value(f"{name}.d", dims[0], "mm", src, lo, hi))
        src, lo, hi = WEIGHT[key]
        for end, x in zip(("min", "max"), p["linear_density"], strict=True):
            out.append(Value(f"PRESETS.{key}.linear_density.{end}", x, "g/m", src, lo, hi))
        for end, x in zip(("min", "max"), p["youngs_modulus"], strict=True):
            out.append(Value(f"PRESETS.{key}.youngs_modulus.{end}", x, "MPa", "stiffness"))
        out.append(Value(f"PRESETS.{key}.tolerance", p["tolerance"], "", "length_tolerance"))
        for length in p["lengths"]:
            out.append(Value(f"PRESETS.{key}.lengths.{length:g}", length, "m", "retail_lengths"))
        if "coil" in p:
            c = p["coil"]
            out.append(Value(f"PRESETS.{key}.coil.diameter", c["diameter"], "mm", "coiled_cord"))
            out.append(Value(f"PRESETS.{key}.coil.pitch", c["pitch"], "× wire", "coiled_cord"))
            for end, x in zip(("min", "max"), c["leads"], strict=True):
                out.append(Value(f"PRESETS.{key}.coil.leads.{end}", x, "mm", "coiled_cord"))
    return out


def _materials() -> list[Value]:
    out = [Value("POISSON", POISSON, "", "poisson")]
    for key, j in JACKETS.items():
        src, lo, hi = FRICTION[key]
        out.append(Value(f"JACKETS.{key}.friction", j["friction"], "", src, lo, hi))
        out.append(Value(f"JACKETS.{key}.restitution", j["restitution"], "", "restitution"))
    out += [
        Value("CONNECTOR_FRICTION", CONNECTOR_FRICTION, "", "friction_table", 0.3, 0.4),  # hard plastic
        Value("CONNECTOR_RESTITUTION", CONNECTOR_RESTITUTION, "", "restitution"),
        Value("cable.STRIP_INSULATION", cable.STRIP_INSULATION * 1e3, "mm", "strip"),
        Value("cable.STRIP_COPPER", cable.STRIP_COPPER * 1e3, "mm", "strip"),
    ]
    for key, spec in CONNECTORS.items():
        out.append(Value(f"CONNECTORS.{key}.density", spec.density, "kg/m³", "connector_body"))
        out.append(Value(f"CONNECTORS.{key}.clearance", spec.clearance, "mm", "connector_body"))
        if spec.opening is not None:
            (wlo, whi), (hlo, hhi) = spec.outer_clearance_range()
            cx, cy = spec.outer_clearance
            src = spec.opening.source
            out.append(Value(f"CONNECTORS.{key}.clearance_width", cx, "mm", src, wlo, whi))
            out.append(Value(f"CONNECTORS.{key}.clearance_height", cy, "mm", src, hlo, hhi))
    return out


def values() -> list[Value]:
    """Every physical value of the generator, with its source (connector dimensions: connectors())."""
    return _presets() + _materials()


def connectors() -> list[tuple[str, str, list, list]]:
    """(key, standard, published figures used, dimensions not from a source) for each connector family."""
    return [(key, s.standard, list(s.sources), list(s.approximate)) for key, s in CONNECTORS.items()]


# Numbers in the code that are not about the real world, and so have no source: what they are.
NOT_PHYSICAL = {
    "PRESETS.*.lengths weights, layouts, ends, colors": "how often each nominal length, layout, end and "
    "colour is drawn: a choice, declared in docs/variation.md",
    "generator.DEFAULT_LENGTH": "the length generated when none is asked for (1 m): a choice",
    "cable.DAMPING_TIME": "the joints' damping as a time constant: a simulation setting (docs/physics.md)",
    "physx.CONTACT_OFFSET, REST_OFFSET, POSITION_ITERATIONS, VELOCITY_ITERATIONS, "
    "MAX_DEPENETRATION_VELOCITY": "solver settings of the PhysX layer",
    "newton.ARMATURE_DT, ARMATURE_PERIOD": "the armature the Newton layer adds to each segment's "
    "inertia, sized as the MuJoCo model's (sim/mujoco_model.py): an engine setting",
    "newton.LIMIT": "the rotation limit the Newton layer adds between segments (±170°), wide enough "
    "never to be reached: an engine setting, not a property of the cable",
    "JACKETS.*.roughness, connectors colours, SHELL_WALL": "render appearance, not a physical property",
    "connectors.TWIST_STEP": "how finely a bayonet's turn is sampled to cut its receptacle",
    "declared.CLIP": "the length's normal draw is kept within ±2.5 standard deviations: a choice",
}


def _fmt(x) -> str:
    return "" if x is None else f"{x:.4g}"


def table() -> str:
    """The Markdown tables of docs/sources.md."""
    out = ["| Value | | Unit | Range the source gives | Source |", "|---|---|---|---|---|"]
    for v in values():
        span = f"{_fmt(v.low)} to {_fmt(v.high)}" if v.low is not None or v.high is not None else ""
        span = "" if span == " to " else span.strip()
        out.append(f"| `{v.path}` | {v.value:g} | {v.unit} | {span} | [{v.source}](#{v.source}) |")
    out += ["", "### Connector dimensions", ""]
    out += ["| Family | Standard | Published figures used | Not from a source |", "|---|---|---|---|"]
    for key, standard, used, approx in connectors():
        out.append(f"| `{key}` | {standard} | {'; '.join(used)} | {'; '.join(approx)} |")
    out += ["", "### Sources", ""]
    for key, s in SOURCES.items():
        links = ", ".join(f"<{u}>" for u in s.urls)
        note = f" Estimate: {s.note}." if s.note else ""
        line = f'- <a id="{key}"></a>**{key}** ({s.kind}): {s.title}.{note}'
        out.append(line + (f" {links}" if links else ""))
    out += ["", "### Numbers that are not physical values", ""]
    out += [f"- `{name}`: {why}." for name, why in NOT_PHYSICAL.items()]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(table())
