"""Shared dojo material library: procedural texture generators (numpy only, no bpy).

Every map is built from periodic FFT noise, periodic Voronoi cells and periodic line functions, so each tile repeats
with no seam (seam test at the end of every set: wrap-around step / interior step). No photo, scan or third-party
pixels; the reference sheets (References/Dojo, AI-generated modelling references) are only measured against.

Output: Exports/DojoKit/Materials/Textures/T_DJ_<Set>_{BC,N,ORM}.png
  BC  sRGB albedo (emissive colour for the two emissive sets)
  N   tangent normal, DirectX convention (green = -Y, Unreal native), linear
  ORM R = ambient occlusion, G = roughness, B = metallic, linear, full range
  plus T_DJ_WearMask_M.png (grey breakup mask used by the weathering vertex colours)
Report: WorkFiles/dojo/build/materials/textures_report.json

Texel density baseline (STYLE_GUIDE 6): 5.12 px/cm. UVs made by dojo_materials' helpers are in TILE units (UV 1.0 =
one tile = SETS[set]['tile_m'] metres), so every material samples at scale 1.

Run with Blender's bundled Python (numpy included):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/materials/dojo_tex_gen.py [--only A,B]
"""
import json
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "Exports" / "DojoKit" / "Materials" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "materials"
LIB_VERSION = "1.1.0"   # r3 (2026-09-28): the Unreal look pass (timber, granite, tile, plaster, lacquer)

# ------------------------------------------------------------------------------------------------ registry
# size = (width = U px, height = V px); tile_m = (U metres, V metres) of one tile (None = unit UV per face / pane)
SETS = {
    "TimberDark":    {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "timber"},
    "TimberDarkEnd": {"size": (1024, 1024), "tile_m": (2.0, 2.0), "kind": "timber_end"},
    "TimberAged":    {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "timber"},
    "TimberAgedEnd": {"size": (1024, 1024), "tile_m": (2.0, 2.0), "kind": "timber_end"},
    "Granite":       {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "stone"},
    "GraniteRubble": {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "stone"},
    "Iron":          {"size": (1024, 1024), "tile_m": (2.0, 2.0), "kind": "metal"},
    "Rope":          {"size": (1024, 512), "tile_m": None, "kind": "rope"},       # U = 4 lays, V = once round
    "PlasterCream":  {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "plaster"},
    "PlasterEarth":  {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "plaster"},
    "RoofTile":      {"size": (2048, 2048), "tile_m": (4.0, 4.0), "kind": "tile"},
    "Lacquer":       {"size": (2048, 2048), "tile_m": (2.0, 2.0), "kind": "lacquer"},  # hero: 10.24 px/cm
    "GlassAmber":    {"size": (512, 512), "tile_m": None, "kind": "emissive"},     # UV 0-1 per pane
    "VendingPanel":  {"size": (512, 1024), "tile_m": None, "kind": "emissive"},   # UV 0-1 over the display
    # r5 (named variant): lit shoji paper, UV 0-1 over ONE lattice cell (bar centre to bar centre)
    "ShojiPaper":    {"size": (256, 256), "tile_m": None, "kind": "emissive"},
}
WEARMASK = {"size": (512, 512), "tile_m": (1.0, 1.0)}

# Tunable look parameters (sRGB hex). Calibrated against the reference crops (ref_crops.py) under the studio rig.
P = {
    # r3 (Unreal look pass): the r2 timber rendered orange-red in UE 5.8 (veranda deck s 0.85, posts 0.90, gate
    # ceiling pure red) against the sheets' ~(80, 59, 46) s 0.43: UE's low sun + Lumen bounce between warm timber and
    # plaster compounds chroma (measured log-chroma gain 1.7-2.9 x the Blender render). The albedo is now a weathered
    # grey-brown (median s ~0.30, hue ~26 deg) so it lands near s 0.45-0.6, hue 20-25 in UE; 'target' is the
    # texture's median sRGB after grading, 'chroma' compresses the per-pixel chroma about luminance before grading
    "TimberDark": dict(light="#8A6243", mid="#5A3D29", dark="#22160D", crack="#0B0806", seed=1101,
                       silver=0.16, sat=1.0, target="#4A3E36", chroma=0.62, contrast=0.60),
    "TimberAged": dict(light="#A07248", mid="#6A4A32", dark="#2E1F14", crack="#100B08", seed=1201,
                       silver=0.20, sat=1.0, target="#57493D", chroma=0.62, contrast=0.60),
    "TimberDarkEnd": dict(face="TimberDark", k=0.70, seed=1151),
    "TimberAgedEnd": dict(face="TimberAged", k=0.72, seed=1251),
    # r3: the r2 granite read terrazzo / dalmatian in UE (coarse, contrasty speckle). v2 = fine crystal grain, low
    # contrast, bush-hammered (tataki) pitting and chisel relief, cavity darkening, sun-bleached highs, sparse lichen
    "Granite": dict(base="#716A63", dark="#2C2A29", white="#D2CEC6", stain="#7A6450", seed=1301, target="#736F6A",
                    lichen_grey="#9FA38C", lichen_ochre="#9C8C5C"),
    "GraniteRubble": dict(base="#6A6560", gap="#16140F", moss="#4F5A35", seed=1401),
    "Iron": dict(bare="#4A4846", rust="#4A3326", seed=1501),
    "Rope": dict(base="#8D6D45", seed=1601),
    # r3: plaster rendered red in UE shade (s 0.96): less chroma, a cream (not peach) hue, and the generator's warm
    # dark-tint (R +5 %, B -12 % in the stains) cut down
    "PlasterCream": dict(base="#BE9470", seed=1701, target="#C0A98C", tint_k=(0.01, 0.03)),
    "PlasterEarth": dict(base="#CAAC89", target="#C0AA90", tint_k=(0.02, 0.05)),
    # r3: calmer mottle, satin (not wet) roughness, a finer craquelure
    "Lacquer": dict(base="#6E3428", seed=1801, target="#66453F"),
    "GlassAmber": dict(k_core=2700, k_edge=2200, seed=1901),
    "VendingPanel": dict(seed=2001),
    # r5: the hall sheet's lit shoji cells, measured (dojo_hall_front_ref, bright cells p95 (220-234, 152-168, 88-98),
    # hue 27-29 deg; dojo1_reference2 (230-240, 148-159, 47-52), hue 33-34): honey amber, never red
    "ShojiPaper": dict(core="#F2B25E", mid="#E0913F", rim="#8E5222", seed=2101),
}


# ------------------------------------------------------------------------------------------------ io + basics
def write_png(path, img):
    a = np.clip(np.round(np.asarray(img, dtype=np.float64) * 255.0), 0, 255).astype(np.uint8)
    if a.ndim == 2:
        ctype, a2 = 0, a
        rows = [a2[r].tobytes() for r in range(a2.shape[0])]
    else:
        ctype = 2
        rows = [a[r].tobytes() for r in range(a.shape[0])]
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def lerp(a, b, t):
    t = np.asarray(t, dtype=np.float64)
    if t.ndim >= 1 and np.ndim(a) == 3 and t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0, angle=None, aspect=1.0):
    """Periodic 1/f^beta noise, zero mean, unit std. stretch_u > 1: features long along U (columns); stretch_v > 1:
    long along V. angle (radians, from +U toward +V) + aspect > 1: features long along that direction."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0
    if angle is None:
        f = np.sqrt((fu * stretch_u) ** 2 + (fv * stretch_v) ** 2)
    else:
        a = fu * np.cos(angle) + fv * np.sin(angle)
        b = -fu * np.sin(angle) + fv * np.cos(angle)
        f = np.sqrt((a * aspect) ** 2 + b ** 2)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    if fmin > 0:
        F[f < fmin] = 0
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def gblur(a, sigma_px):
    """Periodic gaussian blur (FFT)."""
    h, w = a.shape
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fu * fu + fv * fv))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def contrast(col, k):
    """Expand luminance contrast about the median by exponent k (0 = none): col * (L / L50) ** k. Hue kept.
    r3: every r2 render measured a p10-p90 luminance spread 0.5-0.7 x the reference crops'."""
    L = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    m = np.median(L)
    return col * np.power(np.clip(L / (m + 1e-9), 1e-3, None), k)[..., None]


def to_lin(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0, None)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def chroma(col, k):
    """r3: scale each pixel's chroma about its own luminance (sRGB values), k < 1 greys it."""
    L = (0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2])[..., None]
    return L + (col - L) * k


