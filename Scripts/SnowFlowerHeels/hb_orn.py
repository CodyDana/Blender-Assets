"""Ornament builders for the Snow Flower heels: the reference view-A traces (2D, reference pixels) are projected onto
the shoe's outer surfaces through the fitted reference camera and turned into DISCRETE SHELLS with real thickness,
chamfered rims and domed/ridged tops (the construction that worked on the Snow Flower sword guard).

Every builder returns a Part(verts (N,3) local mm, faces list, mat list per face). ``q`` = quality: "high" (bake source)
or "game" (the LOD0 shells, same silhouette, fewer segments).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

import hb_common as C


@dataclass
class Part:
    v: np.ndarray
    f: List[List[int]]
    m: List[str]
    name: str = ""

    @staticmethod
    def join(parts: Sequence["Part"], name="") -> "Part":
        vs, fs, ms = [], [], []
        off = 0
        for p in parts:
            if p is None or len(p.v) == 0:
                continue
            vs.append(p.v)
            fs += [[i + off for i in f] for f in p.f]
            ms += p.m
            off += len(p.v)
        if not vs:
            return Part(np.zeros((0, 3)), [], [], name)
        return Part(np.vstack(vs), fs, ms, name)


class Projector:
    """Near-side hits of camera rays on a set of surfaces (hb_geo.Surf, local mm)."""

    def __init__(self, cam, surfaces):
        self.cam = cam
        self.surfs = surfaces
        self.cdir, self.right, self.up = cam.basis()

    def hit(self, xy, facing=True):
        o, d = self.cam.ray(np.asarray(xy, dtype=float))
        best = None
        for s in self.surfs:
            for p, n, _i, dist in s.hits(o, d, max_hits=6):
                if facing and np.dot(n, self.cdir) <= 0.02:
                    continue
                if best is None or dist < best[2]:
                    best = (p, n, dist)
                break_ok = True
        return best

    def map(self, xy, facing=True, max_jump=10.0):
        """(N,2) px -> P (N,3), Nrm (N,3). Misses and depth outliers are filled from a plane fitted to the valid hits
        (so plate tips that stand off the surface continue its tangent plane)."""
        xy = np.asarray(xy, dtype=float)
        o, d = self.cam.ray(xy)
        t = np.full(len(xy), np.nan)
        nrm = np.zeros((len(xy), 3))
        for i in range(len(xy)):
            h = self.hit(xy[i], facing)
            if h is not None:
                t[i] = h[2]
                nrm[i] = h[1]
        ok = np.isfinite(t)
        if ok.sum() >= 3:
            med = np.median(t[ok])
            ok &= np.abs(t - med) < max(max_jump, 2.5 * np.std(t[ok]) if ok.sum() > 3 else max_jump)
        if ok.sum() == 0:
            # beyond the silhouette: put the ornament at the ray's closest approach to the surfaces, facing out
            c = xy.mean(0)
            oc, dc = self.cam.ray(c)
            best = (1e9, None, None)
            for tt in np.linspace(1300, 2700, 701):
                p = oc + dc * tt
                for sf in self.surfs:
                    loc, n_, _i, dist = sf.tree.find_nearest(Vector(p))
                    if loc is not None and dist < best[0]:
                        best = (dist, tt, np.array(loc))
            _dist, tt, loc = best
            nrm_c = (oc + dc * tt) - loc
            nrm_c /= max(np.linalg.norm(nrm_c), 1e-9)
            nrm_c = 0.6 * nrm_c + 0.4 * self.cdir
            nrm_c /= np.linalg.norm(nrm_c)
            t[:] = tt - 0.8
            nrm[:] = nrm_c
            ok[:] = True
        if (~ok).any():
            A = np.column_stack([np.ones(ok.sum()), xy[ok]])
            if ok.sum() >= 3:
                coef, *_ = np.linalg.lstsq(A, t[ok], rcond=None)
            else:
                coef = np.array([t[ok].mean(), 0, 0])
            t[~ok] = coef[0] + xy[~ok] @ coef[1:]
            nm = nrm[ok].mean(0)
            nrm[~ok] = nm / np.linalg.norm(nm)
        P = o + d * t[:, None]
        return P, nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)

    def px_per_mm(self, n: np.ndarray, direction: np.ndarray) -> float:
        """Image length (px) of 1 mm along ``direction`` on a surface (foreshortening)."""
        dproj = direction - np.dot(direction, self.cdir) * self.cdir
        return self.cam.s * max(np.linalg.norm(dproj), 0.3)


# ------------------------------------------------------------------------------------------------ 2D polygon helpers

def resample_keep_corners(poly: np.ndarray, step: float, closed=True, corner_deg=35.0) -> np.ndarray:
    """Resample a polyline/polygon to ~``step`` spacing, keeping sharp corners (tips) exactly."""
    P = np.asarray(poly, dtype=float)
    n = len(P)
    corners = []
    for i in range(n):
        if not closed and (i == 0 or i == n - 1):
            corners.append(i)
            continue
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        v1, v2 = b - a, c - b
        den = max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-9)
        ang = math.degrees(math.acos(np.clip(np.dot(v1, v2) / den, -1, 1)))
        if ang > corner_deg:
            corners.append(i)
    if closed:
        if not corners:
            corners = [0]
        runs = [(corners[k], corners[(k + 1) % len(corners)]) for k in range(len(corners))]
    else:
        runs = [(corners[k], corners[k + 1]) for k in range(len(corners) - 1)]
    out = []
    for a, b in runs:
        idx = list(range(a, b + 1)) if b > a else list(range(a, n)) + list(range(0, b + 1))
        seg = P[idx]
        L = np.linalg.norm(np.diff(seg, axis=0), axis=1).sum() if len(seg) > 1 else 0.0
        k = max(1, int(round(L / step)))
        rs = C.resample_polyline(seg, n=k + 1) if len(seg) > 1 else seg
        out.extend(rs[:-1])
    if not closed:
        out.append(P[-1])
    return np.array(out)


def smooth_closed(P, it=2, fixed=None):
    P = P.copy()
    for _ in range(it):
        S = (np.roll(P, 1, 0) + 2 * P + np.roll(P, -1, 0)) / 4
        if fixed is not None:
            S[fixed] = P[fixed]
        P = S
    return P


def poly_area(P):
    return 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])


def inset(P, d):
    """Offset a closed polygon inward by d (px), miter-limited."""
    Q = np.asarray(P, dtype=float)
    if poly_area(Q) < 0:
        sgn = -1.0
    else:
        sgn = 1.0
    prev = Q - np.roll(Q, 1, 0)
    nxt = np.roll(Q, -1, 0) - Q
    def nrm(e):
        n = np.stack([-e[:, 1], e[:, 0]], 1) * sgn           # left normal for CCW = inward
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    n1, n2 = nrm(prev), nrm(nxt)
    m = n1 + n2
    m /= np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)
    cosh = np.clip((m * n1).sum(1), 0.35, 1.0)
    return Q + m * (d / cosh)[:, None]


def dist_to_poly(pts, poly):
    a = poly
    b = np.roll(poly, -1, 0)
    p = np.asarray(pts, dtype=float)[:, None]
    ab = (b - a)[None]
    t = np.clip(((p - a[None]) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    return np.linalg.norm(p - (a[None] + ab * t[..., None]), axis=-1).min(1)


def cdt(outer: np.ndarray, holes: Sequence[np.ndarray] = (), interior: Optional[np.ndarray] = None):
    """Constrained Delaunay triangulation of a polygon with holes; returns (pts2 (N,2), tris)."""
    pts = [outer]
    edges = []
    base = 0
    for loop in [outer] + list(holes):
        n = len(loop)
        edges += [(base + k, base + (k + 1) % n) for k in range(n)]
        base += n
        if loop is not outer:
            pts.append(loop)
    if interior is not None and len(interior):
        pts.append(interior)
    allp = np.vstack(pts)
    res = delaunay_2d_cdt([Vector((float(x), float(y))) for x, y in allp], edges, [], 1, 1e-6, True)
    out_v = np.array([[p.x, p.y] for p in res[0]])
    if len(out_v) < len(allp) or np.abs(out_v[:len(allp)] - allp).max() > 1e-3:
        raise RuntimeError("cdt changed the input vertices")
    tris = [list(f) for f in res[2]]
    cen = np.array([out_v[t].mean(0) for t in tris])
    keep = np.ones(len(tris), dtype=bool)
    for hl in holes:
        keep &= C.poly_sdf2(cen, hl) > 0
    tris = [t for t, k in zip(tris, keep) if k]
    # consistent CCW winding
    tris = [t if poly_area(out_v[t]) > 0 else t[::-1] for t in tris]
    return out_v, tris


def interior_grid(poly, step, margin):
    lo = poly.min(0)
    hi = poly.max(0)
    xs = np.arange(lo[0] + step / 2, hi[0], step)
    ys = np.arange(lo[1] + step / 2, hi[1], step)
    X, Y = np.meshgrid(xs, ys)
    P = np.column_stack([X.ravel(), Y.ravel()])
    if len(P) == 0:
        return P
    sd = C.poly_sdf2(P, poly)
    return P[sd < -margin]


# ------------------------------------------------------------------------------------------------ builders

def plate(pj: Projector, outline_px, thick=1.6, bevel_px=3.0, dome=0.7, q="high", mat="silver", lens_px=None,
          lens_depth=0.7, lens_mat="silver_recess", sink=0.35, edge_frac=0.45, smooth=1, name="plate"):
    """A raised plate on the surface under ``outline_px``: a top that rises from ``edge_frac * thick`` at the rim to
    ``thick`` (mm) along the medial ridge (the inset ring gives the chamfer), a side wall sunk into the surface and an
    optional recessed lens."""
    step = 2.0 if q == "high" else 10.0
    P = resample_keep_corners(np.asarray(outline_px, float), step, closed=True)
    if poly_area(P) < 0:
        P = P[::-1]
    if smooth and q == "high":
        P = smooth_closed(P, 1)
    n_out = len(P)
    ring = inset(P, bevel_px)
    ring = ring[C.poly_sdf2(ring, P) < -0.6 * bevel_px] if len(ring) else ring
    holes = []
    L = None
    if lens_px is not None:
        L = resample_keep_corners(np.asarray(lens_px, float), step, closed=True)
        if poly_area(L) < 0:
            L = L[::-1]
        c_ = L.mean(0)
        for _ in range(40):                       # keep the lens strictly inside the plate
            if (C.poly_sdf2(L, P) < -max(bevel_px, 2.0)).all():
                break
            L = c_ + (L - c_) * 0.95
        holes = [L]
    inter = interior_grid(P, 3.0 if q == "high" else 18.0, bevel_px + 1.5)
    pts = [p_ for p_ in (ring, inter) if p_ is not None and len(p_)]
    inter = np.vstack(pts) if pts else None
    if inter is not None and L is not None and len(inter):
        inter = inter[C.poly_sdf2(inter, L) > 1.2]
    top2, ttris = cdt(P, holes, inter)
    d_edge = dist_to_poly(top2, P)
    dmax = max(d_edge.max(), 1e-6)
    h_edge = thick * edge_frac
    # chamfer: rim -> full bevel height over bevel_px, then the dome over the rest
    t_b = np.clip(d_edge / max(bevel_px, 1e-6), 0, 1)
    t_d = np.clip((d_edge - bevel_px) / max(dmax - bevel_px, 1e-6), 0, 1)
    htop = h_edge + (thick * 0.8 - h_edge) * t_b + thick * 0.2 * t_d ** dome
    all2 = np.vstack([top2, P])
    Pw, Nw = pj.map(all2)
    nm = Nw.mean(0)
    nm /= np.linalg.norm(nm)
    Nw = 0.5 * Nw + 0.5 * nm
    Nw /= np.linalg.norm(Nw, axis=1, keepdims=True)
    nt = len(top2)
    h = np.concatenate([htop, np.full(n_out, -sink)])
    V = Pw + Nw * h[:, None]
    faces, mats = [], []
    for t in ttris:
        faces.append([t[0], t[1], t[2]])
        mats.append(mat)
    base0 = nt
    for k in range(n_out):
        k1 = (k + 1) % n_out
        faces.append([k, base0 + k, base0 + k1, k1])
        mats.append(mat)
    if L is not None:
        nl = len(L)
        lr = np.arange(n_out, n_out + nl)
        l2, ltris = cdt(L, (), interior_grid(L, 3.0 if q == "high" else 30.0, 3.0))
        Lw, Ln = pj.map(l2)
        Ln = 0.5 * Ln + 0.5 * nm
        Ln /= np.linalg.norm(Ln, axis=1, keepdims=True)
        hl = htop[lr].mean() - lens_depth
        Vl = Lw + Ln * hl
        off = len(V)
        V = np.vstack([V, Vl])
        for t in ltris:
            faces.append([off + t[0], off + t[1], off + t[2]])
            mats.append(lens_mat)
        for k in range(nl):
            k1 = (k + 1) % nl
            faces.append([lr[k], lr[k1], off + k1, off + k])
            mats.append(lens_mat)
    return Part(V, faces, mats, name)


def band(pj: Projector, center_px, width_px, height=1.4, q="high", mat="silver", profile="round", taper=(0.0, 0.0),
         sink=0.35, closed=False, step_px=None, lift=0.0, name="band", points3d=None, normals3d=None):
    """A swept band/tube on the surface along ``center_px`` (image) or explicit 3D points. ``width_px`` scalar or per
    point (image px, corrected for foreshortening). ``taper`` = (start, end) fraction of the length that narrows to a
    point."""
    step = step_px or (2.5 if q == "high" else 12.0)
    if points3d is None:
        c = np.asarray(center_px, float)
        wpx = np.broadcast_to(np.asarray(width_px, float), (len(c),)).astype(float)
        seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        n = max(3, int(s[-1] / step) + 1)
        ss = np.linspace(0, s[-1], n)
        cc = np.column_stack([np.interp(ss, s, c[:, 0]), np.interp(ss, s, c[:, 1])])
        if q == "high" and len(cc) > 4:
            for _ in range(2):
                cc[1:-1] = (cc[:-2] + 2 * cc[1:-1] + cc[2:]) / 4
        ww = np.interp(ss, s, wpx)
        P, N = pj.map(cc)
        # per-point smoothing of the 3D line and normals
        for _ in range(2):
            N[1:-1] = (N[:-2] + 2 * N[1:-1] + N[2:]) / 4
        N /= np.linalg.norm(N, axis=1, keepdims=True)
    else:
        P = np.asarray(points3d, float)
        N = np.asarray(normals3d, float)
        ww = np.broadcast_to(np.asarray(width_px, float), (len(P),)).astype(float)
        cc = None
    T = np.gradient(P, axis=0)
    if closed:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    B = np.cross(N, T)
    B /= np.maximum(np.linalg.norm(B, axis=1, keepdims=True), 1e-9)
    N = np.cross(T, B)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    tot = max(L[-1], 1e-6)
    hw = np.empty(len(P))
    for i in range(len(P)):
        ppm = pj.px_per_mm(N[i], B[i]) if points3d is None else pj.cam.s
        hw[i] = 0.5 * ww[i] / ppm
    if not closed:
        f = np.ones(len(P))
        if taper[0] > 0:
            f = np.minimum(f, np.clip(L / (taper[0] * tot), 0, 1) ** 0.8)
        if taper[1] > 0:
            f = np.minimum(f, np.clip((tot - L) / (taper[1] * tot), 0, 1) ** 0.8)
        hw = hw * np.maximum(f, 0.02)
        hgt = height * np.maximum(f, 0.25)
    else:
        hgt = np.full(len(P), height)
    if profile == "round":
        k = 9 if q == "high" else 4
        ph = np.linspace(0, math.pi, k)
        prof = [(math.cos(a), math.sin(a) ** 0.8) for a in ph]
    else:   # flat bar with chamfers
        prof = [(1.0, 0.0), (1.0, 0.55), (0.72, 1.0), (-0.72, 1.0), (-1.0, 0.55), (-1.0, 0.0)] if q == "high" else \
               [(1.0, 0.0), (0.8, 1.0), (-0.8, 1.0), (-1.0, 0.0)]
    prof = prof + [(-0.8, -1.0), (0.8, -1.0)] if False else prof
    npf = len(prof)
    V = []
    for i in range(len(P)):
        for (x, y) in prof:
            h = -sink + (hgt[i] + sink) * y if y > 0 else -sink
            V.append(P[i] + N[i] * (h + lift) + B[i] * (x * hw[i]))
    V = np.array(V)
    faces, mats = [], []
    nrow = len(P)
    rows = range(nrow) if closed else range(nrow - 1)
    for i in rows:
        i1 = (i + 1) % nrow
        for j in range(npf - 1):
            faces.append([i * npf + j, i1 * npf + j, i1 * npf + j + 1, i * npf + j + 1])
            mats.append(mat)
    if not closed:     # end caps (fans)
        for row, flip in ((0, True), (nrow - 1, False)):
            c = len(V)
            V = np.vstack([V, V[row * npf:(row + 1) * npf].mean(0)[None]])
            for j in range(npf - 1):
                a, b = row * npf + j, row * npf + j + 1
                faces.append([c, b, a] if flip else [c, a, b])
                mats.append(mat)
    return Part(V, faces, mats, name)


def frame_loop(pj, outline_px, bar_px=5.0, height=1.3, q="high", mat="silver", name="frame"):
    P = np.asarray(outline_px, float)
    Pc = resample_keep_corners(P, 2.0 if q == "high" else 6.0, closed=True)
    return band(pj, Pc, bar_px, height=height, q=q, mat=mat, profile="flat", closed=False, name=name) \
        if False else _closed_band(pj, Pc, bar_px, height, q, mat, name)


def _closed_band(pj, Pc, bar_px, height, q, mat, name):
    P3, N3 = pj.map(Pc)
    return band(pj, None, bar_px, height=height, q=q, mat=mat, profile="flat", closed=True, name=name,
                points3d=P3, normals3d=N3)


def pyramid(pj, outline_px, height=2.2, q="high", mat="silver", name="stud"):
    """Faceted diamond stud (pyramid on the outline polygon)."""
    P = np.asarray(outline_px, float)
    c = P.mean(0)
    Pw, Nw = pj.map(np.vstack([P, c[None]]))
    nm = Nw.mean(0)
    nm /= np.linalg.norm(nm)
    base = Pw[:-1] + nm * 0.2
    sink = Pw[:-1] - nm * 0.35
    apex = Pw[-1] + nm * height
    V = np.vstack([sink, base, apex[None]])
    n = len(P)
    faces, mats = [], []
    for k in range(n):
        k1 = (k + 1) % n
        faces.append([n + k, n + k1, 2 * n])
        faces.append([k, k1, n + k1, n + k])
        mats += [mat, mat]
    return Part(V, faces, mats, name)


def thorn(pj, at_px, direction_px, length_px=12.0, width_px=5.0, height=1.2, q="high", mat="silver", name="thorn"):
    a = np.asarray(at_px, float)
    d = np.asarray(direction_px, float)
    d /= np.linalg.norm(d)
    perp = np.array([-d[1], d[0]])
    outline = [a - perp * width_px / 2, a + d * length_px, a + perp * width_px / 2, a - d * width_px * 0.4]
    return pyramid(pj, outline, height=height, q=q, mat=mat, name=name)


def leaf_outline(base_px, tip_px, width_px, curve=0.0, n=14):
    """Pointed leaf (both ends pointed) from base to tip, optional sideways curve (fraction of length)."""
    b = np.asarray(base_px, float)
    t = np.asarray(tip_px, float)
    d = t - b
    L = np.linalg.norm(d)
    d /= L
    p = np.array([-d[1], d[0]])
    s = np.linspace(0, 1, n)
    wid = width_px / 2 * np.sin(np.pi * s) ** 0.75 * (1 - 0.25 * s)
    bend = curve * L * np.sin(np.pi * s)
    left = b + np.outer(s * L, d) + np.outer(bend + wid, p)
    right = b + np.outer(s * L, d) + np.outer(bend - wid, p)
    return np.vstack([left, right[::-1][1:-1]])


# ------------------------------------------------------------------------------------------------ blossom / bud

def blossom_local(R: float, q="high", petals=5, rot=0.0):
    """A five-petal pearl blossom in its own frame (z up, radius R mm): cupped notched petals with raised silver
    bezels, a silver centre boss and stamen dots. Returns Part in the local flower frame."""
    parts = []
    nr = 7 if q == "high" else 3
    na = 9 if q == "high" else 5
    for k in range(petals):
        ang = rot + 2 * math.pi * k / petals
        ca, sa = math.cos(ang), math.sin(ang)
        # petal param: radial r in [r0, 1], across a in [-1, 1]
        r0 = 0.16
        rs = np.linspace(r0, 1.0, nr)
        As = np.linspace(-1, 1, na)
        V = []
        for r in rs:
            half = 0.30 * math.sin(math.pi * min(r, 0.93) / 0.93 * 0.62 + 0.25) + 0.05     # widest ~ 0.7 R
            half *= 1.0 if r < 0.8 else (1.0 - 0.9 * ((r - 0.8) / 0.2) ** 2) * 0.5 + 0.5
            for a in As:
                rr = r
                if r > 0.86:
                    rr = r - 0.12 * (1 - abs(a)) ** 2 * (r - 0.86) / 0.14          # notch at the tip
                x = rr * R
                y = a * half * R * (1.15 if r > 0.5 else 1.0)
                z = R * (0.10 + 0.20 * (r - r0) ** 1.4 + 0.06 * a * a - 0.03 * (1 - abs(a)) * r)
                V.append([x * ca - y * sa, x * sa + y * ca, z])
        V = np.array(V)
        F = []
        for i in range(nr - 1):
            for j in range(na - 1):
                F.append([i * na + j, i * na + j + 1, (i + 1) * na + j + 1, (i + 1) * na + j])
        # underside (flat-ish, closes the petal) + bezel rim
        Vb = V.copy()
        Vb[:, 2] = np.maximum(V[:, 2] - 0.09 * R, 0.0)
        off = len(V)
        Vall = np.vstack([V, Vb])
        Fb = [[off + f[3], off + f[2], off + f[1], off + f[0]] for f in F]
        # rim loop indices (perimeter) in order
        per = [i * na for i in range(nr)] + [(nr - 1) * na + j for j in range(1, na)] + \
              [i * na + na - 1 for i in range(nr - 2, -1, -1)] + [j for j in range(na - 2, 0, -1)]
        Fr = []
        for a_, b_ in zip(per, per[1:] + per[:1]):
            Fr.append([a_, off + a_, off + b_, b_])
        if q != "high":
            Fb = []
        parts.append(Part(Vall, F + Fb + Fr, ["pearl"] * (len(F) + len(Fb)) + ["silver"] * len(Fr), "petal"))
        if q == "high":
            # raised silver bezel along the petal's outer edge
            edge = V[per]
            parts.append(_tube_loop(edge + np.array([0, 0, 0.012 * R]), 0.028 * R, 5, "silver"))
    # centre boss + stamens
    nb = 10 if q == "high" else 6
    boss = _dome(0.17 * R, 0.16 * R, 0.13 * R, nb, "silver")
    parts.append(boss)
    if q == "high":
        for k in range(10):
            a = 2 * math.pi * k / 10 + 0.3
            c = np.array([0.24 * R * math.cos(a), 0.24 * R * math.sin(a), 0.17 * R])
            parts.append(_dome(0.035 * R, 0.035 * R, c[2], 6, "silver", center=c[:2]))
    return Part.join(parts, "blossom")


def _dome(r, h, z0, n, mat, center=(0.0, 0.0)):
    V = [[center[0], center[1], z0 + h]]
    rings = 3
    for i in range(1, rings + 1):
        rr = r * math.sin(i / rings * math.pi / 2)
        zz = z0 + h * math.cos(i / rings * math.pi / 2)
        for k in range(n):
            a = 2 * math.pi * k / n
            V.append([center[0] + rr * math.cos(a), center[1] + rr * math.sin(a), zz])
    V.append([center[0], center[1], z0 - 0.3 * h])
    V = np.array(V)
    F = []
    for k in range(n):
        F.append([0, 1 + k, 1 + (k + 1) % n])
    for i in range(rings - 1):
        a0 = 1 + i * n
        a1 = 1 + (i + 1) * n
        for k in range(n):
            k1 = (k + 1) % n
            F.append([a0 + k, a1 + k, a1 + k1, a0 + k1])
    last = 1 + (rings - 1) * n
    c = len(V) - 1
    for k in range(n):
        F.append([last + k, c, last + (k + 1) % n])
    return Part(V, F, [mat] * len(F), "dome")


def _tube_loop(pts, r, k, mat):
    P = np.asarray(pts, float)
    n = len(P)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    B = np.cross(T, up)
    B /= np.maximum(np.linalg.norm(B, axis=1, keepdims=True), 1e-9)
    N = np.cross(B, T)
    V = []
    for i in range(n):
        for j in range(k):
            a = 2 * math.pi * j / k
            V.append(P[i] + r * (math.cos(a) * B[i] + math.sin(a) * N[i]))
    F = []
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(k):
            j1 = (j + 1) % k
            F.append([i * k + j, i * k + j1, i1 * k + j1, i1 * k + j])
    return Part(np.array(V), F, [mat] * len(F), "tube")


def place(part: Part, origin, normal, xdir, scale=1.0) -> Part:
    n = np.asarray(normal, float)
    n /= np.linalg.norm(n)
    x = np.asarray(xdir, float) - np.dot(xdir, n) * n
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    M = np.column_stack([x, y, n])
    return Part(part.v * scale @ M.T + np.asarray(origin, float), part.f, part.m, part.name)


def blossom(pj, center_px, d_px, q="high", rot=0.0, lift=0.25, name="blossom", scale_fix=1.0):
    P, N = pj.map(np.array([center_px, [center_px[0] + 4, center_px[1]], [center_px[0], center_px[1] + 4]], float))
    n = N[0]
    xdir = P[1] - P[0]
    R = 0.5 * d_px / pj.cam.s * scale_fix
    return place(blossom_local(R, q, rot=rot), P[0] + n * lift, n, xdir), R


def bud(pj, center_px, d_px, toward_px, q="high", name="bud"):
    """Closed pearl bud (teardrop) on a short silver calyx, pointing away from ``toward_px`` (its stem side)."""
    P, N = pj.map(np.array([center_px, toward_px], float))
    n = N[0]
    axis = P[0] - P[1]
    axis -= np.dot(axis, n) * n
    if np.linalg.norm(axis) < 1e-6:
        axis = np.cross(n, [0, 0, 1.0])
    axis /= np.linalg.norm(axis)
    L = d_px / pj.cam.s * 1.25
    rmax = L * 0.36
    k = 10 if q == "high" else 6
    ns = 8 if q == "high" else 4
    side = np.cross(n, axis)
    V = []
    for i in range(ns + 1):
        t = i / ns
        r = rmax * math.sin(math.pi * min(t * 1.05, 1.0)) ** 0.8 * (1 - 0.35 * t) + 1e-3
        c = P[0] - axis * L * 0.45 + axis * L * t + n * (rmax * 0.9)
        for j in range(k):
            a = 2 * math.pi * j / k
            V.append(c + r * (math.cos(a) * side + math.sin(a) * n))
    V = np.array(V)
    F = []
    for i in range(ns):
        for j in range(k):
            j1 = (j + 1) % k
            F.append([i * k + j, i * k + j1, (i + 1) * k + j1, (i + 1) * k + j])
    tip = len(V)
    V = np.vstack([V, (P[0] + axis * L * 0.62 + n * rmax * 0.9)[None], (P[0] - axis * L * 0.5 + n * rmax * 0.9)[None]])
    for j in range(k):
        F.append([ns * k + j, ns * k + (j + 1) % k, tip])
        F.append([(j + 1) % k, j, tip + 1])
    mats = ["pearl"] * len(F)
    # calyx: silver collar on the lower third
    parts = [Part(V, F, mats, name)]
    stem = band(pj, None, 1.3 * pj.cam.s, height=0.7, q=q, mat="silver", profile="round", name="stem",
                points3d=np.array([P[0] - axis * L * 1.1 + n * 0.3, P[0] - axis * L * 0.75 + n * 0.5,
                                   P[0] - axis * L * 0.35 + n * rmax * 0.7]),
                normals3d=np.array([n, n, n]))
    parts.append(stem)
    return Part.join(parts, name)
