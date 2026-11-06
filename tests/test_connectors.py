import pytest

from filaire.connectors import (
    CONNECTORS,
    keying_of,
    mass_of,
    plug_parts,
    receptacle_parts,
)


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_geometric_keying_matches_declared(key):
    spec = CONNECTORS[key]
    assert keying_of(spec) == spec.keying


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_plug_and_receptacle_do_not_overlap_when_mated(key):
    spec = CONNECTORS[key]
    plug = [p for p in plug_parts(spec) if p.kind == "mating"]
    mounts = ["panel"] + (["inline"] if spec.inline else [])
    for mount in mounts:
        rec = receptacle_parts(spec, mount)
        for a in plug:
            for b in rec:
                if min(a.z1, b.z1) - max(a.z0, b.z0) > 1e-9:  # same depth range
                    assert a.region.intersection(b.region).area < 1e-12


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_parts_are_convex_and_massive(key):
    spec = CONNECTORS[key]
    for parts in (plug_parts(spec), receptacle_parts(spec)):
        hulls = [h for p in parts for h in p.convex_hulls()]
        assert hulls
        assert mass_of(parts, spec.density)["mass"] > 0


def test_female_contacts_and_roles():
    # the IEC C13 enters the C14 inlet but carries the female contacts
    assert CONNECTORS["c13"].gender == "female"
    assert CONNECTORS["usb_c"].gender == "male"
    assert CONNECTORS["xlr3"].inline is not None  # the male XLR on a cable


def test_barrel_plugs_only_fit_compatible_jacks():
    from filaire.connectors import fits

    c = CONNECTORS
    assert fits(c["dc5521"], 0) and fits(c["dc5525"], 0)
    # a 2.5 mm bore goes loosely over the 2.1 jack's pin, as on real connectors...
    assert fits(c["dc5525"], 0, socket=c["dc5521"])
    # ...but a 2.1 mm bore cannot go over the 2.5 jack's thicker pin
    assert not fits(c["dc5521"], 0, socket=c["dc5525"])
    assert not fits(c["dc4017"], 0, socket=c["dc5521"])
    assert not fits(c["dc5521"], 0, socket=c["dc4017"])


def test_micro_b_is_keyed_by_its_trapezoid():
    from filaire.connectors import fits

    spec = CONNECTORS["usb_micro"]
    assert fits(spec, 0) and not fits(spec, 180)


def test_robotics_connectors():
    from filaire.connectors import fits

    c = CONNECTORS
    # a servo plug goes in one way only: its rib meets the slot's wall when turned over
    assert fits(c["servo3"], 0) and not fits(c["servo3"], 180)
    # square jumper pins and sockets go on at every quarter turn
    assert keying_of(c["pin_m"]) == "square" and keying_of(c["pin_f"]) == "square"
    # a male jumper pin goes into the female jumper socket on another wire
    assert fits(c["pin_m"], 90, mount="inline")
    # the battery plug and the D-sub are polarised by their outline
    for key in ("batt35", "dsub9"):
        assert fits(c[key], 0) and not fits(c[key], 180)
    assert not fits(c["bal5"], 180)
