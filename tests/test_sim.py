import pytest

mujoco = pytest.importorskip("mujoco")

from pxr import Usd  # noqa: E402

from filaire import generate_scene, write_outputs  # noqa: E402
from filaire.connectors import CONNECTORS, receptacle_parts  # noqa: E402
from filaire.sim.checks import coil_check, drop_check, insertion_suite, run_folder, sag_check  # noqa: E402
from filaire.sim.usd_reader import cable_paths, read_cable  # noqa: E402


@pytest.fixture(scope="module")
def usb(tmp_path_factory):
    scene = generate_scene("usb_c", count=1, length=0.4, seed=2)
    return write_outputs(scene, tmp_path_factory.mktemp("sim"))


def _cable(folder, name):
    stage = Usd.Stage.Open(str(folder / f"filaire_{name}.usdc"))
    return read_cable(stage, cable_paths(stage)[0])


def test_sag_matches_beam_theory(usb):
    r = sag_check(_cable(usb, "usb_c"))
    assert r["passed"], r


def test_drop_comes_to_rest(usb):
    r = drop_check(_cable(usb, "usb_c"), seconds=1.5)
    assert r["finite"] and r["max_ground_penetration_mm"] < 1.0


def test_coil_matches_spring_theory(tmp_path):
    folder = write_outputs(generate_scene("coiled_handset", count=1, length=0.2), tmp_path)
    r = coil_check(_cable(folder, "coiled_handset"))
    assert r["passed"], r


@pytest.mark.parametrize("key", ["usb_c", "usb_a", "jack35"])
def test_insertion_and_keying(key, usb):
    from filaire.cable import connector_end
    from filaire.sim.usd_reader import Body

    spec = CONNECTORS[key]
    end = connector_end(f"{key}_plug", "#000000")
    plug = Body(key, None, None, end.mass, end.com, [1e-7] * 3, None, hulls=end.hulls)
    rec = [h for p in receptacle_parts(spec) for h in p.convex_hulls()]
    r = insertion_suite(plug, rec, spec.depth * 1e-3, spec.keying)
    assert r["passed"], r


def test_run_folder(usb):
    report = run_folder(usb, cables=1, seconds=1.0, verbose=False)
    assert (usb / "sim_test" / "sim_test.json").exists()
    assert report["insertion"]["usb_c"]["panel"]["passed"]
