"""The pack of a Primvaria generator: the folder it writes for one preset or set, with two
files that are the same in the four generators (this module is, too).

* ``instances.csv``: one row per asset, read back from the OpenUSD files, so the table and
  the files cannot disagree. Columns: name, file, prim, then the identity (generator,
  version, preset, seed), the aspects that were switched on, every drawn value
  (``variation:<name>``), every measured value (``measured:<name>``) and the generator's own.
* ``manifest.json``: what the pack is (contract, generator, version, pack, seed, aspects,
  number of assets, files) and the generator's summary.

    write_pack(folder, pack="beach_sand", seed=1, aspects=("size", "shape"), summary={...})
    check_pack(folder)        # [] when the table still says what the files say
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pxr import Usd

from . import __version__
from .contract import (
    CONTRACT,
    GENERATOR,
    IDENTITY,
    NAMESPACE,
    SUFFIXES,
    asset_roots,
    labels,
    measured,
    variation,
)

TABLE = "instances.csv"
MANIFEST = "manifest.json"
FIRST = ("name", "file", "prim", "generator", "version", "preset", "seed", "aspects", "classes")


def cell(value) -> str:
    """A value as it is written in the table: lists joined by spaces, floats with 9 digits."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.9g}"
    if isinstance(value, (list, tuple)):
        return " ".join(cell(v) for v in value)
    return "" if value is None else str(value)


def usd_files(folder: Path) -> list[str]:
    """The pack's OpenUSD files, as paths relative to the folder, in name order."""
    return sorted(f.relative_to(folder).as_posix() for f in folder.rglob("*") if f.suffix in SUFFIXES)


def asset_rows(folder: Path, files) -> list[dict]:
    """One row per asset of the pack, from the file that defines it (a scene or a layer that
    only references an asset does not list it again)."""
    rows = []
    for rel in files:
        stage = Usd.Stage.Open(str(folder / rel))
        for prim in asset_roots(stage):
            identifier = Usd.ModelAPI(prim).GetAssetIdentifier().path
            if Path(identifier).name != Path(rel).name:
                continue
            row = {"name": prim.GetName(), "file": rel, "prim": str(prim.GetPath())}
            for key in IDENTITY:
                if key != "contract":
                    row[key] = prim.GetAttribute(f"{NAMESPACE}:{key}").Get()
            drawn = variation(prim)
            row["aspects"] = drawn.pop("aspects", [])
            row["classes"] = labels(prim, "class")
            row.update({f"variation:{k}": v for k, v in drawn.items()})
            row.update({f"measured:{k}": v for k, v in measured(prim).items()})
            rows.append({k: cell(v) for k, v in row.items()})
    return rows


def write_pack(folder, pack, seed, aspects=(), summary=None, extra=None) -> Path:
    """Write ``instances.csv`` and ``manifest.json`` for the OpenUSD files already in ``folder``.

    pack: the preset or set the folder holds. summary: the generator's own statistics.
    extra: {asset name: {column: value}}, the generator's own columns, written last."""
    folder = Path(folder)
    files = usd_files(folder)
    rows = asset_rows(folder, files)
    for row in rows:
        row.update({k: cell(v) for k, v in (extra or {}).get(row["name"], {}).items() if k not in row})
    columns = list(FIRST)
    for prefix in ("variation:", "measured:", ""):
        for row in rows:
            columns += [k for k in row if k not in columns and k.startswith(prefix)]
    with open(folder / TABLE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "contract": CONTRACT,
        "generator": GENERATOR,
        "version": __version__,
        "pack": str(pack),
        "seed": int(seed),
        "aspects": [str(a) for a in aspects],
        "assets": len(rows),
        "classes": sorted({c for row in rows for c in row["classes"].split()}),
        "table": TABLE,
        "files": files,
        "summary": summary or {},
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (folder / MANIFEST).write_text(text, encoding="utf-8")
    return folder / TABLE


def read_table(folder) -> list[dict]:
    with open(Path(folder) / TABLE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_manifest(folder) -> dict:
    return json.loads((Path(folder) / MANIFEST).read_text(encoding="utf-8"))


def check_pack(folder) -> list[str]:
    """How a pack's table and manifest depart from its OpenUSD files (empty: they agree)."""
    folder = Path(folder)
    if not (folder / MANIFEST).exists() or not (folder / TABLE).exists():
        return [f"no {MANIFEST} or no {TABLE}"]
    manifest, problems = read_manifest(folder), []
    for key in "contract generator version pack seed aspects assets classes table files".split():
        if key not in manifest:
            problems.append(f"{MANIFEST}: no {key}")
    if problems:
        return problems
    missing = [f for f in manifest["files"] if not (folder / f).exists()]
    if missing:
        return [f"{MANIFEST}: missing file {f}" for f in missing]
    table = read_table(folder)
    if manifest["assets"] != len(table):
        problems.append(f"{MANIFEST}: {manifest['assets']} assets, {len(table)} rows in {TABLE}")
    absent = [c for c in FIRST if table and c not in table[0]]
    if absent:
        return problems + [f"{TABLE}: no column {c}" for c in absent]
    truth = {(r["file"], r["prim"]): r for r in asset_rows(folder, manifest["files"])}
    listed = {(r["file"], r["prim"]) for r in table}
    problems += [f"{TABLE}: no row for {prim} of {file}" for file, prim in sorted(truth.keys() - listed)]
    for row in table:
        where = f"{TABLE}: {row['name']}"
        expected = truth.get((row["file"], row["prim"]))
        if expected is None:
            problems.append(f"{where}: no such asset in {row['file']}")
            continue
        for key, value in expected.items():
            if row.get(key, "") != value:
                problems.append(f"{where}: {key} is {row.get(key, '')!r}, the file says {value!r}")
        for key in row:
            if key.startswith(("variation:", "measured:")) and row[key] and key not in expected:
                problems.append(f"{where}: {key} is not in the file")
    return problems
