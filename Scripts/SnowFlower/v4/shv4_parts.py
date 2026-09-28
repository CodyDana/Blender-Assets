"""Snow Flower sheath parts: low LOD0/1/2 and the high-poly bake source, in millimetres (sheath frame, shv4_spec).

Every low face carries a parametric local UV in mm and an island id (sfv4_mesh.MB), so the three LODs sample one
atlas consistently without any UV transfer (the same scheme as the v4 sword).

Parts (= bake groups)
    body    lacquer core: faceted outer shell (reference outline) + the swept blade cavity, one closed hollow shell
    throat  mouth fitting: a closed ring solid whose front-view silhouette is the union of the designed plate outlines
    band    the mid band (belt mount) ring solid
    chape   the chape: carries the cavity's last 70 mm and closes to the ogive point
    stem    the raised silver vine stem (LOD0 / LOD1 geometry; baked into the body for LOD2)
    bloom   blossom proxies (vine blossoms LOD0 / large ones LOD1; the three fitting blossoms every LOD)
High-poly extra detail (baked only): plate frames and dark insets, ring beads, scroll frieze, lancets, filigree,
lace drips, the second stem, twigs, buds, pods, leaves, the kept revision-3 blossom construction, marble lacquer.
"""
from __future__ import annotations

import math

import numpy as np

import shv4_spec as S
from sfv4_mesh import MB, _norm, arclen, catmull, fan_cap, resample, tube

LACQ, SILV = 0, 1                       # game material slots
# high-poly material indices (same slots as sfv4_rev3's constants so R3.flower / R3.tube work unchanged)
H_LACQ, H_SILVER, H_INLAY, H_RECESS, H_INSET, H_BRANCH, H_CAVITY, H_ANTIQUE = range(8)

FIT_DIR = S.ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build" / "fit"


# ====================================================================== small helpers

def dp_keep(x, Y, tol):
    """Douglas-Peucker on a polyline (x ascending, Y (n, k)); returns kept indices."""
    Y = np.atleast_2d(np.asarray(Y, float))
    if Y.shape[0] != len(x):
        Y = Y.T
    keep = {0, len(x) - 1}
    stack = [(0, len(x) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        t = (x[a + 1:b] - x[a]) / (x[b] - x[a])
        interp = Y[a] + (Y[b] - Y[a]) * t[:, None]
        err = np.abs(Y[a + 1:b] - interp).max(axis=1)
        i = int(np.argmax(err))
        if err[i] > tol:
            m = a + 1 + i
            keep.add(m)
            stack += [(a, m), (m, b)]
    return sorted(keep)


def plan_rows(r0, r1, fn, tol, max_step, must=()):
    """Station rows between r0 and r1: Douglas-Peucker on fn(row) (mm values) plus must-rows and a max spacing."""
    rows = np.arange(r0, r1 + 1e-9, 0.25)
    if rows[-1] < r1:
        rows = np.append(rows, r1)
    vals = np.array([fn(r) for r in rows])
    kept = [rows[i] for i in dp_keep(rows * S.K, vals, tol)]
    kept += [m for m in must if r0 <= m <= r1]
    kept = sorted(set(round(float(r), 3) for r in kept))
    out = [kept[0]]
    for r in kept[1:]:
        while r - out[-1] > max_step + 1e-6:
            out.append(out[-1] + max_step)
        out.append(r)
    return np.array(sorted(set(round(v, 3) for v in out)))


def ring_arclen(P):
    P = np.asarray(P, float)
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1))])


