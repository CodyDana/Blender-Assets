"""Senbon needles: island layout + the numpy painter (BC / roughness / metallic / height -> tangent normal).

Every texel is mapped back to the needle analytically (the UV function is invertible: U -> profile station, V -> the
azimuth), so the finish is painted in real millimetres on the real surface: the blackened coat with scratches and
specks, the bright ground points with grind lines running along the axis, the worn fade of the coat at the grind line,
the polished finger-wear band, and the heavy needle's cotton thread wrap (right-hand single-start helix, pitch 0.6 mm,
end bindings wound square and tighter).  AO (ORM.R) is NOT painted here: it is the Cycles bake passed in.

Arrays are bottom-up (row 0 = v 0, Blender's convention); the writer flips them to PNG order.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from . import senbon_spec as S
from . import senbon_geom as G

D2R = math.pi / 180.0


# =============================================================================================== layout
@dataclass
class Island:
    name: str
    kind: str              # "rev" (revolved strip) or "facet"
    tex: str               # "needle" | "heavy" | "wrap"
    Umin: float
    Umax: float
    Vmin: float
    Vmax: float
    u0: float = 0.0        # px of Umin
    vc: float = 0.0        # px of V = 0
    phi: float = 0.0       # facet normal azimuth (facets)


def island_extents(mbs) -> Dict[str, List[float]]:
    ext: Dict[str, List[float]] = {}
    for mb in mbs:
        _V, _T, _N, UV, _slot, _part, isl = mb.arrays()
        for name in set(isl):
            uv = UV[isl == name].reshape(-1, 2)
            e = ext.setdefault(name, [1e9, -1e9, 1e9, -1e9])
            e[0] = min(e[0], uv[:, 0].min()); e[1] = max(e[1], uv[:, 0].max())
            e[2] = min(e[2], uv[:, 1].min()); e[3] = max(e[3], uv[:, 1].max())
    return ext


def layout_needle(ext) -> Dict[str, Island]:
    t = S.NEEDLE_TEX
    e = ext["needle"]
    isl = Island("needle", "rev", "needle", *e)
    w = (e[1] - e[0]) * t.ppmm
    isl.u0 = 0.5 * (t.size[0] - w)                     # centred in U
    isl.vc = t.size[1] / 2.0
    _check_fit(t, [isl])
    return {"needle": isl}


def layout_heavy(ext) -> Dict[str, Island]:
    t = S.HEAVY_TEX
    out = {}
    butt = Island("heavy_butt", "rev", "heavy", *ext["heavy_butt"])
    body = Island("heavy_body", "rev", "heavy", *ext["heavy_body"])
    facets = [Island(f"heavy_facet_{int(p)}", "facet", "heavy", *ext[f"heavy_facet_{int(p)}"], phi=p)
              for p in S.H_FACET_PHI]
    wb = (butt.Umax - butt.Umin) * t.ppmm
    wbo = (body.Umax - body.Umin) * t.ppmm
    wf = max((f.Umax - f.Umin) for f in facets) * t.ppmm
    total = wb + wbo + wf + 2 * t.gap
    x = 0.5 * (t.size[0] - total)
    butt.u0, butt.vc = x, t.size[1] / 2.0
    x += wb + t.gap
    body.u0, body.vc = x, t.size[1] / 2.0
    x += wbo + t.gap
    hf = max((f.Vmax - f.Vmin) for f in facets) * t.ppmm
    for j, f in enumerate(facets):
        f.u0 = x
        f.vc = t.size[1] / 2.0 + (j - 1) * (hf + t.gap)
    out = {i.name: i for i in [butt, body] + facets}
    _check_fit(t, list(out.values()))
    return out


def layout_wrap(ext) -> Dict[str, Island]:
    t = S.WRAP_TEX
    w = Island("wrap", "rev", "wrap", *ext["wrap"])
    w.u0 = 0.5 * (t.size[0] - (w.Umax - w.Umin) * t.ppmm)
    # FINALISE: the island's lower edge on the middle row (v = 512 px of 1024), so on every mip down to 4 x 4 at least
    # one row of texels is mostly covered (the pack's derive step fits the mip compensation on covered texels)
    w.vc = t.size[1] / 2.0 - w.Vmin * t.ppmm + 1.0
    _check_fit(t, [w])
    return {"wrap": w}


def _check_fit(t, islands):
    for i in islands:
        u1 = i.u0 + (i.Umax - i.Umin) * t.ppmm
        v0 = i.vc + i.Vmin * t.ppmm
        v1 = i.vc + i.Vmax * t.ppmm
        if i.u0 < t.border - 1e-6 or u1 > t.size[0] - t.border + 1e-6 or v0 < t.border - 1e-6 or v1 > t.size[1] - t.border + 1e-6:
            raise ValueError(f"{i.name} does not fit {t.stem}: u {i.u0:.1f}..{u1:.1f}, v {v0:.1f}..{v1:.1f}")


def tex_of(name) -> S.TexDef:
    return {"needle": S.NEEDLE_TEX, "heavy": S.HEAVY_TEX, "wrap": S.WRAP_TEX}[name]


def to_uv(isl: Island, U, V):
    """Island mm -> 0..1 UV of its own texture (the wrap tile is offset by +1 in U by the caller)."""
    t = tex_of(isl.tex)
    u = (isl.u0 + (np.asarray(U) - isl.Umin) * t.ppmm) / t.size[0]
    v = (isl.vc + np.asarray(V) * t.ppmm) / t.size[1]
    return u, v


# =============================================================================================== noise
def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(x, y, seed=0):
    """Smooth value noise in [0, 1] (x, y in lattice units)."""
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(x0, y0, seed); b = _hash(x0 + 1, y0, seed)
    c = _hash(x0, y0 + 1, seed); d = _hash(x0 + 1, y0 + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(x, y, seed=0, octaves=4):
    v, a, f, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        v = v + a * vnoise(x * f, y * f, seed + 17 * o)
        tot += a
        a *= 0.5
        f *= 2.0
    return v / tot


def streaks(t, density, seed=0):
    """Fine lines along the needle axis: a 1-D function of the circumferential coordinate t (mm)."""
    return 0.6 * vnoise(t * density, np.zeros_like(t), seed) + 0.4 * vnoise(t * density * 3.1, np.zeros_like(t) + 7, seed + 3)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# =============================================================================================== texel geometry
def texel_grid(isl: Island):
    """Texel centres of the island's rectangle (+ 24 px apron for the margins) -> island mm coordinates."""
    t = tex_of(isl.tex)
    W, H = t.size
    pad = 24
    j0 = max(0, int(math.floor(isl.u0)) - pad)
    j1 = min(W, int(math.ceil(isl.u0 + (isl.Umax - isl.Umin) * t.ppmm)) + pad)
    i0 = max(0, int(math.floor(isl.vc + isl.Vmin * t.ppmm)) - pad)
    i1 = min(H, int(math.ceil(isl.vc + isl.Vmax * t.ppmm)) + pad)
    jj, ii = np.meshgrid(np.arange(j0, j1), np.arange(i0, i1))
    U = isl.Umin + (jj + 0.5 - isl.u0) / t.ppmm
    V = (ii + 0.5 - isl.vc) / t.ppmm
    e = 1.5 / t.ppmm
    core = (U >= isl.Umin - e) & (U <= isl.Umax + e) & (V >= isl.Vmin - e) & (V <= isl.Vmax + e)
    return (i0, i1, j0, j1, core), U, V


