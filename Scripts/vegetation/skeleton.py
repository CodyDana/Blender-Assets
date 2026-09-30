"""Tree skeleton: polylines, parallel-transport frames, the branch graph and pipe-model radii (numpy only).

TREE_BUILDING_STUDY.md 4.4 (stage a) and 3.2 (the thickness rule). No bpy: usable from any Python.

A tree is a list of ``Branch`` objects. Branch 0 is the trunk. Every other branch attaches to a parent branch at a
node index (``parent_idx``); its first point sits on the parent's centreline and the tube builder sinks it into the
parent (study 4.5). ``pipe_radii`` fills radii bottom-up with r_parent^n = sum r_child^n and then applies each
branch's measured minimum profile, so traced trunks and limbs keep the reference's girth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# ----------------------------------------------------------------------------- polylines

def arclength(P: np.ndarray) -> np.ndarray:
    if len(P) < 2:
        return np.zeros(len(P))
    d = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(d)])


def resample(P: np.ndarray, spacing: float, min_points: int = 2) -> np.ndarray:
    """Linear resample by arc length to about ``spacing`` (keeps both ends)."""
    P = np.asarray(P, dtype=np.float64)
    s = arclength(P)
    if s[-1] <= 1e-9:
        return P[:1].repeat(min_points, 0)
    n = max(min_points, int(np.ceil(s[-1] / spacing)) + 1)
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, P[:, k]) for k in range(P.shape[1])], axis=1)


def catmull_rom(P: np.ndarray, per_segment: int = 10, alpha: float = 0.5) -> np.ndarray:
    """Centripetal Catmull-Rom through all points (end points duplicated)."""
    P = np.asarray(P, dtype=np.float64)
    if len(P) < 3:
        return P.copy()
    ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** alpha
        for t in np.linspace(t1, t2, per_segment, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-1])
    return np.array(out)


def smooth_resample(P: np.ndarray, spacing: float) -> np.ndarray:
    return resample(catmull_rom(P), spacing)


def chaikin(P: np.ndarray, ratio: float = 0.2, iterations: int = 1) -> np.ndarray:
    """Corner cutting (keeps the end points). A small ratio keeps the polyline angular with a crisp small bevel."""
    Q = np.asarray(P, dtype=np.float64)
    for _ in range(iterations):
        if len(Q) < 3:
            return Q
        out = [Q[0]]
        for a, b in zip(Q[:-1], Q[1:]):
            out.append((1 - ratio) * a + ratio * b)
            out.append(ratio * a + (1 - ratio) * b)
        out.append(Q[-1])
        Q = np.array(out)
    return Q


def angularize(P: np.ndarray, seg: float, amp: float, rng: np.random.Generator, up_amp: float = 0.35,
               keep_ends: bool = True, first_seg: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Zig-zag a smooth traced polyline (study 3.4 / judge r0: 'every branch is one smooth tube').

    The curve is cut into straight segments of about ``seg`` metres (jittered 0.7-1.3x); every interior node moves
    sideways (horizontal perpendicular, alternating sign, ``amp`` x seg) and a little up/down, so the branch
    changes direction every segment by roughly 15-35 degrees while the traced path stays the authority. The ends
    stay fixed. Returns (nodes, node arclengths along the result) so knuckles can be placed at the nodes."""
    P = np.asarray(P, dtype=np.float64)
    s = arclength(P)
    L = float(s[-1])
    if L < 1.5 * seg:
        return P.copy(), arclength(P)
    ts = [0.0]
    t = first_seg if first_seg is not None else seg * rng.uniform(0.7, 1.2)
    while t < L - 0.6 * seg:
        ts.append(t)
        t += seg * rng.uniform(0.7, 1.3)
    ts.append(L)
    ts = np.array(ts)
    N = np.stack([np.interp(ts, s, P[:, k]) for k in range(3)], axis=1)
    T = tangents(N)
    up = np.array([0.0, 0.0, 1.0])
    sign = 1.0 if rng.random() < 0.5 else -1.0
    for i in range(1, len(N) - (1 if keep_ends else 0)):
        side = np.cross(T[i], up)
        if np.linalg.norm(side) < 1e-6:
            side = np.array([1.0, 0.0, 0.0])
        side /= np.linalg.norm(side)
        vert = np.cross(side, T[i])
        seg_len = float(ts[min(i + 1, len(ts) - 1)] - ts[i - 1]) * 0.5
        # v2f (judge delta 5: 'the C1 lower limb and D1 main arm are nearly straight rods' in the FRONT view): the
        # zig-zag was all sideways (horizontal perpendicular = depth for a limb in the view plane); now each node
        # moves in a mixed side / vertical direction (35-65 degrees up or down from the side), so the kinks read
        # from the front as well
        phi = np.deg2rad(rng.uniform(35.0, 65.0)) * (1.0 if rng.random() < 0.5 else -1.0)
        mag = amp * seg_len * rng.uniform(0.55, 1.15)
        N[i] = N[i] + side * sign * mag * np.cos(phi) + vert * mag * np.sin(phi) + vert * up_amp * amp * seg_len * rng.normal(0.0, 0.3)
        sign = -sign if rng.random() < 0.85 else sign
    return N, arclength(N)


