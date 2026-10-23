import math

import numpy as np
import pytest

from filaire import geometry2d as g2
from filaire.cable import section
from filaire.mesh3d import extrude, mass_properties, sweep


def test_circle_second_moment():
    d = 10.0
    s = g2.section_properties(g2.circle(d))
    exact = math.pi * d**4 / 64
    assert s["Iuu"] == pytest.approx(exact, rel=0.02)
    assert s["Ivv"] == pytest.approx(exact, rel=0.02)
    assert s["area"] == pytest.approx(math.pi * d * d / 4, rel=0.01)


def test_rectangle_second_moments_and_holes():
    s = g2.section_properties(g2.rect(4.0, 2.0))
    assert s["Iuu"] == pytest.approx(4 * 2**3 / 12)
    assert s["Ivv"] == pytest.approx(2 * 4**3 / 12)
    hollow = g2.rect(4.0, 2.0).difference(g2.rect(2.0, 1.0))
    assert g2.section_properties(hollow)["Iuu"] == pytest.approx(4 * 8 / 12 - 2 * 1 / 12)


def test_flat_cable_is_soft_across_its_thickness():
    sec = section(("flat", 10, 1.27, 0.9))
    assert sec["Iz"] > 100 * sec["Iy"]  # bends far more easily out of plane
    assert sec["width"] == pytest.approx(12.7e-3)


def test_convex_parts_cover_region_without_overlap():
    region = g2.circle(19.0).difference(g2.circle(2.2, 4.4, 1.6)).difference(g2.rect(2.6, 2.4, 0, 9.5))
    parts = g2.convex_parts(region)
    assert sum(p.area for p in parts) == pytest.approx(region.area, rel=1e-6)
    for p in parts:
        assert p.convex_hull.area == pytest.approx(p.area, rel=1e-5)
    assert g2.union(*parts).symmetric_difference(region).area < 1e-6 * region.area


def test_extrusion_mass_properties():
    m = extrude(g2.rect(2.0, 1.0), 0.0, 3.0)
    mp = mass_properties(m, 1000.0)
    assert mp["volume"] == pytest.approx(6.0)
    assert np.allclose(mp["com"], [0, 0, 1.5])
    assert mp["inertia"][2, 2] == pytest.approx(6000 * (4 + 1) / 12)


def test_sweep_is_closed():
    profile = np.c_[
        np.cos(np.linspace(0, 2 * np.pi, 12, endpoint=False)),
        np.sin(np.linspace(0, 2 * np.pi, 12, endpoint=False)),
    ]
    path = np.c_[np.linspace(0, 10, 11), np.zeros(11), np.zeros(11)]
    normals = np.tile([0.0, 1.0, 0.0], (11, 1))
    mp = mass_properties(sweep(profile * 0.5, path, normals), 1.0)
    assert mp["volume"] == pytest.approx(10 * 12 * 0.5 * 0.25 * math.sin(2 * math.pi / 12), rel=1e-6)
