"""Contract, section 8: where each MateFrame is, measured on the connectors' own colliders.

The origin is on the mating plane, the receptacle's front face; +Z is the way the plug goes in;
when the two frames coincide, the plug is in, its tip as deep as the declared insertion depth.
The insertion check of ``sim-test`` places plug and receptacle by these frames.
"""

import numpy as np
import pytest
from pxr import Usd, UsdGeom

from filaire import generate_scene, write_outputs
from filaire.catalog import PRESETS
from filaire.sim.usd_reader import _in_frame

TOL = 1e-6  # m: a vertex on the plane, written in single precision


@pytest.fixture(scope="module")
def folders(tmp_path_factory):
    out = tmp_path_factory.mktemp("mate")
    return [write_outputs(generate_scene(key, count=1, seed=1), out) for key in PRESETS]


def _collider_z(body, frame):
    """The z of a body's collider vertices, in the coordinates of its MateFrame."""
    cache = UsdGeom.XformCache()
    hulls = [h for h in body.GetChild("Collision").GetChildren() if h.IsA(UsdGeom.Mesh)]
    assert hulls, body.GetPath()
    return np.concatenate([_in_frame(h, frame, cache)[:, 2] for h in hulls])


def _ends(folder):
    """(connector, role, collider z in the frame, insertion depth) for every end with a MateFrame,
    every variant of both ends of the folder's first cable."""
    stage = Usd.Stage.Open(str(next(folder.glob("filaire_*.usdc"))))
    cable = stage.GetPrimAtPath("/World/Cables").GetChildren()[0]
    found = []
    for side in ("a", "b"):
        vset = cable.GetVariantSets().GetVariantSet(f"end_{side}")
        for variant in vset.GetVariantNames():
            vset.SetVariantSelection(variant)
            body = cable.GetPrimAtPath(f"End_{side.upper()}/Body")
            frame = body.GetChild("MateFrame") if body else None
            if frame:
                attrs = {a.GetName().removeprefix("filaire:"): a.Get() for a in frame.GetAttributes()}
                found.append(
                    (attrs["connector"], attrs["role"], _collider_z(body, frame), attrs["insertionDepth"])
                )
    return found


@pytest.mark.slow
def test_every_connector_is_measured(folders):
    from filaire.connectors import CONNECTORS

    plugs = {connector for f in folders for connector, role, _, _ in _ends(f) if role == "plug"}
    assert plugs == set(CONNECTORS)


def test_a_plug_reaches_its_insertion_depth_along_plus_z(folders):
    for folder in folders:
        for connector, role, z, depth in _ends(folder):
            if role == "plug":
                assert z.max() == pytest.approx(depth, abs=TOL), connector  # the tip, as deep as declared
                assert z.min() < 0, connector  # the rest of the plug stays out, behind the plane


def test_a_receptacle_starts_on_the_plane_and_goes_along_plus_z(folders):
    for folder in folders:
        for connector, role, z, _ in _ends(folder):  # the receptacles at the end of a cable
            if role == "receptacle":
                assert z.min() == pytest.approx(0, abs=TOL), connector
        if not (folder / "sockets.usdc").exists():
            continue  # a family with bare ends only: no receptacle on a panel
        stage = Usd.Stage.Open(str(folder / "sockets.usdc"))
        for socket in stage.GetPrimAtPath("/World/Sockets").GetChildren():  # those on a panel
            assert _collider_z(socket, socket.GetChild("MateFrame")).min() == pytest.approx(0, abs=TOL)


def test_plug_and_receptacle_declare_the_same_mate(folders):
    """Both frames of a pair carry the same insertion depth and clearance: one mate, seen from each side."""
    for folder in (f for f in folders if (f / "sockets.usdc").exists()):
        stage = Usd.Stage.Open(str(folder / "sockets.usdc"))
        sockets = {
            s.GetName(): s.GetChild("MateFrame") for s in stage.GetPrimAtPath("/World/Sockets").GetChildren()
        }
        for connector, role, _, depth in _ends(folder):
            if role == "plug" and connector in sockets:
                assert sockets[connector].GetAttribute("filaire:insertionDepth").Get() == depth