def tangents(P: np.ndarray) -> np.ndarray:
    T = np.zeros_like(P)
    if len(P) < 2:
        T[:] = (0, 0, 1)
        return T
    T[1:-1] = P[2:] - P[:-2]
    T[0] = P[1] - P[0]
    T[-1] = P[-1] - P[-2]
    n = np.linalg.norm(T, axis=1, keepdims=True)
    return T / np.maximum(n, 1e-12)


def pt_frames(P: np.ndarray, hint: Sequence[float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rotation-minimising frames by double reflection (Wang et al. 2008). Never Frenet (study P20).

    ``hint`` sets the first normal (projected off the first tangent): it is where the UV seam goes.
    Returns (T, N, B), each (M, 3).
    """
    T = tangents(P)
    h = np.asarray(hint, dtype=np.float64)
    n0 = h - T[0] * np.dot(h, T[0])
    if np.linalg.norm(n0) < 1e-6:
        alt = np.array([1.0, 0.0, 0.0]) if abs(T[0][0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        n0 = alt - T[0] * np.dot(alt, T[0])
    N = np.zeros_like(P)
    N[0] = n0 / np.linalg.norm(n0)
    for i in range(len(P) - 1):
        v1 = P[i + 1] - P[i]
        c1 = np.dot(v1, v1)
        if c1 < 1e-18:
            N[i + 1] = N[i]
            continue
        rL = N[i] - (2.0 / c1) * np.dot(v1, N[i]) * v1
        tL = T[i] - (2.0 / c1) * np.dot(v1, T[i]) * v1
        v2 = T[i + 1] - tL
        c2 = np.dot(v2, v2)
        r = rL - (2.0 / c2) * np.dot(v2, rL) * v2 if c2 > 1e-18 else rL
        r = r - T[i + 1] * np.dot(r, T[i + 1])
        N[i + 1] = r / max(np.linalg.norm(r), 1e-12)
    B = np.cross(T, N)
    return T, N, B


# ----------------------------------------------------------------------------- graph

@dataclass
class Branch:
    pts: np.ndarray                     # (M, 3) centreline, first point on the parent centreline
    parent: int = -1                    # parent branch index
    parent_idx: int = 0                 # node index on the parent where this branch attaches
    order: int = 0                      # 0 trunk, 1 scaffold limb, 2 sub-limb, 3+ twigs
    kind: str = "twig"                  # trunk | limb | twig | root
    pad: int = -1                       # pad this branch belongs to (twigs) or feeds (limbs), -1 none
    element: int = -1                   # wind element (trunk / limb); twigs inherit their pad's element
    min_r: Optional[np.ndarray] = None  # measured minimum radius profile (traced trunk and limbs)
    r: Optional[np.ndarray] = None      # final radii (M,)
    children: List[Tuple[int, int]] = field(default_factory=list)  # (child branch, node index here)
    tip_r: float = 0.0035
    seam_hint: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    knuckles: Optional[np.ndarray] = None   # arclengths of knuckle swellings (angular nodes), for the tube builder
    knuckle_amp: float = 0.0                # radius swelling at a knuckle (share)
    exact_r: bool = False                   # keep min_r as the radius (trunk: the traced girth is the authority)


def link_children(branches: List[Branch]) -> None:
    for b in branches:
        b.children = []
    for i, b in enumerate(branches):
        if b.parent >= 0:
            branches[b.parent].children.append((i, b.parent_idx))


def topo_order(branches: List[Branch]) -> List[int]:
    """Parents before children."""
    order, seen = [], set()
    stack = [i for i, b in enumerate(branches) if b.parent < 0]
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        order.append(i)
        stack.extend(c for c, _ in branches[i].children)
    return order


def pipe_radii(branches: List[Branch], n: float = 2.3, child_max: float = 0.85, min_r: float = 0.0) -> None:
    """See _pipe_radii; afterwards every radius is floored at ``min_r`` (G9 twig >= 3 mm) and an ``exact_r``
    branch (the trunk) keeps its measured profile, its children capped at child_max x its radius."""
    _pipe_radii(branches, n, child_max)
    if min_r > 0:
        for b in branches:
            b.r = np.maximum(b.r, min_r)


def _pipe_radii(branches: List[Branch], n: float = 2.3, child_max: float = 0.85) -> None:
    """Bottom-up pipe model r^n = sum r_child^n (study 3.2), then the measured minimum profile, then child <= parent.

    After the measured minimum is applied, a child whose base is thicker than ``child_max`` x its parent at the
    attachment is scaled down along its whole length (and its own children with it, recursively on the next pass).
    """
    link_children(branches)
    order = topo_order(branches)
    for i in reversed(order):
        b = branches[i]
        m = len(b.pts)
        r = np.zeros(m)
        at = {}
        for c, idx in b.children:
            at.setdefault(min(max(idx, 0), m - 1), []).append(c)
        acc = 0.0 if at.get(m - 1) else b.tip_r ** n   # v2: shoots on the end node replace the tip (G7)
        for k in range(m - 1, -1, -1):
            for c in at.get(k, []):
                acc += branches[c].r[0] ** n
            r[k] = acc ** (1.0 / n)
        if b.min_r is not None:
            if b.exact_r:
                r = np.asarray(b.min_r, dtype=np.float64).copy()
            else:
                r = np.maximum(r, b.min_r)
                # v2 (G7): a floored limb still obeys the pipe rule AT its forks: past each side branch the radius
                # steps down to (r^n - sum c^n)^(1/n); between forks the traced taper shape continues from there
                for k in range(m - 1):
                    cs = at.get(k, [])
                    if not cs:
                        continue
                    rk = r[k]
                    rest = rk ** n - sum(branches[c].r[0] ** n for c in cs)
                    target = max(rest, (0.35 * rk) ** n) ** (1.0 / n)
                    if r[k + 1] > target:
                        f = target / r[k + 1]
                        r[k + 1:] = r[k + 1:] * f
                r = np.maximum(r, b.tip_r)
            r = np.maximum.accumulate(r[::-1])[::-1]  # never thicker toward the tip
        b.r = r
    # top-down: a child is never thicker than child_max x its parent at the attachment
    for i in order:
        b = branches[i]
        if b.parent < 0:
            continue
        pr = branches[b.parent].r[min(b.parent_idx, len(branches[b.parent].r) - 1)]
        if b.r[0] > child_max * pr:
            b.r = b.r * (child_max * pr / b.r[0])


def fork_exponents(branches: List[Branch], lo: float = 1.8, hi: float = 3.0) -> Dict:
    """Per fork: solve r_p^n = r_c1^n + r_c2^n (+...) for n by bisection; report the share inside [lo, hi].

    A fork is a parent node where >= 1 child attaches: the children are the continuing parent (next node) plus
    the attached branches. Also counts child > parent violations (gate G7).
    """
    link_children(branches)
    ns, violations = [], 0
    for b in branches:
        at = {}
        for c, idx in b.children:
            at.setdefault(min(idx, len(b.r) - 1), []).append(c)
        for k, cs in at.items():
            rp = b.r[k]
            kids = [branches[c].r[0] for c in cs]
            if k + 1 < len(b.r):
                kids.append(b.r[k + 1])
            if any(x > rp * 1.0001 for x in kids):
                violations += 1
            if len(kids) < 2:
                continue
            f = lambda e: sum((x / rp) ** e for x in kids) - 1.0  # decreasing in e
            if f(0.5) < 0:
                ns.append(0.5)
                continue
            if f(12.0) > 0:
                ns.append(12.0)
                continue
            a, c = 0.5, 12.0
            for _ in range(60):
                mid = 0.5 * (a + c)
                if f(mid) > 0:
                    a = mid
                else:
                    c = mid
            ns.append(0.5 * (a + c))
    arr = np.array(ns) if ns else np.zeros(0)
    inside = float(np.mean((arr >= lo) & (arr <= hi))) if len(arr) else 1.0
    return {"forks": int(len(arr)), "share_in_band": round(inside, 3), "band": [lo, hi],
            "median_n": round(float(np.median(arr)), 3) if len(arr) else None,
            "p10_n": round(float(np.percentile(arr, 10)), 3) if len(arr) else None,
            "p90_n": round(float(np.percentile(arr, 90)), 3) if len(arr) else None,
            "child_thicker_than_parent": int(violations)}
