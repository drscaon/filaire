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


def test_cables_fall_on_an_obstacle_and_each_other(tmp_path):
    import numpy as np
    from scipy.spatial.transform import Rotation

    from filaire.sim.mujoco_model import coarsen, scene_model, transformed

    cables = []
    for k, preset in enumerate(("usb_c", "audio_jack")):
        folder = write_outputs(generate_scene(preset, count=1, layout="straight", length=0.3), tmp_path)
        c = _cable(folder, preset)
        R = Rotation.from_euler("zx", [90, 30 * (k + 1)], degrees=True).as_matrix()
        centre = np.mean([s.position for s in c.segments], axis=0)
        cables.append(coarsen(transformed(c, R, np.array([0, 0, 0.2 + 0.1 * k]) - R @ centre), 20))
    bar = {"type": "cylinder", "pos": [0, 0, 0.03], "size": [0.03, 0.2], "euler": [0, 90, 0]}
    model, init = scene_model(cables, dt=5e-4, obstacles=[bar])
    data = mujoco.MjData(model)
    init(data)

    # how fast the pile settles depends on the platform's floating point (contact order),
    # so simulate until it is at rest rather than for a fixed time
    def speed():
        return np.abs(data.cvel[1:, 3:]).max()

    while data.time < 1.0 or (speed() > 0.01 and data.time < 6.0):
        mujoco.mj_step(model, data)
    assert data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number == 0
    heights = data.xpos[1:, 2]
    assert heights.min() > -0.001 and heights.max() < 0.08  # on the floor or over the bar
    assert speed() < 0.05, f"still moving after {data.time:.1f} s"
