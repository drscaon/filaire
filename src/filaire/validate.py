"""OpenUSD validation of the generated files with the validators shipped with OpenUSD.

Runs every validator of the UsdValidation registry that applies to a single
layer (composition, stage metadata, geometry encapsulation and subsets,
material bindings, shader compliance, UsdPhysics rigid bodies, colliders,
joints and articulations) on the file as authored (its default variant
selections) and on each variant of each cable end, since a variant that is not
selected is not composed. Packaging checks (.usdz) are skipped.

    python -m filaire.validate FILE_OR_FOLDER...
"""

from __future__ import annotations

import sys
from pathlib import Path

from pxr import Usd, UsdValidation

SUFFIXES = (".usd", ".usda", ".usdc")

SKIP = ("usdUtilsValidators:UsdzPackageValidator", "usdUtilsValidators:RootPackageValidator")


def _validators():
    reg = UsdValidation.ValidationRegistry()
    names = [m.name for m in reg.GetAllValidatorMetadata() if m.name not in SKIP]
    return reg.GetOrLoadValidatorsByName(names)


def _variant_states(stage) -> list[dict]:
    """The file as authored, then one selection per end variant (each variant authored somewhere
    is composed at least once)."""
    states, seen = [{}], set()
    for prim in stage.Traverse():
        for name in prim.GetVariantSets().GetNames():
            if not name.startswith("end_"):
                continue
            for v in prim.GetVariantSets().GetVariantSet(name).GetVariantNames():
                if (name, v) not in seen:
                    seen.add((name, v))
                    states.append({(str(prim.GetPath()), name): v})
    return states


def validate(path: str | Path) -> list[str]:
    """Error and warning messages of the OpenUSD validators on a file (empty: compliant)."""
    path = str(path)
    validators = _validators()
    out = []
    for state in _variant_states(Usd.Stage.Open(path)):
        stage = Usd.Stage.Open(path)
        stage.SetEditTarget(stage.GetSessionLayer())  # never touch the file's layer, even in memory
        for (prim_path, vset), v in state.items():
            stage.GetPrimAtPath(prim_path).GetVariantSets().GetVariantSet(vset).SetVariantSelection(v)
        ctx = UsdValidation.ValidationContext(validators)
        for err in ctx.Validate(stage):
            if err.GetType() in (
                UsdValidation.ValidationErrorType.Error,
                UsdValidation.ValidationErrorType.Warn,
            ):
                msg = f"{err.GetType().displayName}: {err.GetMessage()}"
                if msg not in out:
                    out.append(msg)
    return out


def usd_files(paths) -> list[Path]:
    """The OpenUSD files among ``paths``, folders searched recursively."""
    files = []
    for p in map(Path, paths):
        files += sorted(f for f in p.rglob("*") if f.suffix in SUFFIXES) if p.is_dir() else [p]
    return files


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print("usage: python -m filaire.validate FILE_OR_FOLDER...", file=sys.stderr)
        return 2
    missing = [p for p in paths if not Path(p).exists()]
    for p in missing:
        print(f"{p}: not found", file=sys.stderr)
    files, failed = usd_files([p for p in paths if p not in missing]), len(missing)
    for f in files:
        issues = validate(f)
        failed += bool(issues)
        for msg in issues:
            print(f"{f}: {msg}")
    print(f"{len(files)} OpenUSD files checked, {failed} with issues")
    return 1 if failed or not files else 0


if __name__ == "__main__":
    raise SystemExit(main())
