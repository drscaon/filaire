# Contributing to Filaire

Thank you for your interest. Filaire is part of
[Primvaria](https://primvaria.com), and every change is checked against the
suite's [mission](https://github.com/drscaon/primvaria/blob/main/MISSION.md):
vary each instance, measure what was generated, prove it in real engines.

## Before you start

- **A bug**: open a bug report with the command you ran and the version.
- **A request** (a new cable or connector family): open a cable or connector request. New assets enter on request, and say what real object and which measurements they are based on.
- **A larger change**: open an issue first, so the approach is agreed before
  the work is done.
- **A change to the file format**: it goes through the
  [OpenUSD contract](https://github.com/drscaon/primvaria/blob/main/docs/contract.md)
  in the primvaria repository first.

## Setting up

```bash
git clone https://github.com/drscaon/filaire
cd filaire
pip install -e ".[dev]"
git config core.hooksPath .githooks   # refuses direct pushes to main
pytest
```

Python 3.11 or later. Everything runs on CPU.

## Making a change

The project follows GitHub Flow: `main` is protected, and every change goes
through a pull request from a short-lived branch (`feat/<name>`,
`fix/<name>`, `docs/<name>`, `chore/<name>`).

1. Write the change with its test. Code, comments and documentation are in
   English.
2. Run `ruff check .`, `ruff format .` and `pytest`.
3. Add a line to `CHANGELOG.md` under *Unreleased*.
4. If a limit remains, write it in the README's Limits section.
5. Open the pull request and fill in the mission checklist of its template.
   CI must be green before merging.

Commit messages start with the kind of change (`feat:`, `fix:`, `docs:`,
`build:`, `chore:`) and say what changed.

## Shared files

`src/filaire/ground.py`, `src/filaire/contract.py`, `src/filaire/conformance.py`
and `tests/test_contract.py` are byte-identical in the four generators. Change
them in all four at once; a check in the primvaria repository fails when they
differ.

## Licence

By contributing you agree that your contribution is released under the
project's [MIT licence](LICENSE). Dimensions and data must come from public
sources that allow it: no copied standards, no proprietary measurements.
