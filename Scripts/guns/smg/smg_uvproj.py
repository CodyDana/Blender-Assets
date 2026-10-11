"""SMG01 UV projection helper (plain Python): the box frame's six charts (gunlib.uvchart) plus 20 DIAGONAL charts for
slanted faces (chamfers, 45 deg rounds, a ball's shoulders), so no face is projected more than ~22 deg off its own
normal. A box chart compresses a face at angle a by cos(a) in one direction: a 45 deg chamfer read sqrt(cos 45) =
0.84 of its class density, under the plan's B9 bar (classes +-15 %, P5 vs median). Keys: 0..5 box (gunlib), 6..25
the diagonals below. Used by smg_uv (W2) and the LOD transfer (W3).
"""
from __future__ import annotations

import itertools

import numpy as np

from gunlib import uvchart as UC

_D = []
for i, j in itertools.combinations(range(3), 2):
    for si, sj in itertools.product((1.0, -1.0), repeat=2):
        v = np.zeros(3)
        v[i], v[j] = si, sj
        _D.append(v / np.sqrt(2.0))
for s in itertools.product((1.0, -1.0), repeat=3):
    _D.append(np.array(s) / np.sqrt(3.0))
DIAG = np.array(_D)                      # (20, 3)
AXES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)   # box key order
ALL_DIRS = np.vstack([AXES, DIAG])        # key k -> direction (box frame R = identity)
SLANT_COS = 0.866                         # more than 30 deg off the box chart's axis -> its nearest diagonal / axis


def axes_of(key):
    """In-plane axes (a, b) of chart key with a x b = the chart direction (never mirrored)."""
    if key < 6:
        return UC._box_axes(np.eye(3), key)
    d = DIAG[key - 6]
    up = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    a = np.cross(up, d)
    a /= np.linalg.norm(a)
    return a, np.cross(d, a)


def project(P, keys, fr):
    """UV (mm) of points P under per-point keys (box frames; cylinder frames go through gunlib.uvchart)."""
    P = np.asarray(P, float)
    keys = np.asarray(keys)
    if fr["mode"] != "box" or (keys < 6).all():
        return UC.project_loops(P, keys, fr)
    out = np.zeros((len(P), 2))
    for k in np.unique(keys):
        s = keys == k
        a, b = axes_of(int(k))
        out[s] = np.c_[P[s] @ a, P[s] @ b]
    return out


def reproject_slanted(pm, r, fr, cls, skip=None):
    """Faces more than 30 deg off their box chart's axis move to the nearest of the 26 directions (a diagonal, or a
    better axis) and form their own islands (connected per key and class, overlaps split). Updates r (keys, luv, lab)
    in place; returns the number of moved faces."""
    if fr["mode"] != "box" or not np.allclose(fr["R"], np.eye(3)):
        return 0
    keys = np.asarray(r["keys"]).copy()
    cosk = np.einsum("ij,ij->i", pm.fn, AXES[np.clip(keys, 0, 5)])
    slant = (keys < 6) & (cosk < SLANT_COS)
    if skip is not None:
        slant &= ~np.asarray(skip, bool)             # slivers stay in their neighbours' islands (UD3)
    if not slant.any():
        return 0
    best = np.argmax(pm.fn[slant] @ ALL_DIRS.T, axis=1)
    keys[slant] = best
    luv = r["luv"].copy()
    ls = np.isin(pm.loop_f, np.nonzero(slant)[0])
    luv[ls] = project(pm.V[pm.loop_v[ls]], keys[pm.loop_f[ls]], fr)
    grp = keys * 1000 + np.asarray(cls)
    comp = UC.connected(pm, grp, luv, faces_mask=slant)
    lab = np.asarray(r["lab"]).copy()
    base = int(lab.max()) + 1
    _, cinv = np.unique(comp[slant], return_inverse=True)
    lab[slant] = base + cinv
    lab, _ = UC.split_overlapping(pm, lab, luv)
    _, lab = np.unique(lab, return_inverse=True)
    r["keys"], r["luv"], r["lab"] = keys, luv, lab
    return int(slant.sum())
