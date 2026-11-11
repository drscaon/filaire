"""The Primvaria OpenUSD contract, version 0: what every generator of the suite writes alike.

The same file in the four generators (Granulaire, Maillage, Filaire, Quincaillerie); the
contract itself is https://github.com/drscaon/primvaria/blob/main/docs/contract.md.

Writing. Every asset root (one generated instance or prototype) is a model of kind
``component`` with ``assetInfo`` (name, identifier, version) and the ``primvaria:*``
attributes: contract, generator, version, preset, seed. The prims above it are group
models (``/World`` an assembly), so tools find, list and instance assets without knowing
the generator::

    set_group(world, assembly=True)
    set_group(scope)
    write_identity(prim, name="Grain_000", preset="beach_sand", seed=1, identifier="./file.usdc")

Checking. ``conformance(stage)`` lists how a stage departs from sections 2, 4 and 5 of the
contract (empty: it conforms); ``python -m <generator>.conformance`` runs it on files.
"""

from __future__ import annotations

from pathlib import Path

from pxr import Kind, Sdf, Usd, UsdGeom, UsdPhysics

from . import __version__

CONTRACT = "0"
GENERATOR = __package__
GENERATORS = ("granulaire", "maillage", "filaire", "quincaillerie")
NAMESPACE = "primvaria"
SUFFIXES = (".usd", ".usda", ".usdc")

# attribute -> (value type, Python type of the value read back)
IDENTITY = {
    "contract": (Sdf.ValueTypeNames.String, str),
    "generator": (Sdf.ValueTypeNames.Token, str),
    "version": (Sdf.ValueTypeNames.String, str),
    "preset": (Sdf.ValueTypeNames.String, str),
    "seed": (Sdf.ValueTypeNames.Int, int),
}
ASSET_INFO = ("name", "identifier", "version")


def set_group(prim, assembly: bool = False) -> None:
    """Make ``prim`` a group model, so the assets under it form a valid model hierarchy."""
    Usd.ModelAPI(prim).SetKind(Kind.Tokens.assembly if assembly else Kind.Tokens.group)


def write_identity(prim, name: str, preset: str, seed: int, identifier: str) -> None:
    """Mark ``prim`` as an asset root: kind, assetInfo and the primvaria:* attributes.

    identifier: path of the file that defines the asset, relative to the file being written
    (``./granulaire_beach_sand.usdc``)."""
    model = Usd.ModelAPI(prim)
    model.SetKind(Kind.Tokens.component)
    model.SetAssetName(name)
    model.SetAssetIdentifier(Sdf.AssetPath(identifier))
    model.SetAssetVersion(__version__)
    values = {
        "contract": CONTRACT,
        "generator": GENERATOR,
        "version": __version__,
        "preset": str(preset),
        "seed": int(seed),
    }
    for key, (type_name, _) in IDENTITY.items():
        prim.CreateAttribute(f"{NAMESPACE}:{key}", type_name).Set(values[key])


def asset_roots(stage) -> list:
    """The asset roots of a stage: its prims of kind component."""
    return [p for p in stage.Traverse() if Usd.ModelAPI(p).GetKind() == Kind.Tokens.component]


def _identity_problems(prim, own: bool) -> list[str]:
    where, problems = str(prim.GetPath()), []
    info = Usd.ModelAPI(prim).GetAssetInfo()
    for key in ASSET_INFO:
        value = info.get(key)
        if not (value.path if isinstance(value, Sdf.AssetPath) else value):
            problems.append(f"{where}: no assetInfo {key}")
    values = {}
    for key, (type_name, py_type) in IDENTITY.items():
        attr = prim.GetAttribute(f"{NAMESPACE}:{key}")
        value = attr.Get() if attr else None
        if value is None or (py_type is str and not value):
            problems.append(f"{where}: no {NAMESPACE}:{key}")
        elif attr.GetTypeName() != type_name:
            problems.append(f"{where}: {NAMESPACE}:{key} is {attr.GetTypeName()}, not {type_name}")
        else:
            values[key] = value
    if values.get("contract", CONTRACT) != CONTRACT:
        problems.append(f"{where}: {NAMESPACE}:contract is {values['contract']!r}, not {CONTRACT!r}")
    generator = values.get("generator")
    if generator is not None and generator not in GENERATORS:
        problems.append(f"{where}: unknown {NAMESPACE}:generator {generator!r}")
    if own and generator in GENERATORS and generator != GENERATOR:
        problems.append(f"{where}: {NAMESPACE}:generator is {generator!r}, not {GENERATOR!r}")
    if own and generator == GENERATOR and values.get("version", __version__) != __version__:
        problems.append(f"{where}: {NAMESPACE}:version is {values['version']!r}, not {__version__!r}")
    return problems


def conformance(stage, own: bool = True) -> list[str]:
    """How a stage departs from the contract's stage, model hierarchy and identity rules
    (empty: it conforms).

    own: the stage was written by this generator, so its assets name it and its version."""
    problems = []
    if UsdGeom.GetStageMetersPerUnit(stage) != 1.0 or UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        problems.append("stage not in metres with Z up")
    if UsdPhysics.GetStageKilogramsPerUnit(stage) != 1.0:
        problems.append("stage not in kilograms")
    default = stage.GetDefaultPrim()
    if not default or not default.IsValid():
        problems.append("no default prim")

    roots = asset_roots(stage)
    if not roots and any(p.IsA(UsdGeom.Gprim) for p in stage.Traverse()):
        problems.append("geometry but no asset root (a prim of kind component)")
    for prim in roots:
        if not prim.IsModel():
            problems.append(f"{prim.GetPath()}: a prim above it is not a group model")
        problems += _identity_problems(prim, own)
    world = stage.GetPrimAtPath("/World")
    if roots and world and Usd.ModelAPI(world).GetKind() != Kind.Tokens.assembly:
        problems.append("/World is not of kind assembly")
    root_paths = {p.GetPath() for p in roots}
    for prim in stage.Traverse():
        if prim.GetPath() not in root_paths and prim.GetAuthoredPropertiesInNamespace(NAMESPACE):
            problems.append(f"{prim.GetPath()}: {NAMESPACE}:* attributes on a prim that is not an asset root")
    return problems


def check(path: str | Path, own: bool = True) -> list[str]:
    """``conformance`` of a file."""
    return conformance(Usd.Stage.Open(str(path)), own)


def usd_files(paths) -> list[Path]:
    """The OpenUSD files among ``paths``, folders searched recursively."""
    files = []
    for p in map(Path, paths):
        files += sorted(f for f in p.rglob("*") if f.suffix in SUFFIXES) if p.is_dir() else [p]
    return files
