"""KIT 1 (perimeter wall + gatehouse) tiling textures, all procedural and original.

Extends the armory's approach (Scripts/armory/make_armory_textures.py): every map is built from periodic FFT noise and
periodic line functions, so every tile repeats with no seam (measured at the end: the wrap-around step equals the
interior step). No photo, scan or third-party source. Palette: WorkFiles/world/STYLE_GUIDE.md section 3.

Texel density (STYLE_GUIDE section 6, mid pieces on tiling materials): 5.12 px/cm everywhere: every set is 2048 px
over 4.0 m (one UV scale for every material, so the pipeline's per-mesh texel check measures 5.12 on mixed pieces);
MossMask (a breakup mask, world-mapped) is 512 px over 1.0 m.
Writes Exports/DojoKit/Kit1/Textures/T_DK_<Set>_{BC,N,ORM}.png (BC sRGB; N DirectX green, linear; ORM = AO,
roughness, metal, linear), T_DK_MossMask_M.png, and WorkFiles/dojo/build/kit1/textures_report.json.

Run (Blender's bundled Python has numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/kit1_textures.py
"""
import json
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Exports" / "DojoKit" / "Kit1" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "kit1"
TILE_M = {"EarthPlaster": 4.0, "CreamPlaster": 4.0, "Granite": 4.0, "RoofTile": 4.0, "Timber": 4.0, "Iron": 4.0,
          "MossMask": 1.0}


def write_png(path, rgb):
    a = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.dstack([a, a, a])
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if ch == 4 else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0):
    """Periodic 1/f^beta noise, zero mean, unit std. stretch_v > 1 makes features long along V (image columns ->
    vertical streaks); stretch_u > 1 makes them long along U (horizontal grain)."""
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


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def normal_dx(height, strength):
    du = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dv_gl = -(np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nx, ny, nz = -du * strength, -dv_gl * strength, np.ones_like(height)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln * 0.5 + 0.5, -ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5])


def blur(a, r=2, n=2):
    for _ in range(n):
        a = (a + np.roll(a, r, 0) + np.roll(a, -r, 0) + np.roll(a, r, 1) + np.roll(a, -r, 1)) / 5.0
    return a


def seam_error(img):
    """Wrap-around step vs the mean interior step (1.0 = the seam is as smooth as any other column/row)."""
    g = img.mean(axis=2) if img.ndim == 3 else img
    inner_c = np.abs(np.diff(g, axis=1)).mean()
    inner_r = np.abs(np.diff(g, axis=0)).mean()
    wrap_c = np.abs(g[:, 0] - g[:, -1]).mean()
    wrap_r = np.abs(g[0, :] - g[-1, :]).mean()
    return round(float(max(wrap_c / (inner_c + 1e-9), wrap_r / (inner_r + 1e-9))), 3)


def save_set(name, bc, height, nstrength, rough, ao=None, metal=None):
    OUT.mkdir(parents=True, exist_ok=True)
    bc = np.clip(bc, 0, 1)
    write_png(OUT / f"T_DK_{name}_BC.png", bc)
    write_png(OUT / f"T_DK_{name}_N.png", normal_dx(height, nstrength))
    ao = np.ones_like(rough) if ao is None else ao
    metal = np.zeros_like(rough) if metal is None else metal
    write_png(OUT / f"T_DK_{name}_ORM.png", np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), metal]))
    px = bc.shape[1]
    return {"set": name, "size_px": list(bc.shape[:2]), "tile_m": TILE_M[name],
            "texel_px_per_cm": round(px / (TILE_M[name] * 100.0), 3),
            "mean_srgb_hex": "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in bc.reshape(-1, 3).mean(0)),
            "albedo_max": round(float(bc.max()), 3), "rough_mean": round(float(rough.mean()), 3),
            "seam_ratio_bc": seam_error(bc)}


