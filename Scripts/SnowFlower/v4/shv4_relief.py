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
    # final pass: the two sleeve beads (rows 143 / 166) are removed - the reviews read them as invented horizontal
    # silver lines across the throat's lower edge; the collar beads stay
    for row, lift, rad in ((31.8, 0.2, 0.9), (40.0, 0.25, 0.8)):
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
    # final pass: the full-width bead seam at the chape top (row 1262.6) is removed (not in the reference; the stem
    # showed a gap where it crossed it)


# ====================================================================== vine (body group)

def vine_high(sink):
    Pth, U, Rr = P.stem_geometry(1.6)
    tube(sink.mb(P.H_BRANCH), Pth, Rr, sides=14, island="HIGH", mat=P.H_BRANCH, cap=("flat", "flat"),
         squash=S.VINE_SQUASH, up=U)
    stem_xr = P.stem_path(2.0)
    core_or_chape = (lambda rr: P.core_ring(rr) if rr < S.CHAPE_SLEEVE_TOP else P.chape_ring(rr))

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
        # look-match: pearl teardrops pointing UP (toward the throat) on a thin stalk that curls from the stem below
        x = float(S.xp(xpx))
        (sx, srow), _ = nearest_stem(x, row + 20)
        twig(sx, srow, x + 0.8, row + hpx * 0.45, tw * 0.7, bend=0.6)
        a, c = wpx * S.K / 2, hpx * S.K / 2
        p, n = on_core(x, row, a * 0.75)
        mb = sink.mb(R3.INLAY)
        rows_ = []
        for j in range(1, 14):
            ph = math.pi * j / 14
            zz = -math.cos(ph)                      # -1 top (image up) .. +1 bottom
            stretch = 1.0 + 0.6 * max(0.0, -zz)     # the upper half is drawn out into the point
            width = math.sin(ph) * (1.0 - 0.3 * max(0.0, -zz))
            rows_.append([p + np.array([width * a * math.cos(t), 0, zz * c * stretch]) + n * (width * a * 0.8 * math.sin(t))
                          for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)])
        rows_ = np.array(rows_)
        from sfv4_mesh import grid, fan_cap
        idx = grid(mb, rows_, True, "HIGH", R3.INLAY)
        fan_cap(mb, list(idx[0]), p + np.array([0, 0, -c * 1.6]), "HIGH", R3.INLAY, flip=True)
        fan_cap(mb, list(idx[-1]), p + np.array([0, 0, c]), "HIGH", R3.INLAY)
        # a small silver calyx at the stalk end
        ellipsoid(sink.mb(R3.SILVER), p + np.array([0, 0, c * 0.9]), np.array([a * 0.45, 0, 0]),
                  np.array([0, 0, c * 0.22]), n * a * 0.4, island="HIGH", mat=R3.SILVER, seg=10, rings=5)
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
    # ---- lace drips under the throat sleeve: REMOVED in the final pass (the reviews read them as a row of invented
    # dark-tipped spikes; the reference shows filigree leaves there, which is look work for the user to decide)
    for dx, ln in ():
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


# ====================================================================== LOOK-MATCH ROUND 1 (2026-09-27)

def throat_high_lm(sink, lace=True):
    """Crown extras (bake only): two fine beads on the mouth ring and the filigree lace fringe on the lower sleeve."""
    import shv4_plates as PL
    for row, lift, rad in ((31.9, 0.15, 0.7), (41.2, 0.1, 0.55)):
        bead_loop(sink, P.crown_ring(row, "high"), float(S.zr(row)), lift, rad)
    r0, r1 = S.THROAT_LACE_ROWS
    for dx in (S.THROAT_LACE_DX if lace else ()):
        # overlapping scalloped filigree leaves (antique silver, a raised midrib, no dark inset): a lace band
        # a dense fringe of small overlapping filigree leaves (antique frame round a dark inset), pointing down
        # open filigree outlines (antique silver; the crown's dark body shows inside), overlapping: a lace fringe
        lf = PL.Leaf("lace", [(dx, r0), (dx * 1.01, r1)], [(0, 0), (0.2, 4.6), (0.55, 4.0), (0.85, 2.0), (1, 0)],
                     tier=0, env="crown", fill="open", F=0.85, T=0.6, pair=False, lift0=0.05, cup=0.1, lobes=3,
                     lobe_depth=0.2, hmat=P.H_ANTIQUE)
        for side in (-1, 1):
            PL.build_leaf(sink.mb(P.H_ANTIQUE), lf, side, "high", "HIGH", high=True)