def grade_median(col, target_hex):
    """r3: per-channel LINEAR gain so the texture's per-channel median lands on target_hex (sRGB). Sets hue, chroma and
    value of the median; the texture's own structure is kept."""
    lin = to_lin(col)
    med = np.median(lin.reshape(-1, 3), 0)
    return to_srgb(lin * (to_lin(srgb(target_hex)) / np.maximum(med, 1e-6))[None, None, :])


def flatten_low(col, sigma_px, k):
    """r3: pull the low-frequency luminance (gaussian sigma_px) toward the median by exponent k (0 = none, 1 = flat).
    The timber's 4 m tone band put whole members at black or orange depending on grain_uv's random offset."""
    L = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    low = gblur(L, sigma_px)
    return col * np.power(np.median(L) / np.clip(low, 1e-4, None), k)[..., None]


def hp_std_rel(col, sigma_px=3.0):
    """r3 metric: std of the high-pass luminance (below ~sigma_px) / mean luminance: the 'speckle contrast'."""
    L = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    return round(float((L - gblur(L, sigma_px)).std() / (L.mean() + 1e-9)), 4)


def normal_dx(height, strength):
    """Height (rows go down the image = -V) to a DirectX tangent normal (Unreal convention)."""
    du = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dv_gl = -(np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nx, ny, nz = -du * strength, -dv_gl * strength, np.ones_like(height)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln * 0.5 + 0.5, -ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5])


def cavity(height, sigma_px):
    """0..1: how far a texel sits below its blurred neighbourhood (recess mask)."""
    d = gblur(height, sigma_px) - height
    d = np.clip(d, 0, None)
    return np.clip(d / (np.percentile(d, 99.5) + 1e-9), 0, 1)


def seam_ratio(img):
    g = img.mean(axis=2) if img.ndim == 3 else img
    inner_c = np.abs(np.diff(g, axis=1)).mean()
    inner_r = np.abs(np.diff(g, axis=0)).mean()
    wrap_c = np.abs(g[:, 0] - g[:, -1]).mean()
    wrap_r = np.abs(g[0, :] - g[-1, :]).mean()
    return round(float(max(wrap_c / (inner_c + 1e-9), wrap_r / (inner_r + 1e-9))), 3)


def seam_rank(img):
    """Where the wrap-around step falls among all interior column / row steps (0..1, max of U and V). A seamless
    tile ranks like any other column (not in the top 1 %); a seam ranks at 1.0."""
    g = img.mean(axis=2) if img.ndim == 3 else img
    cs = np.abs(np.diff(g, axis=1)).mean(0)
    rs = np.abs(np.diff(g, axis=0)).mean(1)
    wc = np.abs(g[:, 0] - g[:, -1]).mean()
    wr = np.abs(g[0, :] - g[-1, :]).mean()
    return round(float(max((cs < wc).mean(), (rs < wr).mean())), 3)


def voronoi(h, w, nx, ny, jitter, seed, cell_aspect=1.0, with_pos=False):
    """Periodic jittered-grid Voronoi on an h x w image with nx x ny cells. Distances are measured in 'cell units'
    along V scaled by cell_aspect (= cell height / cell width in metres) so cells can be wider than tall.
    Returns F1, F2 (in U-cell units), cell id (int), and the nearest seed's (u, v) in 0..1."""
    rng = np.random.default_rng(seed)
    jx = rng.uniform(-jitter, jitter, (ny, nx))
    jy = rng.uniform(-jitter, jitter, (ny, nx))
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    gu = u / w * nx
    gv = v / h * ny
    ci = np.floor(gu).astype(int)
    cj = np.floor(gv).astype(int)
    F1 = np.full((h, w), 1e9)
    F2 = np.full((h, w), 1e9)
    ID = np.zeros((h, w), int)
    PX = np.zeros((h, w))
    PY = np.zeros((h, w))
    for dj in (-2, -1, 0, 1, 2):
        for di in (-2, -1, 0, 1, 2):
            ni = ci + di
            nj = cj + dj
            wi = ni % nx
            wj = nj % ny
            px = ni + 0.5 + jx[wj, wi]
            py = nj + 0.5 + jy[wj, wi]
            d = np.sqrt((gu - px) ** 2 + ((gv - py) * cell_aspect) ** 2)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, wj * nx + wi, ID)
            if with_pos:
                PX = np.where(closer, gu - px, PX)
                PY = np.where(closer, (gv - py) * cell_aspect, PY)
            F1 = np.where(closer, d, F1)
    if with_pos:
        return F1, F2, ID, PX, PY
    return F1, F2, ID


def kelvin_rgb(k):
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * np.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * np.log(t - 10) - 305.0447927307)
    return np.array([max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b)])


def save_set(name, bc, height, nstrength, rough, ao=None, metal=None, extra=None):
    OUT.mkdir(parents=True, exist_ok=True)
    bc = np.clip(bc, 0, 1)
    h, w = bc.shape[:2]
    write_png(OUT / f"T_DJ_{name}_BC.png", bc)
    write_png(OUT / f"T_DJ_{name}_N.png", normal_dx(height, nstrength))
    ao = np.ones((h, w)) if ao is None else np.clip(ao, 0, 1)
    metal = np.zeros((h, w)) if metal is None else np.clip(metal, 0, 1)
    rough = np.clip(rough, 0.02, 1)
    write_png(OUT / f"T_DJ_{name}_ORM.png", np.dstack([ao, rough, metal]))
    reg = SETS[name]
    lum = 0.2126 * bc[..., 0] + 0.7152 * bc[..., 1] + 0.0722 * bc[..., 2]
    m8 = np.round(metal * 255)
    rep = {"set": name, "size_px": [w, h], "tile_m": reg["tile_m"],
           "texel_px_per_cm": (round(w / (reg["tile_m"][0] * 100.0), 3) if reg["tile_m"] else None),
           "median_srgb": [int(round(x * 255)) for x in np.median(bc.reshape(-1, 3), 0)],
           "mean_srgb_hex": "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in bc.reshape(-1, 3).mean(0)),
           "lum_p10_p50_p90": [round(float(np.percentile(lum, q)) * 255, 1) for q in (10, 50, 90)],
           "albedo_max": round(float(bc.max()), 3),
           "rough_p5_p50_p95": [round(float(np.percentile(rough, q)), 3) for q in (5, 50, 95)],
           "ao_p1_p50": [round(float(np.percentile(ao, q)), 3) for q in (1, 50)],
           "metal_share_ge_0.95": round(float((m8 >= 242).mean()), 4),
           "metal_share_zero": round(float((m8 == 0).mean()), 4),
           "metal_share_partial": round(float(((m8 > 0) & (m8 < 242)).mean()), 4),
           "seam_ratio_bc": seam_ratio(bc), "seam_ratio_height": seam_ratio(height),
           "seam_rank_bc": seam_rank(bc), "seam_rank_height": seam_rank(height), "tiling": reg["tile_m"] is not None
           or name == "Rope"}
    if extra:
        rep.update(extra)
    return rep


# ------------------------------------------------------------------------------------------------ timber
def _dashes(h, w, rng, count, len_px, ang_sd, width_px=1):
    """Short periodic dashes mostly along U (0..1 mask): scratches, pores, flecks."""
    m = np.zeros((h, w))
    for _ in range(count):
        r0, c0 = rng.integers(0, h), rng.integers(0, w)
        L = int(rng.uniform(*len_px))
        ang = rng.normal(0, ang_sd)
        t = np.arange(L)
        rr = (r0 + np.round(np.tan(ang) * t + np.cumsum(rng.normal(0, 0.07, L)))).astype(int) % h
        cc = (c0 + t) % w
        a = rng.uniform(0.5, 1.0) * np.sin(np.pi * (t + 0.5) / L) ** 0.5
        for k in range(width_px):
            m[(rr + k) % h, cc] = np.maximum(m[(rr + k) % h, cc], a * (1.0 if k == 0 else 0.6))
    return m


def _nail_holes(n, rng, count):
    """r3: periodic nail holes: a dark 2-3 px core (4-6 mm at 1.95 mm/px) and a soft iron-stain halo (about 1.5 cm)."""
    hole = np.zeros((n, n))
    halo = np.zeros((n, n))
    rr, cc = np.mgrid[-10:11, -10:11]
    d = np.sqrt(rr * rr + cc * cc)
    for _ in range(count):
        r0, c0 = rng.integers(0, n, 2)
        rad = rng.uniform(1.1, 1.7)
        ys, xs = (r0 + rr) % n, (c0 + cc) % n
        hole[ys, xs] = np.maximum(hole[ys, xs], np.clip(rad + 0.5 - d, 0, 1))
        halo[ys, xs] = np.maximum(halo[ys, xs], np.exp(-(d / rng.uniform(3.0, 5.0)) ** 2) * rng.uniform(0.4, 1.0))
    return {"hole": hole, "halo": halo}


