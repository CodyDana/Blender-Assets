"""Snow Flower sheath high-poly relief (bake source only): plate frames and dark insets on the fittings, ring beads,
the band's scroll frieze, the chape lancets, filigree thorns, lace drips, and the vine (stem, second stem, twigs,
buds, pods, leaves) with the kept revision-3 blossom construction.  Millimetres, sheath frame."""
from __future__ import annotations

import math

import numpy as np

import shv4_parts as P
import shv4_spec as S
import sfv4_rev3 as R3
from sfv4_mesh import MB, _norm, arclen, catmull, ellipsoid, resample, tube

RIM_R = 1.9           # plate frame half-width: the reference frames read ~5-6 px wide on the fittings (4x crops)
RIM_INSET = 2.0       # frame centre inside the outline
LAYER_H = 0.9         # stacking step between plate layers


def _signed_area(P2):
    x, y = P2[:, 0], P2[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _closed_resample(poly, step):
    Q = np.asarray(poly, float)
    L = arclen(np.vstack([Q, Q[:1]]))
    n = max(int(L[-1] / step), 8)
    return resample(Q, n, closed=True)


def _shrink(poly, d):
    """Inward offset by moving every point toward the centroid (the plates are star-shaped from their centroid)."""
    Q = np.asarray(poly, float)
    c = Q.mean(axis=0)
    r = np.linalg.norm(Q - c, axis=1)
    k = np.clip((r - d) / np.maximum(r, 1e-6), 0.05, 1.0)
    return c + (Q - c) * k[:, None]


def _project(xz, ring_fn, side, lift):
    pts, nrm = [], []
    for x, z in xz:
        p, n = P.surf_point(float(x), float(S.row_of(z)), side, lift, ring_fn=ring_fn)
        pts.append(p)
        nrm.append(n)
    return np.array(pts), np.array(nrm)


def rim_loop(sink, poly_xz, ring_fn, side, lift, radius=RIM_R, mat=R3.SILVER, step=1.2, inset=RIM_INSET):
    Q = _closed_resample(_shrink(poly_xz, inset), step)
    pts, nrm = _project(Q, ring_fn, side, lift)
    pts = np.vstack([pts, pts[:2]])
    nrm = np.vstack([nrm, nrm[:2]])
    tube(sink.mb(mat), pts, radius, sides=10, island="HIGH", mat=mat, cap=(None, None), squash=0.55, up=nrm)


def patch(sink, poly_xz, ring_fn, side, lift, mat, rings=10, step=1.0, thick=0.25):
    """A thin CLOSED slab over the plate field (dark inset or silver), following the fitting surface (closed so the
    normal recalculation can never turn it inside out)."""
    Q = _closed_resample(poly_xz, step)
    c = Q.mean(axis=0)
    mb = sink.mb(mat)
    n = len(Q)
    layers = []
    for dl in (0.0, -thick):
        idx = []
        for k in range(rings):
            f = 1.0 - k / rings
            ring = c + (Q - c) * f
            pts, _ = _project(ring, ring_fn, side, lift + dl)
            idx.append(mb.vs(pts))
        cp, _ = _project([c], ring_fn, side, lift + dl)
        layers.append((idx, mb.v(cp[0])))
    for li, (idx, ci) in enumerate(layers):
        for k in range(rings - 1):
            for i in range(n):
                j = (i + 1) % n
                q = [idx[k][i], idx[k][j], idx[k + 1][j], idx[k + 1][i]]
                mb.f(q if li == 0 else q[::-1], None, "HIGH", mat)
        for i in range(n):
            t = [idx[-1][i], idx[-1][(i + 1) % n], ci]
            mb.f(t if li == 0 else t[::-1], None, "HIGH", mat)
    top, bot = layers[0][0][0], layers[1][0][0]
    for i in range(n):
        j = (i + 1) % n
        mb.f([top[j], top[i], bot[i], bot[j]], None, "HIGH", mat)


def plates(sink, table, ring_fn, sides=(-1, 1), silver_patch=()):
    outlines = S.plate_outlines(table)
    for side in sides:
        for name, (poly, layer) in sorted(outlines.items(), key=lambda kv: kv[1][1]):
            base_lift = LAYER_H * layer
            fill = (R3.SILVER if any(name.startswith(s) for s in silver_patch) else P.H_INSET)
            if layer > 0 or fill == R3.SILVER:
                patch(sink, _shrink(poly, 0.3), ring_fn, side, base_lift + 0.08, fill)
            rim_loop(sink, poly, ring_fn, side, base_lift + 0.35)


def bead_loop(sink, ring, z, lift=0.25, radius=0.9, mat=R3.SILVER, n=140):
    """A bead running once around a fitting section (closed), lifted off its surface."""
    Q = resample(np.asarray(ring, float), n, closed=True)
    e = np.roll(Q, -1, axis=0) - np.roll(Q, 1, axis=0)
    nrm = np.stack([-e[:, 1], e[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    pts = np.c_[Q + nrm * lift, np.full(len(Q), z)]
    ups = np.c_[nrm, np.zeros(len(Q))]
    pts = np.vstack([pts, pts[:2]])
    ups = np.vstack([ups, ups[:2]])
    tube(sink.mb(mat), pts, radius, sides=8, island="HIGH", mat=mat, cap=(None, None), squash=0.7, up=ups)


def thorn(sink, pts, r0, mat=R3.SILVER, ups=None):
    pts = np.asarray(pts, float)
    tube(sink.mb(mat), pts, lambda t: r0 * (1.0 - 0.9 * t), sides=6, island="HIGH", mat=mat, cap=("flat", "point"),
         squash=0.7, up=ups)


# ====================================================================== fittings

def throat_high(sink):
    plates(sink, S.THROAT_PLATES, P.throat_ring)
    # collar top bead, collar lower edge, sleeve top/bottom beads (all round)
    for row, lift, rad in ((31.8, 0.2, 0.9), (40.0, 0.25, 0.8), (143.0, 0.2, 0.7), (166.0, 0.25, 0.8)):
        bead_loop(sink, P.throat_ring(row), float(S.zr(row)), lift, rad)
    # filigree: thorn sprigs in the petal gaps around the blossom, and a thorny lace fan above the drop plate
    (xpx, row), d = S.THROAT_BLOSSOM
    R = d * S.K / 2
    cz = float(S.zr(row))
    cx = float(S.xp(xpx))
    for k in range(5):
        a = -math.pi / 2 + (k + 0.5) * 2 * math.pi / 5            # between petals; petal 0 points to -Z (up)
        pts = []
        for t in np.linspace(0.0, 1.0, 7):
            rr = R * (0.78 + 0.42 * t)
            aa = a + 0.18 * math.sin(t * math.pi)
            x, z = cx + rr * math.cos(aa), cz + rr * math.sin(aa)
            p, n = P.surf_point(x, S.row_of(z), -1, 1.6 + LAYER_H * 2, ring_fn=P.throat_ring)
            pts.append(p)
        thorn(sink, pts, 0.75)
    for dx in (-9.0, 0.0, 9.0):
        pts = []
        for t in np.linspace(0.0, 1.0, 6):
            x = cx + (-dx * 0.2 + dx * t) * S.K
            z = float(S.zr(106 + 14 * t))
            p, n = P.surf_point(x, S.row_of(z), -1, 0.3 + LAYER_H * 2, ring_fn=P.throat_ring)
            pts.append(p)
        thorn(sink, pts, 0.8)


def band_high(sink):
    rows = (284.6, 291.6, 308.4, 316.4)
    for row in rows:
        bead_loop(sink, P.band_ring(row), float(S.zr(row)), 0.2, 0.75)
    # frieze: dark ground strip all round, with a running silver leaf scroll on it
    mb = sink.mb(P.H_INSET)
    frows = np.linspace(292.4, 307.6, 7)
    n = 160
    idx = []
    for row in frows:
        Q = resample(P.band_ring(row), n, closed=True)
        e = np.roll(Q, -1, axis=0) - np.roll(Q, 1, axis=0)
        nrm = np.stack([-e[:, 1], e[:, 0]], 1)
        nrm /= np.linalg.norm(nrm, axis=1)[:, None]
        idx.append(mb.vs(np.c_[Q + nrm * 0.12, np.full(n, float(S.zr(row)))]))
    for k in range(len(frows) - 1):
        for i in range(n):
            j = (i + 1) % n
            mb.f([idx[k][i], idx[k][j], idx[k + 1][j], idx[k + 1][i]], None, "HIGH", P.H_INSET)
    ring = P.band_ring(300.0)
    Q = resample(ring, 400, closed=True)
    s = arclen(np.vstack([Q, Q[:1]]))[:-1]
    e = np.roll(Q, -1, axis=0) - np.roll(Q, 1, axis=0)
    nrm = np.stack([-e[:, 1], e[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    period = s[-1] / 12
    zc = float(S.zr(300.0))
    amp = 3.2
    pts = np.c_[Q + nrm * 0.45, zc + amp * np.sin(2 * math.pi * s / period)]
    ups = np.c_[nrm, np.zeros(len(Q))]
    pts = np.vstack([pts, pts[:2]])
    ups = np.vstack([ups, ups[:2]])
    tube(sink.mb(R3.SILVER), pts, 0.5, sides=6, island="HIGH", mat=R3.SILVER, cap=(None, None), squash=0.7, up=ups)
    # curls and leaves at the crests
    for k in range(24):
        i = int((k + 0.25) * len(Q) / 24) % len(Q)
        sgn = 1 if (k % 2 == 0) else -1
        c3 = np.array([Q[i][0] + nrm[i][0] * 0.5, Q[i][1] + nrm[i][1] * 0.5, zc + sgn * amp * 0.95])
        t3 = np.array([-nrm[i][1], nrm[i][0], 0.0])
        n3 = np.array([nrm[i][0], nrm[i][1], 0.0])
        ellipsoid(sink.mb(R3.SILVER), c3 - np.array([0, 0, sgn * 1.4]), t3 * 1.9, np.array([0, 0, 1.0]) * 0.9, n3 * 0.45,
                  island="HIGH", mat=R3.SILVER, seg=10, rings=5)


def chape_high(sink):
    plates(sink, S.CHAPE_PLATES, P.chape_ring, silver_patch=("lancet_outer",))
    bead_loop(sink, P.chape_ring(1262.6), float(S.zr(1262.6)), 0.15, 0.6)


# ====================================================================== vine (body group)

def vine_high(sink):
    Pth, U, Rr = P.stem_geometry(1.6)
    tube(sink.mb(P.H_BRANCH), Pth, Rr, sides=12, island="HIGH", mat=P.H_BRANCH, cap=("flat", "flat"), squash=0.55,
         up=U)
    stem_xr = P.stem_path(2.0)
    core_or_chape = (lambda rr: P.core_ring(rr) if rr < 1262 else P.chape_ring(rr))

    def on_core(x, row, lift):
        return P.surf_point(float(x), float(row), -1, lift, ring_fn=core_or_chape)

    def nearest_stem(x, row):
        d = np.hypot((stem_xr[:, 0] - x), (stem_xr[:, 1] - row) * S.K)
        i = int(np.argmin(d))
        return stem_xr[i], float(d[i])

    def twig(x0, r0, x1, r1, rad, lift=-0.1, bend=0.35):
        a = np.array([x0, r0 * S.K])
        b = np.array([x1, r1 * S.K])
        m = 0.5 * (a + b) + bend * np.array([-(b - a)[1], (b - a)[0]])
        ctrl = [a, m, b]
        pts, ups = [], []
        for t in np.linspace(0, 1, 9):
            q = (1 - t) ** 2 * ctrl[0] + 2 * (1 - t) * t * ctrl[1] + t ** 2 * ctrl[2]
            p, n = on_core(q[0], q[1] / S.K, lift * rad)
            pts.append(p)
            ups.append(n)
        tube(sink.mb(P.H_BRANCH), np.array(pts), lambda t: rad * (1 - 0.35 * t), sides=8, island="HIGH",
             mat=P.H_BRANCH, cap=("flat", "flat"), squash=0.6, up=np.array(ups))

    tw = S.TWIG_PX * S.K / 2
    # ---- twigs to the blossoms that sit off the stem
    for b in S.vine_blossoms_px():
        x, row = float(S.xp(b["x"])), float(b["row"])
        (sx, srow), d = nearest_stem(x, row)
        if d > b["diameter_px"] * S.K * 0.35:
            twig(sx, srow, x, row, tw * 1.1, bend=0.25 if x > sx else -0.25)
    # ---- buds on short stalks
    for k, (row, dx) in enumerate(S.BUDS):
        (sx, srow), _ = nearest_stem(float(S.xp(505.5)), float(row))
        bx = sx - dx * S.K
        brow = row - 3.0
        twig(sx, srow, bx, brow, tw * 0.8, bend=0.3 if k % 2 else -0.3)
        rb = S.BUD_DIAM_PX * S.K / 2 * (0.85 + 0.3 * ((k * 37) % 7) / 6)
        p, n = on_core(bx, brow, rb * 0.55)
        ellipsoid(sink.mb(R3.INLAY), p, np.array([rb, 0, 0]), np.array([0, 0, rb * 1.08]), n * rb * 0.8,
                  island="HIGH", mat=R3.INLAY, seg=12, rings=6)
        # sepal cup at the stalk end
        ellipsoid(sink.mb(R3.SILVER), p + np.array([0, 0, rb * 0.75]), np.array([rb * 0.55, 0, 0]),
                  np.array([0, 0, rb * 0.4]), n * rb * 0.45, island="HIGH", mat=R3.SILVER, seg=8, rings=4)
    # ---- teardrop pods on thin curved stalks
    for (xpx, row), (wpx, hpx) in S.PODS:
        x = float(S.xp(xpx))
        (sx, srow), _ = nearest_stem(x, row - 18)
        twig(sx, srow, x, row - hpx * 0.5, tw * 0.7, bend=0.45)
        a, c = wpx * S.K / 2, hpx * S.K / 2
        p, n = on_core(x, row, a * 0.6)
        mb = sink.mb(R3.INLAY)
        # pointed at the bottom: an ellipsoid whose lower half is stretched
        rows_ = []
        for j in range(1, 10):
            ph = math.pi * j / 10
            zz = -math.cos(ph)
            stretch = 1.0 + 0.55 * max(0.0, zz)
            width = math.sin(ph) * (1.0 - 0.25 * max(0.0, zz))
            rows_.append([p + np.array([width * a * math.cos(t), 0, zz * c * stretch]) + n * (width * a * 0.7 * math.sin(t))
                          for t in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
        rows_ = np.array(rows_)
        from sfv4_mesh import grid, fan_cap
        idx = grid(mb, rows_, True, "HIGH", R3.INLAY)
        fan_cap(mb, list(idx[0]), p + np.array([0, 0, -c]), "HIGH", R3.INLAY, flip=True)
        fan_cap(mb, list(idx[-1]), p + np.array([0, 0, c * 1.55]), "HIGH", R3.INLAY)
    # ---- small pointed leaves
    for (xpx, row, sgn) in S.LEAVES:
        x = float(S.xp(xpx))
        (sx, srow), _ = nearest_stem(x, row)
        p0, n = on_core(sx, srow, 0.2)
        p1, _ = on_core(x, row, 0.2)
        ax = p1 - p0
        ax = ax / max(np.linalg.norm(ax), 1e-6)
        wv = _norm(np.cross(n, ax))
        L = 7.5                                     # small pointed leaf, ~11 x 4 px on the reference
        tube(sink.mb(R3.SILVER), np.array([p0 + ax * L * t + n * (0.3 + 0.4 * math.sin(math.pi * t)) for t in
                                           np.linspace(0, 1, 9)]),
             lambda t: 1.5 * math.sin(math.pi * min(max(t, 0.02), 0.98)) ** 0.8, sides=8, island="HIGH",
             mat=R3.SILVER, cap=("point", "point"), squash=0.3,
             up=np.array([n] * 9))
    # ---- the second, thinner stem: twines rows 930-1000, runs beside rows 1060-1200
    r2 = S.SECOND_STEM_PX * S.K / 2
    for (ra, rb_), mode in S.SECOND_STEM:
        rows = np.linspace(ra, rb_, 40)
        pts, ups = [], []
        for row in rows:
            i = int(np.argmin(np.abs(stem_xr[:, 1] - row)))
            sx = stem_xr[i, 0]
            if mode == "twine":
                off = 4.0 * S.K * math.sin(2 * math.pi * (row - ra) / 35.0)
                lift = 0.8 * r2 * (1 + math.cos(2 * math.pi * (row - ra) / 35.0))
            else:
                off = -6.0 * S.K + 1.2 * math.sin(row / 23.0)
                lift = -0.1 * r2
            p, n = on_core(sx + off, row, lift)
            pts.append(p)
            ups.append(n)
        tube(sink.mb(P.H_BRANCH), np.array(pts), r2, sides=8, island="HIGH", mat=P.H_BRANCH,
             cap=("point", "point"), squash=0.6, up=np.array(ups))
    # ---- lace drips under the throat sleeve (rows 150-178: short pointed silver sprigs beside the drop plate)
    for dx, ln in ((-30, 12), (-17, 9), (17, 10), (30, 12)):
        x = float(S.xp(505.5 + dx))
        pts, ups = [], []
        for t in np.linspace(0, 1, 7):
            p, n = on_core(x + 0.12 * dx * S.K * t, 167.5 + ln * t, 0.1)
            pts.append(p)
            ups.append(n)
        thorn(sink, pts, 1.4, mat=P.H_ANTIQUE, ups=np.array(ups))
        for s_ in (-1, 1):
            q = [on_core(x + s_ * 3.0 * S.K * t, 170.0 + 4 * t, 0.1)[0] for t in np.linspace(0, 1, 4)]
            thorn(sink, q, 0.6, mat=P.H_ANTIQUE)


def blossoms_high(sink, kinds=("vine", "fitting")):
    from mathutils import Vector
    for name, p, n, r, ph, up, kind in P.blossom_list():
        if kind not in kinds:
            continue
        R3.flower(sink, Vector(p), r, Vector(n), ph, large=r > 10.0, blade=True, up_hint=Vector(up))
