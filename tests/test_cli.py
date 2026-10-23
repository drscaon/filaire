import json

import pytest

from filaire import __version__
from filaire.cli import main


def test_list_and_ends(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "usb_c" in out and "Jackets" in out
    assert main(["ends"]) == 0
    assert "c13_inline" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_generate_options(tmp_path, capsys):
    code = main(
        [
            "generate",
            "--preset",
            "audio_jack",
            "--count",
            "2",
            "--length",
            "0.5",
            "--end-a",
            "cut",
            "--end-b",
            "jack35_inline",
            "--layout",
            "straight",
            "--out",
            str(tmp_path),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    summary = json.loads(out[: out.rindex("}") + 1])
    assert summary["end_a"] == {"cut": 2} and summary["end_b"] == {"jack35_inline": 2}
    assert summary["length_m"] == {"min": 0.5, "max": 0.5}
    assert (tmp_path / "audio_jack" / "filaire_audio_jack.usdc").exists()


def test_bad_options():
    for argv in (
        ["generate", "--count", "0"],
        ["generate", "--end-a", "banana"],
        ["generate", "--length", "-1"],
    ):
        with pytest.raises(SystemExit):
            main(argv)


def test_preview_and_connectors(tmp_path):
    pytest.importorskip("matplotlib")
    main(["generate", "--preset", "ribbon_idc", "--count", "2", "--out", str(tmp_path)])
    assert main(["preview", str(tmp_path / "ribbon_idc")]) == 0
    assert (tmp_path / "ribbon_idc" / "sheet.png").exists()
    assert main(["connectors", "--out", str(tmp_path / "c.png")]) == 0
