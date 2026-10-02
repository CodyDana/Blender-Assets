"""Pilot 2 rock weathering fields and scan relief (STONE_BUILDING_STUDY.md 3.7, 3.8, 4.11). numpy (+ mathutils for
ray casts / KD trees). Per-vertex fields on the dense source, written as point colours that the composite bake
material (Scripts/dojo/rocks/rocks_material2.py) reads:

  Mk  R moss, G lichen zone, B wet, A stain (signed: 0.5 neutral, >0.5 tan iron staining, <0.5 grime)
  Mk2 R cavity (crevices, joints, cracks), G olive (algae, low in the wet zone), B arris (convex, bleached)

Rules (pilot 1's failures and the owner's sheet):
- WET is soft and irregular and rises unevenly with the form: a water level warped by two noise octaves (+-20 % of
  the height), lifted in hollows and joints (water wicks and lingers there) and on down-facing faces, lowered on
  up-facing crowns; a wide soft fade (no line) plus splash patches above it. Strongest at the base; the olive algae
  tint lives in the lowest part.
- MOSS lives on the dry, up-facing tops and ledges, preferring flat or concave spots (curvature), broken by 3 noise
  scales; never on overhangs, never in the wet.
- LICHEN zone = exposed dry faces outside the moss, clustered; the rosettes themselves are drawn per pixel by the
  material (lobed Voronoi), so the mask here is only where they may grow.
- STAIN: tan iron patches (the sheet's tan as staining only), streaks running down steep faces below ledges and
  cracks, dark grime mottles at 5-30 cm.
- SCAN RELIEF: the regraded scan's height map (tiger_rock for cliffs, rock_surface for river rocks) sampled
  triplanar in object space at its tile size and applied along the normal (real geometry, baked into the unique
  normal), masked down on the rounded arrises so the rounding survives.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Sequence

import numpy as np

import stone_sdf as sd

ROOT = Path(__file__).resolve().parents[2]
TEXW = ROOT / "WorkFiles" / "dojo" / "build" / "rocks" / "work2" / "tex"

SCAN = {"river": dict(tile_m=1.6, amp=0.012), "cliff": dict(tile_m=1.4, amp=0.018)}
_H = {}


def load_gray(path):
    """A greyscale image as float (H, W), row 0 = top: PIL when present (system Python), else bpy."""
    try:
        from PIL import Image
        return np.asarray(Image.open(path).convert("L"), np.float64) / 255.0
    except ImportError:
        import bpy
        im = bpy.data.images.load(str(path), check_existing=False)
        im.colorspace_settings.name = "Non-Color"
        w, h = im.size
        px = np.empty(w * h * 4, np.float32)
        im.pixels.foreach_get(px)
        bpy.data.images.remove(im)
        return px.reshape(h, w, 4)[::-1, :, 0].astype(np.float64)


def _height(kind):
    if kind not in _H:
        h = load_gray(TEXW / f"Macro_{kind}_H.png")
        h = (h - np.median(h)) / max(np.percentile(h, 95) - np.percentile(h, 5), 1e-6)   # ~ -0.5 .. 0.5
        _H[kind] = h
    return _H[kind]


def _bilinear(img, u, v):
    H, W = img.shape
    x = (u % 1.0) * W - 0.5
    y = (1.0 - (v % 1.0)) * H - 0.5          # image row 0 = top (v = 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    x0 %= W
    y0 %= H
    x1 = (x0 + 1) % W
    y1 = (y0 + 1) % H
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) + img[y1, x0] * (1 - fx) * fy +
            img[y1, x1] * fx * fy)


def triplanar(V, N, img, tile_m, sharp=4.0):
    """Blender BOX-projection convention (Cycles): X faces sample (y, z), Y faces (x, z), Z faces (y, x)."""
    P = V / tile_m
    w = np.abs(N) ** sharp
    w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
    hx = _bilinear(img, P[:, 1], P[:, 2])
    hy = _bilinear(img, P[:, 0], P[:, 2])
    hz = _bilinear(img, P[:, 1], P[:, 0])
    return w[:, 0] * hx + w[:, 1] * hy + w[:, 2] * hz


def scan_displace(V, N, kind, amp=None, mask=None):
    s = SCAN[kind]
    h = triplanar(V, N, _height(kind), s["tile_m"])
    a = s["amp"] if amp is None else amp
    if mask is not None:
        h = h * mask
    return V + N * (h * a)[:, None]


def ledge_field(V, N, F, reach=0.6, sub=4):
    """1 where an up-facing vertex has rock rising above it within ``reach`` (a ledge under a taller block). Ray
    casts on every ``sub``-th up-facing vertex, spread to the rest by nearest neighbour."""
    from mathutils import Vector
    bvh = sd.bvh_of(V, F)
    up = Vector((0.0, 0.0, 1.0))
    idx = np.nonzero(N[:, 2] > 0.45)[0]
    pick = idx[::sub]
    val = np.zeros(len(pick))
    for k, i in enumerate(pick):
        hit = bvh.ray_cast(Vector(V[i] + N[i] * 0.012), up, reach)
        if hit[0] is not None:
            val[k] = 1.0
    out = np.zeros(len(V))
    if len(pick):
        near, _ = sd.kd_nearest(V[pick], V[idx])
        out[idx] = val[near]
    return out


def masks(V, F, N, H, kind, params: Dict, seed: int, crack_paths: Sequence[np.ndarray] = (), H_fine=None):
    """Returns (Mk (n, 4), Mk2 (n, 3), fields). ``H_fine``: mean curvature with no smoothing (the scan relief's pits
    and the chips; pilot 2 fix 1 drives the fine cavity darkening and the ochre staining from it)."""
    nz = N[:, 2]
    z = V[:, 2]
    top = float(z.max())
    E = sd.edges_of(F)
    arris = sd.smoothstep(H, params.get("arris_lo", 5.0), params.get("arris_hi", 22.0))
    cleft = sd.smoothstep(-H, params.get("cleft_lo", 3.0), params.get("cleft_hi", 18.0))
    crack_d = np.full(len(V), 9.0)
    for P in crack_paths:
        P = np.asarray(P, float)
        for A, B in zip(P[:-1], P[1:]):
            d, _ = sd.point_segment_dist(V, A, B)
            crack_d = np.minimum(crack_d, d)
    crack = sd.smoothstep(0.04 - crack_d, 0.0, 0.03)
    n1 = sd.fbm(V, [(0.6, 1.1), (0.4, 2.7)], seed + 1)                      # ~ -0.6 .. 0.6
    n2 = sd.fbm(V, [(0.6, 4.5), (0.4, 11.0)], seed + 2)
    brk = 0.5 + 0.5 * sd.fbm(V, [(0.55, 2.6), (0.30, 7.0), (0.15, 19.0)], seed + 3)
    # ---------------- wet (B) + olive
    wp = params.get("wet")
    if wp:
        lvl = wp["h"] * top
        lvl = lvl + (0.55 * n1 + 0.25 * n2) * wp.get("warp", 0.20) * top / 0.6
        lvl = lvl + (0.10 * cleft + 0.10 * crack) * top                       # wicks up hollows and joints
        lvl = lvl + 0.08 * top * sd.smoothstep(-nz, 0.0, 0.6) - 0.06 * top * sd.smoothstep(nz, 0.5, 0.95)
        soft = wp.get("soft", 0.22) * top
        wet = 1.0 - sd.smoothstep(z, lvl - 0.35 * soft, lvl + soft)
        # splash and seep patches above the level (lower than 75 % of the height)
        sp = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 3.2), (0.4, 8.0)], seed + 5), 0.62, 0.80)
        wet = np.maximum(wet, wp.get("splash", 0.55) * sp * (1.0 - sd.smoothstep(z, 0.45 * top, 0.78 * top)))
        olive = sd.smoothstep(lvl * 0.62 - z, -0.08 * top, 0.12 * top) * wet
        olive *= 0.55 + 0.45 * sd.smoothstep(brk, 0.35, 0.65)
        # pilot 2 fix 1: a thin, broken algae / silt line at the (warped) waterline itself
        wl = np.exp(-((z - (lvl - 0.25 * soft)) / max(0.18 * soft, 1e-3)) ** 2)
        olive = np.maximum(olive, wp.get("waterline", 0.0) * wl * sd.smoothstep(brk, 0.30, 0.55))
    else:
        damp = params.get("damp_h", 0.35)
        wet = 0.6 * (1.0 - sd.smoothstep(z, damp * 0.4, damp + 0.15 * n1)) * (0.6 + 0.4 * brk)
        olive = 0.5 * wet
    wet = np.clip(wet, 0, 1)
    dry = 1.0 - sd.smoothstep(wet, 0.25, 0.6)
    # ---------------- moss (R)
    mp = params.get("moss", {})
    up = sd.smoothstep(nz, mp.get("nz_lo", 0.40), mp.get("nz_hi", 0.80))
    flatc = 1.0 - sd.smoothstep(H, mp.get("curv_lo", 1.0), mp.get("curv_hi", 6.0))   # flat / concave spots
    zone = sd.smoothstep(z, mp.get("z_lo", 0.5) * top, mp.get("z_hi", 0.7) * top) if mp.get("z_lo") is not None \
        else np.ones(len(V))
    led = np.zeros(len(V))
    if mp.get("ledges"):
        led = sd.smooth_field(ledge_field(V, N, F), E, 3)
        zone = np.maximum(zone, sd.smoothstep(led, 0.2, 0.5))
    b1 = sd.smoothstep(brk, mp.get("brk_lo", 0.45), mp.get("brk_hi", 0.58))
    b2 = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 13.0), (0.4, 31.0)], seed + 7), 0.30, 0.50)
    if mp.get("ridge"):
        # pilot 2 fix 1 (judge, checked on the sheet's row 2): moss follows the crest line in a band with satellites,
        # not slabs over each lobe: distance in plan to the crest (per 5 cm x-slice, the y of the highest point)
        sig = mp["ridge"]
        xb = np.round(V[:, 0] / 0.05).astype(np.int64)
        ridge_y = np.zeros(len(V))
        order = np.lexsort((-z, xb))
        xs_sorted = xb[order]
        first = np.r_[True, xs_sorted[1:] != xs_sorted[:-1]]
        top_idx = order[first]
        ymap = dict(zip(xb[top_idx].tolist(), V[top_idx, 1].tolist()))
        ridge_y = np.array([ymap[k] for k in xb])
        rb = np.exp(-((V[:, 1] - ridge_y) / sig) ** 2 * 0.5)
        sat = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 6.0), (0.4, 15.0)], seed + 19), 0.70, 0.78)
        zone = zone * np.clip(rb + 0.8 * sat * sd.smoothstep(nz, 0.55, 0.85), 0, 1)
    moss = up * (0.55 + 0.45 * flatc) * zone * b1 * b2
    crev = np.maximum(crack, cleft) * sd.smoothstep(nz, -0.2, 0.25) * \
        sd.smoothstep(0.5 + 0.5 * n2, 0.45, 0.62) * mp.get("crevice", 0.6)
    moss = np.maximum(moss, crev) * mp.get("amount", 1.0)
    moss *= sd.smoothstep(nz, -0.10, 0.10) * dry * sd.smoothstep(z, 0.04, 0.15)
    moss = np.clip(sd.smooth_field(moss, E, 2), 0, 1)
    moss = sd.smoothstep(moss, 0.18, 0.55)
    # ---------------- lichen zone (G)
    lp = params.get("lichen", {})
    cluster = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.7, 1.6), (0.3, 4.4)], seed + 9), lp.get("c_lo", 0.40),
                            lp.get("c_hi", 0.58))
    exposed = sd.smoothstep(nz, lp.get("nz_lo", -0.35), lp.get("nz_hi", 0.10)) * (1.0 - cleft) *         sd.smoothstep(z, 0.10 * top, 0.35 * top)
    lichen = np.clip(cluster * exposed * (1.0 - moss) * dry * lp.get("amount", 1.0), 0, 1)
    # ---------------- stain (A)
    ochre = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 1.4), (0.3, 3.8), (0.1, 10.0)], seed + 11),
                          params.get("ochre_lo", 0.55), params.get("ochre_lo", 0.55) + 0.22)
    Vs = V * np.array([1.0, 1.0, 0.16])
    streak = sd.smoothstep(0.5 + 0.5 * sd.fbm(Vs, [(0.7, 8.0), (0.3, 20.0)], seed + 13), 0.58, 0.76)
    streak *= sd.smoothstep(-nz, -0.6, 0.0)
    if mp.get("ledges"):
        streak *= 0.5 + 0.5 * sd.smoothstep(led, 0.1, 0.4)
    mott = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.4, 4.0), (0.35, 10.0), (0.25, 26.0)], seed + 15),
                         params.get("mott_lo", 0.50), params.get("mott_hi", 0.70))
    grime = np.clip(np.maximum(mott * params.get("grime", 0.8), streak * params.get("streak", 0.6)) +
                    0.4 * cleft + 0.4 * crack, 0, 1)
    pits = np.zeros(len(V))
    if H_fine is not None:
        q1, q2 = np.percentile(-H_fine, (82, 98))
        pits = sd.smoothstep(-H_fine, q1, q2)
    cavx = np.clip(np.maximum(np.maximum(cleft, crack), 0.85 * pits), 0, 1)
    if params.get("ochre_cavity"):
        # pilot 2 fix 1 (delta 5, checked: the sheet's ochre / rust sits in crevices and pits, the dark grey in the
        # hollows, light on convex wear): ochre from the cavity, gated by a broad noise so not every pit is rusty;
        # the world-space grime blotches are cut to a faint mottle
        gate = 0.35 + 0.65 * ochre
        tan = np.clip(params["ochre_cavity"] * gate * sd.smoothstep(np.maximum(cleft, pits), 0.15, 0.7) +
                      0.35 * ochre * params.get("ochre", 0.8), 0, 1) * (1.0 - 0.6 * wet)
        grime = np.clip(params.get("mott_keep", 0.35) * mott * params.get("grime", 0.8) +
                        streak * params.get("streak", 0.6) + 0.4 * cleft + 0.4 * crack, 0, 1)
    else:
        tan = ochre * params.get("ochre", 0.8) * (1.0 - 0.6 * grime) * (1.0 - 0.6 * wet)
    stain = np.clip(0.5 + 0.5 * tan - 0.5 * grime, 0, 1)
    cav = cavx if H_fine is not None else np.clip(np.maximum(cleft, crack), 0, 1)
    # pilot 2 fix 1: FRESH (unweathered, crystal grain shows at full contrast): worn convex arrises and, on the
    # cliff, fresh fracture patches on steep faces; the weathered rest keeps a damped grain (the grain at full
    # strength everywhere read as terrazzo at the studio distance)
    fp = params.get("fresh", {})
    patch = sd.smoothstep(0.5 + 0.5 * sd.fbm(V, [(0.6, 2.2), (0.4, 5.5)], seed + 23), fp.get("lo", 0.58),
                          fp.get("hi", 0.66)) * sd.smoothstep(1.0 - np.abs(nz), 0.3, 0.7) * fp.get("patch", 0.0)
    fresh = np.clip(np.maximum(fp.get("arris", 0.5) * arris, patch) * (1.0 - moss) * (1.0 - 0.7 * wet), 0, 1)
    Mk = np.stack([moss, lichen, wet, stain], 1)
    Mk2 = np.stack([cav, np.clip(olive, 0, 1), arris * (1.0 - wet), fresh], 1)
    fields = {"fresh": fresh, "moss_top": moss * up, "arris": arris, "cleft": cleft, "crack": crack, "ledge": led, "moss": moss}
    return Mk, Mk2, fields


def shares(Mk, V, F):
    _, a = sd.face_normals_areas(V, F)
    above = V[F].mean(1)[:, 2] > 0.0
    w = a * above
    fm = Mk[F].mean(1)
    out = {k: round(float((fm[:, i] > 0.5) @ w / w.sum()), 4) for i, k in enumerate(("moss", "lichen_zone", "wet"))}
    out["tan_gt_0.65"] = round(float((fm[:, 3] > 0.65) @ w / w.sum()), 4)
    out["grime_lt_0.35"] = round(float((fm[:, 3] < 0.35) @ w / w.sum()), 4)
    return out


def lichen_fields(V, N, zone, seed, per_m2=160.0, r=(0.012, 0.028), min_gap=0.85, F=None):
    """Rosette seeds scattered ON the surface (pilot 2: a 3-D Voronoi sliced by the surface gave few, truncated
    rosettes): seeds drawn from the vertices weighted by the lichen ``zone`` field, at least ``min_gap`` x (r_a +
    r_b) apart, then every vertex stores its offset to the nearest seed (Lc, metres) and that seed's parameters
    (Lp: R radius m, G lobe-count random, B phase random, A 1 = a rosette). The material draws the lobed rosette
    per pixel from the interpolated offset, so its outline is exact on the surface."""
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    rng = np.random.default_rng(seed)
    if F is not None:
        _, a = sd.face_normals_areas(V, F)
        va = np.zeros(len(V))
        for k in range(3):
            np.add.at(va, F[:, k], a / 3.0)
    else:
        va = np.full(len(V), 1.0 / len(V))
    w = va * np.clip(zone, 0, 1) ** 1.5
    area_zone = float((va * np.clip(zone, 0, 1)).sum())
    n_try = int(area_zone * per_m2 * 2.5) + 1
    Lc = np.zeros((len(V), 3))
    Lp = np.zeros((len(V), 4))
    if w.sum() <= 0 or n_try < 2:
        Lc[:] = 9.0
        return Lc, Lp, 0
    cand = rng.choice(len(V), n_try, p=w / w.sum())
    rad = np.exp(rng.uniform(math.log(r[0]), math.log(r[1]), n_try))
    keep = []
    cell = 2 * r[1]
    grid = {}
    for i, (vi, ri) in enumerate(zip(cand, rad)):
        p = V[vi]
        key = tuple((p // cell).astype(int))
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if np.linalg.norm(V[cand[j]] - p) < min_gap * (rad[j] + ri):
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            keep.append(i)
            grid.setdefault(key, []).append(i)
        if len(keep) >= area_zone * per_m2:
            break
    S = V[cand[keep]]
    kd = KDTree(len(S))
    for i, p in enumerate(S):
        kd.insert(Vector(p), i)
    kd.balance()
    who = np.empty(len(V), np.int64)
    for j, p in enumerate(V):
        who[j] = kd.find(p)[1]
    Lc = V - S[who]
    params = np.stack([rad[keep], rng.uniform(size=len(keep)), rng.uniform(size=len(keep)),
                       np.ones(len(keep))], 1)
    Lp = params[who]
    return Lc, Lp, len(keep)
