"""The looks (visual pieces by colour) cover the same solid as the parts the colliders come from."""

import pytest

from filaire.connectors import (
    CONNECTORS,
    part_mesh,
    plug_looks,
    plug_parts,
    receptacle_looks,
    receptacle_parts,
)
from filaire.mesh3d import mass_properties


def _volume(parts):
    return mass_properties(part_mesh(parts), 1.0)["mass"]


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_panel_receptacle_looks_cover_the_receptacle(key):
    spec = CONNECTORS[key]
    looks = [p for p, _c, _l in receptacle_looks(spec, "panel")]
    assert _volume(looks) == pytest.approx(_volume(receptacle_parts(spec, "panel")), rel=1e-6)


@pytest.mark.parametrize("key", [k for k, s in CONNECTORS.items() if s.inline is not None])
def test_inline_receptacle_looks_cover_the_receptacle(key):
    spec = CONNECTORS[key]
    looks = [p for p, _c, _l in receptacle_looks(spec, "inline")]
    assert _volume(looks) == pytest.approx(_volume(receptacle_parts(spec, "inline")), rel=1e-6)


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_plug_looks_cover_the_plug(key):
    spec = CONNECTORS[key]
    looks = [p for p, _c, _l in plug_looks(spec)]
    assert _volume(looks) == pytest.approx(_volume(plug_parts(spec)), rel=1e-6)


def test_metal_shells_and_inserts():
    looks = {c for _p, c, lk in receptacle_looks(CONNECTORS["usb_c"], "panel") if lk == "metal"}
    assert looks, "USB-C port has a metal shell"
    pins = [lk for _p, _c, lk in receptacle_looks(CONNECTORS["c13"], "panel") if lk == "metal"]
    assert pins, "the C14 inlet's pins are metal"
    bands = [c for _p, c, _l in plug_looks(CONNECTORS["jack35"])]
    assert len(bands) >= 5, "3.5 mm plug cut into tip, rings and insulators"
    assert any(lk == "clear" for _p, _c, lk in plug_looks(CONNECTORS["rj45"]))