def _colour_stats(col):
    """r3: median hue / saturation (sRGB) and the high-pass speckle contrast, for the report."""
    import colorsys
    m = np.median(col.reshape(-1, 3), 0)
    h, s_, v = colorsys.rgb_to_hsv(*[float(x) for x in m])
    return {"median_hue_deg": round(h * 360, 1), "median_sat": round(s_, 3), "hp_std_rel": hp_std_rel(col)}


def timber_fields(n, seed, tile_m=4.0):
    """Grain geometry shared by the face and end-grain sets: returns dict of 0..1 fields (rows = V across the grain,
    cols = U along the grain). 2048 px over 4 m = 1.95 mm per px."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:n, 0:n].astype(np.float64) / n
    # board/member tone bands (long along U): each member samples a different V band
    band = pnoise(n, n, 2.2, seed, stretch_u=40.0)
    # flat-sawn cathedral figure: low-frequency warp of the ring phase, long along U
    # r2: stronger, shorter warp (stretch 2.5-5 instead of 7-16) so the rings arch and wander (cathedral figure)
    warp = (7.0 * pnoise(n, n, 2.5, seed + 1, stretch_u=2.5) + 2.2 * pnoise(n, n, 2.0, seed + 2, stretch_u=5.0)
            + 0.7 * pnoise(n, n, 1.6, seed + 7, stretch_u=9.0))
    # knots: the grain flows round them (phase bump) + a dark core
    knot = np.zeros((n, n))
    kpush = np.zeros((n, n))
    nk = 40
    for _ in range(nk):
        ku, kv = rng.uniform(0, 1, 2)
        ru = rng.uniform(0.016, 0.034) / tile_m          # 1.6-3.4 cm half-length along the grain
        rv = ru * rng.uniform(0.55, 0.8)
        du = (u - ku + 0.5) % 1.0 - 0.5
        dv = (v - kv + 0.5) % 1.0 - 0.5
        d2 = (du / ru) ** 2 + (dv / rv) ** 2
        kpush += rng.uniform(1.5, 3.0) * np.exp(-d2 / 9.0)
        core = np.clip(1.25 - np.sqrt(d2), 0, 1) ** 0.6
        knot = np.maximum(knot, core)
    lines = 150                                          # ring lines per 4 m across the grain (2.7 cm)
    # uneven ring spacing: the phase rate itself varies across the grain
    ph = v * lines + 6.0 * pnoise(n, n, 2.8, seed + 8, stretch_u=30.0) + warp + kpush
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    late = ring ** 5 * np.clip(0.6 + 0.4 * pnoise(n, n, 1.6, seed + 3, stretch_u=18.0), 0.15, 1.0)
    ph2 = v * 620 + 0.35 * warp + 1.5 * pnoise(n, n, 2.0, seed + 4, stretch_u=25.0)
    fine = (0.5 + 0.5 * np.cos(2 * np.pi * ph2)) ** 3
    fibre = pnoise(n, n, 0.7, seed + 5, stretch_u=50.0)
    streak = pnoise(n, n, 1.4, seed + 6, stretch_u=22.0)
    # long dark figure streaks (the sheets' wood is streaked with dark weathered lines of many widths)
    dstreak = np.clip((pnoise(n, n, 1.2, seed + 9, stretch_u=45.0) - 0.9) * 1.4, 0, 1)
    # deep drying checks: long thin cracks along the grain, sparse
    chk = np.zeros((n, n))
    for _ in range(170):
        r0, c0 = rng.integers(0, n, 2)
        L = int(rng.uniform(0.03, 0.16) * n)
        wmax = rng.uniform(0.9, 2.4)
        t = np.linspace(0, 1, L)
        width = wmax * np.sin(np.pi * t) ** 0.6
        wander = np.cumsum(rng.normal(0, 0.16, L))
        cc = (c0 + np.arange(L)) % n
        for k in range(-3, 4):
            rr = (r0 + np.round(wander).astype(int) + k) % n
            chk[rr, cc] = np.maximum(chk[rr, cc], np.clip(width - abs(k), 0, 1))
    chk = np.clip(gblur(chk, 0.7) * 1.6, 0, 1)
    pores = _dashes(n, n, rng, 5200, (3, 12), 0.03, 1)
    scuff = _dashes(n, n, rng, 260, (6, 30), 0.9, 1)
    return dict(v=v, u=u, band=band, late=late, fine=fine, fibre=fibre, streak=streak, chk=chk, knot=knot, dstreak=dstreak,
                pores=pores, scuff=scuff, ring=ring)


def timber(name, n=2048):
    p = P[name]
    f = timber_fields(n, p["seed"])
    light, mid, dark = srgb(p["light"]), srgb(p["mid"]), srgb(p["dark"])
    # tone 0..1: 0 = dark latewood, 1 = light earlywood
    # r3 (lib 1.1): the across-grain band and dark streaks weaker again (members came out black or orange by their
    # grain_uv offset), the latewood lines softer (-0.55 -> -0.32: the 2.7 cm ring lines read as zebra stripes)
    t = (0.60 + 0.02 * f["band"] + 0.12 * f["fibre"] + 0.16 * f["streak"] - 0.32 * f["late"] - 0.10 * f["fine"]
         - 0.12 * f["dstreak"])
    t = np.clip(t, 0, 1)
    col = np.where((t < 0.5)[..., None], lerp(dark, mid, np.clip(t / 0.5, 0, 1)[..., None]),
                   lerp(mid, light, np.clip((t - 0.5) / 0.5, 0, 1)[..., None]))
    # pores and flecks: short dark dashes along the grain
    col = lerp(col, dark * 0.7, np.clip(0.55 * f["pores"], 0, 1))
    # knots: dark resinous core with a darker rim
    col = lerp(col, dark * 0.6, np.clip(0.85 * f["knot"], 0, 1))
    # weathering: a little grey silvering on the lighter streaks (kept small: the judge found greyed timber wrong)
    sil = np.clip(pnoise(n, n, 1.8, p["seed"] + 20, stretch_u=12.0) - 0.6, 0, 1) * p["silver"]
    g = col.mean(2, keepdims=True)
    col = lerp(col, g * np.array([1.03, 1.0, 0.96]) * 1.08, sil[..., None])
    # scuffs: a touch lighter and greyer (not a light band: the edges are done by the Wear mask in the material)
    col = lerp(col, g * 1.12, np.clip(0.30 * f["scuff"], 0, 1)[..., None])
    # r3: nail holes (square-ish 4-6 mm holes with a dark iron-stain halo), about 4 per m2 of face
    nail = _nail_holes(n, np.random.default_rng(p["seed"] + 40), 70)
    col = lerp(col, np.array([0.20, 0.17, 0.15]) * col, np.clip(0.55 * nail["halo"], 0, 1)[..., None])
    col = lerp(col, srgb(p["crack"]), np.clip(nail["hole"], 0, 1)[..., None])
    # height: latewood proud (weathered earlywood erodes), deep checks and knot cracks
    height = (0.30 * f["late"] + 0.10 * f["fine"] + 0.06 * f["fibre"] - 1.00 * f["chk"] - 0.10 * f["pores"]
              - 0.15 * f["scuff"] + 0.08 * f["knot"] - 1.2 * nail["hole"])
    cav = cavity(height, 5.0)
    # grime in recesses: checks near black, grooves darkened
    col = col * (1 - 0.45 * cav)[..., None]
    col = lerp(col, srgb(p["crack"]), np.clip(1.15 * f["chk"], 0, 1)[..., None])
    # r3: contrast to the sheets' spread (p10-p90 about 40-60 grey levels lit)
    col = contrast(col, p.get("contrast", 0.75))
    # r3: no member-scale tone band (low-frequency luminance flattened at ~15 cm), weathered grey-brown chroma, and
    # the median graded to the Unreal-calibrated target (P[name]['target'])
    col = flatten_low(col, 80.0, 0.80)
    col = chroma(col, p.get("chroma", 1.0))
    col = grade_median(col, p["target"])
    rough = 0.80 + 0.05 * np.tanh(f["fibre"]) + 0.06 * (1 - f["late"]) + 0.12 * f["chk"] + 0.04 * cav + 0.1 * nail["hole"]
    ao = np.clip(1 - 0.75 * f["chk"] - 0.45 * cav - 0.6 * nail["hole"], 0.12, 1)
    return save_set(name, col, height, 20.0, rough, ao, extra=_colour_stats(col))


def timber_end(name, n=1024):
    """End grain over 2 m: growth rings as arcs of far-off piths (periodic warped stripes: no seams, no cell
    pattern), short radial checks across the rings, darker and rougher than the face set (end grain soaks up grime:
    the judges saw light end grain)."""
    p = P[name]
    face = P[p["face"]]
    rng = np.random.default_rng(p["seed"])
    v, u = np.mgrid[0:n, 0:n].astype(np.float64) / n
    bend = 0.09 * np.sin(2 * np.pi * u) + 0.035 * np.sin(4 * np.pi * u + 1.3) + 0.012 * np.sin(6 * np.pi * u + 0.4)
    wob = 0.006 * pnoise(n, n, 2.2, p["seed"] + 1) + 0.002 * pnoise(n, n, 1.4, p["seed"] + 5)
    rings = 180                                             # ~1.1 cm per ring over the 2 m tile
    ph = (v + bend + wob) * rings + 4.0 * pnoise(n, n, 2.8, p["seed"] + 6, stretch_u=4.0)
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    late = ring ** 4
    # radial checks: short cracks running ACROSS the rings (along V), tapering
    chk = _dashes(n, n, rng, 90, (25, 110), 0.25, 2).T
    chk = np.clip(gblur(chk, 0.6) * 1.8, 0, 1)
    pores = pnoise(n, n, 0.5, p["seed"] + 3)
    mott = pnoise(n, n, 2.0, p["seed"] + 4)
    mid, dark = srgb(face["mid"]), srgb(face["dark"])
    base = lerp(dark, mid, 0.70) * (1 + 0.07 * pores + 0.10 * mott)[..., None]
    col = lerp(base, dark * 0.85, np.clip(0.55 * late, 0, 1)[..., None])
    col = lerp(col, srgb(face["crack"]), np.clip(chk, 0, 1)[..., None])
    height = 0.2 * (1 - late) + 0.06 * pores - 1.0 * chk
    cav = cavity(height, 3.0)
    col = col * (1 - 0.30 * cav)[..., None]
    # r3: graded like the face set: the face target x 0.78 in luminance (dark end grain), a little less chroma
    col = chroma(col, P[p["face"]].get("chroma", 1.0) * 0.9)
    col = grade_median(col, "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in to_srgb(to_lin(srgb(face["target"])) * 0.78)))
    rough = 0.88 + 0.05 * np.tanh(pores) + 0.07 * chk
    ao = np.clip(1 - 0.7 * chk - 0.4 * cav, 0.15, 1)
    return save_set(name, col, height, 6.0, rough, ao)


# ------------------------------------------------------------------------------------------------ granite
def granite_fields(n, seed, tile_m=4.0):
    """Rough-hewn granite height + grain fields (tile 4 m, 1.95 mm/px). r2: the relief is built from chipped FACETS
    (periodic Voronoi cells, each a randomly tilted plane, so every chip has a crisp edge) at two scales (about 2.5 and
    7 cm) over a pitched-face undulation, plus short chisel grooves in tool-mark patches and pits. The sheets' stone
    reads as bright crests and dark hollows at the 1-5 cm scale; r1's smooth noise read as concrete."""
    rng = np.random.default_rng(seed)
    relief = pnoise(n, n, 1.9, seed + 1)                                  # 10-60 cm undulation

    def facets(cell_m, jitter, sd, s):
        cells = int(round(tile_m / cell_m))
        F1, F2, ID, dx, dy = voronoi(n, n, cells, cells, jitter, s, with_pos=True)
        g = np.random.default_rng(s + 1).normal(0, sd, (cells * cells, 2))
        off = np.random.default_rng(s + 2).normal(0, 0.15, cells * cells)
        return g[ID, 0] * dx + g[ID, 1] * dy + off[ID] - 0.25 * F1 ** 2

    fac_s = facets(0.035, 0.45, 0.60, seed + 30)   # r3: 3.5 / 9 cm chips (r2's 2.5 / 7 read as fine sand)
    fac_m = facets(0.09, 0.45, 0.50, seed + 40)
    bump = pnoise(n, n, 1.1, seed + 2)
    cells = int(round(tile_m / 0.12))
    F1, F2, ID = voronoi(n, n, cells, cells, 0.45, seed + 3)
    dir_of = rng.integers(0, 4, cells * cells)[ID]
    chisel = np.zeros((n, n))
    for k, ang in enumerate((0.35, 1.05, 1.9, 2.6)):
        g = pnoise(n, n, 0.9, seed + 10 + k, angle=ang, aspect=7.0)
        groove = np.clip(1 - np.abs(g) / 0.30, 0, 1) ** 1.5
        chisel += groove * (dir_of == k)
    chisel = gblur(chisel, 0.8) * np.clip(pnoise(n, n, 1.5, seed + 15) + 0.3, 0, 1)
    pits = np.clip((pnoise(n, n, 0.55, seed + 5) - 1.8) * 1.5, 0, 1)
    dark = np.clip((pnoise(n, n, 0.25, seed + 6) - 1.6) * 3.0, 0, 1)     # biotite (r2: sparser, r1 read terrazzo)
    white = np.clip((pnoise(n, n, 0.3, seed + 7) - 1.85) * 3.0, 0, 1)    # feldspar
    quartz = pnoise(n, n, 0.5, seed + 8)
    mottle = pnoise(n, n, 2.1, seed + 9)
    stain = np.clip(pnoise(n, n, 2.2, seed + 20) - 1.0, 0, 1)
    # r4: softer chips (r3's outlined cells read as crazy paving), more lumpy bump
    height = gblur(0.35 * relief + 0.40 * fac_m + 0.18 * fac_s + 0.25 * bump - 0.30 * chisel, 1.0) - 0.9 * pits \
        + 0.03 * white
    return dict(relief=relief, bump=bump, chisel=chisel, pits=pits, dark=dark, white=white, quartz=quartz,
                mottle=mottle, stain=stain, height=height)