def zipper(mb, A_idx, A_pts, B_idx, B_pts, island, mat, flip=False):
    """Triangulate the band between two closed loops (both clockwise seen from +Z): shortest-diagonal stitching
    starting at the vertices nearest angle 0 around the inner loop's centre.  Local UV = planar (x, y) mm."""
    A_pts, B_pts = np.asarray(A_pts, float), np.asarray(B_pts, float)
    ctr = B_pts.mean(axis=0)

    def order(idx, pts):
        a = np.arctan2(pts[:, 1] - ctr[1], pts[:, 0] - ctr[0])
        s = int(np.argmin(np.abs(a)))
        return list(idx[s:]) + list(idx[:s]), np.vstack([pts[s:], pts[:s]])
    A_idx, A_pts = order(list(A_idx), A_pts)
    B_idx, B_pts = order(list(B_idx), B_pts)
    n, m = len(A_idx), len(B_idx)

    def ang(p):
        a = -np.arctan2(p[1] - ctr[1], p[0] - ctr[0])          # clockwise -> increasing
        return a % (2 * math.pi)

    aa = [ang(p) for p in A_pts] + [2 * math.pi]
    bb = [ang(p) for p in B_pts] + [2 * math.pi]
    aa[0] = 0.0 if aa[0] > math.pi else aa[0]
    bb[0] = 0.0 if bb[0] > math.pi else bb[0]

    def area(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    i = j = 0
    while i < n or j < m:
        if i < n and j < m:
            okA = area(A_pts[i % n], B_pts[j % m], A_pts[(i + 1) % n]) > 1e-9
            okB = area(A_pts[i % n], B_pts[j % m], B_pts[(j + 1) % m]) > 1e-9
            pref_a = aa[i + 1] <= bb[j + 1]
            step_a = (pref_a and okA) or (not okB and okA) or (pref_a and not okB)
        else:
            step_a = i < n
        if step_a:
            tri = [A_idx[i % n], B_idx[j % m], A_idx[(i + 1) % n]]
            pts = [A_pts[i % n], B_pts[j % m], A_pts[(i + 1) % n]]
            i += 1
        else:
            tri = [A_idx[i % n], B_idx[j % m], B_idx[(j + 1) % m]]
            pts = [A_pts[i % n], B_pts[j % m], B_pts[(j + 1) % m]]
            j += 1
        uv = [(float(p[0]), float(p[1])) for p in pts]
        if flip:
            tri, uv = tri[::-1], uv[::-1]
        mb.f(tri, uv, island, mat)


# ====================================================================== sections

def core_rows(level):
    r0 = float(S.row_of(S.Z_MOUTH + 0.25))
    must = [142, 167, 169, 284, 317, 560, 820, 1060] + [r for r, _ in S.BODY_PX if r0 < r < S.CHAPE_POCKET_END_ROW]
    step = {0: 30.0, 1: 70.0, 2: 150.0, "high": 8.0}[level]
    return plan_rows(r0, S.CHAPE_POCKET_END_ROW, lambda r: [float(S.core_w(r)), float(S.body_d(r))], 0.05, step, must)


BODY_SEGS = [(31, 169, True), (169, 284, False), (284, 317, True), (317, 560, False), (560, 820, False),
             (820, 1060, False), (1060, 1296, False)]


def body_seg(row):
    for k, (a, b, hidden) in enumerate(BODY_SEGS):
        if row < b - 1e-6:
            return k, hidden
    return len(BODY_SEGS) - 1, BODY_SEGS[-1][2]


def core_ring(row):
    return S.core_section(float(S.core_w(row)), float(S.body_d(row)))


def ring_uv_front_back(ring_full):
    """u (mm) per full-ring index for the front island (0..8) and back island (8..16)."""
    s = ring_arclen(ring_full)
    n = len(ring_full)
    h = n // 2
    uf = {j: s[j] - s[h // 2] for j in range(0, h + 1)}
    ub = {j: -(s[j] - s[h + h // 2]) for j in range(h, n + 1)}
    return uf, ub


def fit_section(a, Wc, Dc, t, e=3.6):
    """Ring (20 points, clockwise from the +X side over the front) of a fitting over the core: half-width ``a`` in
    front view; over the core it is the core section offset by ``t``; beyond it a flange tapering to ``e``."""
    c, b = Wc / 2.0, Dc / 2.0
    co = c + t
    F4 = (S.SEC_FRONT * c + 0.3 * t, -(b + t))
    F3 = (S.SEC_CHAMF * c + 0.8 * t, -(S.SEC_CHAMF_Y * b + t))
    if a > co + 0.8:
        F0 = (a, 0.0)
        F1 = (a - 0.35 * (a - co), -e)
        F2 = (co, -(S.SEC_SIDE_Y * b + t))
    else:
        a = max(a, co)
        F0 = (a, 0.0)
        F1 = (a, -0.5 * (S.SEC_SIDE_Y * b + t))
        F2 = (a, -(S.SEC_SIDE_Y * b + t))
    q = [F0, F1, F2, F3, F4, (0.0, -(b + t))]
    front = q + [(-x, y) for x, y in q[-2::-1]]
    back = [(x, -y) for x, y in front[-2:0:-1]]
    return np.array(front + back, float)


FIT_LOD2 = [0, 2, 3, 4, 6, 7, 8, 10, 12, 13, 14, 16, 17, 18]     # drop the flange-edge points and the face centres
FIT_SIDE_IDX = {0, 1, 2, 8, 9, 10, 11, 12, 18, 19}               # ring points on the flanks (silver base in the high)


def front_y(ring, x):
    """Front surface y at lateral x for a clockwise ring (front half = indices 0 .. n/2)."""
    n = len(ring)
    fr = ring[: n // 2 + 1]
    xs, ys = fr[::-1, 0], fr[::-1, 1]                            # ascending x
    xu, iu = np.unique(xs, return_index=True)
    # at duplicated x (vertical side faces) take the front-most y
    yu = np.array([ys[xs == v].min() for v in xu])
    return float(np.interp(x, xu, yu))


def front_normal(ring, x, side=-1):
    """Outward normal (x, y) of the ring's front (side -1) or back (+1) surface at lateral x."""
    n = len(ring)
    fr = ring[: n // 2 + 1]
    best = None
    for i in range(len(fr) - 1):
        (x0, y0), (x1, y1) = fr[i], fr[i + 1]
        lo, hi = min(x0, x1), max(x0, x1)
        if lo - 1e-9 <= x <= hi + 1e-9 and abs(x1 - x0) > 1e-9:
            e = np.array([x1 - x0, y1 - y0])
            nrm = _norm(np.array([-e[1], e[0]]))                 # clockwise ring -> outward
            if best is None or (nrm[1] < best[1]):
                best = nrm
    if best is None:
        best = np.array([0.0, -1.0])
    return np.array([best[0], -best[1]]) if side > 0 else best


# ====================================================================== cavity

def cavity_level(level):
    d = np.load(FIT_DIR / f"cavity_L{level}.npz")
    st, polys = d["stations"], d["polys"]
    return st, polys


def cw_poly(P):
    """CCW support polygon -> clockwise ring starting near angle 0 (the core's ring convention)."""
    Q = np.asarray(P, float)[::-1]
    a = np.arctan2(Q[:, 1], Q[:, 0])
    s = int(np.argmin(np.abs(a)))
    return np.vstack([Q[s:], Q[:s]])


def cavity_at(level, z, offset=0.0):
    st, polys = cavity_level(level)
    z = float(np.clip(z, st[0], st[-1]))
    k = int(np.clip(np.searchsorted(st, z) - 1, 0, len(st) - 2))
    t = (z - st[k]) / (st[k + 1] - st[k])
    P = (1 - t) * polys[k] + t * polys[k + 1]
    if offset:
        from sfv4_prims import offset_polygon
        P = offset_polygon(P, -offset)
    return cw_poly(P)


def cavity_stations(level, z0, z1):
    st, _ = cavity_level(level)
    zs = [z0] + [z for z in st if z0 + 1.0 < z < z1 - 1.0] + [z1]
    return np.array(zs)


# ====================================================================== the lacquer core (+ cavity)

def build_core(mb: MB, level, uvmode="atlas"):
    """Outer faceted shell (mouth -> row 1266) + cavity + top/bottom annuli: one closed hollow shell.
    uvmode 'atlas': islands; 'pattern': UV = (u + offset, z) mm into the painted lacquer image (high only)."""
    rows = core_rows(level)
    keep = list(range(16)) if level != 2 else S.CORE_LOD2
    O_idx, O_pts = [], []
    for r in rows:
        ring = core_ring(r)
        z = float(S.zr(r))
        pts3 = [(ring[j][0], ring[j][1], z) for j in keep]
        O_idx.append(mb.vs(pts3))
        O_pts.append(ring)
    nk = len(keep)
    for i in range(len(rows) - 1):
        seg, hidden = body_seg(0.5 * (rows[i] + rows[i + 1]))
        ufs = [ring_uv_front_back(O_pts[i]), ring_uv_front_back(O_pts[i + 1])]
        zs = [float(S.zr(rows[i])), float(S.zr(rows[i + 1]))]
        for c in range(nk):
            ja, jb = keep[c], (keep[(c + 1) % nk] if c + 1 < nk else 16)
            front = jb <= 8
            q = [O_idx[i][c], O_idx[i][(c + 1) % nk], O_idx[i + 1][(c + 1) % nk], O_idx[i + 1][c]]
            uv = []
            for rr, j in ((0, ja), (0, jb), (1, jb), (1, ja)):
                uf, ub = ufs[rr]
                u = uf[j] if front else ub[j]
                if uvmode == "pattern":
                    u = u + (0.0 if front else 100.0)
                uv.append((u, zs[rr]))
            isl = f"body{seg}_{'f' if front else 'b'}"
            mat = H_LACQ if uvmode == "pattern" else LACQ
            mb.f(q, uv, isl, mat)
    # ---- cavity (the swept blade + clearance), same z range
    lv = 0 if level == "high" else level
    z0, z1 = float(S.zr(rows[0])), float(S.zr(rows[-1]))
    cz = cavity_stations(lv, z0, z1)
    C_idx, C_pts = [], []
    for z in cz:
        P = cavity_at(lv, z)
        C_idx.append(mb.vs([(p[0], p[1], z) for p in P]))
        C_pts.append(P)
    m = len(C_pts[0])
    for i in range(len(cz) - 1):
        s0, s1 = ring_arclen(C_pts[i]), ring_arclen(C_pts[i + 1])
        isl = "cav_mouth" if cz[i] < S.Z_MOUTH + 60 else f"cav{min(int((cz[i] - S.Z_MOUTH) / 260), 3)}"
        for c in range(m):
            c2 = (c + 1) % m
            q = [C_idx[i][c], C_idx[i + 1][c], C_idx[i + 1][c2], C_idx[i][c2]]
            uv = [(s0[c], cz[i]), (s1[c], cz[i + 1]), (s1[c + 1], cz[i + 1]), (s0[c + 1], cz[i])]
            mb.f(q, uv, isl, H_CAVITY if uvmode == "pattern" else LACQ)
    # ---- annuli
    top_mat = H_LACQ if uvmode == "pattern" else LACQ
    zipper(mb, O_idx[0], O_pts[0][keep], C_idx[0], C_pts[0], "core_top", top_mat)
    zipper(mb, O_idx[-1], O_pts[-1][keep], C_idx[-1], C_pts[-1], "core_bot", top_mat)
    return {"rows": rows, "outer": O_pts, "cav_z": cz}


# ====================================================================== fittings

def throat_rows(level):
    tol = {0: 0.35, 1: 1.2, 2: 2.2, "high": 0.15}[level]
    step = {0: 12.0, 1: 30.0, 2: 60.0, "high": 4.0}[level]
    must = [31.0, S.THROAT_COLLAR_ROWS[1], 142.0, 167.0]
    return plan_rows(31.0, 167.0, S.throat_half, tol, step, must)


def band_rows(level):
    tol = {0: 0.2, 1: 0.6, 2: 1.5, "high": 0.1}[level]
    step = {0: 6.0, 1: 12.0, 2: 33.0, "high": 3.0}[level]
    return plan_rows(S.BAND_ROWS[0], S.BAND_ROWS[1], S.band_half, tol, step, [292.0, 300.0, 308.0])


def chape_rows(level):
    tol = {0: 0.3, 1: 0.8, 2: 1.8, "high": 0.12}[level]
    step = {0: 20.0, 1: 40.0, 2: 80.0, "high": 5.0}[level]
    must = [1262.0, 1266.0, 1292.0, 1344.0, 1386.5, 1388.0]
    return plan_rows(1262.0, 1494.0, lambda r: [S.chape_half(r), S.chape_depth(r)], tol, step, must)


def throat_ring(row):
    Wc, Dc = float(S.core_w(row)), float(S.body_d(row))
    return fit_section(S.throat_half(row), Wc, Dc, S.T_THROAT)


def band_ring(row):
    Wc, Dc = float(S.core_w(row)), float(S.body_d(row))
    return fit_section(S.band_half(row), Wc, Dc, S.T_BAND)


def chape_ring(row):
    a = S.chape_half(row)
    body_half = 72.4 * S.K / 2
    D = S.chape_depth(row)
    if row <= 1388.0:
        return fit_section(a, 2 * body_half - 0.3, D - 0.3, 0.15, e=2.0)
    # ogive: the section is its own core (no flange)
    return fit_section(a, 2 * max(a - 0.15, 0.3), max(D - 0.3, 0.6), 0.15)


def _loft_fitting(mb, rows, ring_fn, level, prefix, base_mat_fn=None, uvmode="atlas", mat=SILV):
    keep = list(range(20)) if level in (0, "high") else FIT_LOD2
    nk = len(keep)
    idx, pts = [], []
    for r in rows:
        ring = ring_fn(r)
        z = float(S.zr(r))
        idx.append(mb.vs([(ring[j][0], ring[j][1], z) for j in keep]))
        pts.append(ring)
    for i in range(len(rows) - 1):
        ufs = [ring_uv_front_back(pts[i]), ring_uv_front_back(pts[i + 1])]
        zs = [float(S.zr(rows[i])), float(S.zr(rows[i + 1]))]
        for c in range(nk):
            ja, jb = keep[c], (keep[(c + 1) % nk] if c + 1 < nk else 20)
            front = jb <= 10
            q = [idx[i][c], idx[i][(c + 1) % nk], idx[i + 1][(c + 1) % nk], idx[i + 1][c]]
            uv = []
            for rr, j in ((0, ja), (0, jb), (1, jb), (1, ja)):
                uf, ub = ufs[rr]
                uv.append(((uf[j] if front else ub[j]), zs[rr]))
            m = base_mat_fn(0.5 * (rows[i] + rows[i + 1]), ja, jb % 20) if base_mat_fn else mat
            mb.f(q, uv, f"{prefix}_{'f' if front else 'b'}", m)
    return idx, [p[keep] for p in pts]


def _inner_ring(row, shrink=0.4):
    return S.core_section(float(S.core_w(row)) - 2 * shrink, float(S.body_d(row)) - 2 * shrink)


def build_throat(mb: MB, level, high=False):
    rows = throat_rows(level)
    base = None
    if high:
        def base(row, ja, jb):
            if row < S.THROAT_COLLAR_ROWS[1] + 0.5 or row > 163.0:
                return H_SILVER
            if ja in FIT_SIDE_IDX and jb in FIT_SIDE_IDX:
                return H_SILVER
            return H_INSET
    O_idx, O_pts = _loft_fitting(mb, rows, throat_ring, level, "throat", base, mat=SILV)
    # inner: lip at the mouth (cavity + 0.3), then the core shrunk 0.4 mm, down to the sleeve bottom
    lv = 0 if level == "high" else level
    in_rows = [31.0, float(S.row_of(S.Z_MOUTH + 1.5))] + [r for r in rows if r > S.row_of(S.Z_MOUTH + 1.5) + 0.5]
    I_idx, I_pts = [], []
    for k, r in enumerate(in_rows):
        P = cavity_at(lv, S.Z_MOUTH, offset=0.3) if k == 0 else _inner_ring(r)
        z = float(S.zr(r))
        I_idx.append(mb.vs([(p[0], p[1], z) for p in P]))
        I_pts.append(P)
    imat = H_INSET if high else SILV
    for i in range(len(in_rows) - 1):
        n = len(I_pts[i])
        for c in range(n):
            c2 = (c + 1) % n
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 5.0, in_rows[i] * S.K), (c * 5.0, in_rows[i + 1] * S.K), ((c + 1) * 5.0, in_rows[i + 1] * S.K),
                  ((c + 1) * 5.0, in_rows[i] * S.K)]
            mb.f(q, uv, "throat_in", imat)
    tmat = H_SILVER if high else SILV
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "throat_top", tmat)
    zipper(mb, O_idx[-1], O_pts[-1], I_idx[-1], I_pts[-1], "throat_bot", tmat)
    return rows


def build_band(mb: MB, level, high=False):
    rows = band_rows(level)
    O_idx, O_pts = _loft_fitting(mb, rows, band_ring, level, "band", (lambda r, a, b: H_SILVER) if high else None)
    I_idx, I_pts = [], []
    for r in rows:
        P = _inner_ring(r)
        I_idx.append(mb.vs([(p[0], p[1], float(S.zr(r))) for p in P]))
        I_pts.append(P)
    imat = H_INSET if high else SILV
    for i in range(len(rows) - 1):
        for c in range(16):
            c2 = (c + 1) % 16
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 5.0, rows[i] * S.K), (c * 5.0, rows[i + 1] * S.K), ((c + 1) * 5.0, rows[i + 1] * S.K),
                  ((c + 1) * 5.0, rows[i] * S.K)]
            mb.f(q, uv, "band_in", imat)
    tmat = H_SILVER if high else SILV
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "band_top", tmat)
    zipper(mb, O_idx[-1], O_pts[-1], I_idx[-1], I_pts[-1], "band_bot", tmat)
    return rows


def build_chape(mb: MB, level, high=False):
    rows = chape_rows(level)
    base = None
    if high:
        def base(row, ja, jb):
            if ja in FIT_SIDE_IDX and jb in FIT_SIDE_IDX:
                return H_SILVER
            return H_INSET
    O_idx, O_pts = _loft_fitting(mb, rows, chape_ring, level, "chape", base)
    # the point
    tip = mb.v((0.0, 0.0, S.Z_POINT))
    last = O_idx[-1]
    n = len(last)
    for c in range(n):
        p0, p1 = O_pts[-1][c], O_pts[-1][(c + 1) % n]
        mb.f([last[c], last[(c + 1) % n], tip], [(p0[0], p0[1]), (p1[0], p1[1]), (0.0, 0.0)], "chape_point",
             H_SILVER if high else SILV)
    # inner: the cavity (offset 0.2 so it never coincides with the core's), from row 1262 to the cavity end
    lv = 0 if level == "high" else level
    st, _ = cavity_level(lv)
    z0 = float(S.zr(1262.0))
    cz = cavity_stations(lv, z0, float(st[-1]))
    I_idx, I_pts = [], []
    for z in cz:
        P = cavity_at(lv, z, offset=0.2)
        I_idx.append(mb.vs([(p[0], p[1], z) for p in P]))
        I_pts.append(P)
    imat = H_CAVITY if high else SILV
    for i in range(len(cz) - 1):
        m = len(I_pts[i])
        for c in range(m):
            c2 = (c + 1) % m
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 4.0, cz[i]), (c * 4.0, cz[i + 1]), ((c + 1) * 4.0, cz[i + 1]), ((c + 1) * 4.0, cz[i])]
            mb.f(q, uv, "chape_cav", imat)
    ctr = I_pts[-1].mean(axis=0)
    fan_cap(mb, list(I_idx[-1]), (ctr[0], ctr[1], cz[-1]), "chape_cav", imat,
            uv_ring=[(p[0], p[1]) for p in I_pts[-1]], uv_center=(ctr[0], ctr[1]))
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "chape_top", H_SILVER if high else SILV)
    return rows


