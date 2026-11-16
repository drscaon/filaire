"""Reproducibility (contract, section 6, rule 1): a fixed version, preset, seed and options give
the same assets on every platform and Python.

Shared, byte for byte, by the four generators of the suite. Each case of tests/golden/cases.json
runs the generator's command line into a temporary folder, reads back every pack table it wrote
(instances.csv, which holds what was drawn and what was measured, read from the OpenUSD files)
and compares it with the reference stored next to it, tests/golden/<case>.json. Numbers agree
to a relative 1e-7, the precision of the table; text agrees exactly.

A failure means the values changed. If the change is wanted, regenerate the references with
PRIMVARIA_GOLDEN_UPDATE=1 pytest tests/test_golden.py, and list the change in the changelog
under "Changed values" (contract, section 12).
"""

import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent / "golden"
SETUP = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
# the generator's version changes at every release without changing a value
IGNORED = {"version"}
TOLERANCE = 1e-7
UPDATE = os.environ.get("PRIMVARIA_GOLDEN_UPDATE") == "1"


def tables(folder: Path) -> dict:
    """{path of each instances.csv under folder: its rows, ignored columns left out}."""
    found = {}
    for path in sorted(folder.rglob("instances.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            rows = [{k: v for k, v in row.items() if k not in IGNORED} for row in csv.DictReader(f)]
        found[path.relative_to(folder).as_posix()] = rows
    return found


def same(expected: str, actual: str) -> bool:
    """Equal text, or equal numbers within TOLERANCE, token by token for space-separated lists."""
    if expected == actual:
        return True
    a, b = expected.split(), actual.split()
    if len(a) != len(b):
        return False
    for x, y in zip(a, b, strict=True):
        if x == y:
            continue
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            return False
        if not math.isclose(fx, fy, rel_tol=TOLERANCE, abs_tol=1e-12):
            return False
    return True


def differences(expected: dict, actual: dict) -> list:
    """What differs between two results of tables(), in words."""
    found = []
    for table in sorted(set(expected) | set(actual)):
        old, new = expected.get(table), actual.get(table)
        if old is None or new is None:
            found.append(f"{table}: {'missing' if new is None else 'new'}")
            continue
        if len(old) != len(new):
            found.append(f"{table}: {len(new)} rows instead of {len(old)}")
            continue
        for i, (a, b) in enumerate(zip(old, new, strict=True)):
            for key in sorted(set(a) | set(b)):
                if key not in a or key not in b:
                    found.append(f"{table} row {i}: column {key} {'missing' if key not in b else 'new'}")
                elif not same(a[key], b[key]):
                    found.append(f"{table} row {i} ({a.get('name')}): {key} {a[key]!r} became {b[key]!r}")
    return found


@pytest.mark.parametrize("case", SETUP["cases"], ids=lambda case: case["name"])
def test_same_values_as_the_reference(case, tmp_path):
    command = [sys.executable, "-m", SETUP["package"], *case["args"], "--out", str(tmp_path)]
    subprocess.run(command, check=True, capture_output=True)
    actual = tables(tmp_path)
    assert actual, f"{case['name']}: no instances.csv written"
    reference = HERE / f"{case['name']}.json"
    if UPDATE:
        reference.write_text(json.dumps(actual, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(reference.read_text(encoding="utf-8"))
    found = differences(expected, actual)
    assert not found, f"{case['name']}: values differ from the reference:\n" + "\n".join(found[:20])
