"""--no-vary and --nominal, the suite's common way to keep aspects nominal (PRV-35)."""

import csv
import subprocess
import sys

import pytest

BASE = ["generate", "--preset", "usb_c", "--count", "2", "--seed", "4"]


def table(tmp_path, *extra):
    out = tmp_path / "_".join(e.strip("-") for e in extra) if extra else tmp_path / "all"
    subprocess.run(
        [sys.executable, "-m", "filaire", *BASE, *extra, "--out", str(out)], check=True, capture_output=True
    )
    (path,) = out.rglob("instances.csv")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.slow
def test_no_vary_is_the_old_option(tmp_path):
    assert table(tmp_path, "--no-vary", "layout") == table(tmp_path, "--no-vary-layout")


def test_nominal_turns_every_aspect_off(tmp_path):
    rows = table(tmp_path, "--nominal")
    assert all(row["aspects"] == "" for row in rows)


def test_an_unknown_aspect_is_refused(tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "filaire", *BASE, "--no-vary", "nope", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2 and "unknown aspect nope" in run.stderr
