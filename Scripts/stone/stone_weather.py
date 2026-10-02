"""Weathering masks for rocks (STONE_BUILDING_STUDY.md 3.8, 4.11): per-vertex fields on the dense source, baked to
the shipped mesh's unique mask map T_<P>_<Rock>_M:  R moss, G lichen, B wet (or foot dirt), A stain (tan iron /
grime weathering). Geometry-driven, then broken by noise; never a whole-face tint. numpy (+ mathutils KDTree).

    moss   = up-facing x (top zone | ledge | crevice) x breakup, never on overhangs, never below the wet line
    lichen = exposed (up/side-facing, convex or flat) x round rosette patches 1.5-9 cm, clustered, not under moss
    wet    = below a wavy water line (river), or a damp foot band (cliff)
    stain  = low-frequency ochre patches + streaks running down from ledges and cracks + crevice grime
"""
from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np

import stone_sdf as sd


def _kd_points(P):
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    kd = KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    return kd


def ledge_field(V, N, F, step=0.06, reach=0.5):
    """1 where an up-facing vertex has rock rising above it within ``reach`` (a ledge or a step under a block),
    0 on the free top. Tested by casting a ray upward from just above the surface."""
    from mathutils import Vector
    bvh = sd.bvh_of(V, F)
    up = Vector((0.0, 0.0, 1.0))
    out = np.zeros(len(V))
    idx = np.nonzero(N[:, 2] > 0.55)[0]
    for i in idx:
        o = Vector(V[i] + N[i] * 0.01)
        hit = bvh.ray_cast(o, up, reach)
        if hit[0] is not None:
            out[i] = 1.0
    return out


