"""Every script of examples/ runs as it is."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


def test_there_are_examples():
    assert len(EXAMPLES) >= 3


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.stem)
def test_example_runs(script, tmp_path):
    if "mujoco" in script.stem:
        pytest.importorskip("mujoco")
    assert script.read_text().lstrip().startswith('"""'), "an example explains itself in its docstring"
    done = subprocess.run(
        [sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, cwd=tmp_path
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.strip()
