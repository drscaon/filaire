"""What was drawn for each cable is written into the file (primvaria:variation:*)."""

import pytest
from pxr import Usd

from filaire import Variations, generate_scene, write_outputs
from filaire.contract import asset_roots, variation


def _drawn(tmp_path, preset="hdmi", **variations):
    scene = generate_scene(preset, count=3, seed=7, variations=Variations(**variations))
    folder = write_outputs(scene, tmp_path)
    stage = Usd.Stage.Open(str(folder / f"filaire_{preset}.usdc"))
    return scene, folder, {prim.GetName(): variation(prim) for prim in asset_roots(stage)}


def test_every_cable_carries_its_draws(tmp_path):
    scene, _, drawn = _drawn(tmp_path)
    assert len(drawn) == len(scene.cables)
    for c in scene.cables:
        d = drawn[c.name]
        assert d["aspects"] == ["length", "layout", "ends", "color", "stiffness", "density"]
        assert (d["length_m"], d["nominal_length_m"]) == pytest.approx((c.length, c.nominal_length))
        assert d["layout"] == c.layout and d["color"] == c.color
        assert (d["end_a"], d["end_b"]) == (c.selected["a"], c.selected["b"])
        assert d["youngs_modulus_pa"] == pytest.approx(c.youngs_modulus)
        assert d["linear_density_kg_per_m"] == pytest.approx(c.linear_density)


def test_an_aspect_switched_off_is_recorded_at_its_nominal_value(tmp_path):
    _, _, on = _drawn(tmp_path / "on")
    _, _, off = _drawn(tmp_path / "off", stiffness=False)
    assert (
        len({d["youngs_modulus_pa"] for d in off.values()})
        == 1
        < len({d["youngs_modulus_pa"] for d in on.values()})
    )
    for name, d in off.items():
        assert "stiffness" not in d["aspects"]
        # the other aspects keep their draws
        for key in ("length_m", "layout", "end_a", "end_b", "color", "linear_density_kg_per_m"):
            assert d[key] == on[name][key]


def test_sockets_draw_nothing_and_coiled_cords_record_their_leads(tmp_path):
    _, folder, drawn = _drawn(tmp_path, preset="coiled_handset")
    assert all(len(d["coil_leads_m"]) == 2 for d in drawn.values())
    sockets = Usd.Stage.Open(str(folder / "sockets.usdc"))
    assert all(variation(prim) == {"aspects": []} for prim in asset_roots(sockets))
