"""Geometric edge masks for the per-texel painter (plain Python: numpy + scipy).

Why (AR-01 realism-fix round, 2026-10-07): the Cycles bevel-node edge bake (gunlib.bake 'edge') compares the bevel
normal with the INTERPOLATED shading normal. On the long sliver triangles of the CDT-triangulated flats (receiver
walls, magazine sides, feed-lip blocks) the vertex normals of a bevel corner leak across the whole sliver, so whole
triangles read as 'edge': the painter chipped them to bare steel (white triangular shards in the middle of panels,
dashed lines along seams). Here the edges are measured on the TRUE geometry instead:

  1. the bake objects' triangles (gunlib.bake.dump_tris, frame M mm) are welded; every interior edge gets its
     dihedral angle and its sign (convex / concave) from its two faces; an edge inside a planar face (two coplanar
     triangles) has angle 0 and contributes nothing, so no triangle structure can ever show
  2. a texel's edge value at scale sigma is the angle-weighted Gaussian line integral of the convex edges of ITS OWN
     part: E(p) = sum_i theta_i * exp(-d_perp^2 / 2 s^2) * [Phi((L - t) / s) - Phi(-t / s)]   (/ (pi / 2))
     i.e. a single 90 deg corner reads 1.0 on its line and falls off over ~2 sigma; a bevel chain of three 30 deg
     edges reads the same as its 90 deg corner; a smooth round of radius R reads ~0.56 sigma / R (a 7.5 mm barrel at
     sigma 0.3: 0.02 - not an edge); a coplanar sliver reads 0
  3. dist_convex(p): the distance to the nearest convex edge sharper than `sharp_deg` (the gates' 'panel interior'
     test and the chip rule 'bare only within 0.6 mm of a real edge')
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree
from scipy.special import erf


def weld(V, tol=1e-3):
    """V (n, 3, 3) mm -> (P unique points, F (n, 3) indices), welding points within ~tol mm (grid snap)."""
    q = np.round(V.reshape(-1, 3) / tol).astype(np.int64)
    _u, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    P = V.reshape(-1, 3)[first].astype(np.float64)
    F = inv.reshape(-1, 3)
    keep = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    return P, F[keep], keep


def edges(V, tol=1e-3, area_eps=1e-8):
    """Interior edges of a triangle soup with their signed dihedral angle (rad; + convex, - concave) and the boundary
    edges (one face: an exposed sheet edge, treated as a 90 deg convex edge). Returns A (m, 3), B (m, 3), theta (m,)."""
    P, F, _keep = weld(V, tol)
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    n = np.cross(b - a, c - a)
    ar = np.linalg.norm(n, axis=1)
    ok = ar > area_eps
    F, n, ar = F[ok], n[ok], ar[ok]
    n = n / ar[:, None]
    nf = len(F)
    # half-edges: (v0, v1, opposite vertex, face)
    e0 = np.concatenate([F[:, 0], F[:, 1], F[:, 2]])
    e1 = np.concatenate([F[:, 1], F[:, 2], F[:, 0]])
    op = np.concatenate([F[:, 2], F[:, 0], F[:, 1]])
    fi = np.concatenate([np.arange(nf)] * 3)
    lo, hi = np.minimum(e0, e1), np.maximum(e0, e1)
    key = lo.astype(np.int64) * (len(P) + 1) + hi
    order = np.argsort(key, kind="stable")
    key, lo, hi, op, fi = key[order], lo[order], hi[order], op[order], fi[order]
    start = np.r_[0, np.nonzero(np.diff(key))[0] + 1]
    cnt = np.diff(np.r_[start, len(key)])
    A, Bv, T = [], [], []
    # pairs (first two faces of each edge; a > 2 fan is rare and its first pair is representative)
    two = start[cnt >= 2]
    f1, f2 = fi[two], fi[two + 1]
    o2 = op[two + 1]
    cosd = np.clip(np.sum(n[f1] * n[f2], axis=1), -1.0, 1.0)
    th = np.arccos(cosd)
    pa = P[lo[two]]
    convex = np.sum(n[f1] * (P[o2] - pa), axis=1) < 0.0
    A.append(pa)
    Bv.append(P[hi[two]])
    T.append(np.where(convex, th, -th))
    one = start[cnt == 1]
    A.append(P[lo[one]])
    Bv.append(P[hi[one]])
    T.append(np.full(len(one), math.pi / 2))
    return np.concatenate(A), np.concatenate(Bv), np.concatenate(T)


def pieces(A, B, T, maxlen):
    """Split segments into pieces no longer than maxlen (mm)."""
    L = np.linalg.norm(B - A, axis=1)
    k = np.maximum(1, np.ceil(L / maxlen).astype(int))
    idx = np.repeat(np.arange(len(A)), k)
    j = np.concatenate([np.arange(m) for m in k]) if len(k) else np.zeros(0, int)
    kk = k[idx]
    t0, t1 = j / kk, (j + 1) / kk
    D = B[idx] - A[idx]
    return A[idx] + D * t0[:, None], A[idx] + D * t1[:, None], T[idx]


class EdgeField:
    """Convex-edge field of ONE part (its own triangles)."""

    def __init__(self, V, min_deg=2.0, maxlen=0.5):
        A, B, T = edges(V)
        cv = T > math.radians(min_deg)
        self.maxlen = maxlen
        self.A, self.B, self.T = pieces(A[cv], B[cv], T[cv], maxlen)
        self.mid = 0.5 * (self.A + self.B)
        self.tree = cKDTree(self.mid) if len(self.mid) else None

    def value(self, Q, sigma, k=48, chunk=150000):
        """E(Q) / (pi / 2) at points Q (n, 3) mm for Gaussian scale sigma (mm)."""
        out = np.zeros(len(Q), np.float32)
        if self.tree is None or not len(Q):
            return out
        r = 3.0 * sigma + 0.5 * self.maxlen
        kk = int(min(k, len(self.mid)))
        s2 = math.sqrt(2.0) * sigma
        for s in range(0, len(Q), chunk):
            q = Q[s:s + chunk].astype(np.float64)
            d, ii = self.tree.query(q, k=kk, distance_upper_bound=r)
            if kk == 1:
                d, ii = d[:, None], ii[:, None]
            valid = np.isfinite(d)
            ii = np.where(valid, ii, 0)
            a = self.A[ii]
            u = self.B[ii] - a
            L = np.linalg.norm(u, axis=2)
            u = u / np.maximum(L, 1e-9)[..., None]
            w = q[:, None, :] - a
            t = np.sum(w * u, axis=2)
            dp2 = np.maximum(np.sum(w * w, axis=2) - t * t, 0.0)
            g = np.exp(-dp2 / (2.0 * sigma * sigma)) * 0.5 * (erf((L - t) / s2) - erf(-t / s2))
            out[s:s + chunk] = (np.where(valid, g * self.T[ii], 0.0).sum(1) / (math.pi / 2)).astype(np.float32)
        return out

    def dist_sharp(self, Q, sharp_deg=25.0, chunk=400000):
        """Distance (mm) from Q to the nearest convex edge piece sharper than sharp_deg (inf if none)."""
        sel = self.T > math.radians(sharp_deg)
        out = np.full(len(Q), np.inf, np.float32)
        if not sel.any() or not len(Q):
            return out
        A, B = self.A[sel], self.B[sel]
        tr = cKDTree(0.5 * (A + B))
        for s in range(0, len(Q), chunk):
            q = Q[s:s + chunk].astype(np.float64)
            _d, ii = tr.query(q, k=min(4, len(A)))
            if ii.ndim == 1:
                ii = ii[:, None]
            a, b = A[ii], B[ii]
            u = b - a
            L2 = np.maximum(np.sum(u * u, axis=2), 1e-12)
            t = np.clip(np.sum((q[:, None, :] - a) * u, axis=2) / L2, 0.0, 1.0)
            pr = a + u * t[..., None]
            out[s:s + chunk] = np.sqrt(np.sum((q[:, None, :] - pr) ** 2, axis=2)).min(1)
        return out


def part_fields(V, pid, Q, qpid, sigmas, sharp_deg=25.0, log=None):
    """Per-part edge values at the texel points Q (n, 3) of part ids qpid (n,): returns {sigma: E (n,)} and the
    distance to the nearest sharp convex edge of the texel's own part."""
    out = {s: np.zeros(len(Q), np.float32) for s in sigmas}
    dist = np.full(len(Q), np.inf, np.float32)
    for p in np.unique(qpid):
        sel = np.nonzero(qpid == p)[0]
        tv = V[pid == p]
        if not len(tv):
            continue
        ef = EdgeField(tv)
        for s in sigmas:
            out[s][sel] = ef.value(Q[sel], s)
        dist[sel] = ef.dist_sharp(Q[sel], sharp_deg)
        if log:
            log("edgemask part", int(p), "texels", len(sel), "edge pieces", len(ef.mid))
    return out, dist
