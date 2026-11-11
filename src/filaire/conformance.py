"""Command line of the Primvaria contract check (the same file in the four generators)::

python -m <generator>.conformance output/<preset>     # files or folders; exit 1 on any issue
"""

from __future__ import annotations

import sys

from .contract import CONTRACT, GENERATOR, check, usd_files


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print(f"usage: python -m {GENERATOR}.conformance FILE_OR_FOLDER...", file=sys.stderr)
        return 2
    files, failed = usd_files(paths), 0
    for f in files:
        issues = check(f)
        failed += bool(issues)
        for msg in issues:
            print(f"{f}: {msg}")
    print(f"{len(files)} OpenUSD files checked against contract {CONTRACT}, {failed} with issues")
    return 1 if failed or not files else 0


if __name__ == "__main__":
    raise SystemExit(main())