# ====================================================================== surfaces for placing ornament

def surface_ring(row):
    """The outermost ring at a reference row (fitting where there is one, else the core)."""
    if S.THROAT_COLLAR_ROWS[0] <= row <= 167.0:
        return throat_ring(row)
    if S.BAND_ROWS[0] <= row <= S.BAND_ROWS[1]:
        return band_ring(row)
    if row >= S.CHAPE_SLEEVE_TOP:
        return chape_ring(min(row, 1494.0))
    return core_ring(row)


def surf_point(x, row, side=-1, lift=0.0, ring_fn=None):
    """Point (mm) on the front (-1) or back (+1) surface at lateral x, reference row; lifted along the normal."""
    ring = (ring_fn or surface_ring)(row)
    y = front_y(ring, x)
    nrm = front_normal(ring, x, side)
    p = np.array([x, y if side < 0 else -y, float(S.zr(row))])
    n3 = np.array([nrm[0], nrm[1], 0.0])
    return p + n3 * lift, n3


# ====================================================================== vine

def stem_path(step_mm):
    pts = S.vine_path_px()
    # look-match: the stem ends at the chape arch's apex (the arch legs are its fork), not under the sleeve
    pts = [(158.0, pts[0][1])] + list(pts)[:-1] + [(1256.0, 513.5), (1267.0, 512.5)]
    P = np.array([[S.xp(x), float(r)] for r, x in pts])
    C = catmull(P, steps=8)
    L = arclen(np.c_[C[:, 0], C[:, 1] * S.K])
    n = max(int(L[-1] / step_mm), 8)
    R = resample(np.c_[C[:, 0], C[:, 1] * S.K], n)
    R[:, 1] /= S.K
    return R                                                  # (x mm, row)