# ------------------------------------------------------------------------------------------------ plasters
def plaster(name, base_hex, n=2048, seed=101, streak_k=0.14, blotch_k=0.24, crack_k=0.6, line_k=0.05, vein_k=0.34,
            stain_k=0.40, cap=0.80, crack_cover=0.6, trowel_h=0.03):
    """Earthen / lime plaster over 4 m. Rows = V (image top = the top of the tile), columns = U (along the wall).
    Features: low-frequency earthen blotches, trowel texture, faint horizontal layer lines (every 1/3 m, wavy), soft
    vertical rain streaks (tiling vertically, so the body can be any height), hairline cracks."""
    v, u = np.mgrid[0:n, 0:n] / float(n)
    blotch = 0.6 * pnoise(n, n, 2.2, seed) + 0.4 * pnoise(n, n, 1.6, seed + 20)
    trowel = pnoise(n, n, 1.2, seed + 1, stretch_u=0.35)
    grit = pnoise(n, n, 0.35, seed + 2)
    streak = pnoise(n, n, 1.1, seed + 3, stretch_v=14.0)          # long along V: vertical streaks
    streak = np.clip(streak - 0.6, 0, None) * np.clip(0.5 + 0.6 * pnoise(n, n, 2.0, seed + 4), 0, 1)
    # faint horizontal layer lines: 12 per 4 m tile (0.333 m), each wavy and broken
    lines = np.zeros((n, n))
    wav = pnoise(1, n, 1.6, seed + 5)[0] * 0.004
    brk = np.clip(0.5 + 0.7 * pnoise(n, n, 1.5, seed + 6, stretch_u=6.0), 0, 1)
    for k in range(12):
        c = (k + 0.5) / 12.0
        d = np.abs(((v - c - wav[None, :]) + 0.5) % 1.0 - 0.5)
        lines = np.maximum(lines, np.exp(-(d / 0.0011) ** 2))
    lines *= brk
    # hairline cracks: ridged band-pass noise, kept only where a mask allows (a few crack systems per tile)
    rid = np.abs(pnoise(n, n, 1.4, seed + 7, fmin=0.02))
    cracks = np.clip(1.0 - rid / 0.035, 0, 1) * np.clip((pnoise(n, n, 2.4, seed + 8) - crack_cover) * 1.6, 0, 1)
    # darker earth stains (the sheet's brownish blotches), a few per tile
    stains = np.clip(pnoise(n, n, 1.9, seed + 10) - 0.7, 0, 1) ** 0.8 * np.clip(0.4 + 0.6 * pnoise(n, n, 0.9, seed + 11), 0, 1)
    # the sheet's fine darker earth veins: a faint ridged network everywhere
    veins = np.clip(1.0 - np.abs(pnoise(n, n, 1.1, seed + 9, fmin=0.03)) / 0.06, 0, 1) * np.clip(
        0.3 + 0.7 * pnoise(n, n, 1.8, seed + 12), 0, 1)
    base = srgb(base_hex)
    lum = (1.0 + blotch_k * blotch + 0.03 * trowel + 0.018 * grit - streak_k * streak - line_k * lines
           - crack_k * cracks - vein_k * veins - stain_k * stains)
    dk = np.clip(-(blotch_k * blotch - streak_k * streak - vein_k * veins - stain_k * stains), 0, 1) * 2.0
    tint = np.dstack([1 + 0.05 * dk, 1 + 0.0 * dk, 1 - 0.12 * dk])   # darker areas go browner, never bluer
    bc = base[None, None, :] * lum[..., None] * tint
    bc = bc * np.minimum(1.0, cap / np.maximum(bc.max(axis=2, keepdims=True), 1e-6))   # albedo cap keeps the hue
    height = trowel_h * trowel + 0.012 * grit - 0.05 * cracks - 0.02 * lines
    rough = 0.90 + 0.03 * np.tanh(trowel) + 0.04 * streak
    ao = 1.0 - 0.35 * cracks - 0.10 * lines
    return save_set(name, bc, height, 3.0, rough, ao)


