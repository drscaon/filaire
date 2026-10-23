"""Simulation checks in MuJoCo, on CPU, read from the OpenUSD files.

- **drop**: each tested cable, with its selected ends, is lifted 2 cm and
  dropped on the ground in its authored layout; it must stay finite, not go
  through the ground and come to rest.
- **sag** (straight cables): a sample of the cable is clamped at one end and
  sags under its own weight; the tip deflection is compared with the
  cantilever beam w L⁴ / (8 E I), E I read back from the joint springs in
  the file. The sample length is chosen for a deflection of about 10 % of
  its length, where the linear beam formula holds.
- **coil** (coiled cords): a coil hangs from its top; its extension is
  compared with W / (2 k) for a spring of stiffness k loaded by its own
  weight W.
- **insertion**: for every connector family of the scene, the plug read
  from the cable file is pushed into the fixed receptacle read from
  `sockets.usdc` (and into the receptacle on a cable, when the family has
  one), at 0°, 90° and 180° about the insertion axis. It must go in fully at
  the angles its keying allows and be stopped at the others.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import mujoco
import numpy as np
from pxr import Usd

from .mujoco_model import add_hulls, cable_model, chain_model, coarsen
from .usd_reader import cable_paths, end_options, read_cable, read_sockets

G = 9.81
EXPECTED = {"none": {0, 90, 180}, "reversible": {0, 180}, "keyed": {0}}


# ------------------------------------------------------------------ drop


def drop_check(cable, seconds: float = 3.0, max_links: int | None = 60) -> dict:
    full = len(cable.segments)
    if max_links:
        cable = coarsen(cable, max_links)
    model, init = cable_model(cable)
    data = mujoco.MjData(model)
    init(data)
    steps = int(seconds / model.opt.timestep)
    min_dist = 0.0
    for i in range(steps):
        mujoco.mj_step(model, data)
        if not np.isfinite(data.qpos).all():
            break
        if i >= steps // 2:  # resting contact, after the impact
            for c in data.contact[: data.ncon]:
                if c.geom1 == 0 or c.geom2 == 0:  # the ground plane
                    min_dist = min(min_dist, c.dist)
    finite = bool(np.isfinite(data.qpos).all())
    speed = float(np.abs(data.cvel[1:, 3:]).max()) if finite else math.inf
    heights = data.xpos[1 : 1 + len(cable.segments), 2] if finite else np.array([math.nan])
    radius = cable.segments[0].capsule[0] if cable.segments[0].capsule else cable.segments[0].box[2] / 2
    ok = finite and speed < 0.05 and -min_dist < 0.5 * radius
    return {
        "cable": cable.name,
        "ends": cable.variants,
        "segments": full,
        "links_simulated": len(cable.segments),
        "seconds": seconds,
        "finite": finite,
        "max_speed_end": round(speed, 4),
        "max_ground_penetration_mm": round(-min_dist * 1e3, 3),
        "mean_height_mm": round(float(np.mean(heights)) * 1e3, 2),
        "passed": bool(ok),
    }


# ------------------------------------------------------------- sag / coil


def _settle(model, data, seconds: float, max_seconds: float = 60.0):
    """Simulate at least `seconds`, then until every joint speed is below 1e-6."""
    while data.time < seconds or (np.abs(data.qvel).max() > 1e-6 and data.time < max_seconds):
        mujoco.mj_step(model, data)


def sag_check(cable, links: int = 40) -> dict:
    seg = cable.segments[0]
    L_seg = seg.capsule[1] if seg.capsule else seg.box[0]
    radius = seg.capsule[0] if seg.capsule else seg.box[2] / 2
    w = seg.mass / L_seg * G  # N/m
    j = cable.joints[0]
    EI = j.stiffness["rotY"] * L_seg  # bending in the vertical plane, cable lying flat
    GJ = j.stiffness["rotX"] * L_seg
    L = (0.8 * EI / w) ** (1 / 3)  # tip deflection ≈ 10 % of L
    dl = L / (links + 0.5)
    model = chain_model(links, dl, w / G * dl, radius, EI / dl, GJ / dl, offset=dl / 2)
    data = mujoco.MjData(model)
    _settle(model, data, 4.0)
    tip = data.xpos[-1] + data.xmat[-1].reshape(3, 3) @ np.array([dl / 2, 0, 0])
    sim = float(-tip[2])
    beam = w * L**4 / (8 * EI)
    # same chain, small-angle theory: hinge j (at x_j) turns by M_j / k
    x = dl / 2 + np.arange(links) * dl
    centers = x + dl / 2
    discrete = float(sum(w * dl * (centers[centers > xj] - xj).sum() / (EI / dl) * (L - xj) for xj in x))
    err = sim / beam - 1
    return {
        "cable": cable.name,
        "bending_stiffness_nm2": float(f"{EI:.4g}"),
        "sample_length_m": round(L, 4),
        "tip_deflection_mm": round(sim * 1e3, 2),
        "beam_theory_mm": round(beam * 1e3, 2),
        "discrete_theory_mm": round(discrete * 1e3, 2),
        "error": round(float(err), 4),
        "passed": bool(abs(err) < 0.05),
    }


def coil_check(cable) -> dict:
    n = len(cable.segments)
    seg = cable.segments[0]
    L_seg = seg.capsule[1]
    k_j = cable.joints[0].stiffness["transX"]
    model = chain_model(
        n,
        L_seg,
        seg.mass,
        seg.capsule[0],
        cable.joints[0].stiffness["rotY"],
        cable.joints[0].stiffness["rotX"],
        vertical=True,
        k_axial=k_j,
    )
    data = mujoco.MjData(model)
    _settle(model, data, 6.0)
    ext = float(sum(data.qpos[model.joint(f"s{i}").qposadr[0]] for i in range(n)))
    W = seg.mass * n * G
    k_total = k_j / n  # n slides in series (the first one at the top support)
    theory = W / (2 * k_total) * (n + 1) / n  # exact for n lumped links
    err = ext / theory - 1
    return {
        "cable": cable.name,
        "coil_stiffness_n_per_m": float(f"{k_total:.4g}"),
        "weight_n": round(W, 4),
        "extension_mm": round(ext * 1e3, 2),
        "spring_theory_mm": round(theory * 1e3, 2),
        "error": round(float(err), 4),
        "passed": bool(abs(err) < 0.05),
    }


# -------------------------------------------------------------- insertion


def insertion_check(plug, receptacle_hulls, depth: float, angle_deg: float, seconds: float = 1.0) -> dict:
    """Push a plug along its axis into a receptacle; both in the mate frame (origins coincide when in)."""
    spec = mujoco.MjSpec()
    spec.option.timestep = 1e-4
    spec.option.gravity = [0, 0, 0]
    add_hulls(spec, spec.worldbody, receptacle_hulls, "rec", 0.3, (0.8, 0.8, 0.8, 1))
    start = -(depth + 0.002)
    a = math.radians(angle_deg)
    b = spec.worldbody.add_body(name="plug", pos=[0, 0, 0], quat=[math.cos(a / 2), 0, 0, math.sin(a / 2)])
    b.add_joint(name="slide", type=mujoco.mjtJoint.mjJNT_SLIDE, axis=[0, 0, 1], damping=2.0)
    b.explicitinertial = True
    b.ipos = [0, 0, 0]
    b.iquat = [1, 0, 0, 0]
    b.mass = max(plug.mass, 1e-3)
    b.inertia = list(np.maximum(plug.inertia, 1e-9))
    add_hulls(spec, b, plug.hulls, "plug", 0.3)
    act = spec.add_actuator(name="push", target="slide", trntype=mujoco.mjtTrn.mjTRN_JOINT)
    act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
    act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
    kp = 2000.0
    act.gainprm[0] = kp
    act.biasprm[1] = -kp
    act.forcelimited = True
    act.forcerange = [-5.0, 5.0]
    model = spec.compile()
    data = mujoco.MjData(model)
    q = model.joint("slide").qposadr[0]
    data.qpos[q] = start
    steps = int(seconds / model.opt.timestep)
    for i in range(steps):
        data.ctrl[0] = start + (0.0005 - start) * min(1.0, 1.25 * i / steps)
        mujoco.mj_step(model, data)
    reached = float(data.qpos[q] - start - 0.002)  # how deep the tip went past the front face
    return {
        "angle": angle_deg,
        "depth_reached_mm": round(reached * 1e3, 3),
        "fraction": round(reached / depth, 3),
    }


def insertion_suite(plug, receptacle_hulls, depth: float, keying: str) -> dict:
    expected = EXPECTED[keying]
    trials = []
    for angle in (0, 90, 180):
        r = insertion_check(plug, receptacle_hulls, depth, angle)
        r["should_enter"] = angle in expected
        r["entered"] = r["fraction"] >= 0.95
        r["passed"] = r["entered"] == r["should_enter"] and (r["entered"] or r["fraction"] < 0.6)
        trials.append(r)
    return {
        "keying": keying,
        "depth_mm": round(depth * 1e3, 3),
        "trials": trials,
        "passed": all(t["passed"] for t in trials),
    }


# ------------------------------------------------------------------ folder


def _word(r: dict) -> str:
    return "pass" if r["passed"] else "FAIL"


def run_folder(
    folder: str | Path,
    cables: int = 2,
    seconds: float = 3.0,
    out: str | Path | None = None,
    verbose: bool = True,
    max_links: int | None = 60,
) -> dict:
    folder = Path(folder)
    usd = next(folder.glob("filaire_*.usdc"))
    stage = Usd.Stage.Open(str(usd))
    paths = cable_paths(stage)
    report: dict = {"file": usd.name, "drop": [], "stiffness": None, "insertion": {}}

    def log(text):
        if verbose:
            print(text, flush=True)

    for p in paths[:cables]:
        r = drop_check(read_cable(stage, p), seconds, max_links)
        report["drop"].append(r)
        log(
            f"drop      {r['cable']:<20} {_word(r)}  speed {r['max_speed_end']} m/s, "
            f"penetration {r['max_ground_penetration_mm']} mm  [{r['ends']['a']} / {r['ends']['b']}]"
        )

    first = read_cable(stage, paths[0])
    if first.joints and first.joints[0].free_axial:
        r = coil_check(first)
        log(
            f"coil      {r['cable']:<20} {_word(r)}  extension {r['extension_mm']} mm, "
            f"theory {r['spring_theory_mm']} mm ({r['error']:+.1%})"
        )
    else:
        r = sag_check(first)
        log(
            f"sag       {r['cable']:<20} {_word(r)}  tip {r['tip_deflection_mm']} mm, "
            f"beam {r['beam_theory_mm']} mm ({r['error']:+.1%})"
        )
    report["stiffness"] = r

    sockets_file = folder / "sockets.usdc"
    sockets = read_sockets(sockets_file) if sockets_file.exists() else {}
    variants = end_options(stage, paths[0], "a") + end_options(stage, paths[0], "b")
    for key, sock in sockets.items():
        plug_variant = f"{key}_plug"
        side = "a" if plug_variant in end_options(stage, paths[0], "a") else "b"
        if plug_variant not in variants:
            continue
        cab = read_cable(stage, paths[0], {side: plug_variant})
        plug = cab.ends[side][0]
        depth = float(sock["attrs"]["filaire:insertionDepth"])
        keying = str(sock["attrs"]["filaire:keying"])
        res = {"panel": insertion_suite(plug, sock["hulls"], depth, keying)}
        inline = f"{key}_inline"
        if inline in variants:
            s2 = "a" if inline in end_options(stage, paths[0], "a") else "b"
            rec = read_cable(stage, paths[0], {s2: inline}).ends[s2][0]
            res["inline"] = insertion_suite(plug, rec.hulls, depth, keying)
        report["insertion"][key] = res
        for mount, suite in res.items():
            fr = ", ".join(f"{t['angle']}°: {t['fraction']:.2f}" for t in suite["trials"])
            log(
                f"insertion {key + ' (' + mount + ')':<20} {'pass' if suite['passed'] else 'FAIL'}  "
                f"{keying}, depth reached {fr}"
            )

    report["passed"] = (
        all(r["passed"] for r in report["drop"])
        and report["stiffness"]["passed"]
        and all(s["passed"] for res in report["insertion"].values() for s in res.values())
    )
    out_dir = Path(out) if out else folder / "sim_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sim_test.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"{'PASSED' if report['passed'] else 'FAILED'} — report in {out_dir / 'sim_test.json'}")
    return report