def stem_geometry(step_mm, lift_frac=-0.05):
    xr = stem_path(step_mm)
    path, ups, rad = [], [], []
    for x, row in xr:
        r = S.stem_width_px(row) * S.K / 2
        p, n = surf_point(x, row, -1, 0.0, ring_fn=lambda rr: core_ring(rr) if rr < S.CHAPE_SLEEVE_TOP else chape_ring(rr))
        path.append(p + n * (lift_frac * r))
        ups.append(n)
        rad.append(r)
    return np.array(path), np.array(ups), np.array(rad)


def build_stem(mb: MB, level, high=False, mat=SILV):
    step = {0: 4.0, 1: 11.0, "high": 1.6}[level]
    sides = {0: 6, 1: 4, "high": 12}[level]
    P, U, R = stem_geometry(step)
    L = arclen(P)
    nseg = 4

    def isl(r):
        return f"stem{min(int(L[min(r, len(L) - 1)] / L[-1] * nseg), nseg - 1)}"
    tube(mb, P, R, sides=sides, island=isl, mat=mat, cap=("flat", "flat"), squash=S.VINE_SQUASH, up=U)


# ====================================================================== blossoms

FITTING_LIFT = {"throat": 1.6, "band": 0.9, "chape": 1.4}


def blossom_list():
    """(name, centre xyz, normal, radius mm, phase, up_hint, kind) - vine blossoms on the core, fitting blossoms on
    their fittings (lifted over the plate frames)."""
    out = []
    rng = np.random.default_rng(3131)
    for i, b in enumerate(S.vine_blossoms_px()):
        x, row = float(S.xp(b["x"])), float(b["row"])
        r = b["diameter_px"] * S.K / 2
        p, n = surf_point(x, row, -1, 0.35, ring_fn=core_ring)
        out.append((f"v{i}", p, n, r, float(rng.uniform(0, 2 * math.pi)), (0.0, 0.0, -1.0), "vine"))
    for name, ((xpx, row), d), ring_fn, lift in (("throat", S.THROAT_BLOSSOM, throat_ring, FITTING_LIFT["throat"]),
                                                 ("band", S.BAND_BLOSSOM, band_ring, FITTING_LIFT["band"]),
                                                 ("chape", S.CHAPE_BLOSSOM, chape_ring, FITTING_LIFT["chape"])):
        p, n = surf_point(float(S.xp(xpx)), float(row), -1, lift, ring_fn=ring_fn)
        out.append((name, p, n, d * S.K / 2, 0.0, (0.0, 0.0, -1.0), "fitting"))
    return out


