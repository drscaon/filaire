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