def granite_colour(f, base, dkc, wc, stainc, height, crest_k=0.40, cav_k=0.70):
    hp = height - gblur(height, 5.0)
    sc = np.percentile(np.abs(hp), 98) + 1e-9
    crest = np.clip(hp / sc, 0, 1)
    cav = np.clip(-hp / sc, 0, 1)
    cav2 = cavity(height, 12.0)
    lum = 1.0 + 0.07 * f["mottle"] + 0.05 * f["quartz"] + crest_k * crest - cav_k * cav - 0.25 * cav2
    col = base[None, None, :] * lum[..., None]
    col = lerp(col, dkc, np.clip(0.80 * f["dark"], 0, 1)[..., None])
    col = lerp(col, wc, np.clip(0.60 * f["white"], 0, 1)[..., None])
    col = lerp(col, dkc * 0.8, np.clip(0.9 * f["pits"], 0, 1)[..., None])
    col = lerp(col, stainc, np.clip(0.18 * f["stain"], 0, 1)[..., None])
    return col, np.clip(cav + cav2, 0, 1)


def granite(name="Granite", n=2048):
    """r3 (lib 1.1, the Unreal look pass): v2 granite. The r2 set's chipped 3.5 / 9 cm facets, dark biotite blots and
    contrast step read as terrazzo / dalmatian on the step band, lanterns and path in UE. Now (tile 4 m, 1.95 mm/px):
      relief  pitched-face undulation (10-60 cm), soft 7 cm chips, bush-hammered (tataki) pitting (3-8 mm pits over
              ~20 % of the face), directional chisel strokes in patches, a sparse fine crevice network
      colour  fine crystal grain at the texel scale (+-5 %), small sparse mica / feldspar specks at low contrast,
              cavity darkening at two scales, dark crevices, sun-bleached (lighter, greyer) highs, crustose lichen
              (pale grey-green and ochre) in sparse clusters; median graded to P['Granite']['target']
    GraniteRubble keeps the r2 fields (granite_fields / granite_colour), unchanged."""
    p = P[name]
    seed = p["seed"]
    tile_m = 4.0
    relief = pnoise(n, n, 1.9, seed + 1)

    def facets(cell_m, jitter, sd, s_):
        cells = int(round(tile_m / cell_m))
        F1, F2, ID, dx, dy = voronoi(n, n, cells, cells, jitter, s_, with_pos=True)
        g = np.random.default_rng(s_ + 1).normal(0, sd, (cells * cells, 2))
        off = np.random.default_rng(s_ + 2).normal(0, 0.15, cells * cells)
        return g[ID, 0] * dx + g[ID, 1] * dy + off[ID] - 0.25 * F1 ** 2

    chips = gblur(facets(0.07, 0.45, 0.45, seed + 40), 2.0)
    bump = pnoise(n, n, 1.1, seed + 2)
    # tataki: dense small pits
    pits = gblur(np.clip((pnoise(n, n, 0.6, seed + 5, fmin=0.15) - 0.85) * 1.4, 0, 1), 0.9)   # 4-10 mm
    # chisel strokes in 12 cm patches, one of four directions per patch
    cells = int(round(tile_m / 0.12))
    F1, F2, ID = voronoi(n, n, cells, cells, 0.45, seed + 3)
    dir_of = np.random.default_rng(seed).integers(0, 4, cells * cells)[ID]
    chisel = np.zeros((n, n))
    for k, ang in enumerate((0.35, 1.05, 1.9, 2.6)):
        g = pnoise(n, n, 0.9, seed + 10 + k, angle=ang, aspect=7.0)
        chisel += (np.clip(1 - np.abs(g) / 0.30, 0, 1) ** 1.5) * (dir_of == k)
    chisel = gblur(chisel, 0.8) * np.clip(pnoise(n, n, 1.5, seed + 15) + 0.3, 0, 1)
    # fine crevices: thin ridged-noise lines in patches
    rid = np.abs(pnoise(n, n, 1.4, seed + 16, fmin=0.02))
    crev = np.clip(1 - rid / 0.035, 0, 1) * np.clip((pnoise(n, n, 2.0, seed + 17) - 0.7) * 1.5, 0, 1)
    crev = gblur(crev, 0.6)
    height = (0.30 * relief + 0.40 * chips + 0.18 * bump - 0.35 * chisel) - 0.50 * pits - 0.9 * crev
    # colour
    grain = pnoise(n, n, 0.1, seed + 8, fmin=0.5)                          # single crystals (2-4 mm)
    mica = np.clip((pnoise(n, n, 0.2, seed + 6, fmin=0.45) - 2.1) * 3.0, 0, 1)
    felds = np.clip((pnoise(n, n, 0.2, seed + 7, fmin=0.45) - 2.1) * 3.0, 0, 1)
    mottle = pnoise(n, n, 2.1, seed + 9)
    hp = height - gblur(height, 6.0)
    sc = np.percentile(np.abs(hp), 98) + 1e-9
    crest = np.clip(hp / sc, 0, 1)
    cav = np.clip(-hp / sc, 0, 1)
    cav2 = cavity(height, 14.0)
    lum = (1.0 + 0.04 * grain + 0.06 * mottle - 0.18 * mica + 0.12 * felds + 0.24 * crest - 0.40 * cav - 0.25 * cav2
           - 0.55 * crev)
    base = srgb(p["base"])
    col = base[None, None, :] * lum[..., None]
    # sun-bleached highs: lighter AND greyer
    col = lerp(col, chroma(col, 0.4) * 1.05, np.clip(0.6 * crest, 0, 1))
    # crustose lichen: sparse clusters (pale grey-green, some ochre), a few percent of the face
    lpatch = np.clip((pnoise(n, n, 1.7, seed + 30) - 1.25) * 1.6, 0, 1)
    lbreak = np.clip((pnoise(n, n, 0.5, seed + 31, fmin=0.2) + 0.3) * 1.5, 0, 1)
    lich = gblur(lpatch * lbreak, 0.8)
    ochre = np.clip((pnoise(n, n, 1.2, seed + 32) - 0.8) * 2.0, 0, 1)
    lc = lerp(np.ones((n, n, 3)) * srgb(p["lichen_grey"]), np.ones((n, n, 3)) * srgb(p["lichen_ochre"]), ochre)
    col = lerp(col, lc * (0.92 + 0.08 * grain)[..., None], np.clip(0.55 * lich * (1 - cav), 0, 1))
    col = grade_median(col, p["target"])
    rough = 0.82 + 0.04 * np.tanh(relief) - 0.07 * crest + 0.08 * cav + 0.06 * lich - 0.06 * felds
    ao = np.clip(1 - 0.45 * cav - 0.25 * cav2 - 0.6 * crev - 0.2 * pits, 0.15, 1)
    extra = _colour_stats(col)
    extra.update({"version": "v2 (r3): fine grain, tataki pits, chisel, crevices, bleached highs, lichen",
                  "lichen_cover": round(float((lich > 0.3).mean()), 4)})
    return save_set(name, col, height, 12.0, rough, ao, extra=extra)