def build_blooms(mb: MB, level):
    from sfv4_blade import flower_disc
    for name, p, n, r, ph, up, kind in blossom_list():
        if level == 2 and kind != "fitting":
            continue
        if level == 1 and kind == "vine" and r * 2 / S.K < 30:
            continue
        n_out = {0: 25, 1: 15, 2: 10}[level]
        # final pass: a fitting blossom sits FITTING_LIFT above its fitting; its proxy rim now sinks 0.4 mm into the
        # fitting instead of floating 1.1-0.4 mm above it (a thin card with a dark edge at grazing angles)
        sink = FITTING_LIFT[name] + 0.4 if kind == "fitting" else 0.5
        # flower_disc puts lobe k at angle phase + k*72deg from up_hint's projection; its lobes follow cos(2.5*(th-phase))
        flower_disc(mb, p, r, n, ph, f"bl_{name}", SILV, n_out=n_out, up_hint=up, height=0.17, sink=sink)


# ====================================================================== LOOK-MATCH ROUND 1: the throat crown
#: fractions of the half-width sampled on the front (and back) of the crown ring, per level
CROWN_FRONT = {0: [1.0, 0.86, 0.72, 0.56, 0.38, 0.19, 0.0],
               1: [1.0, 0.8, 0.45, 0.0],
               2: [1.0, 0.6, 0.0],
               "high": list(np.linspace(1.0, 0.0, 30))}


def _oct_front_y(row, x):
    """Front y (negative) of the core octagon offset by the throat wall, at lateral x (clamped to the ring)."""
    ring = S.core_section(float(S.core_w(row)) + 2 * S.T_THROAT, float(S.body_d(row)) + 2 * S.T_THROAT)
    c = float(np.abs(ring[:, 0]).max())
    return front_y(ring, float(np.clip(x, -c, c)))


def _collar_offset(row, nx, ny):
    """Outward offset (mm) of the crown ring at a row: the rounded mouth ring (fillet + bead + groove)."""
    dz = (row - S.ROW_MOUTH) * S.K
    fx, fy = S.COLLAR_FILLET
    R = abs(nx) * fx + abs(ny) * fy
    fil = R - math.sqrt(max(R * R - (R - dz) ** 2, 0.0)) if dz < R else 0.0
    r0, r1, bead = S.COLLAR_BEAD
    b = bead * math.sin(math.pi * (row - r0) / (r1 - r0)) if r0 <= row <= r1 else 0.0
    gr, gw, gd = S.COLLAR_GROOVE
    g = gd * math.exp(-((row - gr) / gw) ** 2)
    return -fil + b - g


