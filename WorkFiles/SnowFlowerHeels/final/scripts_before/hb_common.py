"""Snow Flower heels, round 1 builder: shared frame, paths, design constants and small numpy helpers.

Local shoe frame (millimetres, RIGHT shoe): u = forward along the posed foot axis, v = z x u (+v = MEDIAL, the
far/closed side; -v = LATERAL, the open ornamented side the reference shows), w = up from the floor.
Origin = HEEL_HeelTipFloor_R (the floor point under the posed heel contact). The left shoe is the exact mirror of the
right one across world X = 0 (the fitting body is symmetric to 0.05 mm, heel_pose.json).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
WORK = ROOT / "WorkFiles" / "SnowFlowerHeels"
R1 = WORK / "r1"
CACHE = R1 / "cache"
REF_PNG = ROOT / "References" / "SnowFlowerHeels" / "snowflowerheels_reference.png"
SPEC = WORK / "heels_spec.json"
POSE_JSON = WORK / "heel_pose.json"
FOOT_POSED_BLEND = WORK / "foot_posed.blend"
ASSET_BLEND = ROOT / "Assets" / "SnowFlowerHeels" / "SnowFlowerHeels.blend"
EXPORT_DIR = ROOT / "Exports" / "SnowFlowerHeels"
RENDER_DIR = ROOT / "Renders" / "SnowFlowerHeels"

# frame (from foot_posed.blend empties; heel_pose.json solve.per_foot.r mirrored)
ORIGIN_R = np.array([-0.15174, -0.01408, 0.0])
U_R = np.array([-0.171304, -0.985218, 0.0])
V_R = np.cross([0.0, 0.0, 1.0], U_R)          # (0.985, -0.171, 0) = toward the body midline = medial for the right foot
W_R = np.array([0.0, 0.0, 1.0])

# ---- design numbers (mm, local frame) -----------------------------------------------------------------------------
D = {
    "toe_tip": (255.0, 10.0, 13.0),     # silver-capped point of the toe (u, v, w): ~67 mm past her toes (u 188)
    "sole_tip_w": 8.0,                  # outsole bottom at the toe tip (toe spring, heel_pose.json design)
    "forefoot_sole": 6.0,               # outsole 4 + insole 2 under the ball (the insole top follows her sole skin)
    "outsole": 4.0,
    "insole_gap": 0.6,                  # insole top below her skin
    "clear_min": 1.2,                   # minimum air between the last and her skin
    "clear_blur": 2.4,                  # the smoothed envelope's offset
    "blur_sigma": 3.0,
    "outline_margin": 2.0,
    "upper_thick": 1.3,
    "toplift_uv": (-15.0, 3.0),         # top-lift centre on the floor (the reference sets it far back under the seat)
    "toplift_size": (8.0, 8.5),         # along u, along v
    "toplift_h": 6.0,
    "collar_back_w": 238.0,             # collar top at the back (far panel); crest spike stands above it
}


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def local_to_world(p_mm: np.ndarray, side: str = "r") -> np.ndarray:
    """(N,3) local mm -> world metres. side 'l' mirrors world X."""
    p = np.asarray(p_mm, dtype=float) / 1000.0
    w = ORIGIN_R + p[..., 0:1] * U_R + p[..., 1:2] * V_R + p[..., 2:3] * W_R
    if side == "l":
        w = w * np.array([-1.0, 1.0, 1.0])
    return w


def world_to_local(p_m: np.ndarray, side: str = "r") -> np.ndarray:
    p = np.asarray(p_m, dtype=float)
    if side == "l":
        p = p * np.array([-1.0, 1.0, 1.0])
    d = p - ORIGIN_R
    return np.stack([d @ U_R, d @ V_R, d @ W_R], axis=-1) * 1000.0


def local_matrix(side: str = "r"):
    """4x4 (numpy) mapping local mm -> world m (mirrored for the left shoe)."""
    m = np.eye(4)
    m[:3, 0] = U_R / 1000.0
    m[:3, 1] = V_R / 1000.0
    m[:3, 2] = W_R / 1000.0
    m[:3, 3] = ORIGIN_R
    if side == "l":
        m = np.diag([-1.0, 1.0, 1.0, 1.0]) @ m
    return m


# ---- small numpy helpers ------------------------------------------------------------------------------------------

def smin(a, b, k):
    """Polynomial smooth minimum (union of SDFs), k in the SDF's units."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def blur3(a: np.ndarray, sigma_vox: float) -> np.ndarray:
    """Separable Gaussian blur of a 3D array (edge-clamped)."""
    r = int(math.ceil(3 * sigma_vox))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / sigma_vox) ** 2)
    k /= k.sum()
    out = a.astype(np.float32)
    for axis in range(3):
        pad = [(0, 0)] * 3
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for i, kv in enumerate(k):
            sl = [slice(None)] * 3
            sl[axis] = slice(i, i + out.shape[axis])
            acc += kv * p[tuple(sl)]
        out = acc
    return out