def granite_rubble(name="GraniteRubble", n=2048):
    """Dry-laid rough polygonal chisel-faced stones (the wall sheet's footing): 12 x 16 cells per 4 m tile
    (stones about 33 x 25 cm), rounded pillowed faces, deep dark joints, per-stone tone, a little moss in the joints."""
    p = P[name]
    seed = p["seed"]
    nx, ny = 12, 16
    F1, F2, ID, dx, dy = voronoi(n, n, nx, ny, 0.38, seed, cell_aspect=(4.0 / ny) / (4.0 / nx), with_pos=True)
    cell_m = 4.0 / nx                                         # U cell width in metres; distances are in U-cell units
    edge = (F2 - F1) * 0.5 * cell_m                           # metres to the joint
    edge = edge + 0.006 * pnoise(n, n, 1.6, seed + 1)         # irregular, chipped joint line
    gap = np.clip(1 - (edge - 0.002) / 0.006, 0, 1)           # r2: ~0.5-1 cm dark joint (r1 read 4 cm)
    pillow = np.clip(edge / 0.08, 0, 1)                      # r2: rounder, bulging stones
    pillow = pillow * pillow * (3 - 2 * pillow)
    rng = np.random.default_rng(seed + 2)
    tone = rng.normal(0, 0.09, nx * ny)[ID]
    warm = rng.normal(0, 0.04, nx * ny)[ID]
    tilt_a = rng.normal(0, 1, (nx * ny, 2))
    v, u = np.mgrid[0:n, 0:n].astype(np.float64) / n
    tilt = (tilt_a[ID, 0] * dx + tilt_a[ID, 1] * dy) * 0.5 - 1.2 * F1 ** 2      # tilted, domed stone faces
    f = granite_fields(n, seed + 100)
    face_h = 0.12 * tilt + 0.35 * f["relief"] + 0.25 * (f["bump"] - 1.3 * f["chisel"]) + 0.5 * f["height"]
    height = 1.2 * pillow + face_h * pillow - 0.8 * f["pits"] - 1.5 * gap
    base = srgb(p["base"]) * np.ones((n, n, 1))
    base = base * (1 + tone)[..., None] * np.dstack([1 + warm, np.ones_like(warm), 1 - warm])
    col, cav = granite_colour(f, np.array([1.0, 1.0, 1.0]), srgb(P["Granite"]["dark"]), srgb(P["Granite"]["white"]),
                              srgb(P["Granite"]["stain"]), face_h)
    col = col * base
    # r2: the crest / cavity shading reads the stone FACE only (r1 fed it the deep joints, which smeared a 4 cm dark
    # band round every stone); rounded edges fall into shadow over the last ~2 cm; joints near black
    col = col * (0.62 + 0.38 * np.clip(edge / 0.035, 0, 1) ** 0.7)[..., None]   # r3: the sheet's dark stone rims
    moss_m = np.clip(pnoise(n, n, 1.8, seed + 3) - 0.3, 0, 1) * np.clip(1 - pillow, 0, 1) * (1 - gap)
    col = lerp(col, srgb(p["moss"]) * 0.8, np.clip(0.35 * moss_m, 0, 1)[..., None])
    col = contrast(col, 0.35)
    col = lerp(col, srgb(p["gap"]), gap[..., None])
    rough = 0.82 + 0.06 * np.tanh(f["relief"]) + 0.10 * gap + 0.05 * cav
    ao = np.clip(1 - 0.85 * gap - 0.35 * (1 - pillow) - 0.4 * cav, 0.08, 1)
    return save_set(name, col, height, 28.0, rough, ao, extra={"stones_per_tile": [nx, ny]})