def crown_ring(row, level=0):
    """Closed ring (x, y) of the crown bulb at a reference row, clockwise from the +X side over the FRONT (-Y).
    Section: the plate envelope (a broad superellipse, AX) over the front and back, rounded into the sides by a
    squircle of the bulb's own half-width (no flat box sides); the leaves float free where the bulb curves away."""
    A = S.crown_half(row)
    Yb = S.crown_Yb(row)
    fr = CROWN_FRONT[level]
    blend = float(np.clip((row - 140.0) / 20.0, 0.0, 1.0))      # the lower sleeve hugs the octagon (rows 140-160)
    # the side: angles from the +X axis toward the front; squircle x = A cos^(2/m), y = Yb' sin^(2/m)
    ms = S.CROWN_SIDE_M
    pts = []
    nside = {0: 5, 1: 3, 2: 2, "high": 12}[level]
    th_max = math.acos(min((fr[1] + 0.035) ** (ms / 2), 0.9999))   # the side ends just outside the first front sample
    for k in range(nside + 1):                        # +X side (y = 0) .. into the front
        th = th_max * k / (nside + 1)
        x = A * math.cos(th) ** (2 / ms)
        y = -Yb * math.sin(th) ** (2 / ms)
        pts.append((x, y))
    xs_front = [A * f for f in fr[1:]]                # front samples (inner part), then mirrored
    front = []
    for x in xs_front:
        y_env = -Yb * (1.0 - min(abs(x) / S.CROWN_AX, 0.999) ** S.CROWN_M) ** (1.0 / S.CROWN_M)
        y_sq = -Yb * (1.0 - min(abs(x) / A, 0.999) ** ms) ** (1.0 / ms)
        y = max(y_env, y_sq)                          # the inner of the two (both negative on the front)
        if blend > 0:
            y = (1 - blend) * y + blend * _oct_front_y(row, x)
        front.append((x, y))
    side_r = []
    for x, y in pts:
        if blend > 0:
            yo = _oct_front_y(row, x) if y < 0 else 0.0
            y = (1 - blend) * y + blend * yo
        side_r.append((x, y))
    half = side_r + front + [(-x, y) for x, y in front[-2::-1]] + [(-x, y) for x, y in side_r[::-1]]
    ring = half + [(x, -y) for x, y in half[-2:0:-1]]
    P = np.array(ring, float)
    if row < S.COLLAR_GROOVE[0] + 3 * S.COLLAR_GROOVE[1]:
        n = len(P)
        Q = P.copy()
        for i in range(n):
            e = P[(i + 1) % n] - P[i - 1]
            nrm = np.array([e[1], -e[0]])
            nrm /= max(np.linalg.norm(nrm), 1e-9)
            if nrm @ P[i] < 0:
                nrm = -nrm
            Q[i] = P[i] + nrm * _collar_offset(row, nrm[0], nrm[1])
        P = Q
    return P


def crown_rows(level):
    if level == "high":
        top = list(np.arange(31.0, 45.0, 0.35))
        return np.array(sorted(set([round(r, 3) for r in top + list(np.arange(45.0, 167.0, 3.0)) + [167.0]])))
    return np.array({0: [31.0, 31.35, 31.9, 32.7, 33.8, 35.3, 37.0, 39.0, 40.8, 41.8, 42.5, 43.4, 45.5, 55.0, 66.0,
                         80.0, 92.0, 104.0, 122.0, 140.0, 150.0, 160.0, 167.0],
                     1: [31.0, 32.0, 34.0, 37.5, 41.3, 42.5, 44.5, 62.0, 81.0, 100.0, 130.0, 150.0, 167.0],
                     2: [31.0, 33.0, 37.5, 42.3, 62.0, 100.0, 140.0, 167.0]}[level], float)


def throat_ring(row):
    """(kept name) the outermost throat ring at a row - the crown bulb at LOD0 resolution."""
    return crown_ring(float(row), 0)