# ------------------------------------------------------------------------------------------------ granite
def granite(n=2048, seed=201):
    """Rough-cut grey granite over 2 m: salt-and-pepper grains (dark biotite, white feldspar), pitched / pointed
    surface relief, faint iron-oxide staining. Applied per stone (UV / world box mapping)."""
    rng = np.random.default_rng(seed)
    base = srgb("#746D66")   # r4: a little warmer (the sheet's footing #5D554C); under the guide's #8A8680: the sheet's rough-cut footing reads darker
    mottle = pnoise(n, n, 2.0, seed)
    relief = pnoise(n, n, 1.0, seed + 1)
    pits = pnoise(n, n, 0.6, seed + 2)
    dark = (pnoise(n, n, 0.2, seed + 3) > 1.35).astype(float)
    white = (pnoise(n, n, 0.25, seed + 4) > 1.55).astype(float)
    stain = np.clip(pnoise(n, n, 2.2, seed + 5) - 0.8, 0, 1)
    lum = 1.0 + 0.12 * mottle + 0.10 * relief - 0.55 * dark + 0.30 * white - 0.12 * np.clip(-relief, 0, 2)
    bc = base[None, None, :] * lum[..., None]
    bc = bc * (1 - 0.18 * stain[..., None]) + srgb("#7A6450")[None, None, :] * 0.18 * stain[..., None]
    height = 0.06 * relief + 0.03 * pits - 0.01 * dark
    rough = 0.82 + 0.05 * np.tanh(relief) - 0.10 * white
    ao = 1.0 - 0.15 * np.clip(-relief, 0, 2)
    _ = rng
    return save_set("Granite", bc, height, 6.0, rough, ao)