# ------------------------------------------------------------------------------------------------ iron
def iron(name="Iron", n=1024):
    """Old forged iron over 2 m: hammer dishes, pitting, mill-scale mottle; bare iron metallic 0.95-1.0, rust
    patches metallic 0 (a hard mask: no partial-metal texels)."""
    p = P[name]
    seed = p["seed"]
    F1, F2, ID = voronoi(n, n, 64, 64, 0.45, seed)            # ~3 cm hammer dishes
    dish = F1 ** 2
    mottle = pnoise(n, n, 1.5, seed + 1)
    fine = pnoise(n, n, 0.5, seed + 2)
    pits = np.clip((pnoise(n, n, 0.45, seed + 3) - 1.9) * 2.0, 0, 1)
    rustn = pnoise(n, n, 1.9, seed + 4) + 0.45 * pnoise(n, n, 0.9, seed + 5)
    rust = (rustn > 1.35).astype(float)                         # hard mask
    rust_amt = np.clip((rustn - 1.35) * 1.5, 0, 1)
    bare = srgb(p["bare"]) * (1 + 0.10 * mottle + 0.04 * fine)[..., None]
    bare = lerp(bare, srgb("#252423"), np.clip(0.8 * pits, 0, 1)[..., None])
    rc = srgb(p["rust"]) * (1 + 0.15 * fine + 0.2 * rust_amt)[..., None]
    col = lerp(bare, rc, rust[..., None])
    height = -0.3 * dish + 0.05 * mottle + 0.03 * fine - 0.5 * pits + 0.25 * rust * (0.5 + 0.5 * fine)
    rough = np.where(rust > 0.5, 0.86 + 0.06 * np.tanh(fine), 0.50 + 0.08 * np.tanh(mottle) + 0.15 * pits)
    metal = np.where(rust > 0.5, 0.0, 0.975 + 0.025 * np.tanh(mottle))
    metal = np.where(rust > 0.5, 0.0, np.clip(metal, 0.95, 1.0))
    ao = np.clip(1 - 0.5 * pits - 0.4 * cavity(height, 3.0), 0.3, 1)
    return save_set(name, col, height, 4.0, rough, ao, metal)


# ------------------------------------------------------------------------------------------------ rope
def rope(name="Rope"):
    """Three-strand straw rope. U (1024 px) = 4 lay lengths along the rope, V (512 px) = once round it. Each
    strand turns once round the rope per lay, so strand boundaries are the lines frac(3 (v + 4 u)) = 0 (right-hand
    lay); the strand index repeats across both tile edges (12 u and 3 v are whole numbers of strands). Fibres follow
    each strand."""
    p = P[name]
    seed = p["seed"]
    w, h = SETS[name]["size"]
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    v /= h
    u /= w
    s = 3.0 * v + 12.0 * u
    strand = np.floor(s).astype(int) % 3
    fr = s - np.floor(s)
    prof = np.sin(np.pi * fr) ** 0.6
    # fibres run along each strand. pnoise's angle lives in normalised (u, v) tile space, where the strand lines
    # 3 v + 12 u = const run along (du, dv) = (1, -4)
    ang = np.arctan2(-4.0, 1.0)
    fib = pnoise(h, w, 0.8, seed + 1, angle=ang, aspect=12.0)
    fib2 = pnoise(h, w, 0.5, seed + 2, angle=ang + 0.2, aspect=8.0)
    coarse = pnoise(h, w, 1.6, seed + 3)
    tint = np.array([0.0, 0.05, -0.05])[strand]
    base = srgb(p["base"])
    lum = 0.80 + 0.22 * prof + 0.10 * fib + 0.06 * fib2 + 0.06 * coarse + tint
    col = base[None, None, :] * lum[..., None]
    col = lerp(col, srgb("#CDAE78"), np.clip(0.30 * (fib - 0.8), 0, 0.35)[..., None] * prof[..., None])
    col = lerp(col, srgb("#2E2216"), np.clip((1 - prof) ** 3 * 0.55, 0, 1)[..., None])
    hair = np.clip((pnoise(h, w, 0.4, seed + 4, angle=0.4, aspect=10.0) - 2.2) * 2.0, 0, 1)
    col = lerp(col, srgb("#D6BB88"), (0.6 * hair)[..., None])
    height = 1.0 * prof + 0.12 * fib + 0.05 * fib2 + 0.08 * hair
    rough = 0.86 + 0.05 * np.tanh(fib)
    ao = np.clip(0.35 + 0.65 * prof ** 0.6, 0, 1)
    _ = rng
    return save_set(name, col, height, 10.0, rough, ao, extra={"lays_per_tile_u": 4, "strands": 3})


# ------------------------------------------------------------------------------------------------ plaster + tile (kit 1)
# Ported VERBATIM from Scripts/dojo/kit1_textures.py (the judged kit-1 sets; that file cannot be imported because it
# writes kit 1's textures on import). _k1_pnoise is kit 1's pnoise, so the same seed gives the same pixels: the
# PlasterEarth and RoofTile outputs WERE byte-identical to T_DK_EarthPlaster / T_DK_RoofTile up to lib 1.0.0; r3 (lib 1.1)
# grades PlasterEarth (tint_k, median) and replaces the RoofTile generator (roof_tile below), so both now differ.
def _k1_pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0):
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0 * stretch_v
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0 * stretch_u
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    if fmin > 0:
        F[f < fmin] = 0
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def _k1_plaster(base_hex, n=2048, seed=101, streak_k=0.14, blotch_k=0.24, crack_k=0.6, line_k=0.05, vein_k=0.34,
                stain_k=0.40, cap=0.80, crack_cover=0.6, trowel_h=0.03, tint_k=(0.05, 0.12)):
    pn = _k1_pnoise
    v, u = np.mgrid[0:n, 0:n] / float(n)
    blotch = 0.6 * pn(n, n, 2.2, seed) + 0.4 * pn(n, n, 1.6, seed + 20)
    trowel = pn(n, n, 1.2, seed + 1, stretch_u=0.35)
    grit = pn(n, n, 0.35, seed + 2)
    streak = pn(n, n, 1.1, seed + 3, stretch_v=14.0)
    streak = np.clip(streak - 0.6, 0, None) * np.clip(0.5 + 0.6 * pn(n, n, 2.0, seed + 4), 0, 1)
    lines = np.zeros((n, n))
    wav = pn(1, n, 1.6, seed + 5)[0] * 0.004
    brk = np.clip(0.5 + 0.7 * pn(n, n, 1.5, seed + 6, stretch_u=6.0), 0, 1)
    for k in range(12):
        c = (k + 0.5) / 12.0
        d = np.abs(((v - c - wav[None, :]) + 0.5) % 1.0 - 0.5)
        lines = np.maximum(lines, np.exp(-(d / 0.0011) ** 2))
    lines *= brk
    rid = np.abs(pn(n, n, 1.4, seed + 7, fmin=0.02))
    cracks = np.clip(1.0 - rid / 0.035, 0, 1) * np.clip((pn(n, n, 2.4, seed + 8) - crack_cover) * 1.6, 0, 1)
    stains = np.clip(pn(n, n, 1.9, seed + 10) - 0.7, 0, 1) ** 0.8 * np.clip(0.4 + 0.6 * pn(n, n, 0.9, seed + 11), 0, 1)
    veins = np.clip(1.0 - np.abs(pn(n, n, 1.1, seed + 9, fmin=0.03)) / 0.06, 0, 1) * np.clip(
        0.3 + 0.7 * pn(n, n, 1.8, seed + 12), 0, 1)
    base = srgb(base_hex)
    lum = (1.0 + blotch_k * blotch + 0.03 * trowel + 0.018 * grit - streak_k * streak - line_k * lines
           - crack_k * cracks - vein_k * veins - stain_k * stains)
    dk = np.clip(-(blotch_k * blotch - streak_k * streak - vein_k * veins - stain_k * stains), 0, 1) * 2.0
    tint = np.dstack([1 + tint_k[0] * dk, 1 + 0.0 * dk, 1 - tint_k[1] * dk])   # r3: tint_k (kit 1: 0.05, 0.12)
    bc = base[None, None, :] * lum[..., None] * tint
    bc = bc * np.minimum(1.0, cap / np.maximum(bc.max(axis=2, keepdims=True), 1e-6))
    height = trowel_h * trowel + 0.012 * grit - 0.05 * cracks - 0.02 * lines
    rough = 0.90 + 0.03 * np.tanh(trowel) + 0.04 * streak
    ao = 1.0 - 0.35 * cracks - 0.10 * lines
    return bc, height, 3.0, rough, ao