def masks(V, F, N, H, params: Dict, seed: int, crack_paths: Sequence[np.ndarray] = ()):
    """Returns (n, 4) float masks and a dict of the fields used (moss_top drives the cushion shell)."""
    rng = np.random.default_rng(seed)
    nz = N[:, 2]
    z = V[:, 2]
    top = float(z.max())
    E = sd.edges_of(F)
    arris = sd.smoothstep(H, 6.0, 25.0)
    cleft = sd.smoothstep(-H, 4.0, 22.0)
    brk = 0.5 + 0.5 * sd.fbm(V, [(0.6, 3.0), (0.3, 8.0), (0.1, 22.0)], seed + 11)
    brk2 = 0.5 + 0.5 * sd.fbm(V, [(0.6, 6.0), (0.4, 17.0)], seed + 12)
    crack_d = np.full(len(V), 9.0)
    for P in crack_paths:
        P = np.asarray(P, float)
        for A, B in zip(P[:-1], P[1:]):
            d, _ = sd.point_segment_dist(V, A, B)
            crack_d = np.minimum(crack_d, d)
    crack = sd.smoothstep(0.05 - crack_d, 0.0, 0.035)
    # ---- wet / damp (B)
    wet = np.zeros(len(V))
    if params.get("wet"):
        h = params["wet"]["h"] * top
        soft = params["wet"]["soft"] * top
        # an irregular line (the sheet's wet band wanders and fades upward; round 1's line read as paint)
        wave = 0.9 * soft * sd.fbm(V, [(0.55, 1.8), (0.3, 5.0), (0.15, 14.0)], seed + 31)
        wave2 = 0.8 * soft * sd.fbm(V, [(0.6, 3.0), (0.4, 9.0)], seed + 32)
        wet = sd.smoothstep(h + wave - z, -0.10 * soft, 0.45 * soft)
        damp = 0.45 * sd.smoothstep(h + 1.4 * soft + wave2 - z, 0.0, 1.4 * soft)
        wet = np.clip(np.maximum(wet, damp), 0, 1)
    else:
        wet = 0.55 * sd.smoothstep(0.30 - z, 0.0, 0.30) * (0.6 + 0.4 * brk)       # damp foot / soil splash
    dry = 1.0 - sd.smoothstep(wet, 0.4, 0.8)
    # ---- moss (R)
    mp = params.get("moss", {})
    up = sd.smoothstep(nz, 0.30, 0.65)
    moss_top = np.zeros(len(V))
    if mp.get("top", 0) > 0:
        zone = sd.smoothstep(z, mp["top"] * top, (mp["top"] + 0.18) * top)
        brk3 = 0.5 + 0.5 * sd.fbm(V, [(0.6, 11.0), (0.4, 28.0)], seed + 13)
        moss_top = up * zone * sd.smoothstep(brk, mp.get("brk_lo", 0.42), mp.get("brk_hi", 0.58)) * \
            sd.smoothstep(brk3, 0.30, 0.48)
    moss_ledge = np.zeros(len(V))
    if mp.get("ledges"):
        led = ledge_field(V, N, F)
        led = sd.smooth_field(led, E, 4)
        free_top = up * sd.smoothstep(z, top - 0.35, top - 0.10)                # the block tops at the crown
        moss_ledge = np.maximum(sd.smoothstep(led, 0.2, 0.5), free_top) * up * sd.smoothstep(brk, 0.28, 0.44)
    crev = np.maximum(crack, 0.8 * cleft) * sd.smoothstep(nz, -0.35, 0.10) * \
        sd.smoothstep(brk2, mp.get("crev_lo", 0.40), mp.get("crev_lo", 0.40) + 0.16)
    crev *= mp.get("crevice", 0.8)
    moss = np.clip(np.maximum(np.maximum(moss_top, moss_ledge), crev) * mp.get("amount", 1.0), 0, 1)
    moss *= sd.smoothstep(nz, -0.20, 0.05)                                      # never on overhangs
    moss *= dry * sd.smoothstep(z, 0.03, 0.12)
    moss = sd.smooth_field(moss, E, 2)
    # ---- lichen (G): rosette patches (Voronoi-like seeds), clustered on exposed faces
    area = float(sd.face_normals_areas(V, F)[1].sum())
    lp = params.get("lichen", {})
    ns = int(area * lp.get("per_m2", 160))
    idx = rng.choice(len(V), ns, replace=False)
    kd = _kd_points(V[idx])
    rad = np.exp(rng.uniform(math.log(lp.get("r_lo", 0.008)), math.log(lp.get("r_hi", 0.045)), ns))
    who = np.empty(len(V), np.int64)
    d = np.empty(len(V))
    for j, p in enumerate(V):
        _, k, dd = kd.find(p)
        who[j] = k
        d[j] = dd
    lobes = 0.5 + 0.5 * sd.vnoise3(V * 55.0, seed + 23)                       # lobed rosette rims
    patch = sd.smoothstep(rad[who] * (0.7 + 0.6 * lobes) - d, 0.0, 0.0025)
    cluster = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.7, 1.8), (0.3, 5.0)], seed + 25), lp.get("c_lo", 0.45),
                            lp.get("c_hi", 0.62))
    exposed = sd.smoothstep(nz, -0.35, 0.05) * (1.0 - cleft) * sd.smoothstep(z, 0.15, 0.45)
    # pale specks 0.5-2 cm (the sheet's white flecks at viewing distance), exposed dry faces only
    speck = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, params.get('pale_f', 55.0)), (0.4, 2 * params.get('pale_f', 55.0))], seed + 27), params.get("pale_lo", 0.70),
                          params.get("pale_lo", 0.70) + 0.08) * params.get("pale", 0.7)
    lichen = np.clip(np.maximum(patch * cluster, speck) * exposed * (1.0 - moss) * dry, 0, 1)
    # ---- stain (A): ochre patches + streaks under ledges / cracks + crevice grime
    ochre = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 1.2), (0.3, 3.5), (0.1, 9.0)], seed + 41), 0.52, 0.78)
    Vs = V * np.array([1.0, 1.0, 0.18])                                         # noise stretched along z: streaks
    streak = sd.smoothstep(0.5 + 0.5 * sd.fbm(Vs, [(0.7, 9.0), (0.3, 22.0)], seed + 43), 0.58, 0.78)
    streak *= sd.smoothstep(-nz, -0.6, 0.0)                                     # on steep and vertical faces
    # grime: the sheet's dark grey weathering mottles (5-30 cm) + streaks + crevices; tan: the ochre patches.
    # A is a signed tone: 0.5 neutral, toward 1 tan stain, toward 0 grime (one channel carries both)
    mott = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.4, 5.0), (0.35, 12.0), (0.25, 30.0)], seed + 45),
                         params.get("mott_lo", 0.54), params.get("mott_hi", 0.74))
    # dark flecks 1-2.5 cm (the sheet's black flecks and lichen spots at viewing distance)
    fleck = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, params.get('fleck_f', 45.0)), (0.4, 2 * params.get('fleck_f', 45.0))], seed + 47), params.get("fleck_lo", 0.66),
                          params.get("fleck_lo", 0.66) + 0.08) * params.get("fleck", 0.8)
    grime = np.clip(np.maximum(np.maximum(mott * params.get("grime", 0.8), streak * params.get("streak", 0.6)),
                               fleck) + 0.6 * cleft + 0.5 * crack, 0, 1)
    tan = ochre * params.get("ochre", 0.85) * (1.0 - 0.7 * grime)
    stain = np.clip(0.5 + 0.5 * tan - 0.5 * grime, 0, 1)
    M = np.stack([moss, lichen, wet, stain], 1)
    return M, {"moss_top": np.maximum(moss_top, moss_ledge) * (moss > 0.3), "arris": arris, "cleft": cleft,
               "crack": crack}


def shares(M, V, F):
    """Area shares of each mask over the above-grade surface (vertex masks, face-averaged)."""
    _, a = sd.face_normals_areas(V, F)
    above = V[F].mean(1)[:, 2] > 0.0
    w = a * above
    fm = M[F].mean(1)
    out = {k: round(float((fm[:, i] > 0.5) @ w / w.sum()), 4) for i, k in enumerate(("moss", "lichen", "wet"))}
    out["tan_gt_0.65"] = round(float((fm[:, 3] > 0.65) @ w / w.sum()), 4)
    out["grime_lt_0.35"] = round(float((fm[:, 3] < 0.35) @ w / w.sum()), 4)
    return out
