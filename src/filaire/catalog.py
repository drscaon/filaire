"""Cable presets: what kind of cable is generated.

Each preset describes *distributions*, not a single cable:

- profile: cross-section of the cable, in mm: ("round", d), ("figure8", d)
  (two round cores side by side, as zip cord), ("flat", n, pitch, thickness)
  (ribbon); a coiled cord adds `coil`;
- conductors: insulation colours of the cores (sRGB), shown when an end is
  stripped;
- jacket: jacket material (see JACKETS) and colours drawn per cable;
- lengths: nominal lengths in m with weights; tolerance: relative standard
  deviation of the actual length;
- youngs_modulus: range of the *effective* Young's modulus of the whole
  cable (jacket, insulation, conductors) in MPa; the bending stiffness is
  E·I of the profile, the torsional one G·J with G = E / (2 (1 + ν));
- linear_density: range in g/m;
- layouts: how the cable lies on the ground, with weights (see centerline.py);
- ends: for each end, the variants with weights; `<connector>_plug` is the
  part that enters, `<connector>_inline` the receptacle on a cable (the
  female end of an extension or a coupler), `cut` a clean cut, `stripped` a
  stripped end with the cores out. Every variant listed is authored in the
  OpenUSD file (a variant set per end); the weights only choose which one is
  selected.
- coil (coiled cords): mean coil diameter in mm, coiled lengths in m, pitch
  as a multiple of the wire size (close-wound ≈ 1).

Values are realistic orders of magnitude for simulation, not measurements of
a specific product; nothing is calibrated yet (see the README).
"""

from __future__ import annotations

CATEGORIES = ["Power", "Data", "Audio", "Industrial", "Telephone"]

POISSON = 0.45  # jacket polymers and stranded conductors, order of magnitude

JACKETS = {
    "pvc": {"label": "PVC", "friction": 0.55, "restitution": 0.1, "roughness": 0.55},
    "tpe": {"label": "TPE", "friction": 0.7, "restitution": 0.15, "roughness": 0.6},
    "pur": {"label": "PUR", "friction": 0.5, "restitution": 0.1, "roughness": 0.45},
    "lszh": {"label": "LSZH", "friction": 0.6, "restitution": 0.1, "roughness": 0.6},
}

# connector plastic and metal, for the physics material of the ends
CONNECTOR_FRICTION = 0.4

_POWER_CORES = ["#7b4a2a", "#2a5fa8", "#c9b52a"]  # brown, blue, green-yellow (drawn yellow)
_BLACKS = ["#1c1c1c", "#202326"]
_PAIRS = ["#e88a2a", "#f2f2f2", "#2e8b3a", "#f2f2f2", "#2a5fa8", "#f2f2f2", "#7b4a2a", "#f2f2f2"]

