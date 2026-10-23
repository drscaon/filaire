import numpy as np
import pytest

from filaire import PRESETS, Variations, generate_scene
from filaire.generator import all_end_variants


def test_default_length_is_one_metre():
    scene = generate_scene("usb_c", count=3)
    assert [round(c.length, 9) for c in scene.cables] == [1.0, 1.0, 1.0]


def test_length_option_and_preset_lengths():
    assert generate_scene("ethernet", count=1, length=2.5).cables[0].length == pytest.approx(2.5)
    lengths = {round(c.nominal_length, 3) for c in generate_scene("ethernet", count=12, length=None).cables}
    assert lengths <= set(PRESETS["ethernet"]["lengths"]) and len(lengths) > 1


@pytest.mark.parametrize("preset", list(PRESETS))
def test_every_preset_generates(preset):
    scene = generate_scene(preset, count=2, seed=3)
    for c in scene.cables:
        assert len(c.segments) >= 2
        assert c.selected["a"] in c.ends["a"] and c.selected["b"] in c.ends["b"]
        assert "cut" in c.ends["a"] and "stripped" in c.ends["b"]  # always authored
        assert all(v > 0 for v in c.joint_stiffness.values())


def test_ends_are_independent_and_free():
    scene = generate_scene("power_c13", count=2, ends={"a": "usb_c_plug", "b": "rj45_inline"})
    for c in scene.cables:
        assert c.selected == {"a": "usb_c_plug", "b": "rj45_inline"}
        assert "usb_c_plug" in c.ends["a"] and "rj45_inline" in c.ends["b"]
    assert "usb_c" in scene.connectors and "rj45" in scene.connectors
    with pytest.raises(ValueError):
        generate_scene("usb_c", count=1, ends={"a": "nope"})
    assert "cut" in all_end_variants() and "xlr3_inline" in all_end_variants()


def test_same_seed_same_cables_and_streams_independent():
    a = generate_scene("hdmi", count=3, seed=7)
    b = generate_scene("hdmi", count=3, seed=7)
    assert [c.layout for c in a.cables] == [c.layout for c in b.cables]
    assert np.allclose(a.cables[1].segments[5].center, b.cables[1].segments[5].center)
    c = generate_scene("hdmi", count=3, seed=7, variations=Variations(color=False))
    assert [x.layout for x in c.cables] == [x.layout for x in a.cables]
    assert {x.color for x in c.cables} == {PRESETS["hdmi"]["colors"][0]}


@pytest.mark.parametrize("layout", ["straight", "slack", "coil"])
def test_layouts_and_plug_frames(layout):
    c = generate_scene("usb_c", count=1, layout=layout, length=1.5).cables[0]
    assert c.layout == layout
    plug = c.ends["b"]["usb_c_plug"]
    # the plug's insertion axis points away from the cable
    last = c.segments[-1]
    assert (plug.origin - last.center) @ plug.rotation[:, 2] > 0


def test_coiled_cord_has_axial_spring():
    c = generate_scene("coiled_handset", count=1, length=0.3).cables[0]
    assert c.axial_stiffness and c.axial_stiffness > 0
    assert c.coil["wire_length"] > 3 * c.length


def test_options_override_draws():
    c = generate_scene("audio_jack", count=1, color="#123456", youngs_modulus=55.0).cables[0]
    assert c.color == "#123456"
    assert c.youngs_modulus == pytest.approx(55e6)
