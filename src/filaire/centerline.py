"""Centre lines: how a cable lies on the ground.

Layouts (all in the ground plane, z set separately):

- straight: a straight line along +x;
- slack: a smooth random curve (heading = sum of a few sines along the
  length), its curvature kept below 1 / minimum bend radius and the curve
  kept free of self-crossings;
- coil: a loose flat spiral, as a cable coiled on the floor: loops at least
  two cable widths apart, starting at a radius that leaves room for the end
  connector.

Each function returns points sampled densely along the curve (arc length
spacing `step`), starting at the origin.
"""

from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString

LAYOUTS = ("straight", "slack", "coil")


def _resample(points: np.ndarray, step: float) -> np.ndarray:
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    n = max(2, int(math.ceil(d[-1] / step)) + 1)
    s = np.linspace(0.0, d[-1], n)
    return np.c_[np.interp(s, d, points[:, 0]), np.interp(s, d, points[:, 1])]


def straight(length: float, step: float) -> np.ndarray:
    n = max(2, int(math.ceil(length / step)) + 1)
    return np.c_[np.linspace(0.0, length, n), np.zeros(n)]


def slack(length: float, step: float, rng: np.random.Generator, min_radius: float) -> np.ndarray:
    kmax = 1.0 / min_radius
    n = max(8, int(math.ceil(length / step)) + 1)
    s = np.linspace(0.0, length, n)
    for attempt in range(40):
        waves = rng.integers(2, 5)
        f = rng.uniform(0.4, 3.0, waves) / length * (2 * math.pi)  # angular frequency per metre
        phase = rng.uniform(0, 2 * math.pi, waves)
        a = rng.normal(0.0, 1.0, waves)
        bound = (np.abs(a) * f).sum()  # max of |dθ/ds| for unit amplitudes
        scale = rng.uniform(0.35, 0.9) * kmax / bound * (0.85**attempt)
        # keep the total turning moderate on long cables (no tight bundles)
        scale = min(scale, 2.2 / np.abs(a).sum())
        theta = scale * (a[None, :] * np.sin(f[None, :] * s[:, None] + phase[None, :])).sum(1)
        theta -= theta.mean()
        ds = np.diff(s)
        tm = 0.5 * (theta[1:] + theta[:-1])
        xy = np.r_[[[0.0, 0.0]], np.cumsum(np.c_[np.cos(tm) * ds, np.sin(tm) * ds], axis=0)]
        if LineString(xy).is_simple:
            return xy
    return straight(length, step)


def coil(length: float, step: float, width: float, start_radius: float, spacing: float = 0.0) -> np.ndarray:
    """Archimedean spiral r = r0 + b φ from the inside out, b = loop spacing / 2π.

    The cable starts at the centre of the spiral, with a half-circle lead of
    radius r0 / 2 that joins the first loop tangentially, so that the inner
    end (and its connector) points into the empty middle, not across the loops.
    """
    spacing = max(spacing, 2.2 * width, width + 0.006)
    b = spacing / (2 * math.pi)
    r0 = start_radius
    lead_len = math.pi * r0 / 2
    if length < lead_len + 2 * math.pi * r0:
        return straight(length, step)
    a = np.linspace(math.pi, 2 * math.pi, 48)  # lower half circle, centre (r0/2, 0)
    lead = np.c_[r0 / 2 + r0 / 2 * np.cos(a), r0 / 2 * np.sin(a)]
    rest = length - lead_len
    # arc length of r0 + b φ is ≈ ∫ (r0 + b φ) dφ for loose spirals; solve for φ_end
    phi_end = (-r0 + math.sqrt(r0 * r0 + 2 * b * rest)) / b
    phi = np.linspace(0.0, phi_end, max(64, int(phi_end * 64)))
    r = r0 + b * phi
    xy = np.vstack([lead, np.c_[r * np.cos(phi), r * np.sin(phi)][1:]])
    xy = _resample(xy, step)
    # exact length: trim or extend along the last tangent
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    if d[-1] > length:
        keep = d <= length
        xy = xy[keep]
    return _resample(xy, step)


def fit_length(points: np.ndarray, length: float) -> np.ndarray:
    """Cut the polyline at the given arc length, or extend it straight along its last tangent."""
    d = arc_length(points)
    if d[-1] >= length:
        keep = d < length
        end = np.array([np.interp(length, d, points[:, k]) for k in range(points.shape[1])])
        return np.vstack([points[keep], end])
    t = points[-1] - points[-2]
    t /= np.linalg.norm(t)
    return np.vstack([points, points[-1] + t * (length - d[-1])])


def tangents(points: np.ndarray) -> np.ndarray:
    t = np.gradient(points, axis=0)
    return t / np.linalg.norm(t, axis=1, keepdims=True)


def arc_length(points: np.ndarray) -> np.ndarray:
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