PRESETS = {
    # ------------------------------------------------------------- Power
    "power_c13": {
        "category": "Power",
        "label": "Power cord, CEE 7/7 to IEC C13",
        "profile": ("round", 6.4),
        "conductors": _POWER_CORES,
        "jacket": "pvc",
        "colors": _BLACKS + ["#e9e9e6", "#8a8d91"],
        "lengths": {1.0: 0.2, 1.5: 0.3, 1.8: 0.3, 2.0: 0.2},
        "tolerance": 0.01,
        "youngs_modulus": (60.0, 120.0),
        "linear_density": (75.0, 90.0),
        "layouts": {"slack": 0.6, "coil": 0.25, "straight": 0.15},
        "ends": {
            "a": {"c13_plug": 1.0},
            "b": {"cee77_plug": 0.7, "c13_inline": 0.2, "stripped": 0.1},
        },
    },
    "power_c7": {
        "category": "Power",
        "label": "Figure-8 power cord, Europlug to IEC C7",
        "profile": ("figure8", 3.4),
        "conductors": _POWER_CORES[:2],
        "jacket": "pvc",
        "colors": _BLACKS + ["#e9e9e6"],
        "lengths": {1.5: 0.6, 1.8: 0.4},
        "tolerance": 0.01,
        "youngs_modulus": (50.0, 100.0),
        "linear_density": (30.0, 40.0),
        "layouts": {"slack": 0.7, "coil": 0.15, "straight": 0.15},
        "ends": {"a": {"c7_plug": 1.0}, "b": {"cee716_plug": 0.85, "stripped": 0.15}},
    },
    # -------------------------------------------------------------- Data
    "usb_c": {
        "category": "Data",
        "label": "USB-C to USB-C",
        "profile": ("round", 4.0),
        "conductors": ["#c0392b", "#1c1c1c", "#2e8b3a", "#f2f2f2"],
        "jacket": "tpe",
        "colors": _BLACKS + ["#f0f0ee", "#9aa0a6"],
        "lengths": {0.5: 0.2, 1.0: 0.5, 2.0: 0.3},
        "tolerance": 0.01,
        "youngs_modulus": (40.0, 90.0),
        "linear_density": (30.0, 45.0),
        "layouts": {"slack": 0.6, "coil": 0.2, "straight": 0.2},
        "ends": {"a": {"usb_c_plug": 1.0}, "b": {"usb_c_plug": 0.8, "usb_c_inline": 0.2}},
    },
    "usb_a_to_c": {
        "category": "Data",
        "label": "USB-A to USB-C",
        "profile": ("round", 3.8),
        "conductors": ["#c0392b", "#1c1c1c", "#2e8b3a", "#f2f2f2"],
        "jacket": "tpe",
        "colors": _BLACKS + ["#f0f0ee"],
        "lengths": {1.0: 0.6, 2.0: 0.4},
        "tolerance": 0.01,
        "youngs_modulus": (40.0, 90.0),
        "linear_density": (25.0, 40.0),
        "layouts": {"slack": 0.6, "coil": 0.2, "straight": 0.2},
        "ends": {"a": {"usb_a_plug": 1.0}, "b": {"usb_c_plug": 1.0}},
    },
    "ethernet": {
        "category": "Data",
        "label": "Ethernet patch cord, Cat 6 RJ45",
        "profile": ("round", 6.0),
        "conductors": _PAIRS,
        "jacket": "pvc",
        "colors": ["#2a6fbf", "#9aa0a6", "#e3c22a", "#c0392b", "#2e8b3a", "#1c1c1c"],
        "lengths": {0.5: 0.2, 1.0: 0.3, 2.0: 0.3, 3.0: 0.2},
        "tolerance": 0.005,
        "youngs_modulus": (80.0, 150.0),
        "linear_density": (40.0, 55.0),
        "layouts": {"slack": 0.6, "coil": 0.25, "straight": 0.15},
        "ends": {"a": {"rj45_plug": 1.0}, "b": {"rj45_plug": 0.85, "rj45_inline": 0.15}},
    },
    "hdmi": {
        "category": "Data",
        "label": "HDMI cable, type A",
        "profile": ("round", 7.0),
        "conductors": ["#c0392b", "#2e8b3a", "#2a5fa8", "#f2f2f2", "#1c1c1c"],
        "jacket": "pvc",
        "colors": _BLACKS,
        "lengths": {1.0: 0.3, 1.5: 0.3, 2.0: 0.4},
        "tolerance": 0.01,
        "youngs_modulus": (80.0, 160.0),
        "linear_density": (60.0, 90.0),
        "layouts": {"slack": 0.6, "coil": 0.25, "straight": 0.15},
        "ends": {"a": {"hdmi_a_plug": 1.0}, "b": {"hdmi_a_plug": 0.85, "hdmi_a_inline": 0.15}},
    },
    # ------------------------------------------------------------- Audio
    "audio_jack": {
        "category": "Audio",
        "label": "3.5 mm audio cable (jack to jack)",
        "profile": ("round", 3.5),
        "conductors": ["#c0392b", "#f2f2f2", "#b87333"],
        "jacket": "tpe",
        "colors": _BLACKS + ["#f0f0ee", "#c0392b"],
        "lengths": {0.5: 0.2, 1.0: 0.5, 2.0: 0.3},
        "tolerance": 0.01,
        "youngs_modulus": (30.0, 70.0),
        "linear_density": (12.0, 20.0),
        "layouts": {"slack": 0.65, "coil": 0.2, "straight": 0.15},
        "ends": {"a": {"jack35_plug": 1.0}, "b": {"jack35_plug": 0.8, "jack35_inline": 0.2}},
    },
    "xlr_mic": {
        "category": "Audio",
        "label": "Microphone cable, XLR3 female to male",
        "profile": ("round", 6.0),
        "conductors": ["#c0392b", "#f2f2f2"],
        "jacket": "pvc",
        "colors": _BLACKS,
        "lengths": {3.0: 0.4, 5.0: 0.4, 10.0: 0.2},
        "tolerance": 0.01,
        "youngs_modulus": (20.0, 50.0),
        "linear_density": (50.0, 70.0),
        "layouts": {"coil": 0.5, "slack": 0.4, "straight": 0.1},
        "ends": {"a": {"xlr3_plug": 1.0}, "b": {"xlr3_inline": 1.0}},
    },
    "speaker_wire": {
        "category": "Audio",
        "label": "Speaker wire 2 × 1.5 mm² (zip cord)",
        "profile": ("figure8", 3.2),
        "conductors": ["#c0392b", "#1c1c1c"],
        "jacket": "pvc",
        "colors": ["#d9d4c8", "#1c1c1c", "#c0392b"],
        "lengths": {2.0: 0.4, 3.0: 0.4, 5.0: 0.2},
        "tolerance": 0.02,
        "youngs_modulus": (40.0, 90.0),
        "linear_density": (40.0, 55.0),
        "layouts": {"slack": 0.6, "coil": 0.3, "straight": 0.1},
        "ends": {"a": {"stripped": 0.7, "cut": 0.3}, "b": {"stripped": 0.7, "cut": 0.3}},
    },
    # -------------------------------------------------------- Industrial
    "m12_sensor": {
        "category": "Industrial",
        "label": "Sensor cable, M12 A-coded female, open end",
        "profile": ("round", 5.0),
        "conductors": ["#7b4a2a", "#f2f2f2", "#2a5fa8", "#1c1c1c"],
        "jacket": "pur",
        "colors": ["#3a3f45", "#e88a2a", "#8a8d91"],
        "lengths": {2.0: 0.5, 5.0: 0.5},
        "tolerance": 0.01,
        "youngs_modulus": (50.0, 100.0),
        "linear_density": (35.0, 50.0),
        "layouts": {"coil": 0.5, "slack": 0.4, "straight": 0.1},
        "ends": {"a": {"m12a_plug": 1.0}, "b": {"stripped": 0.8, "cut": 0.2}},
    },
    "ribbon_idc": {
        "category": "Industrial",
        "label": "Ribbon cable 10-way, IDC 2 × 5 sockets",
        "profile": ("flat", 10, 1.27, 0.9),
        "conductors": ["#c0392b"] + ["#9aa0a6"] * 9,
        "jacket": "pvc",
        "colors": ["#9aa0a6", "#8a8d91"],
        "lengths": {0.15: 0.4, 0.3: 0.4, 0.5: 0.2},
        "tolerance": 0.02,
        "youngs_modulus": (150.0, 300.0),
        "linear_density": (8.0, 12.0),
        "layouts": {"straight": 0.5, "slack": 0.5},
        "ends": {"a": {"idc10_plug": 1.0}, "b": {"idc10_plug": 0.9, "cut": 0.1}},
    },
    # --------------------------------------------------------- Telephone
    "coiled_handset": {
        "category": "Telephone",
        "label": "Coiled handset cord, RJ9 (4P4C)",
        "profile": ("round", 2.8),
        "conductors": ["#c0392b", "#2e8b3a", "#e3c22a", "#1c1c1c"],
        "jacket": "pvc",
        "colors": _BLACKS + ["#e9e4d8", "#9aa0a6"],
        "lengths": {0.25: 0.5, 0.35: 0.5},  # coiled (relaxed) length
        "tolerance": 0.03,
        "youngs_modulus": (30.0, 60.0),
        "linear_density": (10.0, 15.0),  # of the wire itself
        "layouts": {"straight": 0.4, "slack": 0.6},
        "coil": {"diameter": 8.5, "pitch": 1.05},
        "ends": {"a": {"rj9_plug": 1.0}, "b": {"rj9_plug": 1.0}},
    },
}


def end_connector(variant: str) -> tuple[str | None, str]:
    """('usb_c', 'plug') for 'usb_c_plug', (None, 'cut') for 'cut'."""
    for role in ("plug", "inline"):
        if variant.endswith("_" + role):
            return variant[: -len(role) - 1], role
    return None, variant


def connectors_of(preset: dict) -> list[str]:
    """Connector families used by a preset's ends, in order of appearance."""
    out = []
    for end in ("a", "b"):
        for variant in preset["ends"][end]:
            key, _ = end_connector(variant)
            if key and key not in out:
                out.append(key)
    return out
