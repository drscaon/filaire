"""Every physical value names its source, and lies in the range its source gives (PRV-33).

docs/sources.md is written from filaire.sources; this test fails on a value of the catalogue with no
source, on a source that is neither cited nor an explained estimate, on a value outside the range its
source gives, on a cable drawn outside it, and on a connector family that says neither where its
dimensions come from nor which are approximate.
"""

from pathlib import Path

import numpy as np
import pytest

from filaire import generator, sources
from filaire.catalog import JACKETS, PRESETS
from filaire.connectors import CONNECTORS

DOC = Path(__file__).parents[1] / "docs" / "sources.md"
BY_PATH = {v.path: v for v in sources.values()}


def test_every_number_of_the_catalogue_names_its_source():
    expected = ["POISSON", "CONNECTOR_FRICTION", "CONNECTOR_RESTITUTION"]
    expected += ["cable.STRIP_INSULATION", "cable.STRIP_COPPER"]
    for key, p in PRESETS.items():
        kind = p["profile"][0]
        dims = ("pitch", "thickness") if kind == "flat" else ("d",)
        expected += [f"PRESETS.{key}.profile.{d}" for d in dims]
        for field in ("linear_density", "youngs_modulus"):
            expected += [f"PRESETS.{key}.{field}.min", f"PRESETS.{key}.{field}.max"]
        expected += [f"PRESETS.{key}.tolerance"] + [f"PRESETS.{key}.lengths.{x:g}" for x in p["lengths"]]
        if "coil" in p:
            expected += [f"PRESETS.{key}.coil.{n}" for n in ("diameter", "pitch", "leads.min", "leads.max")]
    for key in JACKETS:
        expected += [f"JACKETS.{key}.friction", f"JACKETS.{key}.restitution"]
    for key in CONNECTORS:
        expected += [f"CONNECTORS.{key}.density", f"CONNECTORS.{key}.clearance"]
    missing = [path for path in expected if path not in BY_PATH]
    assert not missing, f"no source for {missing}"


def test_values_are_the_code_values():
    for key, p in PRESETS.items():
        lo, hi = p["linear_density"]
        assert BY_PATH[f"PRESETS.{key}.linear_density.min"].value == lo
        assert BY_PATH[f"PRESETS.{key}.linear_density.max"].value == hi
        if p["profile"][0] != "flat":
            assert BY_PATH[f"PRESETS.{key}.profile.d"].value == p["profile"][1]
    for key, j in JACKETS.items():
        assert BY_PATH[f"JACKETS.{key}.friction"].value == j["friction"]


@pytest.mark.parametrize("key", list(sources.SOURCES))
def test_a_source_is_cited_or_an_explained_estimate(key):
    s = sources.SOURCES[key]
    assert s.kind in sources.KINDS
    if s.kind == "estimate":
        assert s.note, f"{key}: an estimate says what it rests on"
    else:
        assert s.urls and all(u.startswith("https://") for u in s.urls), f"{key}: where to read it"


def test_every_source_is_used():
    used = {v.source for v in sources.values()}
    assert set(sources.SOURCES) == used, set(sources.SOURCES) - used


def test_every_value_lies_in_the_range_its_source_gives():
    for v in sources.values():
        assert v.source in sources.SOURCES, v.path
        if v.low is not None:
            assert v.value >= v.low - 1e-9, v.path
        if v.high is not None:
            assert v.value <= v.high + 1e-9, v.path


@pytest.mark.parametrize("preset", list(PRESETS))
def test_drawn_cables_stay_within_their_source(preset, monkeypatch):
    """The linear density each cable is built with, against the range its datasheet gives."""
    monkeypatch.setattr(generator, "build_cable", lambda **kw: kw)
    kwargs = [generator.make_cable(preset, i, 7, generator.Variations(), length=None) for i in range(300)]
    drawn = np.array([kw["linear_density"] for kw in kwargs])
    v = BY_PATH[f"PRESETS.{preset}.linear_density.min"]
    lo = -np.inf if v.low is None else v.low
    hi = np.inf if v.high is None else v.high
    assert lo - 1e-9 <= drawn.min() * 1e3 and drawn.max() * 1e3 <= hi + 1e-9


@pytest.mark.parametrize("key", list(CONNECTORS))
def test_a_connector_says_where_its_dimensions_come_from(key):
    spec = CONNECTORS[key]
    assert spec.sources or spec.approximate, key
    for text in spec.sources:
        for word in text.split():
            if "://" in word:
                assert word.startswith("https://"), (key, word)


def test_documentation_is_the_sources():
    text = DOC.read_text(encoding="utf-8")
    start, end = "<!-- sources: begin -->\n", "<!-- sources: end -->"
    assert start in text and end in text
    written = text[text.index(start) + len(start) : text.index(end)]
    assert written.strip() == sources.table().strip(), "docs/sources.md: run python -m filaire.sources"
