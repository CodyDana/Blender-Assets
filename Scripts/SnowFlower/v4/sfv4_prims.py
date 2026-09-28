"""Snow Flower v4 hard-surface primitives with per-face island UVs: lathe, superellipse loft,
polygon plate (rim + recess) and the cupped almond leaf."""
from __future__ import annotations

import math

import numpy as np

from sfv4_mesh import MB, _norm, arclen, fan_cap, poly_fill, resample


# ====================================================================== lathe

def lathe(mb: MB, profile, segs, bands, mat=0, center=(0.0, 0.0), prefix="lathe", angle0=0.0,
          close_first=True, close_last=True, level_island=True, band_mats=None):
    """Revolve ``profile`` [(r, z), ...] about the Z axis (through ``center``).
    ``bands``: list of (i0, i1, mode) profile index ranges -> island "<prefix>_<k>", mode 'planar'
    (XY projection) or 'cyl' (u = angle x mean radius, v = profile arclength). A profile point with
    r == 0 becomes a single pole vertex."""
    cx, cy = center
    prof = np.asarray(profile, float)
    ang = angle0 + np.linspace(0, 2 * math.pi, segs, endpoint=False)
    idx = []
    for r, z in prof:
        if r < 1e-6:
            idx.append([mb.v((cx, cy, z))] * segs)
        else:
            idx.append(mb.vs([(cx + r * math.cos(a), cy + r * math.sin(a), z) for a in ang]))
    idx = np.array(idx)
    s_prof = arclen(prof)
    band_of = {}
    for k, (i0, i1, mode) in enumerate(bands):
        for i in range(i0, i1):
            band_of[i] = (k, mode, i0, i1)
    for i in range(len(prof) - 1):
        k, mode, i0, i1 = band_of[i]
        isl = f"{prefix}_{k}"
        fmat = band_mats[k] if band_mats else mat
        rmean = max(float(prof[i0:i1 + 1, 0].mean()), 1e-3)
        for j in range(segs):
            j2 = (j + 1) % segs
            q = [idx[i, j], idx[i, j2], idx[i + 1, j2], idx[i + 1, j]]
            if mode == "planar":
                uv = [(prof[ii, 0] * math.cos(ang[jj]), prof[ii, 0] * math.sin(ang[jj]))
                      for ii, jj in ((i, j), (i, j2), (i + 1, j2), (i + 1, j))]
            else:
                a0 = j * 2 * math.pi / segs
                a1 = (j + 1) * 2 * math.pi / segs
                uv = [(a0 * rmean, s_prof[i]), (a1 * rmean, s_prof[i]), (a1 * rmean, s_prof[i + 1]), (a0 * rmean, s_prof[i + 1])]
            # drop the degenerate corner of a pole triangle
            if prof[i, 0] < 1e-6:
                q = [q[0], q[2], q[3]]
                uv = [uv[0], uv[2], uv[3]]
                if mode == "cyl":
                    uv[0] = ((a0 + a1) * 0.5 * rmean, s_prof[i])
            elif prof[i + 1, 0] < 1e-6:
                q = [q[0], q[1], q[2]]
                uv = [uv[0], uv[1], uv[2]]
                if mode == "cyl":
                    uv[2] = ((a0 + a1) * 0.5 * rmean, s_prof[i + 1])
            mb.f(q, uv, isl, fmat)
    return idx


# ====================================================================== superellipse loft

def superellipse_ring(a, b, n, segs, z, cx=0.0, cy=0.0, angle0=0.0):
    out = []
    for k in range(segs):
        t = angle0 + 2 * math.pi * k / segs
        c, s = math.cos(t), math.sin(t)
        x = a * np.sign(c) * abs(c) ** (2.0 / n)
        y = b * np.sign(s) * abs(s) ** (2.0 / n)
        out.append((cx + x, cy + y, z))
    return out


