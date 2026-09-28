"""Snow Flower v4 blade: steel (all LODs + high), relief layout (kept revision-3 routing), relief
high-poly (revision-3 construction) and the LOD0 low-poly relief proxies."""
from __future__ import annotations

import math

import numpy as np

import sfv4_spec as S
from sfv4_mesh import MB, grid, fan_cap, tube, arclen, _norm

# --------------------------------------------------------------------------- steel

#: lateral stations used per LOD (indices into S.SECTION)
_SECTION_LOD = {
    "high": None,
    0: [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    1: [0, 1, 4, 5, 7, 9, 10, 12, 13],
    2: [0, 1, 4, 9, 12, 13],
}


def _z_stations(level):
    if level == "high":
        zs = list(np.arange(S.Z_BLADE_ROOT, 680, 4.0)) + list(np.arange(680, 1000, 2.0)) + list(np.arange(1000, 1039.5, 0.8))
    elif level == 0:
        zs = [S.Z_BLADE_ROOT, 100, 104, 112, 124, 140] + list(np.arange(170, 680, 34.0)) + \
             list(np.arange(680, 960, 14.0)) + list(np.arange(960, 1030, 7.0)) + [1030, 1034, 1037.5]
    elif level == 1:
        zs = [S.Z_BLADE_ROOT, 104, 124] + list(np.arange(160, 680, 65.0)) + list(np.arange(680, 1000, 28.0)) + [1000, 1020, 1033]
    else:
        zs = [S.Z_BLADE_ROOT, 124, 400, 680, 820, 920, 980, 1020, 1034]
    # every LOD must have rings ON the island seams, or a face straddling a seam samples the padding
    zs = list(zs) + [b for _, b in BLADE_SEGMENTS[:-1]]
    zs = sorted(set(round(float(z), 3) for z in zs if z < S.Z_TIP - 0.5))
    return np.array(zs)


def _section_s(level):
    ss = np.array([p[0] for p in S.SECTION])
    if level == "high":
        return np.unique(np.concatenate([ss, np.linspace(0, 1, 60)]))
    return ss[_SECTION_LOD[level]]


BLADE_SEGMENTS = [(S.Z_BLADE_ROOT, 420.0), (420.0, 740.0), (740.0, S.Z_TIP)]


def _seg_of(z):
    for i, (a, b) in enumerate(BLADE_SEGMENTS):
        if z < b:
            return i
    return len(BLADE_SEGMENTS) - 1


def blade_steel(mb: MB, level, mat=0):
    """Closed steel blade: front face (s 0..1, y<0), edge strip, back face, spine strip; a single
    tip vertex. Islands blade_F<k> / blade_B<k> in 3 lengthwise segments; UV u = lateral mm from the
    spine line (spine strip at negative u on the front island), v = z mm."""
    zs = _z_stations(level)
    ss = _section_s(level)
    island = "HIGH" if level == "high" else None
    rows_f, rows_b = [], []
    for z in zs:
        T = float(S.thickness(z))
        rows_f.append([S.blade_point(z, s, -1) for s in ss])
        rows_b.append([S.blade_point(z, s, +1) for s in ss])
    rows_f = np.array(rows_f)
    rows_b = np.array(rows_b)
    nz, ns = rows_f.shape[:2]
    idx_f = np.array(mb.vs(rows_f.reshape(-1, 3))).reshape(nz, ns)
    idx_b = np.array(mb.vs(rows_b.reshape(-1, 3))).reshape(nz, ns)
    W = S.width(zs)
    Tz = S.thickness(zs)

    def uvf(r, c):   # front face: u = s*w, v = z
        return (float(ss[c] * W[r]), float(zs[r]))

    def uvb(r, c):   # back face mirrored so it is not a reflection in texture space
        return (float(-ss[c] * W[r]), float(zs[r]))

    for r in range(nz - 1):
        k = _seg_of(0.5 * (zs[r] + zs[r + 1]))
        isf = island or f"blade_F{k}"
        isb = island or f"blade_B{k}"
        for c in range(ns - 1):
            mb.f([idx_f[r, c], idx_f[r + 1, c], idx_f[r + 1, c + 1], idx_f[r, c + 1]],
                 [uvf(r, c), uvf(r + 1, c), uvf(r + 1, c + 1), uvf(r, c + 1)], isf, mat)
            mb.f([idx_b[r, c], idx_b[r, c + 1], idx_b[r + 1, c + 1], idx_b[r + 1, c]],
                 [uvb(r, c), uvb(r, c + 1), uvb(r + 1, c + 1), uvb(r + 1, c)], isb, mat)
        # spine strip (front island, u < 0) and edge strip (front island, u > w)
        sp = [(-(2 * 0.40 * Tz[r]), zs[r]), (-(2 * 0.40 * Tz[r + 1]), zs[r + 1]), (0.0, zs[r + 1]), (0.0, zs[r])]
        mb.f([idx_b[r, 0], idx_b[r + 1, 0], idx_f[r + 1, 0], idx_f[r, 0]], sp, isf, mat)
        e0, e1 = W[r], W[r + 1]
        eg = [(e0, zs[r]), (e1, zs[r + 1]), (e1 + 0.04 * Tz[r + 1] + 0.05, zs[r + 1]), (e0 + 0.04 * Tz[r] + 0.05, zs[r])]
        mb.f([idx_f[r, ns - 1], idx_f[r + 1, ns - 1], idx_b[r + 1, ns - 1], idx_b[r, ns - 1]], eg, isf, mat)
    # root cap (hidden inside the guard) -> small separate island
    from sfv4_mesh import poly_fill
    ring = list(idx_f[0]) + list(idx_b[0][::-1])
    pts = np.vstack([rows_f[0], rows_b[0][::-1]])
    isr = island or "blade_root"
    poly_fill(mb, ring, None, [(float(p[0]), float(p[1])) for p in pts], isr, mat)
    # tip: single vertex on the spine line
    tip = (float(S.spine_x(S.Z_TIP)), 0.0, float(S.Z_TIP))
    ti = mb.v(tip)
    r = nz - 1
    k = _seg_of(zs[r])
    isf = island or f"blade_F{k}"
    isb = island or f"blade_B{k}"
    tuv_f = (0.0, float(S.Z_TIP))
    for c in range(ns - 1):
        mb.f([idx_f[r, c], ti, idx_f[r, c + 1]], [uvf(r, c), tuv_f, uvf(r, c + 1)], isf, mat)
        mb.f([idx_b[r, c + 1], ti, idx_b[r, c]], [uvb(r, c + 1), tuv_f, uvb(r, c)], isb, mat)
    mb.f([idx_b[r, 0], ti, idx_f[r, 0]], [(-(2 * 0.40 * Tz[r]), zs[r]), (0.0, float(S.Z_TIP) + 0.5), (0.0, zs[r])], isf, mat)
    mb.f([idx_f[r, ns - 1], ti, idx_b[r, ns - 1]], [(W[r], zs[r]), (0.0, float(S.Z_TIP)), (W[r] + 0.1, zs[r])], isf, mat)
    return idx_f, idx_b


# --------------------------------------------------------------------------- relief layout

#: kept from revision 3 (blade_revision.py): trunk knots (t along the relief run, u across the width)
R3_KNOTS = [(0, -.11), (.016, -.02), (.034, .20), (.049, .17), (.062, -.03),
            (.078, -.17), (.092, -.14), (.101, -.22), (.118, -.18), (.138, .04),
            (.154, .15), (.174, .12), (.198, -.11), (.218, -.19), (.235, -.07),
            (.251, -.02), (.270, .13), (.285, .20), (.310, .13), (.333, .06),
            (.363, -.13), (.393, -.15), (.417, -.04), (.439, .09), (.462, .14),
            (.490, .12), (.521, -.05), (.552, -.16), (.582, -.13), (.606, .06),
            (.622, .13), (.641, .10), (.665, -.07), (.693, -.17), (.730, -.15),
            (.762, -.07), (.795, .12), (.819, .15), (.845, .02), (.874, -.08), (.930, .10)]
#: revision-3 clusters, radii x1.12 (audit change 7: larger blossoms) ...
R3_CLUSTERS = [
    ((.008, .17, 6.4, .15), [(.015, .03, 3.2, 1.1)]),
    ((.074, -.15, 6.7, .87), [(.064, -.27, 3.2, .2), (.086, -.08, 2.7, 2.1)]),
    ((.115, .19, 6.3, 1.5), []),
    ((.149, -.18, 7.0, 2.4), [(.150, -.02, 4.1, 1.0), (.158, -.21, 3.5, .4)]),
    ((.182, .12, 5.2, .3), [(.179, .28, 3.0, 1.8)]),
    ((.267, .14, 6.8, 2.0), [(.256, .25, 3.8, .7), (.276, .24, 4.2, 2.8)]),
    ((.294, -.13, 5.7, 1.1), []),
    ((.616, -.12, 6.3, .4), [(.615, .06, 4.2, 1.5)]),
    ((.650, .15, 5.9, 2.7), [(.643, .25, 3.1, .1), (.659, .04, 3.3, 1.9)]),
]
#: ... plus v4 additions in the upper 40 % (the sheet's dense zone: rows 380-600 carry ~8 blossoms)
V4_EXTRA_CLUSTERS = [
    ((.040, -.21, 6.0, 1.9), [(.047, -.30, 2.8, .5)]),
    ((.210, .18, 6.2, 2.2), [(.221, .27, 3.0, 1.2)]),
    ((.232, -.17, 5.8, .6), []),
    ((.338, .15, 6.1, 1.3), [(.349, .22, 3.0, 2.4)]),
    ((.372, -.11, 5.4, 2.5), []),
]
BLOSSOM_SCALE = 1.12
R3_BUD_T = (.040, .103, .126, .212, .285, .351, .449, .533, .604, .687, .789, .863)
RELIEF_Z0 = S.Z_PENDANT_TIP - 4.0
RELIEF_SPAN = 900.0
CH_MID = 0.5 * (S.CHANNEL_S[0] + S.CHANNEL_S[1])
CH_HALF = 0.5 * (S.CHANNEL_S[1] - S.CHANNEL_S[0])


def relief_z(t):
    return RELIEF_Z0 + RELIEF_SPAN * t


def floor_point(z, s, side, lift=0.0):
    """Point on the channel floor (s inside the channel) lifted ``lift`` mm along the face normal."""
    x = float(S.spine_x(z) - s * S.width(z))
    T = float(S.thickness(z))
    return np.array([x, side * (S.section_half(s, T) + lift), z])


def _u_to_s(t, u, side):
    u = u * 1.5
    if side == +1:
        u = -u * .92 + .023 * math.sin(t * 27)
    return float(np.clip(CH_MID - u * (CH_HALF / 0.36), S.CHANNEL_S[0] + 0.035, S.CHANNEL_S[1] - 0.035))


def relief_layout(side):
    """Positions of the trunk, twigs, blossoms and bud sprigs for one face (side -1 front, +1 back)."""
    def pt(t, u, lift=0.0):
        z = relief_z(t)
        return floor_point(z, _u_to_s(t, u, side), side, lift)

    trunk = [pt(t, u) for t, u in R3_KNOTS]
    radii = []
    for t, u in R3_KNOTS:
        swell = sum(.32 * math.exp(-((t - c) / .009) ** 2) for c in (.092, .198, .285, .417, .622, .795))
        radii.append((2.3 * (1 - t) ** .45 + .30) * (1 + .11 * math.sin(t * 63) + swell))
    z0 = S.Z_BLADE_SEAT + 4
    trunk.insert(0, floor_point(z0, _u_to_s(0, -.11, side), side))
    radii.insert(0, 2.6)
    # dense sampling of the trunk centre line (for twig anchoring and the ribbon)
    from sfv4_mesh import catmull
    samples = catmull(trunk, 12)

    def main_at(t):
        z = relief_z(t)
        j = int(np.clip(np.searchsorted(samples[:, 2], z), 1, len(samples) - 1))
        a, b = samples[j - 1], samples[j]
        w = (z - a[2]) / max(1e-6, b[2] - a[2])
        return a + (b - a) * np.clip(w, 0, 1)

    blossoms, twigs, stalks = [], [], []
    clusters = R3_CLUSTERS + V4_EXTRA_CLUSTERS
    for i, (main, sats) in enumerate(clusters):
        t, u, r, ph = main
        r *= BLOSSOM_SCALE
        base_t = max(0, t - (.011, .021, .015, .028)[i % 4])
        base = main_at(base_t)
        target = pt(t, u, 0.45)
        if abs(target[0] - main_at(t)[0]) < r + 2.0:
            target = pt(t, u, max(.45, 2.4 * (1 - t * .65)))
        mid = base + (target - base) * .52
        mid[0] += (-1 if i % 2 else 1) * 1.1
        mid[2] -= 1.5 if i % 3 else 3.0
        shoulder = base + (mid - base) * .28
        twigs.append(([base, shoulder, mid, target], [1.25, 1.10, 0.66, 0.32]))
        nrm = _norm([.045 * math.sin(i * 2.1), side, .055 * math.cos(i * 1.7)])
        blossoms.append((target, r, nrm, ph + side * .15))
        for j, (t2, u2, r2, ph2) in enumerate(sats):
            r2 *= BLOSSOM_SCALE
            tp = pt(t2, u2, .44 + j * .08)
            if abs(tp[0] - main_at(t2)[0]) < r2 + 2.0:
                tp = pt(t2, u2, max(.44, 2.4 * (1 - t2 * .65)))
            start = target + (mid - target) * .52
            turn = start + (tp - start) * .55 + np.array([.6 * (-1 if j % 2 else 1), 0, -1.2])
            stalks.append(([start, turn, tp], [.56, .42, .24]))
            n2 = _norm([.075 * math.sin(i + j), side, .055 * math.cos(i - j)])
            blossoms.append((tp, r2, n2, ph2))
    forks = []
    for i, t in enumerate(R3_BUD_T):
        p = main_at(t)
        z = relief_z(t)
        s_here = (S.spine_x(z) - p[0]) / S.width(z)
        u_here = (CH_MID - s_here) / (CH_HALF / 0.36) / 1.5
        if side == 1:
            u_here = -(u_here - .023 * math.sin(t * 27) / 1.5) / .92
        sign = 1 if i % 2 else -1
        q = pt(t + (.009 if i % 3 else .014), max(-.31, min(.31, u_here + sign * .14)), .12)
        bend = p + (q - p) * .60 + np.array([sign * .7, 0, -1.9])
        budr = .80 if t < .7 else .50
        forks.append(([p, bend, q], [.76 * (1 - t * .6), .44, .18], budr))
    return {"trunk": trunk, "radii": radii, "samples": samples, "blossoms": blossoms,
            "twigs": twigs, "stalks": stalks, "forks": forks}


# --------------------------------------------------------------------------- relief high

def relief_high(sink, side):
    import sfv4_rev3 as R3
    from mathutils import Vector
    L = relief_layout(side)
    nrm = (0, side, 0)
    R3.relief_branch(sink, [Vector(p) for p in L["trunk"]], L["radii"], nrm, steps=24)
    for pts, rad in L["twigs"]:
        R3.relief_branch(sink, [Vector(p) for p in pts], rad, nrm)
    for pts, rad in L["stalks"]:
        R3.relief_branch(sink, [Vector(p) for p in pts], rad, nrm, woody=False)
    for c, r, n, ph in L["blossoms"]:
        R3.flower(sink, Vector(c), r, Vector(n), ph)
    for pts, rad, budr in L["forks"]:
        R3.relief_branch(sink, [Vector(p) for p in pts], rad, nrm, woody=False)
        q, bend = Vector(pts[2]), Vector(pts[1])
        d = (q - bend).normalized()
        lat = Vector((d.z, 0, -d.x)).normalized()
        R3.ellipsoid(sink, q + d * budr * .4, lat * budr, Vector((0, budr * .62, 0)), d * budr * 1.45, R3.SILVER, 10, 5)
    return L


# --------------------------------------------------------------------------- relief low proxies

def flower_disc(mb: MB, center, radius, normal, phase, island, mat=0, n_out=30, up_hint=(0, 0, 1),
                height=0.16, sink=0.15):
    """Low-poly blossom proxy: a five-lobed domed disc (height field over the flower plane).
    Local UV = flower-plane coordinates in mm (planar, consistent across LODs)."""
    C = np.asarray(center, float)
    N = _norm(normal)
    U = np.asarray(up_hint, float)
    U = _norm(U - N * np.dot(U, N))
    V = np.cross(N, U)
    th = np.linspace(0, 2 * math.pi, n_out, endpoint=False)
    # five lobes: radius from 0.62r (between petals) to 1.0r (petal tip)
    lobe = np.abs(np.cos(2.5 * (th - phase)))
    rho = radius * (0.60 + 0.40 * lobe ** 0.55)
    out = []
    uv = []
    for k in (1.0, 0.55):
        for a, rr in zip(th, rho):
            h = (-sink if k == 1.0 else radius * height * 0.8)
            p = C + (U * math.cos(a) + V * math.sin(a)) * rr * k + N * h
            out.append(p)
            uv.append((rr * k * math.cos(a), rr * k * math.sin(a)))
    out = np.array(out).reshape(2, n_out, 3)
    uvs = np.array(uv).reshape(2, n_out, 2)
    idx = np.array(mb.vs(out.reshape(-1, 3))).reshape(2, n_out)
    for i in range(n_out):
        j = (i + 1) % n_out
        mb.f([idx[0, i], idx[0, j], idx[1, j], idx[1, i]],
             [tuple(uvs[0, i]), tuple(uvs[0, j]), tuple(uvs[1, j]), tuple(uvs[1, i])], island, mat)
    fan_cap(mb, list(idx[1]), C + N * radius * height, island, mat,
            uv_ring=[tuple(x) for x in uvs[1]], uv_center=(0.0, 0.0))
    # hidden underside closes the shell, so the normal recalculation can never flip the disc inward
    fan_cap(mb, list(idx[0]), C - N * (sink + 0.3), island + "_under", mat,
            uv_ring=[tuple(x) for x in uvs[0]], uv_center=(0.0, 0.0), flip=True)


def relief_low(mb: MB, side, level, mat=0):
    """Blossom proxies only (LOD0 all blossoms, LOD1 the large ones, LOD2 none). The trunk, twigs and
    buds (<= 2.3 mm proud) live in the blade's own normal/AO/colour bake (cage 2.6 mm): a proxy tube
    whose shape differs from the woody high branch baked noisy seams."""
    if level == 2 or level == "high":
        return
    L = relief_layout(side)
    tag = "F" if side < 0 else "B"
    for i, (c, r, nn, ph) in enumerate(L["blossoms"]):
        if level == 1 and r < 5.0:
            continue
        flower_disc(mb, c, r, nn, ph, f"relief_{tag}_bl{i}", mat, n_out=25 if level == 0 else 15, sink=0.6)