def _k1_roof_tile(n=2048, seed=301):
    pn = _k1_pnoise
    base = srgb("#47484B")
    mottle = pn(n, n, 2.0, seed, fmin=0.25)
    fine = pn(n, n, 0.5, seed + 1)
    speck = (pn(n, n, 0.15, seed + 2) > 1.6).astype(float)
    bloom = np.clip(pn(n, n, 1.8, seed + 3, fmin=0.25) - 1.0, 0, 1)
    lum = 1.0 + 0.10 * mottle + 0.03 * fine - 0.2 * speck + 0.25 * bloom
    bc = base[None, None, :] * lum[..., None]
    height = 0.02 * fine + 0.03 * mottle
    wear = np.clip(pn(n, n, 1.2, seed + 4, fmin=0.25) - 0.9, 0, 1)
    bc = bc * (1 - 0.35 * wear[..., None]) + srgb("#7E7F80")[None, None, :] * 0.35 * wear[..., None]
    rough = 0.50 + 0.12 * np.tanh(mottle) + 0.16 * bloom + 0.18 * wear + 0.05 * np.tanh(fine)
    metal = np.clip(0.22 + 0.12 * np.tanh(mottle) - 0.25 * bloom - 0.25 * wear, 0, 1)
    return bc, height, 2.0, rough, None, metal


def plaster_earth():
    # kit 1's judged EarthPlaster generator and parameters; r2: only the base colour is re-measured against the
    # wall sheet under the library's studio rig (kit 1's #A48B6D rendered x0.77 dark and too saturated here; kit 1's
    # own T_DK_EarthPlaster is untouched)
    bc, h, s, r, ao = _k1_plaster(P["PlasterEarth"]["base"], seed=101, streak_k=0.14, blotch_k=0.22, crack_k=0.70, line_k=0.03,
                                  vein_k=0.16, stain_k=0.32, crack_cover=0.22, trowel_h=0.07,
                                  tint_k=P["PlasterEarth"]["tint_k"])
    bc = grade_median(bc, P["PlasterEarth"]["target"])      # r3: less chroma (UE: hue +11-13 deg toward orange)
    extra = {"source": "kit1_textures.plaster EarthPlaster params; r3: tint_k and median graded"}
    extra.update(_colour_stats(bc))
    return save_set("PlasterEarth", bc, h, s, r, ao, extra=extra)


def plaster_cream():
    # kit 1's plaster generator with the hall / storehouse cream (the hall sheet: finer veins, softer stains)
    p = P["PlasterCream"]
    bc, h, s, r, ao = _k1_plaster(p["base"], seed=p["seed"], streak_k=0.08, blotch_k=0.10, crack_k=0.55,
                                  line_k=0.02, vein_k=0.36, stain_k=0.14, crack_cover=0.35, trowel_h=0.05,
                                  tint_k=p["tint_k"])
    bc = grade_median(bc, p["target"])                      # r3: cream, not peach (UE shade read red, s 0.96)
    extra = {"source": "kit1_textures.plaster, cream parameters; r3: tint_k and median graded"}
    extra.update(_colour_stats(bc))
    return save_set("PlasterCream", bc, h, s, r, ao, extra=extra)


def roof_tile(n=2048, seed=301):
    """r3 (lib 1.1): no longer kit 1's verbatim set. The wall-cap and gate tiles red-shifted in UE (R/B 1.28-1.88
    against ~1.0) while the hall's read charcoal: warm bounce and the 2400 K gate lamps on a neutral / partly metallic
    tile. Now a neutral charcoal with a slight blue-black glaze (median R/B ~0.86), a glossier glaze (roughness ~0.4) so
    the tile rolls pick up a highlight from their own curvature, the silvery ibushi bloom kept, and a little bronze
    wear (instead of r2's pale grey patches)."""
    pn = _k1_pnoise
    mottle = pn(n, n, 2.0, seed, fmin=0.25)
    fine = pn(n, n, 0.5, seed + 1)
    speck = (pn(n, n, 0.15, seed + 2) > 1.6).astype(float)
    bloom = np.clip(pn(n, n, 1.8, seed + 3, fmin=0.25) - 1.0, 0, 1)
    wear = np.clip((pn(n, n, 1.2, seed + 4, fmin=0.25) - 1.2) * 1.5, 0, 1)
    base = srgb("#3F434B")
    lum = 1.0 + 0.07 * mottle + 0.03 * fine - 0.15 * speck
    bc = base[None, None, :] * lum[..., None]
    bc = lerp(bc, srgb("#5D636D") * np.ones((n, n, 3)), np.clip(0.45 * bloom, 0, 1))     # silvery bloom
    bc = lerp(bc, srgb("#6B5B48") * np.ones((n, n, 3)), np.clip(0.30 * wear, 0, 1))      # bronze wear
    bc = grade_median(bc, "#40434A")
    height = 0.02 * fine + 0.03 * mottle - 0.02 * wear
    rough = 0.40 + 0.08 * np.tanh(mottle) + 0.10 * bloom + 0.22 * wear + 0.04 * np.tanh(fine)
    metal = np.clip(0.20 + 0.10 * np.tanh(mottle) - 0.20 * bloom - 0.20 * wear, 0, 1)
    extra = {"source": "r3 own (was kit1_textures.roof_tile verbatim)", "median_r_over_b":
             round(float(np.median(bc[..., 0]) / max(np.median(bc[..., 2]), 1e-6)), 3)}
    extra.update(_colour_stats(bc))
    return save_set("RoofTile", bc, height, 2.0, rough, None, metal, extra=extra)


# ------------------------------------------------------------------------------------------------ lacquer
def lacquer(name="Lacquer", n=2048):
    """Aged urushi-style red-brown lacquer over 2 m (hero 10.24 px/cm): soft mottle, patchy craquelure (fine crack
    network), pale fine scratches, dull wear patches."""
    p = P[name]
    seed = p["seed"]
    rng = np.random.default_rng(seed)
    mottle = pnoise(n, n, 2.0, seed)
    fine = pnoise(n, n, 0.6, seed + 1)
    # r2: the taiko sheet's lacquer shows short cracks mostly along the staves (U) plus a sparse crackle network
    F1, F2, ID = voronoi(n, n, 110, 110, 0.45, seed + 2)          # ~1.8 cm crackle cells
    net = np.clip(1 - (F2 - F1) / 0.03, 0, 1) * np.clip((pnoise(n, n, 1.8, seed + 3) - 0.6) * 1.4, 0, 1)
    short = gblur(_dashes(n, n, rng, 2600, (6, 30), 0.55, 1), 0.5) * 1.5   # r3: r2's 0.12 spread read as grain
    crk = np.clip(np.maximum(net, short), 0, 1)
    scr = _dashes(n, n, rng, 2600, (8, 70), 0.6, 1)
    scr = np.maximum(scr, _dashes(n, n, rng, 500, (6, 40), 1.2, 1))
    wear = np.clip(pnoise(n, n, 1.6, seed + 4) - 1.0, 0, 1)
    base = srgb(p["base"])
    # r3: the r2 mottle read blotchy and the roughness wet: mottle 0.10 -> 0.035, craquelure lighter (0.75 -> 0.45),
    # satin roughness (0.30 -> 0.46 base), median graded to a browner, less saturated red-brown
    col = base[None, None, :] * (1 + 0.035 * mottle + 0.03 * fine)[..., None]
    col = lerp(col, srgb("#3A1A14"), np.clip(0.45 * crk, 0, 1)[..., None])
    col = lerp(col, srgb("#9A6A58"), np.clip(0.40 * scr, 0, 1)[..., None])
    col = lerp(col, col * 1.08 * np.array([1.0, 0.97, 0.97]), (0.3 * wear)[..., None])
    col = contrast(col, 0.25)
    col = grade_median(col, p["target"])
    height = 0.01 * mottle - 0.6 * crk - 0.25 * scr + 0.01 * fine
    rough = 0.46 + 0.04 * np.tanh(fine) + 0.15 * crk + 0.20 * scr + 0.08 * wear
    ao = np.clip(1 - 0.4 * crk, 0.3, 1)
    return save_set(name, col, height, 3.0, rough, ao, extra=_colour_stats(col))