def loft_rings(mb: MB, rings, island, mat=0, cap0=True, cap1=True, cap_islands=None):
    """Closed loft through equal-length rings; island may be callable(row). Caps are fans with planar UVs."""
    from sfv4_mesh import grid
    R = np.asarray(rings, float)
    idx = grid(mb, R, True, island, mat)
    for end, do in ((0, cap0), (1, cap1)):
        if not do:
            continue
        ring = R[0] if end == 0 else R[-1]
        ids = idx[0] if end == 0 else idx[-1]
        ctr = ring.mean(axis=0)
        isl = (cap_islands or {}).get(end, (island(0) if callable(island) else island) + f"_cap{end}")
        fan_cap(mb, list(ids), ctr, isl, mat, uv_ring=[(p[0], p[1]) for p in ring], uv_center=(ctr[0], ctr[1]),
                flip=(end == 0))
    return idx


# ====================================================================== polygon plate

def offset_polygon(P, d, max_miter=2.4):
    """Inward offset of a CCW polygon by d (mitred, clamped)."""
    P = np.asarray(P, float)
    n = len(P)
    out = np.zeros_like(P)
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        e1 = _norm(b - a)
        e2 = _norm(c - b)
        n1 = np.array([-e1[1], e1[0]])
        n2 = np.array([-e2[1], e2[0]])
        m = n1 + n2
        if np.linalg.norm(m) < 1e-9:
            m = n1
        m = _norm(m)
        cosang = max(np.dot(m, n1), 1.0 / max_miter)
        out[i] = b + m * d / cosang
    return out


def offset_polygon_safe(P, d, max_miter=2.4, iters=40):
    """look-match R1: inward offset that never folds - where an offset edge would shrink below 25 % of its outer edge
    or reverse (a narrow spike such as the guard's wing hook), the two vertices' offsets are reduced locally."""
    P = np.asarray(P, float)
    n = len(P)
    di = np.full(n, float(d))
    for _ in range(iters):
        Q = np.array([offset_polygon(P, 1.0, max_miter)[i] for i in range(n)])  # unit offset directions
        Q = P + (Q - P) * di[:, None]
        bad = False
        for i in range(n):
            j = (i + 1) % n
            e0 = P[j] - P[i]
            e1 = Q[j] - Q[i]
            if np.dot(e0, e1) < 0.25 * np.dot(e0, e0):
                di[i] *= 0.85
                di[j] *= 0.85
                bad = True
        if not bad:
            break
    return Q


def plate(mb: MB, outline, O, U, V, N, th_front, th_back, prefix, mat=0, rim=2.6, recess=0.9, bevel=0.7,
          rim_rise=0.0, level=0, bend=None, mats=None, mapper=None):
    """Planar polygon plate (CCW ``outline`` in local mm). Front face at +th_front along N with a
    bevelled rim of width ``rim`` and a recessed field ``recess`` deep; flat back at -th_back.
    ``th_front``/``bend`` may be callables of the local 2D point (thickness taper, curl).
    Islands: <prefix>_front (planar), <prefix>_side (outline arclength x height), <prefix>_back."""
    P = np.asarray(outline, float)
    O, U, V, N = (np.asarray(x, float) for x in (O, U, V, N))
    tf = th_front if callable(th_front) else (lambda p, t=th_front: t)
    bd = bend if callable(bend) else (lambda p: 0.0)

    def to3(p2, h):
        if mapper is not None:        # look-match R1: plates laid on a curved surface (mapper(p2, h) -> 3D)
            return np.asarray(mapper(p2, h + bd(p2)), float)
        return O + U * p2[0] + V * p2[1] + N * (h + bd(p2))

    r1 = offset_polygon_safe(P, bevel)
    r2 = offset_polygon_safe(r1, max(rim - bevel, 0.05))      # sequential: each ring nests inside the previous one
    r3 = offset_polygon_safe(r2, 0.45)
    rings2 = [P, r1, r2, r3]
    heights = [lambda p: tf(p) - bevel * 0.8, lambda p: tf(p) + rim_rise, lambda p: tf(p) + rim_rise,
               lambda p: tf(p) - recess]
    idx = []
    for r2, hf in zip(rings2, heights):
        idx.append(mb.vs([to3(p, hf(p)) for p in r2]))
    back = mb.vs([to3(p, -th_back) for p in P])
    n = len(P)
    isf, iss, isb = f"{prefix}_front", f"{prefix}_side", f"{prefix}_back"
    M = mats or {}
    for k in range(len(rings2) - 1):
        mk = M.get("rim", mat) if k < 2 else M.get("field", mat)
        for i in range(n):
            j = (i + 1) % n
            q = [idx[k][i], idx[k][j], idx[k + 1][j], idx[k + 1][i]]
            uv = [tuple(rings2[k][i]), tuple(rings2[k][j]), tuple(rings2[k + 1][j]), tuple(rings2[k + 1][i])]
            mb.f(q, uv, isf, mk)
    poly_fill(mb, idx[-1], None, [tuple(p) for p in rings2[-1]], isf, M.get("field", mat))
    # side wall
    s = arclen(P, closed=True)
    for i in range(n):
        j = (i + 1) % n
        hi = tf(P[i]) + th_back
        hj = tf(P[j]) + th_back
        q = [back[i], back[j], idx[0][j], idx[0][i]]
        uv = [(s[i], 0.0), (s[i + 1], 0.0), (s[i + 1], hj), (s[i], hi)]
        mb.f(q, uv, iss, M.get("side", mat))
    # back (mirrored u so the island is not a reflection)
    poly_fill(mb, back, None, [(-p[0], p[1]) for p in P], isb, M.get("back", mat))
    return idx, back