def build_throat(mb: MB, level, high=False):
    """The crown bulb: rounded mouth ring on top, a superellipse bulb that carries the leaf plates, the lower sleeve
    hugging the body; hollow (mouth lip = cavity + 0.3, then the core shrunk 0.4 mm)."""
    rows = crown_rows(level)
    O_idx, O_pts = [], []
    for r in rows:
        ring = crown_ring(float(r), level)
        O_idx.append(mb.vs([(p[0], p[1], float(S.zr(r))) for p in ring]))
        O_pts.append(ring)
    n = len(O_pts[0])
    h = n // 2
    for i in range(len(rows) - 1):
        z0, z1 = float(S.zr(rows[i])), float(S.zr(rows[i + 1]))
        s0, s1 = ring_arclen(O_pts[i]), ring_arclen(O_pts[i + 1])
        for c in range(n):
            c2 = (c + 1) % n
            front = c < h
            q = [O_idx[i][c], O_idx[i][c2], O_idx[i + 1][c2], O_idx[i + 1][c]]
            # u: arclength from the front centre (front island) / back centre (back island); v: z
            if front:
                u0, u1 = s0[c] - s0[h // 2], s0[c + 1] - s0[h // 2]
                w0, w1 = s1[c] - s1[h // 2], s1[c + 1] - s1[h // 2]
            else:
                u0, u1 = -(s0[c] - s0[h + h // 2]), -(s0[c + 1] - s0[h + h // 2])
                w0, w1 = -(s1[c] - s1[h + h // 2]), -(s1[c + 1] - s1[h + h // 2])
            uv = [(u0, z0), (u1, z0), (w1, z1), (w0, z1)]
            if high:
                m = H_SILVER if rows[i] < S.COLLAR_GROOVE[0] else H_INSET
                mb.f(q, None, "HIGH", m)
            else:
                mb.f(q, uv, f"crown_{'f' if front else 'b'}", SILV)
    # inner: lip at the mouth (cavity + 0.3), then the core shrunk 0.4 mm, down to the sleeve bottom
    lv = 0 if level == "high" else level
    in_rows = [31.0, float(S.row_of(S.Z_MOUTH + 1.5))] + [r for r in rows if r > S.row_of(S.Z_MOUTH + 1.5) + 0.5]
    I_idx, I_pts = [], []
    for k, r in enumerate(in_rows):
        P = cavity_at(lv, S.Z_MOUTH, offset=0.3) if k == 0 else _inner_ring(r)
        z = float(S.zr(r))
        I_idx.append(mb.vs([(p[0], p[1], z) for p in P]))
        I_pts.append(P)
    imat = H_INSET if high else SILV
    for i in range(len(in_rows) - 1):
        m_ = len(I_pts[i])
        for c in range(m_):
            c2 = (c + 1) % m_
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 5.0, in_rows[i] * S.K), (c * 5.0, in_rows[i + 1] * S.K), ((c + 1) * 5.0, in_rows[i + 1] * S.K),
                  ((c + 1) * 5.0, in_rows[i] * S.K)]
            mb.f(q, uv if not high else None, "throat_in" if not high else "HIGH", imat)
    tmat = H_SILVER if high else SILV
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "throat_top" if not high else "HIGH", tmat)
    zipper(mb, O_idx[-1], O_pts[-1], I_idx[-1], I_pts[-1], "throat_bot" if not high else "HIGH", tmat)
    return rows


# ====================================================================== LOOK-MATCH ROUND 1: plates

def plate_sides(part):
    """Front (-1) always; the back (+1) continues the front's design (the reference shows only the front)."""
    return (-1, 1)


def build_plates(mb: MB, part, level, tiers=None, high=False, sides=None):
    import shv4_plates as PL
    table = {"throat": (S.THROAT_LEAVES, "crown"), "chape": (getattr(S, "CHAPE_LEAVES", []), "chape"),
             "band": (getattr(S, "BAND_LEAVES", []), "core")}[part]
    leaves = PL.expand(PL.leaves_from(*table))
    n = 0
    for tag, lf in leaves:
        if tiers is not None and lf.tier not in tiers:
            continue
        for side in (sides or lf.sides):
            isl = f"pl_{part}_{tag}_{'f' if side < 0 else 'b'}"
            n += PL.build_leaf(mb, lf, side, level, isl, SILV, high=high)
    return n


# ====================================================================== LOOK-MATCH ROUND 1: pearl blossoms

def fitting_blossoms():
    """(name, centre, normal, radius, phase, up, side) of the fitting blossoms: throat (front + back), band (front),
    chape (front + back).  Each sits over its fitting's top plate tier."""
    import shv4_plates as PL
    out = []
    (xpx, row), d = S.THROAT_BLOSSOM
    x, z = float(S.xp(xpx)), float(S.zr(row))
    env = PL.ENVS["crown"]
    for side in (-1, 1):
        n = env.normal(x, z, side)
        c = env.point(x, z, side) + n * S.THROAT_BLOSSOM_TIER_LIFT
        out.append((f"throat{'F' if side < 0 else 'B'}", c, n, d * S.K / 2, 0.0, np.array([0.0, 0.0, -1.0]), side))
    for name, spec, env_name, lift_attr in (("band", S.BAND_BLOSSOM, "band", "BAND_BLOSSOM_LIFT"),
                                            ("chape", S.CHAPE_BLOSSOM, "chape", "CHAPE_BLOSSOM_LIFT")):
        (xpx, row), d = spec
        x, z = float(S.xp(xpx)), float(S.zr(row))
        env = PL.ENVS[env_name]
        for side in ((-1,) if name == "band" else (-1, 1)):
            n = env.normal(x, z, side)
            c = env.point(x, z, side) + n * getattr(S, lift_attr, 1.0)
            out.append((f"{name}{'F' if side < 0 else 'B'}", c, n, d * S.K / 2, 0.0, np.array([0.0, 0.0, -1.0]), side))
    return out


def vine_blossoms():
    out = []
    rng = np.random.default_rng(3131)
    for i, b in enumerate(S.vine_blossoms_px()):
        x, row = float(S.xp(b["x"])), float(b["row"])
        r = b["diameter_px"] * S.K / 2
        p, n = surf_point(x, row, -1, 0.0, ring_fn=core_ring)
        out.append((f"v{i}", p, n, r, float(rng.uniform(0, 2 * math.pi)), np.array([0.0, 0.0, -1.0]), -1))
    return out


def build_pearl_blooms(mb: MB, level, kinds=("vine", "fitting"), high_sink=None):
    import shv4_bloom as BL
    items = []
    if "fitting" in kinds:
        items += [("f", *it) for it in fitting_blossoms()]
    if "vine" in kinds:
        items += [("v", *it) for it in vine_blossoms()]
    for kind, name, c, n, r, ph, up, side in items:
        if high_sink is not None:
            BL.build_high(high_sink, c, n, up, r, ph)
            continue
        if level == 2 and kind == "v":
            continue
        if level == 1 and kind == "v" and r * 2 / S.K < 30:
            continue
        BL.build_low(mb, c, n, up, r, level, f"bl_{name}", SILV, ph)


# ====================================================================== LOOK-MATCH ROUND 1: the chape
CHAPE_FRONT = {0: [1.0, 0.96, 0.86, 0.7, 0.48, 0.24, 0.0], 1: [1.0, 0.9, 0.6, 0.0], 2: [1.0, 0.75, 0.0],
               "high": list(np.linspace(1.0, 0.0, 22))}


def chape_ring(row, level=0):
    """Closed ring of the chape body at a row (clockwise from +X over the front): the sleeve (rows 1292-1388) is a
    rounded superellipse over the core; the ogive (1388-1496) a lens whose rounded sides are the bevelled rim."""
    row = float(min(row, 1495.0))
    A = S.chape_body_half(row)
    Yb = S.chape_Yb(row)
    ax, m = S.chape_ax(row), S.chape_m(row)
    fr = CHAPE_FRONT[level]
    xs = [A * f for f in fr] + [-A * f for f in fr[-2::-1]]
    r0, r1, lip = S.CHAPE_TOP_LIP
    e = lip * math.sin(math.pi * (row - r0) / (r1 - r0)) ** 0.5 if r0 <= row <= r1 else 0.0
    A2, Yb2 = A + e, Yb + e
    front = [(x * A2 / A, -Yb2 * (1.0 - min(abs(x) / ax, 0.999) ** m) ** (1.0 / m)) for x in xs]
    ring = [(A2, 0.0)] + front + [(-A2, 0.0)] + [(x, -y) for x, y in front[::-1]]
    return np.array(ring, float)


def chape_rows_lm(level):
    if level == "high":
        r = list(np.arange(S.CHAPE_SLEEVE_TOP, 1387.9, 2.0)) + [1387.9, 1388.1] + list(np.arange(1390.0, 1494.0, 2.0))
        return np.array(r + [1494.0])
    return np.array({0: [1292.0, 1293.2, 1295.5, 1297.8, 1299.0, 1310.0, 1340.0, 1370.0, 1387.9, 1388.1, 1400.0, 1420.0, 1440.0, 1458.0,
                         1474.0, 1486.0, 1494.0],
                     1: [1292.0, 1295.5, 1299.0, 1340.0, 1387.9, 1388.1, 1420.0, 1450.0, 1476.0, 1494.0],
                     2: [1292.0, 1295.5, 1299.0, 1387.9, 1388.1, 1440.0, 1494.0]}[level], float)


def build_chape(mb: MB, level, high=False):
    rows = chape_rows_lm(level)
    O_idx, O_pts = [], []
    for r in rows:
        ring = chape_ring(float(r), level)
        O_idx.append(mb.vs([(p[0], p[1], float(S.zr(r))) for p in ring]))
        O_pts.append(ring)
    n = len(O_pts[0])
    h = n // 2
    for i in range(len(rows) - 1):
        z0, z1 = float(S.zr(rows[i])), float(S.zr(rows[i + 1]))
        s0, s1 = ring_arclen(O_pts[i]), ring_arclen(O_pts[i + 1])
        for c in range(n):
            c2 = (c + 1) % n
            front = c < h
            q = [O_idx[i][c], O_idx[i][c2], O_idx[i + 1][c2], O_idx[i + 1][c]]
            if front:
                u0, u1 = s0[c] - s0[h // 2], s0[c + 1] - s0[h // 2]
                w0, w1 = s1[c] - s1[h // 2], s1[c + 1] - s1[h // 2]
            else:
                u0, u1 = -(s0[c] - s0[h + h // 2]), -(s0[c + 1] - s0[h + h // 2])
                w0, w1 = -(s1[c] - s1[h + h // 2]), -(s1[c + 1] - s1[h + h // 2])
            uv = [(u0, z0), (u1, z0), (w1, z1), (w0, z1)]
            if high:
                # the sleeve between its plates is dark (like the reference); its top lip and the ogive are silver
                rm = 0.5 * (rows[i] + rows[i + 1])
                dark = S.CHAPE_TOP_LIP[1] + 0.5 < rm < S.CHAPE_OGIVE_ROW
                mb.f(q, None, "HIGH", H_INSET if dark else H_SILVER)
            else:
                mb.f(q, uv, f"chape_{'f' if front else 'b'}", SILV)
    # the point
    tip = mb.v((0.0, 0.0, S.Z_POINT))
    last = O_idx[-1]
    for c in range(n):
        p0, p1 = O_pts[-1][c], O_pts[-1][(c + 1) % n]
        mb.f([last[c], last[(c + 1) % n], tip], None if high else [(p0[0], p0[1]), (p1[0], p1[1]), (0.0, 0.0)],
             "HIGH" if high else "chape_point", H_SILVER if high else SILV)
    # the step at the ogive (rows 1387.9 -> 1388.1) is part of the loft; inner: the cavity from the sleeve top
    lv = 0 if level == "high" else level
    st, _ = cavity_level(lv)
    z0 = float(S.zr(S.CHAPE_SLEEVE_TOP))
    cz = cavity_stations(lv, z0, float(st[-1]))
    I_idx, I_pts = [], []
    for z in cz:
        P = cavity_at(lv, z, offset=0.2)
        I_idx.append(mb.vs([(p[0], p[1], z) for p in P]))
        I_pts.append(P)
    imat = H_CAVITY if high else SILV
    for i in range(len(cz) - 1):
        m_ = len(I_pts[i])
        for c in range(m_):
            c2 = (c + 1) % m_
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 4.0, cz[i]), (c * 4.0, cz[i + 1]), ((c + 1) * 4.0, cz[i + 1]), ((c + 1) * 4.0, cz[i])]
            mb.f(q, None if high else uv, "HIGH" if high else "chape_cav", imat)
    ctr = I_pts[-1].mean(axis=0)
    fan_cap(mb, list(I_idx[-1]), (ctr[0], ctr[1], cz[-1]), "HIGH" if high else "chape_cav", imat,
            uv_ring=[(p[0], p[1]) for p in I_pts[-1]], uv_center=(ctr[0], ctr[1]))
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "HIGH" if high else "chape_top", H_SILVER if high else SILV)
    return rows


# ====================================================================== LOOK-MATCH ROUND 1: the band

def band_t(row):
    """Offset (mm) of the band over the core at a row: the frieze level plus two rounded rims."""
    t = S.BAND_T_FRIEZE
    for r0, r1 in S.BAND_RIMS:
        if r0 <= row <= r1:
            s = (row - r0) / (r1 - r0)
            t += S.BAND_RIM_H * min(1.0, 3.0 * math.sin(math.pi * s)) ** 0.5
    return t


def band_ring(row):
    Wc, Dc = float(S.core_w(row)), float(S.body_d(row))
    t = band_t(float(row))
    r0, r1, _, _ = S.BAND_FRIEZE
    a = float(S.core_w(row)) / 2 + t
    if r0 < row < r1:                     # only the frieze carries the pointed side ends (a flange)
        a = max(S.band_half(row), a)
    return fit_section(a, Wc, Dc, t)


def band_rows(level):
    if level == "high":
        return np.array(sorted(set([round(r, 3) for r in list(np.arange(284.0, 317.01, 0.5))])))
    base = {0: [284.0, 285.2, 287.0, 288.3, 290.5, 292.5, 294.0, 297.0, 300.0, 303.0, 306.0, 308.5, 310.5, 312.7,
                314.2, 316.0, 317.0],
            1: [284.0, 286.0, 288.3, 292.5, 300.0, 308.5, 312.7, 315.0, 317.0],
            2: [284.0, 288.3, 292.5, 300.0, 308.5, 312.7, 317.0]}[level]
    return np.array(base, float)


def build_band(mb: MB, level, high=False):
    rows = band_rows(level)

    def hmat(r, a, b):
        in_rim = any(r0 - 0.2 <= r <= r1 + 0.2 for r0, r1 in S.BAND_RIMS)
        return H_SILVER if in_rim else H_INSET
    O_idx, O_pts = _loft_fitting(mb, rows, band_ring, level, "band", hmat if high else None)
    I_idx, I_pts = [], []
    for r in rows:
        P = _inner_ring(r)
        I_idx.append(mb.vs([(p[0], p[1], float(S.zr(r))) for p in P]))
        I_pts.append(P)
    imat = H_INSET if high else SILV
    for i in range(len(rows) - 1):
        for c in range(16):
            c2 = (c + 1) % 16
            q = [I_idx[i][c], I_idx[i + 1][c], I_idx[i + 1][c2], I_idx[i][c2]]
            uv = [(c * 5.0, rows[i] * S.K), (c * 5.0, rows[i + 1] * S.K), ((c + 1) * 5.0, rows[i + 1] * S.K),
                  ((c + 1) * 5.0, rows[i] * S.K)]
            mb.f(q, uv, "band_in", imat)
    tmat = H_SILVER if high else SILV
    zipper(mb, O_idx[0], O_pts[0], I_idx[0], I_pts[0], "band_top", tmat)
    zipper(mb, O_idx[-1], O_pts[-1], I_idx[-1], I_pts[-1], "band_bot", tmat)
    return rows