def blur2(a: np.ndarray, sigma: float) -> np.ndarray:
    r = int(math.ceil(3 * sigma))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    out = a.astype(float)
    for axis in range(2):
        pad = [(0, 0)] * 2
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for i, kv in enumerate(k):
            sl = [slice(None)] * 2
            sl[axis] = slice(i, i + out.shape[axis])
            acc += kv * p[tuple(sl)]
        out = acc
    return out


def resample_polyline(pts: np.ndarray, n: int = None, step: float = None, closed: bool = False) -> np.ndarray:
    pts = np.asarray(pts, dtype=float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    if n is None:
        n = max(2, int(round(total / step)) + 1)
    t = np.linspace(0.0, total, n, endpoint=not closed) if closed else np.linspace(0.0, total, n)
    out = np.stack([np.interp(t, s, pts[:, k]) for k in range(pts.shape[1])], axis=1)
    return out


def catmull(pts: np.ndarray, per_seg: int = 8, closed: bool = False) -> np.ndarray:
    """Centripetal-ish Catmull-Rom through the points (uniform parametrisation)."""
    P = np.asarray(pts, dtype=float)
    if closed:
        P = np.vstack([P[-1:], P, P[:2]])
    else:
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, per_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-2])
    return np.array(out)


def poly_sdf2(points: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Signed distance (negative inside) from 2D points (N,2) to a closed polygon (M,2). Even-odd inside test."""
    pts = np.asarray(points, dtype=float)
    a = np.asarray(poly, dtype=float)
    b = np.roll(a, -1, axis=0)
    best = np.full(len(pts), np.inf)
    inside = np.zeros(len(pts), dtype=bool)
    chunk = 20000
    for c0 in range(0, len(pts), chunk):
        p = pts[c0:c0 + chunk][:, None, :]
        ab = (b - a)[None]
        ap = p - a[None]
        t = np.clip((ap * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
        d = np.linalg.norm(ap - ab * t[..., None], axis=-1)
        best[c0:c0 + chunk] = d.min(1)
        y = p[..., 1]
        cond = ((a[None, :, 1] > y) != (b[None, :, 1] > y))
        xint = a[None, :, 0] + (y - a[None, :, 1]) * (b[None, :, 0] - a[None, :, 0]) / np.where(
            np.abs(b[None, :, 1] - a[None, :, 1]) < 1e-12, 1e-12, b[None, :, 1] - a[None, :, 1])
        cross = cond & (p[..., 0] < xint)
        inside[c0:c0 + chunk] = (cross.sum(1) % 2) == 1
    return np.where(inside, -best, best)


def convex_hull2(p: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain; returns CCW hull."""
    pts = sorted(map(tuple, np.asarray(p, dtype=float)))
    if len(pts) <= 2:
        return np.array(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return np.array(lower[:-1] + upper[:-1])