def raster_cover(shape, mbs_uv_tris):
    """Coverage mask (bottom-up) of UV triangles given in px (n, 3, 2)."""
    H, W = shape
    m = np.zeros((H, W), bool)
    for tri in mbs_uv_tris:
        x0, y0 = np.floor(tri.min(axis=0)).astype(int)
        x1, y1 = np.ceil(tri.max(axis=0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = tri
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        l3 = 1 - l1 - l2
        e = -1e-6
        inside = (l1 >= e) & (l2 >= e) & (l3 >= e)
        m[y0:y1 + 1, x0:x1 + 1] |= inside
    return m


def grow(values, known, iters=32):
    v = values.copy()
    k = known.copy()
    for _ in range(iters):
        if k.all():
            break
        acc = np.zeros_like(v)
        cnt = np.zeros(k.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            kk = np.roll(np.roll(k, dy, 0), dx, 1)
            vv = np.roll(np.roll(v, dy, 0), dx, 1)
            acc += vv * (kk[..., None] if v.ndim == 3 else kk)
            cnt += kk
        new = (~k) & (cnt > 0)
        v[new] = acc[new] / (cnt[new][:, None] if v.ndim == 3 else cnt[new])
        k = k | new
    return v, k


# =============================================================================================== look
@dataclass(frozen=True)
class Look:
    coat: Tuple[float, float, float] = S.COAT
    coat_rough: float = S.COAT_ROUGH
    ground: Tuple[float, float, float] = S.GROUND
    ground_rough: float = S.GROUND_ROUGH
    worn: Tuple[float, float, float] = (0.30, 0.302, 0.31)    # the fade's exposed steel: the ground value x 0.71
    mottle: float = 0.05                 # +- coat value, 6 mm noise
    scratch_per_mm2: float = 1 / 25.0    # fine light scratches on the coat
    scratch_lift: float = 0.55           # value lift on a scratch line (x coat), feathered over ~1 px
    speck_per_mm2: float = 1 / 20.0      # pack SPECK presence
    speck_darken: float = 0.5 * 0.35     # pack SPECK darken x BAR_SPECK_SCALE
    wear_lift: float = 0.25              # spec body_wear: at most +25 % of the coat
    grind_contrast: float = 0.10         # ground streak value modulation (+-)
    grind_density: float = 9.0           # streaks per mm around the circumference
    wrap_crest: float = 0.16             # thread crest lift
    wrap_groove: float = 0.45            # groove darkening
    wrap_relief_mm: float = 0.060        # thread relief height in the normal map (FINALISE: 0.10 -> 0.06, crest tilt p99 ~21 deg)
    grind_relief_mm: float = 0.0015      # grind-line relief (near flat)
    facet_rough: float = 0.27            # FINALISE: the heavy's planar facets (spec 0.22 + the spread; see _ground_facet)
    facet_relief_mm: float = 0.004       # FINALISE: facet grind relief (a few degrees of normal spread)
    scratch_relief_mm: float = 0.002


LOOK = Look()


def _segments_mask(U, V, n, seed, len_mm=(1.0, 6.0), width_px=0.9, ppmm=14.0, ang_spread=0.6,
                   bounds=None):
    """Random short straight scratches in island mm space -> soft mask (0..1)."""
    rng = np.random.default_rng(seed)
    m = np.zeros_like(U)
    if n <= 0:
        return m
    u_lo, u_hi, v_lo, v_hi = bounds if bounds else (U.min(), U.max(), V.min(), V.max())
    hw = width_px / ppmm
    for _ in range(n):
        cu, cv = rng.uniform(u_lo, u_hi), rng.uniform(v_lo, v_hi)
        L = rng.uniform(*len_mm)
        a = rng.normal(0.0, ang_spread) + (0 if rng.random() < 0.7 else rng.uniform(0, math.pi))
        du, dv = math.cos(a) * L / 2, math.sin(a) * L / 2
        sel = (np.abs(U - cu) <= abs(du) + 3 * hw) & (np.abs(V - cv) <= abs(dv) + 3 * hw)
        if not sel.any():
            continue
        pu, pv = U[sel] - (cu - du), V[sel] - (cv - dv)
        ex, ey = 2 * du, 2 * dv
        t = np.clip((pu * ex + pv * ey) / (ex * ex + ey * ey), 0, 1)
        d = np.hypot(pu - t * ex, pv - t * ey)
        fade = np.sin(np.pi * t) ** 0.5
        val = np.clip(1 - d / hw, 0, 1) * fade * rng.uniform(0.4, 1.0)
        m[sel] = np.maximum(m[sel], val)
    return m


def _specks(U, V, n, seed, r_mm=(0.06, 0.15), bounds=None):
    rng = np.random.default_rng(seed)
    m = np.zeros_like(U)
    u_lo, u_hi, v_lo, v_hi = bounds if bounds else (U.min(), U.max(), V.min(), V.max())
    for _ in range(n):
        cu, cv, r = rng.uniform(u_lo, u_hi), rng.uniform(v_lo, v_hi), rng.uniform(*r_mm)
        sel = (np.abs(U - cu) <= 2 * r) & (np.abs(V - cv) <= 2 * r)
        if sel.any():
            d = np.hypot(U[sel] - cu, V[sel] - cv)
            m[sel] = np.maximum(m[sel], np.clip(1.5 - d / r, 0, 1))
    return m


def _coat(U, V, area_mm2, seed, look, ppmm, bounds):
    """Blackened coat colour (linear RGB), roughness, height (mm)."""
    mott = fbm(U / 6.0, V / 6.0, seed, 3) - 0.5
    k = 1.0 + 2 * look.mottle * mott
    n_scr = int(round(area_mm2 * look.scratch_per_mm2))
    scr = _segments_mask(U, V, n_scr, seed + 1, ppmm=ppmm, bounds=bounds)
    n_spk = int(round(area_mm2 * look.speck_per_mm2))
    spk = _specks(U, V, n_spk, seed + 2, bounds=bounds)
    k = k * (1 + look.scratch_lift * scr) * (1 - look.speck_darken * spk)
    col = np.asarray(look.coat)[None, None, :] * k[..., None]
    rough = look.coat_rough + 0.02 * mott - 0.05 * scr + 0.04 * spk
    h = -look.scratch_relief_mm * scr
    return col, rough, h, {"scratches": n_scr, "specks": n_spk}


def _ground(U, arc, seed, look):
    """Bright ground steel: grind lines along the axis (a function of the circumferential arc only)."""
    st = streaks(arc, look.grind_density, seed)
    k = 1.0 + 2 * look.grind_contrast * (st - 0.5)
    col = np.asarray(look.ground)[None, None, :] * k[..., None]
    rough = look.ground_rough + 0.03 * (st - 0.5)
    h = look.grind_relief_mm * (st - 0.5)
    return col, rough, h


def _ground_facet(U, lat, seed, look):
    """FINALISE 1.1.0 (craft review): the heavy's three PLANAR facets.  Same base colour as every ground surface (the
    pack's 0.42); only the microsurface differs.  A planar near-mirror reflects one direction of the world, so the
    facets went darker than the body under some HDRIs: fine straight grind streaks (period ~0.25 mm, below the old
    0.5-0.7 mm waves, nothing above the 12 px/mm Nyquist), their contrast mostly in roughness (mean ~0.27, +-0.035)
    and a little relief (0.004 mm), so the reflection spreads by a few degrees.  The colour streaks are halved."""
    fine = 0.65 * vnoise(lat * 4.0, U / 3.0, seed) + 0.35 * vnoise(lat * 5.3 + 7.0, U / 2.1, seed + 3)
    coarse = vnoise(lat * 0.9, U / 6.0, seed + 5)
    st = 0.8 * fine + 0.2 * coarse
    k = 1.0 + 2 * (0.5 * look.grind_contrast) * (st - 0.5)
    col = np.asarray(look.ground)[None, None, :] * k[..., None]
    rough = look.facet_rough + 0.07 * (st - 0.5)
    h = look.facet_relief_mm * (fine - 0.5)
    return col, rough, h


def _fade(d_mm, theta_mm, seed):
    """Worn coat fade back from the grind line: 1 at the line, 0 past 1.5-2.5 mm, broken up (not a stripe)."""
    fw = S.FADE_MM[0] + (S.FADE_MM[1] - S.FADE_MM[0]) * vnoise(theta_mm / 1.3, np.zeros_like(theta_mm) + 3, seed)
    brk = fbm(d_mm / 0.35, theta_mm / 0.35, seed + 5, 3) - 0.5
    t = np.clip(1.0 - d_mm / fw + 0.55 * brk, 0, 1)
    return np.where(d_mm < 0, 1.0, t ** 1.6)


# =============================================================================================== needle
def paint_needle(isl: Island, look=LOOK, seed=20261003):
    t = S.NEEDLE_TEX
    canon = G.needle_canon()
    box, U, V = texel_grid(isl)
    s, r = canon.at(U)
    r = np.maximum(r, 1e-4)
    tp = 180.0 - (V / r) / D2R                       # theta' (deg)
    arc = (tp % 360.0) * D2R * np.maximum(r, 0.3)    # circumferential coordinate for the streaks
    area = S.NEEDLE_L * math.pi * S.NEEDLE_D_BELLY
    bounds = (isl.Umin, isl.Umax, isl.Vmin, isl.Vmax)
    ccol, crough, ch, cstat = _coat(U, V, area, seed, look, t.ppmm, bounds)
    gcol, grough, gh = _ground(U, (tp % 360.0) * D2R * 1.15, seed + 11, look)
    ax = np.abs(s)
    ground = ax >= S.NEEDLE_SH_X
    d = S.NEEDLE_SH_X - ax
    fade = np.where(ground, 1.0, _fade(np.maximum(d, 0), (tp % 360.0) * D2R * 1.2, seed + 21))
    # body wear: polished lines along the axis over |x| 0-25 (spec), lift <= +25 %
    env = 1.0 - smoothstep(20.0, 25.0, ax)
    wl = streaks((tp % 360.0) * D2R * r, 6.0, seed + 31)
    wear = np.clip((wl - 0.45) / 0.55, 0, 1) * env
    ccol = ccol * (1 + look.wear_lift * wear)[..., None]
    crough = crough - 0.05 * wear
    worn_col = np.asarray(look.worn)[None, None, :] * (0.9 + 0.2 * streaks(arc, 7.0, seed + 41))[..., None]
    col = np.where(ground[..., None], gcol, ccol * (1 - fade[..., None]) + worn_col * fade[..., None])
    rough = np.where(ground, grough, crough * (1 - fade) + (look.ground_rough + 0.05) * fade)
    h = np.where(ground, gh, ch)
    out = _assemble_many(t, [(box, col, rough, h, ground, isl.name, {})], metal=1.0)
    out["stats"] = {"coat": cstat, "ground_fraction_island": float(ground.mean()),
                    "wear_band_x_mm": [0, 25], "fade_mm": list(S.FADE_MM)}
    return out


# =============================================================================================== heavy steel
def paint_heavy_steel(islands: Dict[str, Island], look=LOOK, seed=20261013):
    t = S.HEAVY_TEX
    canon = G.heavy_canon()
    parts = []
    for name, isl in islands.items():
        box, U, V = texel_grid(isl)
        bounds = (isl.Umin, isl.Umax, isl.Vmin, isl.Vmax)
        if isl.kind == "rev":
            s, r = canon.at(U)
            r = np.maximum(r, 1e-4)
            tp = 180.0 - (V / r) / D2R
            th = (S.SEAM_DEG + tp) % 360.0
            area = (isl.Umax - isl.Umin) * (isl.Vmax - isl.Vmin)
            ccol, crough, ch, cstat = _coat(U, V, area, seed + len(parts) * 101, look, t.ppmm, bounds)
            if name == "heavy_body":
                # grind line on the lands: s_cut(theta) = 170 - 22 cos(theta - nearest facet)
                c = np.max(np.stack([np.cos((th - p) * D2R) for p in S.H_FACET_PHI]), axis=0)
                s_cut = S.HEAVY_L - S.H_PT_L * c
                d = np.where(s > S.H_PT0 - 3.0, s_cut - s, 99.0)
                fade = _fade(np.maximum(d, 0), (tp % 360) * D2R * 2.25, seed + 23)
                fade = np.where(d < 0, 1.0, fade)
                env = smoothstep(S.H_TAIL_END, S.H_TAIL_END + 3, s) * (1 - smoothstep(75.0, 80.0, s))
                wl = streaks((tp % 360.0) * D2R * r, 6.0, seed + 33)
                wear = np.clip((wl - 0.45) / 0.55, 0, 1) * env
                ccol = ccol * (1 + look.wear_lift * wear)[..., None]
                crough = crough - 0.05 * wear
                worn_col = np.asarray(look.worn)[None, None, :] * (0.9 + 0.2 * streaks((tp % 360) * D2R * 2.25, 7.0, seed + 43))[..., None]
                col = ccol * (1 - fade[..., None]) + worn_col * fade[..., None]
                rough = crough * (1 - fade) + (look.ground_rough + 0.05) * fade
                ground = np.zeros(U.shape, bool)
            else:
                col, rough, ground = ccol, crough, np.zeros(U.shape, bool)
            h = ch
        else:
            # facet: planar coordinates (U = s, V = -lateral); grind lines run along the facet (along s)
            lat = -V
            gcol, grough, gh = _ground_facet(U, lat + 10.0 * (int(isl.phi) // 120), seed + 51 + int(isl.phi), look)
            col, rough, h = gcol, grough, gh
            ground = np.ones(U.shape, bool)
            cstat = {}
        parts.append((box, col, rough, h, ground, name, cstat))
    return _assemble_many(t, parts, metal=1.0)


# =============================================================================================== wrap
def paint_wrap(isl: Island, look=LOOK, seed=20261023):
    """Twisted 2-ply cotton thread, hand wound (FINALISE 1.1.0, the craft review's 'reads as ribbed rubber' fix).

    Every pattern is a CONTINUOUS function on the surface: the thread is parameterised by its own length
    L = (2 pi turn + theta) r (continuous across theta = 0 and the -Z seam), so nothing jumps at an azimuth.
      - each stretch of thread has its own height (+-0.02 mm) and shade (+-8 %), varying slowly along its length,
        so the turns are not mechanically identical;
      - the 2-ply twist shows as diagonal ply grooves at 37 deg to the thread, period 0.5 mm along it, in N and BC;
      - a lower crest relief (normal tilt p99 about 21 deg): depth reads from the baked AO in the grooves;
      - a faint fibre halo on the crest tops: roughness toward 0.95, value +4 %.
    Bindings: square turns at 0.45 mm (periodic in theta), the same ply / fibre treatment."""
    t = S.WRAP_TEX
    canon = G.heavy_canon()
    box, U, V = texel_grid(isl)
    s, r = canon.at(U)
    r = np.maximum(r, 1e-4)
    tp = 180.0 - (V / r) / D2R
    th = ((S.SEAM_DEG + tp) % 360.0) * D2R
    rb, fb = S.H_RB, S.H_FB
    binding = ((s >= rb[0] - 1e-6) & (s <= rb[1] + 1e-6)) | ((s >= fb[0] - 1e-6) & (s <= fb[1] + 1e-6))
    face = binding & (r < S.H_R_BIND - S.H_BIND_ROUND - 1e-6)        # the binding end faces (radial)
    p = S.THREAD_PITCH
    pb = 0.45                                                         # bindings: square turns, tighter
    # right-hand single-start helix about +X: crest lines x / p - theta / 2pi = const
    ph_w = (s - S.H_WRAP[0]) / p - th / (2 * math.pi)
    ph_b = s / pb
    ph = np.where(binding, ph_b, ph_w)
    turn = np.floor(ph)
    f = ph - turn
    cross = f * np.where(binding, pb, p)                              # mm across the thread (0 .. pitch)
    # thread length coordinate: continuous along the helix; on the square binding rings periodic in theta
    L_w = (2 * math.pi * turn + th) * r
    n_ring = max(1, int(round(2 * math.pi * S.H_R_BIND / 0.5)))
    L_b = th / (2 * math.pi) * n_ring * 0.5                            # 0.5 mm units, n_ring per ring (periodic)
    L = np.where(binding, L_b, L_w)
    cth, sth = np.cos(th), np.sin(th)
    # per-stretch character (continuous along the thread; bindings: per ring + periodic in theta)
    jit_w_h = vnoise(L_w / 5.0, np.zeros_like(L_w) + 0.5, seed + 31) - 0.5
    jit_w_v = vnoise(L_w / 7.0, np.zeros_like(L_w) + 4.5, seed + 32) - 0.5
    jit_b_h = (vnoise(2.0 * cth + 9.0 * turn, 2.0 * sth, seed + 33) - 0.5)
    jit_b_v = (vnoise(2.0 * cth + 9.0 * turn + 50.0, 2.0 * sth, seed + 34) - 0.5)
    jit_h = np.where(binding, jit_b_h, jit_w_h) * 2.0                  # -1 .. 1
    jit_v = np.where(binding, jit_b_v, jit_w_v) * 2.0
    # round thread section, 0 in the groove; slightly flattened crest (soft cotton, wound under tension)
    prof = np.sqrt(np.clip(1 - (2 * f - 1) ** 2, 0, 1))
    prof_c = np.clip(prof * 1.08, 0, 1)
    # 2-ply twist: ply boundary lines at 37 deg to the thread axis, 0.5 mm apart along the thread
    cot = 1.0 / math.tan(37.0 * D2R)
    ply_ph = (L - cot * cross) / 0.5
    plyg = np.abs(np.sin(math.pi * ply_ph)) ** 0.7                   # 0 on the ply groove lines
    # fibres (fine, ~30 deg to the thread) and fuzz, both continuous
    fib = vnoise(L / 0.11 + cross / 0.19, cross / 0.11 - L / 0.19, seed + 3)
    fuzz = vnoise(L / 0.07, cross / 0.07 + 13.0 * turn, seed + 7)
    # end faces of the bindings: the thread ends seen edge-on: concentric layers + fibre noise
    pr_face = 0.6 + 0.4 * np.cos(2 * math.pi * (r - S.H_R_TAIL) / 0.3)
    relief = prof_c * (1.0 + 0.3 * jit_h) * (0.80 + 0.20 * plyg)
    h_unit = np.where(face, 0.4 * pr_face, relief) + 0.06 * (fib - 0.5) * prof + 0.03 * (fuzz - 0.5)
    halo = np.clip((prof - 0.80) / 0.20, 0, 1) * (0.6 + 0.4 * fuzz)    # crest tops
    dye = 0.5 * (fbm(s / 4.0, 1.2 * cth, seed + 9, 3) + fbm(s / 4.0 + 17.0, 1.2 * sth, seed + 19, 3)) - 0.5
    val = (1.0 - look.wrap_groove * (1 - prof) ** 2 + look.wrap_crest * (prof - 0.6)
           + 0.16 * (plyg - 0.5) * prof          # ply twist in the colour, +-8 %
           + 0.08 * jit_v                         # each stretch of thread its own shade, +-8 %
           + 0.04 * halo                          # fibre halo on the crests
           + 0.07 * (fib - 0.5) + 0.04 * (fuzz - 0.5) + 0.06 * dye)
    val = np.where(face, 0.75 + 0.15 * (pr_face - 0.5) + 0.08 * (fib - 0.5), val)
    val = np.where(binding & ~face, val * 1.04, val)
    base = np.asarray(S.WRAP_LINEAR)
    col = base[None, None, :] * np.clip(val, 0.2, 2.0)[..., None]
    rough = S.WRAP_ROUGH + 0.05 * (1 - prof) - 0.03 * (fib - 0.5)
    rough = rough + (0.95 - rough) * halo
    rough = np.clip(rough, 0.75, 1.0)
    h = look.wrap_relief_mm * h_unit
    parts = [(box, col, rough, h, np.zeros(U.shape, bool), "wrap", {})]
    out = _assemble_many(t, parts, metal=0.0)
    out["stats"] = {"thread_pitch_mm": p, "helix": "right-hand, single start", "binding_turn_pitch_mm": pb,
                    "ply_twist": "2-ply, grooves at 37 deg to the thread, 0.5 mm along it",
                    "per_stretch": "height +-0.3 x relief (+-0.02 mm), shade +-8 % (continuous along the thread)",
                    "relief_mm": look.wrap_relief_mm}
    return out


def normalise_wrap(out):
    """The covered mean colour equals the spec's shipped colour (#373532), the recolour default (run after
    finish_maps, so the margin follows)."""
    base = np.asarray(S.WRAP_LINEAR)
    cov = out["cover"]
    gain = base / out["albedo"][cov].mean(axis=0)
    out["albedo"] = np.clip(out["albedo"] * gain[None, None, :], 0, 1).astype(np.float32)
    out["stats"]["mean_gain"] = [round(float(g), 5) for g in gain]
    return out


# =============================================================================================== assemble
def _assemble_many(t, parts, metal):
    W, H = t.size
    alb = np.zeros((H, W, 3), np.float32)
    ro = np.zeros((H, W), np.float32)
    hh = np.zeros((H, W), np.float32)
    gr = np.zeros((H, W), bool)
    nrm = np.zeros((H, W, 3), np.float32)
    written = np.zeros((H, W), bool)
    prepared = []
    for (i0, i1, j0, j1, core), col, rough, h, ground, name, _st in parts:
        # tangent normal from the height field (mm) on this island's own grid (no cross-island derivatives)
        dhdv, dhdu = np.gradient(h, 1.0 / t.ppmm)
        n = np.stack([-dhdu, -dhdv, np.ones_like(h)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        prepared.append(((slice(i0, i1), slice(j0, j1)), core, col, rough, h, ground, n))
    # pass 1: every island's own rectangle; pass 2: the aprons, only where nothing was written
    for pass_core in (True, False):
        for sl, core, col, rough, h, ground, n in prepared:
            sel = (core if pass_core else ~core) & ~written[sl]
            alb[sl][sel] = col[sel]
            ro[sl][sel] = rough[sel]
            hh[sl][sel] = h[sel]
            gr[sl][sel] = ground[sel]
            nrm[sl][sel] = n[sel]
            written[sl] |= sel
    return {"albedo": alb, "rough": ro, "metal": np.full((H, W), metal, np.float32), "height": hh,
            "ground": gr, "N": nrm, "written": written, "stats": {}}


def finish_maps(out, cover, t, metal):
    """Apply the island coverage: covered texels keep the paint, the 16 px margin is EXTENDed from the islands,
    everything farther takes the covered mean (BC / roughness) or flat (N): the unused-texel fill."""
    W, H = t.size
    alb, ro, nrm = out["albedo"], out["rough"], out["N"]
    alb_g, k = grow(np.where(cover[..., None], alb, 0), cover, 16)
    ro_g, _ = grow(np.where(cover, ro, 0), cover, 16)
    n_g, _ = grow(np.where(cover[..., None], nrm, 0), cover, 16)
    far = ~k
    alb_g[far] = alb[cover].mean(axis=0)
    ro_g[far] = ro[cover].mean()
    n_g[far] = (0.0, 0.0, 1.0)
    n_g /= np.linalg.norm(n_g, axis=-1, keepdims=True)
    out["albedo"], out["rough"], out["N"] = alb_g, ro_g, n_g
    out["cover"] = cover
    out["margin"] = k & ~cover
    out["metal"] = np.full((H, W), metal, np.float32)
    return out