# ====================================================================== almond leaf

def leaf(mb: MB, base, tip, normal_hint, width, th, prefix, mat=0, na=12, nf=4, rim=0.20, recess=0.8,
         rim_rise=0.35, rib=0.5, cup=2.5, curl=3.0, widest=0.42, sink=None, mats=None, fold=0.0, rim_flat=False):
    """Cupped almond leaf plate from ``base`` to ``tip``. Local frame: A along the leaf, W across,
    N out of the front. Front: bevelled rim (fraction ``rim`` of the half-width), recessed field
    with a raised central rib. Cup lifts the edges along N, curl lifts the tip along N.
    Islands: <prefix>_front (planar a,f), <prefix>_side (two wall strips), <prefix>_back."""
    base = np.asarray(base, float)
    tip = np.asarray(tip, float)
    Lvec = tip - base
    L = float(np.linalg.norm(Lvec))
    A = Lvec / L
    Nn = np.asarray(normal_hint, float)
    Nn = _norm(Nn - A * np.dot(Nn, A))
    W = np.cross(Nn, A)
    # a-samples (interior), denser toward the tips
    a_s = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, na + 2))[1:-1]

    def hw(a):
        # almond: pointed at both ends, widest at ``widest``
        x = np.where(a < widest, a / widest * 0.5, 0.5 + (a - widest) / (1 - widest) * 0.5)
        return 0.5 * width * np.sin(math.pi * x) ** 0.85

    # front profile across f (fraction of half-width), symmetric: (f, height above mid-plane)
    ht = th * 0.5
    # the field is FOLDED along the leaf axis (a raised central crease, as on the sheet's guard leaves)
    fend = 1 - rim - 0.06
    fold_h = lambda f: fold * max(0.0, 1.0 - f / fend)
    prof = [(0.0, ht - recess + rib + fold), (0.07, ht - recess + rib * 0.35 + fold_h(0.07)),
            (0.14, ht - recess + fold_h(0.14))]
    fl = np.linspace(0.14, fend, max(nf - 2, 1) + 1)[1:]
    prof += [(float(f), ht - recess + fold_h(f)) for f in fl]
    if rim_flat:   # look-match R1 (sword guard): a wide FLAT-topped bevelled silver band, inner wall, rounded outer edge
        prof += [(1 - rim, ht + rim_rise * 0.55), (1 - rim * 0.86, ht + rim_rise), (1 - rim * 0.22, ht + rim_rise),
                 (1 - rim * 0.07, ht + rim_rise * 0.55), (1.0, ht - 0.25 * th)]
    else:
        prof += [(1 - rim, ht + rim_rise * 0.7), (1 - rim * 0.45, ht + rim_rise), (1.0, ht - 0.35 * th)]
    fvals = [p[0] for p in prof]
    top_f = [-f for f in fvals[::-1][:-1]] + fvals          # -1 .. +1
    top_h = [p[1] for p in prof[::-1][:-1]] + [p[1] for p in prof]

    def surf(a, f, h):
        w = hw(a)
        lift = cup * (abs(f) ** 2) * (w / (0.5 * width)) + curl * a ** 2
        return base + A * (a * L) + W * (f * w) + Nn * (h + lift)

    rows_top, rows_back = [], []
    for a in a_s:
        rows_top.append([surf(a, f, h) for f, h in zip(top_f, top_h)])
        rows_back.append([surf(a, f, -ht) for f in (1.0, 0.5, 0.0, -0.5, -1.0)])
    rows_top = np.array(rows_top)
    rows_back = np.array(rows_back)
    na_, nt = rows_top.shape[:2]
    it = np.array(mb.vs(rows_top.reshape(-1, 3))).reshape(na_, nt)
    ib = np.array(mb.vs(rows_back.reshape(-1, 3))).reshape(na_, 5)
    t0 = mb.v(base + Nn * (0.0 + 0.0))
    t1 = mb.v(tip + Nn * (curl * 1.0))
    isf, iss, isb = f"{prefix}_front", f"{prefix}_side", f"{prefix}_back"

    def uvt(i, c):
        return (float(a_s[i] * L), float(top_f[c] * hw(a_s[i])))

    M = mats or {}

    def colmat(c):
        fm = 0.5 * (abs(top_f[c]) + abs(top_f[c + 1]))
        if fm > 1 - rim - 0.01:
            return M.get("rim", mat)
        if fm < 0.1 and rib > 0:
            return M.get("rib", mat)
        return M.get("field", mat)

    for i in range(na_ - 1):
        for c in range(nt - 1):
            mb.f([it[i, c], it[i + 1, c], it[i + 1, c + 1], it[i, c + 1]],
                 [uvt(i, c), uvt(i + 1, c), uvt(i + 1, c + 1), uvt(i, c + 1)], isf, colmat(c))
    bf = (1.0, 0.5, 0.0, -0.5, -1.0)

    def uvb(i, c):
        return (float(a_s[i] * L), float(-bf[c] * hw(a_s[i])))

    for i in range(na_ - 1):
        for c in range(4):
            mb.f([ib[i, c], ib[i + 1, c], ib[i + 1, c + 1], ib[i, c + 1]],
                 [uvb(i, c), uvb(i + 1, c), uvb(i + 1, c + 1), uvb(i, c + 1)], isb, M.get("back", mat))
    # walls: +f edge (top col nt-1 -> back col 0) and -f edge (top col 0 -> back col 4)
    s_a = a_s * L
    for i in range(na_ - 1):
        for (ct, cb, off) in ((nt - 1, 0, 0.0), (0, 4, th + 1.5)):
            q = [it[i, ct], ib[i, cb], ib[i + 1, cb], it[i + 1, ct]]
            uv = [(s_a[i], off + th), (s_a[i], off), (s_a[i + 1], off), (s_a[i + 1], off + th)]
            if ct == 0:
                q = q[::-1]
                uv = uv[::-1]
            mb.f(q, uv, iss, M.get("side", mat))
    # tips
    for ti, i, aval in ((t0, 0, 0.0), (t1, na_ - 1, L)):
        for c in range(nt - 1):
            q = [ti, it[i, c + 1], it[i, c]] if i == 0 else [ti, it[i, c], it[i, c + 1]]
            uv = [(aval, 0.0), uvt(i, c + 1), uvt(i, c)] if i == 0 else [(aval, 0.0), uvt(i, c), uvt(i, c + 1)]
            mb.f(q, uv, isf, M.get("rim", mat))
        for c in range(4):
            q = [ti, ib[i, c], ib[i, c + 1]] if i == 0 else [ti, ib[i, c + 1], ib[i, c]]
            uv = [(aval, 0.0), uvb(i, c), uvb(i, c + 1)] if i == 0 else [(aval, 0.0), uvb(i, c + 1), uvb(i, c)]
            mb.f(q, uv, isb, M.get("back", mat))
        for (ct, cb, off) in ((nt - 1, 0, 0.0), (0, 4, th + 1.5)):
            q = [ti, it[i, ct], ib[i, cb]] if i == 0 else [ti, ib[i, cb], it[i, ct]]
            uv = [(aval, off + th * 0.5), (s_a[i], off + th), (s_a[i], off)] if i == 0 else \
                 [(aval, off + th * 0.5), (s_a[i], off), (s_a[i], off + th)]
            if ct == 0:
                q = q[::-1]
                uv = uv[::-1]
            mb.f(q, uv, iss, M.get("side", mat))
    return {"A": A, "W": W, "N": Nn, "L": L, "hw": hw, "surf": surf}