def band_high_lm(sink):
    """The band frieze: a dark ground with a running silver laurel (leaves angled outward from the front centre)."""
    zc = float(S.zr(300.0))
    ring = P.band_ring(300.0)
    Q = resample(np.asarray(ring, float), 480, closed=True)
    e = np.roll(Q, -1, axis=0) - np.roll(Q, 1, axis=0)
    nrm = np.stack([-e[:, 1], e[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    for i in range(len(nrm)):
        if nrm[i] @ Q[i] < 0:
            nrm[i] = -nrm[i]
    s = arclen(np.vstack([Q, Q[:1]]))[:-1]
    i_front = int(np.argmin(Q[:, 1]))          # front centre (most negative y)
    i_back = int(np.argmax(Q[:, 1]))
    L = s[-1]
    # a thin central stem line all round
    pts = np.c_[Q + nrm * 0.25, np.full(len(Q), zc)]
    ups = np.c_[nrm, np.zeros(len(Q))]
    tube(sink.mb(R3.SILVER), np.vstack([pts, pts[:2]]), 0.32, sides=6, island="HIGH", mat=R3.SILVER, cap=(None, None),
         squash=0.7, up=np.vstack([ups, ups[:2]]))
    step = 4.4
    for centre in (i_front, i_back):
        for direction in (-1, 1):
            k = 1
            while k * step < L / 2 - 2.0:
                sd = (s[centre] + direction * k * step) % L
                i = int(np.argmin(np.abs(s - sd)))
                t3 = np.array([-nrm[i][1], nrm[i][0], 0.0]) * direction
                n3 = np.array([nrm[i][0], nrm[i][1], 0.0])
                base = np.array([Q[i][0], Q[i][1], zc]) + n3 * 0.35
                for sgn in (-1, 1):                     # upper and lower leaf of the pair, angled outward
                    ax = _norm(t3 * 0.75 + np.array([0, 0, sgn * 0.66]))
                    c = base + ax * 2.9
                    wv = _norm(np.cross(n3, ax))
                    ellipsoid(sink.mb(R3.SILVER), c, ax * 3.0, wv * 1.25, n3 * 0.55, island="HIGH", mat=R3.SILVER,
                              seg=12, rings=6)
                k += 1


def band_leaf_veins(sink):
    """Engraving on the band's filigree plates: a raised midrib and angled side veins (antique silver)."""
    import shv4_plates as PL
    for tag, lf in PL.expand(PL.leaves_from(S.BAND_LEAVES, "core")):
        R, T, Na = PL.spine_mm(lf, 60)
        env = PL.ENVS[lf.env]
        top = lf.lift + lf.T + 0.05
        pts, ups = [], []
        for (x, z) in R[3:-3]:
            n = env.normal(x, z, -1)
            pts.append(env.point(x, z, -1) + n * top)
            ups.append(n)
        tube(sink.mb(P.H_ANTIQUE), np.array(pts), 0.28, sides=6, island="HIGH", mat=P.H_ANTIQUE,
             cap=("point", "point"), squash=0.6, up=np.array(ups))
        wa, wb = PL.widths(lf, np.linspace(0, 1, 60))
        for k in range(8, 52, 7):
            for sgn, w in ((1, wa[k]), (-1, wb[k])):
                x0, z0 = R[k]
                vp, vu = [], []
                for t in np.linspace(0.0, 0.8, 5):
                    x, z = R[min(k + int(6 * t), 59)] + Na[k] * sgn * w * t
                    n = env.normal(x, z, -1)
                    vp.append(env.point(x, z, -1) + n * top)
                    vu.append(n)
                tube(sink.mb(P.H_ANTIQUE), np.array(vp), 0.18, sides=5, island="HIGH", mat=P.H_ANTIQUE,
                     cap=("flat", "point"), squash=0.6, up=np.array(vu))


def body_filigree_lm(sink):
    """The feathered filigree leaf on the right chamfer below the throat (rows ~170-238) and the thin forked twig
    with buds on the left (rows ~190-255): antique silver / branch relief on the lacquer, bake only."""
    import shv4_plates as PL
    lf = PL.Leaf("feather", [(40, 239), (37, 206), (43, 171)], [(0, 0), (0.12, 6.5), (0.5, 7.5), (0.85, 4), (1, 0)],
                 tier=0, env="core", fill="silver", F=0.9, T=0.55, pair=False, lift0=0.02, cup=0.25, lobes=9,
                 lobe_depth=0.45, hmat=P.H_ANTIQUE)
    PL.build_leaf(sink.mb(P.H_ANTIQUE), lf, -1, "high", "HIGH", high=True)
    # its engraved midrib
    R, T, Na = PL.spine_mm(lf, 50)
    env = PL.ENVS["core"]
    pts = np.array([env.point(x, z, -1) + env.normal(x, z, -1) * (lf.lift + lf.T + 0.05) for x, z in R[2:-2]])
    ups = np.array([env.normal(x, z, -1) for x, z in R[2:-2]])
    tube(sink.mb(P.H_ANTIQUE), pts, 0.26, sides=6, island="HIGH", mat=P.H_ANTIQUE, cap=("point", "point"),
         squash=0.6, up=ups)
    # the forked twig to the left carrying three buds
    stem_xr = P.stem_path(2.0)
    i = int(np.argmin(np.abs(stem_xr[:, 1] - 252.0)))
    sx, srow = stem_xr[i]
    ctrl = [(sx, srow), (float(S.xp(S.X_AXIS_PX - 14)), 228.0), (float(S.xp(S.X_AXIS_PX - 20)), 205.0),
            (float(S.xp(S.X_AXIS_PX - 16)), 188.0)]
    C = catmull(np.array([[x, r * S.K] for x, r in ctrl]), steps=8)
    pts, ups = [], []
    for x, zz in C:
        p, n = P.surf_point(float(x), float(zz / S.K), -1, 0.0, ring_fn=P.core_ring)
        pts.append(p)
        ups.append(n)
    rad = S.TWIG_PX * S.K / 2 * 1.15
    tube(sink.mb(P.H_BRANCH), np.array(pts), lambda t: rad * (1 - 0.45 * t), sides=8, island="HIGH", mat=P.H_BRANCH,
         cap=("flat", "flat"), squash=0.65, up=np.array(ups))
    for k, (dx, row) in enumerate(((-20, 186.0), (-8, 206.0), (-26, 214.0))):
        p, n = P.surf_point(float(S.xp(S.X_AXIS_PX + dx)), row, -1, 1.6, ring_fn=P.core_ring)
        rb = 2.2 - 0.3 * k
        ellipsoid(sink.mb(R3.INLAY), p, np.array([rb, 0, 0]), np.array([0, 0, rb * 1.1]), n * rb * 0.85,
                  island="HIGH", mat=R3.INLAY, seg=14, rings=7)
