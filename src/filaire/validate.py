"""OpenUSD validation of the generated files with the validators shipped with OpenUSD.

Runs every validator of the UsdValidation registry that applies to a single
layer (composition, stage metadata, geometry encapsulation and subsets,
material bindings, shader compliance, UsdPhysics rigid bodies, colliders,
joints and articulations) on each variant of each cable end, since a variant
that is not selected is not composed. Packaging checks (.usdz) are skipped.
"""

from __future__ import annotations

from pathlib import Path

from pxr import Usd, UsdValidation

SKIP = ("usdUtilsValidators:UsdzPackageValidator", "usdUtilsValidators:RootPackageValidator")


def _validators():
    reg = UsdValidation.ValidationRegistry()
    names = [m.name for m in reg.GetAllValidatorMetadata() if m.name not in SKIP]
    return reg.GetOrLoadValidatorsByName(names)


def _variant_states(stage) -> list[dict]:
    """One selection per end variant (each variant authored somewhere is composed at least once)."""
    states, seen = [], set()
    for prim in stage.Traverse():
        for name in prim.GetVariantSets().GetNames():
            if not name.startswith("end_"):
                continue
            for v in prim.GetVariantSets().GetVariantSet(name).GetVariantNames():
                if (name, v) not in seen:
                    seen.add((name, v))
                    states.append({(str(prim.GetPath()), name): v})
    return states or [{}]


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