def plate2(mb: MB, outline, O, U, V, N, half_th, prefix, mat=0, rim=2.6, recess=0.9, bevel=0.7, rim_rise=0.0,
           mats=None, face_detail=True):
    """Closed two-sided polygon plate: both faces carry the bevelled rim and recessed field.
    ``half_th`` may be a callable of the local 2D point. Islands <prefix>_front / _back / _side."""
    P = np.asarray(outline, float)
    O, U, V, N = (np.asarray(x, float) for x in (O, U, V, N))
    ht = half_th if callable(half_th) else (lambda p, t=half_th: t)
    M = mats or {}
    if face_detail:
        rings2 = [P, offset_polygon(P, bevel), offset_polygon(P, rim), offset_polygon(P, rim + 0.45)]
        dh = [-bevel * 0.8, rim_rise, rim_rise, -recess]
    else:
        rings2 = [P, offset_polygon(P, bevel)]
        dh = [-bevel * 0.8, 0.0]
    n = len(P)
    faces_idx = {}
    for sgn, isl in ((1.0, f"{prefix}_front"), (-1.0, f"{prefix}_back")):
        idx = []
        for r2, d in zip(rings2, dh):
            idx.append(mb.vs([O + U * p[0] + V * p[1] + N * sgn * (ht(p) + d) for p in r2]))
        faces_idx[sgn] = idx
        mir = (lambda q: (q[0], q[1])) if sgn > 0 else (lambda q: (-q[0], q[1]))
        for k in range(len(rings2) - 1):
            mk = M.get("rim", mat) if k < 2 else M.get("field", mat)
            for i in range(n):
                j = (i + 1) % n
                q = [idx[k][i], idx[k][j], idx[k + 1][j], idx[k + 1][i]]
                uv = [mir(rings2[k][i]), mir(rings2[k][j]), mir(rings2[k + 1][j]), mir(rings2[k + 1][i])]
                if sgn < 0:
                    q = q[::-1]
                    uv = uv[::-1]
                mb.f(q, uv, isl, mk)
        poly_fill(mb, idx[-1], None, [mir(p) for p in rings2[-1]], isl,
                  M.get("field", mat) if face_detail else M.get("rim", mat), flip=(sgn < 0))
    s = arclen(P, closed=True)
    f0 = faces_idx[1.0][0]
    b0 = faces_idx[-1.0][0]
    for i in range(n):
        j = (i + 1) % n
        hi = 2 * ht(P[i]) - 1.6 * bevel
        hj = 2 * ht(P[j]) - 1.6 * bevel
        q = [b0[i], b0[j], f0[j], f0[i]]
        uv = [(s[i], 0.0), (s[i + 1], 0.0), (s[i + 1], hj), (s[i], hi)]
        mb.f(q, uv, f"{prefix}_side", M.get("side", mat))