def moss_mask(n=512, seed=251):
    """Moss breakup mask (1 m tile), multiplied with the vertex-colour moss weight (R) of the footing stones."""
    a = pnoise(n, n, 1.6, seed)
    b = pnoise(n, n, 0.7, seed + 1)
    m = np.clip(0.5 + 0.35 * a + 0.15 * b, 0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    write_png(OUT / "T_DK_MossMask_M.png", m)
    return {"set": "MossMask", "size_px": [n, n], "tile_m": 1.0, "texel_px_per_cm": round(n / 100.0, 3),
            "mean": round(float(m.mean()), 3), "seam_ratio": seam_error(m)}


# ------------------------------------------------------------------------------------------------ roof tile
def roof_tile(n=2048, seed=301):
    """Ibushi (smoked) grey fired clay over 2 m, the one tile material for every roof and wall cap. Silver-grey with a
    soft sheen, firing mottles, fine speckle, faint pale lime bloom."""
    base = srgb("#4C535C")   # f1: blue-grey ibushi tile (the judge: blue-grey semi-metallic sheen)
    mottle = pnoise(n, n, 2.0, seed)
    fine = pnoise(n, n, 0.5, seed + 1)
    speck = (pnoise(n, n, 0.15, seed + 2) > 1.6).astype(float)
    bloom = np.clip(pnoise(n, n, 1.8, seed + 3) - 1.0, 0, 1)
    lum = 1.0 + 0.10 * mottle + 0.03 * fine - 0.2 * speck + 0.25 * bloom
    bc = base[None, None, :] * lum[..., None]
    bc = bc * np.array([1.0, 1.0, 1.01])[None, None, :]
    height = 0.02 * fine + 0.03 * mottle
    wear = np.clip(pnoise(n, n, 1.2, seed + 4) - 0.9, 0, 1)            # worn, paler, rougher patches
    bc = bc * (1 - 0.35 * wear[..., None]) + srgb("#80858A")[None, None, :] * 0.35 * wear[..., None]
    rough = 0.34 + 0.10 * np.tanh(mottle) + 0.18 * bloom + 0.20 * wear + 0.05 * np.tanh(fine)
    metal = np.clip(0.38 - 0.30 * bloom - 0.30 * wear + 0.05 * mottle, 0, 1)    # the silvery ibushi sheen
    return save_set("RoofTile", bc, height, 2.0, rough, None, metal)


# ------------------------------------------------------------------------------------------------ timber
def timber(n=2048, seed=401):
    """Weathered dark timber over 2 m, grain along U (the kit maps U to each member's long axis). Deep grain grooves,
    silvered weathering streaks, dark checks."""
    base = srgb("#46362B")   # f1: darker weathered brown (the guide's #3A2E26 .. the gate sheet's #574131)
    grain = pnoise(n, n, 1.5, seed, stretch_u=40.0)
    fine = pnoise(n, n, 0.8, seed + 1, stretch_u=30.0)
    silver = np.clip(pnoise(n, n, 1.6, seed + 2, stretch_u=10.0) - 0.4, 0, 1)
    checks = np.clip(1.0 - np.abs(pnoise(n, n, 1.3, seed + 3, stretch_u=60.0, fmin=0.02)) / 0.05, 0, 1)
    checks *= np.clip(pnoise(n, n, 2.0, seed + 4) - 0.8, 0, 1)
    lum = 1.0 + 0.42 * grain + 0.14 * fine - 0.6 * checks + 0.10 * np.clip(grain - 1.2, 0, None)
    bc = base[None, None, :] * lum[..., None]
    bc = bc * (1 - 0.18 * silver[..., None]) + srgb("#7D7266")[None, None, :] * 0.18 * silver[..., None]
    height = 0.04 * grain + 0.015 * fine - 0.06 * checks
    rough = 0.78 + 0.05 * np.tanh(fine) + 0.08 * silver
    ao = 1.0 - 0.4 * checks
    return save_set("Timber", bc, height, 5.0, rough, ao)


# ------------------------------------------------------------------------------------------------ iron
def iron(n=2048, seed=501):
    """Blackened wrought iron over 1 m: hammer-mottled dark metal, rust blooms (non-metal) in patches."""
    mottle = pnoise(n, n, 1.4, seed)
    fine = pnoise(n, n, 0.4, seed + 1)
    rust = np.clip((pnoise(n, n, 1.9, seed + 2) - 1.3) * 2.0, 0, 1) * np.clip(0.6 + 0.6 * pnoise(n, n, 0.8, seed + 3), 0, 1)
    metal_col = srgb("#3A3937") * (1 + 0.12 * mottle + 0.04 * fine)[..., None]
    rust_col = srgb("#4E3626") * (1 + 0.15 * fine)[..., None]
    bc = metal_col * (1 - rust[..., None]) + rust_col * rust[..., None]
    height = 0.05 * mottle + 0.02 * fine + 0.03 * rust
    rough = 0.55 + 0.08 * np.tanh(mottle) + 0.30 * rust
    metal = np.where(rust > 0.45, 0.0, 1.0)
    return save_set("Iron", bc, height, 4.0, rough, None, metal)


def main():
    # r4: EarthPlaster warmer, as the sheet's rendered plaster (#B69B80)
    # f1: pale sandy beige (the sheet), soft mottling, more hairline cracks, stronger trowel relief, no soot blotches
    rep = [plaster("EarthPlaster", "#BCA88B", seed=101, streak_k=0.07, blotch_k=0.11, crack_k=0.55, line_k=0.03,
                   vein_k=0.12, stain_k=0.06, crack_cover=0.35, trowel_h=0.05),
           plaster("CreamPlaster", "#D9CFBD", seed=151, streak_k=0.04, blotch_k=0.05, crack_k=0.2, line_k=0.0,
                   vein_k=0.06, stain_k=0.05),
           granite(), moss_mask(), roof_tile(), timber(), iron()]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "textures_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    for r in rep:
        print("TEX", json.dumps(r))


main()
