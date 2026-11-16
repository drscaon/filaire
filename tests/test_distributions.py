"""Every cable draws what docs/variation.md declares (PRV-34).

For every preset, thousands of cables are drawn with fixed seeds (the geometry is not built, only
the draws), so the result is the same on every run. Every value must lie in its declared range and
follow its rule: chi-square for choices, Kolmogorov-Smirnov for numbers, at p > 0.001. A cable of
each preset is also built, to check that what it records is what was drawn. The rules are in
filaire.declared, which also writes the documentation.
"""

from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from filaire import declared, generator
from filaire.catalog import PRESETS
from filaire.usd_export import drawn_values

N = 1500
P_MIN = 1e-3
SEED = 20261116
DOC = Path(__file__).parents[1] / "docs" / "variation.md"
# the values passed to build_cable, by column (kwarg, scale to the recorded unit)
KWARGS = {
    "nominal_length_m": "nominal_length",
    "length_m": "length",
    "layout": "layout",
    "color": "color",
    "youngs_modulus_pa": "youngs_modulus",
    "linear_density_kg_per_m": "linear_density",
}


def drawn(preset, monkeypatch, n=N):
    """The arguments build_cable receives for n cables of the preset: the draws, no geometry."""
    monkeypatch.setattr(generator, "build_cable", lambda **kw: kw)
    return [generator.make_cable(preset, i, SEED, generator.Variations(), length=None) for i in range(n)]


def column(rows, name):
    if name in ("end_a", "end_b"):
        return np.array([r["selected"][name[-1]] for r in rows], dtype=object)
    if name == "coil_leads_m":
        return np.array([x for r in rows for x in r["coil_leads"]], float)
    values = [r[KWARGS[name]] for r in rows]
    return np.array(values, dtype=object if isinstance(values[0], str) else float)


def chi2(values, expected: dict, what):
    keys = list(expected)
    observed = np.array([np.sum(values == k) for k in keys])
    assert observed.sum() == len(values), f"{what}: a value outside {keys}"
    if len(keys) > 1:
        p = np.array([expected[k] for k in keys], float)
        assert stats.chisquare(observed, p / p.sum() * len(values)).pvalue > P_MIN, f"{what}: {observed}"


@pytest.mark.parametrize("preset", list(PRESETS))
def test_drawn_as_declared(preset, monkeypatch):
    p = PRESETS[preset]
    rows = drawn(preset, monkeypatch)
    for name, _aspect, rule, _note in declared.DECLARED:
        kind, *args = rule
        what = f"{preset}: {name}"
        if kind == "uniform":
            bounds = declared.field(p, args[0])
            if bounds is None:  # only coiled cords have leads
                continue
            lo, hi = (b * args[1] for b in bounds)
            values = column(rows, name)
            assert lo - 1e-12 <= values.min() and values.max() <= hi + 1e-12, f"{what}: outside {lo} to {hi}"
            assert stats.kstest(values, stats.uniform(lo, hi - lo).cdf).pvalue > P_MIN, what
        elif kind == "weights":
            weights = declared.field(p, args[0])
            values = column(rows, name)
            if name == "nominal_length_m":
                values = values.astype(float)
                weights = {float(k): w for k, w in weights.items()}
            chi2(values, weights, what)
        elif kind == "pick":
            items = declared.field(p, args[0])
            chi2(column(rows, name), {c: items.count(c) for c in dict.fromkeys(items)}, what)
        elif kind == "tolerance":
            e = (column(rows, "length_m") / column(rows, "nominal_length_m") - 1) / p["tolerance"]
            assert np.all(np.abs(e) <= declared.CLIP + 1e-9), f"{what}: beyond ±{declared.CLIP}"
            inner = e[np.abs(e) < declared.CLIP - 1e-9]
            truncated = stats.truncnorm(-declared.CLIP, declared.CLIP)
            assert stats.kstest(inner, truncated.cdf).pvalue > P_MIN, what
            at_bounds, expected = len(e) - len(inner), 2 * stats.norm.sf(declared.CLIP) * len(e)
            _, repeats = np.unique(np.round(inner, 9), return_counts=True)
            assert repeats.max() < 3, f"{what}: a value repeated inside ±{declared.CLIP}: clipped elsewhere?"
            near = abs(at_bounds - expected) < 3.5 * np.sqrt(expected) + 1
            assert near, f"{what}: {at_bounds} at ±{declared.CLIP}, {expected:.0f} expected"


@pytest.mark.parametrize("preset", list(PRESETS))
def test_recorded_is_drawn(preset, monkeypatch):
    """A cable built for real records what was drawn for it, and nothing undeclared."""
    calls = []
    real = generator.build_cable

    def spy(**kw):
        calls.append(kw)
        return real(**kw)

    monkeypatch.setattr(generator, "build_cable", spy)
    cable = generator.make_cable(preset, 0, SEED, generator.Variations(), length=None)
    kw, recorded = calls[0], drawn_values(cable)
    undeclared = set(recorded) - {row[0] for row in declared.DECLARED}
    assert not undeclared, f"{preset}: recorded but not declared: {sorted(undeclared)}"
    for name, arg in KWARGS.items():
        assert (
            recorded[name] == pytest.approx(kw[arg])
            if isinstance(kw[arg], float)
            else recorded[name] == kw[arg]
        )
    assert (recorded["end_a"], recorded["end_b"]) == (kw["selected"]["a"], kw["selected"]["b"])
    if "coil_leads_m" in recorded:  # rounded to whole segments when built
        seg = cable.segments[0].length
        for got, want in zip(recorded["coil_leads_m"], kw["coil_leads"], strict=True):
            assert abs(got - want) <= seg / 2 + 1e-9, f"{preset}: lead {got} m, drawn {want} m"


def test_documentation_is_the_declaration():
    text = DOC.read_text(encoding="utf-8")
    begin, end = "<!-- declared: begin -->\n", "<!-- declared: end -->"
    assert begin in text and end in text, "docs/variation.md has lost its markers"
    block = text[text.index(begin) + len(begin) : text.index(end)].strip()
    assert block == declared.table().strip(), "docs/variation.md is out of date: python -m filaire.declared"