# ------------------------------------------------------------------------------------------------ emissive
def glass_amber(name="GlassAmber"):
    """Emissive amber pane (UV 0-1 over one pane): a hotspot gradient from a 2700 K core to a deeper 2200 K amber at
    the frame, with a faint frosted-diffuser grain. BC doubles as the emissive colour."""
    p = P[name]
    w, h = SETS[name]["size"]
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    u = (u + 0.5) / w - 0.5
    v = (v + 0.5) / h - 0.5
    r = np.sqrt(u * u + (v * 1.05) ** 2) / 0.5                   # 0 centre .. 1 at the edge midpoints
    core = np.exp(-(r / 0.55) ** 2)
    k_core = kelvin_rgb(p["k_core"])
    k_edge = kelvin_rgb(p["k_edge"])
    # r2: amber, not peach. Rim = the 2200 K colour, core = 2700 K lifted 40 % toward white (the sheets' lamps read
    # pale yellow in the middle, amber at the frame); brightness falls to 60 % at the rim
    # r2: r1 read peach (blackbody hues ~28 deg + a white lift = pink-orange). The sheets' lamps sit at hue 36-42
    # deg: pale yellow-amber core, saturated amber mid, deep amber rim. The kelvin colours set the luminance step
    # (2700 K core -> 2200 K rim); the hue is pinned to amber.
    amber_core = np.array([1.0, 0.86, 0.45])     # r4: less blue (r3's glow still read peach at hue 25 deg)
    amber_mid = np.array([1.0, 0.66, 0.18])
    amber_rim = np.array([0.75, 0.36, 0.06])
    lk = (k_edge.mean() / k_core.mean())
    col = np.where((core > 0.5)[..., None], lerp(amber_mid, amber_core, np.clip((core - 0.5) / 0.5, 0, 1)[..., None]),
                   lerp(amber_rim, amber_mid, np.clip(core / 0.5, 0, 1)[..., None]))
    col = col * (lk + (1 - lk) * core)[..., None]
    grain = pnoise(h, w, 0.6, p["seed"]) * 0.025 + pnoise(h, w, 1.8, p["seed"] + 1) * 0.03
    col = col * (1 + grain)[..., None]
    # edge falloff into the frame (the muntins cast their own soft shadow)
    edge = np.clip(np.minimum(0.5 - np.abs(u), 0.5 - np.abs(v)) / 0.06, 0, 1)
    col = col * (0.55 + 0.45 * edge)[..., None]
    height = 0.02 * pnoise(h, w, 1.2, p["seed"] + 2)
    rough = 0.35 + 0.05 * np.tanh(grain * 20)
    return save_set(name, col, height, 1.0, rough, None, None,
                    extra={"core_kelvin": p["k_core"], "edge_kelvin": p["k_edge"],
                           "core_srgb": [int(round(x * 255)) for x in col[h // 2, w // 2]],
                           "edge_srgb": [int(round(x * 255)) for x in col[h // 2, 8]]})


def shoji_paper(name="ShojiPaper"):
    """r5 named variant: backlit shoji paper over ONE lattice cell (UV 0-1 from bar centre to bar centre). A bright
    honey-amber core in each cell falling to a darker amber where the paper meets the bars (the bars cover the outer
    ~15 %), faint washi fibres. Hue held at 29-36 deg everywhere (GlassAmber's 2200 K rim read salmon on the hall);
    the brightness falls to about 45 % at the bar line, so only the cell cores read bright. BC doubles as emission."""
    p = P[name]
    w, h = SETS[name]["size"]
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    u = (u + 0.5) / w - 0.5
    v = (v + 0.5) / h - 0.5
    # squircle distance: flat bright core, soft shoulder toward the bars
    r = (np.abs(u / 0.5) ** 4 + np.abs(v / 0.5) ** 4) ** 0.25
    core = np.clip(1.0 - (r - 0.35) / 0.65, 0.0, 1.0) ** 1.6
    c_core, c_mid, c_rim = srgb(p["core"]), srgb(p["mid"]), srgb(p["rim"])
    col = np.where((core > 0.5)[..., None], lerp(c_mid, c_core, np.clip((core - 0.5) / 0.5, 0, 1)[..., None]),
                   lerp(c_rim, c_mid, np.clip(core / 0.5, 0, 1)[..., None]))
    fib = pnoise(h, w, 2.4, p["seed"]) * 0.035 + pnoise(h, w, 0.7, p["seed"] + 1) * 0.025
    col = col * (1 + fib)[..., None]
    height = 0.015 * pnoise(h, w, 2.4, p["seed"] + 2)
    rough = 0.80 + 0.05 * np.tanh(fib * 20)
    lum = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]

    def hue(c):
        r_, g_, b_ = c
        mx, mn = max(c), min(c)
        return round(60.0 * (g_ - b_) / (mx - mn), 1) if mx == r_ and mx > mn else None
    cc, ce = col[h // 2, w // 2], col[h // 2, 4]
    return save_set(name, col, height, 1.0, rough, None, None,
                    extra={"core_srgb": [int(round(x * 255)) for x in cc], "edge_srgb": [int(round(x * 255)) for x in ce],
                           "core_hue_deg": hue(cc), "edge_hue_deg": hue(ce),
                           "edge_to_core_lum": round(float(lum[h // 2, 4] / lum[h // 2, w // 2]), 3)})


def vending_panel(name="VendingPanel"):
    """Backlit vending display diffuser (UV 0-1 over the display window, portrait 1:2): the modern sheet's pale
    cyan glow (blank: no text, no brands, no products), brighter centre, soft falloff to the frame, diffuser grain."""
    p = P[name]
    w, h = SETS[name]["size"]
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    u = (u + 0.5) / w - 0.5
    v = (v + 0.5) / h - 0.5
    r = np.sqrt((u / 0.5) ** 2 + (v / 0.5) ** 2 * 0.8)
    core = np.exp(-(r / 0.9) ** 2)
    rim = srgb("#1F7F93")          # r2: the sheet's display is saturated cyan, not white
    mid = srgb("#4FB3C4")
    hot = srgb("#A8E4EC")
    col = lerp(rim, mid, np.clip(core * 1.6, 0, 1)[..., None])
    col = lerp(col, hot, np.clip((core - 0.55) / 0.45, 0, 1)[..., None])
    grain = pnoise(h, w, 0.6, p["seed"]) * 0.02 + pnoise(h, w, 2.0, p["seed"] + 1) * 0.04
    col = col * (1 + grain)[..., None]
    edge = np.clip(np.minimum(0.5 - np.abs(u), 0.5 - np.abs(v)) / 0.04, 0, 1)
    col = col * (0.6 + 0.4 * edge)[..., None]
    height = 0.01 * pnoise(h, w, 1.0, p["seed"] + 2)
    rough = 0.25 + 0.0 * grain
    return save_set(name, col, height, 1.0, rough, None, None)


def wear_mask():
    w, h = WEARMASK["size"]
    a = pnoise(h, w, 1.5, 2101)
    b = pnoise(h, w, 0.6, 2102)
    m = 0.5 + 0.30 * a + 0.20 * b
    m = (m - m.min()) / (m.max() - m.min())                     # full range 0..1
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_DJ_WearMask_M.png", m)
    return {"set": "WearMask", "size_px": [w, h], "tile_m": WEARMASK["tile_m"], "texel_px_per_cm": 5.12,
            "mean": round(float(m.mean()), 3), "seam_ratio": seam_ratio(m)}


GENERATORS = {
    "TimberDark": lambda: timber("TimberDark"),
    "TimberDarkEnd": lambda: timber_end("TimberDarkEnd"),
    "TimberAged": lambda: timber("TimberAged"),
    "TimberAgedEnd": lambda: timber_end("TimberAgedEnd"),
    "Granite": granite,
    "GraniteRubble": granite_rubble,
    "Iron": iron,
    "Rope": rope,
    "PlasterCream": plaster_cream,
    "PlasterEarth": plaster_earth,
    "RoofTile": roof_tile,
    "Lacquer": lacquer,
    "GlassAmber": glass_amber,
    "VendingPanel": vending_panel,
    "ShojiPaper": shoji_paper,
    "WearMask": wear_mask,
}


def generate(only=None):
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / "textures_report.json"
    rep = json.loads(path.read_text()) if path.exists() else {}
    for name, fn in GENERATORS.items():
        if only and name not in only:
            continue
        t0 = time.time()
        rep[name] = fn()
        rep[name]["seconds"] = round(time.time() - t0, 1)
        print("TEX", name, json.dumps(rep[name]), flush=True)
    rep["_library_version"] = LIB_VERSION
    path.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    generate(only)
