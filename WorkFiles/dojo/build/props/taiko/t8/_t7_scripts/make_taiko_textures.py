"""Kit 6 taiko set (drum, stand, sticks): procedural tiling textures, all OUR OWN (numpy FFT noise, no scans).

Every map is built from periodic FFT noise and wrapped line stamps, so each tile repeats with no seam (the seam test
in the report measures it). Sizes are powers of two. Texel density: 2048 px over 2.0 m = 10.24 px/cm for the drum,
hide and stand sets, 1024 px over 1.0 m = 10.24 px/cm for the stick wood and iron (the drum is a hero piece, see
BUILD_NOTES; the style guide's 5.12 px/cm is the floor for hero/near pieces).

Grain / fibre direction runs along U (texture columns) in every wood set: the build script maps U along the drum axis,
along each beam and along the stick.

Writes Exports/DojoKit/Props/taiko/Textures/T_DKP_Taiko_<Set>_{BC,N,ORM}.png (BC sRGB; N DirectX green-flipped,
linear; ORM = AO, roughness, metallic, linear) and WorkFiles/dojo/build/props/taiko/textures_report.json.

Generic vs unique (for the later look pass that unifies shared materials):
  Timber, Iron, StickWood  -> GENERIC (dark weathered timber, wrought iron, worn pale timber)
  Lacquer, Hide            -> UNIQUE to the taiko

Run: py Scripts/dojo/props/taiko/make_taiko_textures.py [--only Lacquer,Hide]   (system Python 3.12 + numpy)
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko"
ARGS = sys.argv[1:]
ONLY = set(ARGS[ARGS.index("--only") + 1].split(",")) if "--only" in ARGS else None


# --------------------------------------------------------------------------- helpers (copied from kit 2's
# make_ground_textures.py, which this run may read but not edit)

def write_png(path, rgb):
    a = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if ch == 4 else 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def pnoise(h, w, beta, seed, stretch_u=1.0, stretch_v=1.0, fmin=0.0, fmax=None):
    """Periodic 1/f^beta noise, zero mean, unit std (rows = v, columns = u). stretch_u > 1 elongates features along u."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h / 256.0 * stretch_v
    fu = np.fft.fftfreq(w)[None, :] * w / 256.0 * stretch_u
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / np.power(f, beta)
    if fmin > 0:
        F[f < fmin] = 0
    if fmax is not None:
        F[f > fmax] = 0
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-9)


def blur(a, radius):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * radius) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def srgb(hexstr):
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


GOLD_HSV = (7.0, 0.85, 0.72)   # t7 (judge r6 item 3: the gold zone rendered a little dark and saturated, luminance about
#   128 / s 0.41 against the photo's 157 / 0.32): saturation x 1.25 -> 0.85, value x 0.575 -> 0.72, tuned on the t7
#   renders (t7/judge_style_metrics.json gold_front_centre, t7/gold_sample_*.json). t6 (judge t5 item 3):
GOLD_TINT0 = 0.88   # t7: the gold's linear-light share where the ramp proper starts (0.12 d under the band): the
#   photo's warm cream right under the band (rendered luminance about 200, saturation 0.10-0.14; tuned on t7 renders)
#   (t6 note:) hue shift (deg), saturation and value factors for the gold. The
#   judge's estimate (+6 deg, x 0.70, x 0.88) rendered (215, 199, 171), far too pale under the photo-studio light; these
#   were found by re-rendering drum_front_standing_photo and sampling (t6/gold_sample.py; see gold_sample_*.json): mid gold vs
#   the judge's photo sample (186, 158, 115), the classed gold band vs the photo's (172, 146, 107), both within +-8


def gold_adj(lin, dh=None, ks=None, kv=None):
    """t6: shift a linear RGB gold in sRGB HSV (hue + dh deg, saturation x ks, value x kv); returns linear RGB."""
    import colorsys
    dh = GOLD_HSV[0] if dh is None else dh
    ks = GOLD_HSV[1] if ks is None else ks
    kv = GOLD_HSV[2] if kv is None else kv
    hh, ss, vv = colorsys.rgb_to_hsv(*[float(x) for x in to_srgb(lin)])
    r_, g_, b_ = colorsys.hsv_to_rgb((hh + dh / 360.0) % 1.0, ss * ks, vv * kv)
    return to_lin(np.array([r_, g_, b_]))


def normal_dx(height_m, px_m):
    du = (np.roll(height_m, -1, 1) - np.roll(height_m, 1, 1)) / (2 * px_m)
    dv = -(np.roll(height_m, -1, 0) - np.roll(height_m, 1, 0)) / (2 * px_m)
    nx, ny, nz = -du, -dv, np.ones_like(height_m)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln * 0.5 + 0.5, -ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5])   # DX: green flipped


def seam_score(a):
    a = a.mean(2) if a.ndim == 3 else a
    rows = np.abs(a[0] - a[-1]).mean() / (np.abs(np.diff(a, axis=0)).mean() + 1e-12)
    cols = np.abs(a[:, 0] - a[:, -1]).mean() / (np.abs(np.diff(a, axis=1)).mean() + 1e-12)
    return round(float(rows), 3), round(float(cols), 3)


def ao_from_height(height_m, px_m, radius_px=6, strength=1.0):
    """Cheap cavity AO: how far below its blurred neighbourhood each texel sits (periodic)."""
    d = height_m - blur(height_m, radius_px)
    s = d.std() + 1e-12
    return np.clip(1.0 + strength * 0.25 * np.clip(d / s, -4, 0), 0.4, 1.0)


def stamp_lines(h, w, count, seed, len_px=(10, 80), width_px=(1.0, 2.0), angle_deg=(0.0, 12.0), axis="u"):
    """Wrapped short straight scratches (anti-aliased), returned as a 0-1 mask. axis 'u' = mostly along the columns."""
    rng = np.random.default_rng(seed)
    m = np.zeros((h, w))
    for _ in range(count):
        L = rng.uniform(*len_px)
        wd = rng.uniform(*width_px)
        ang = np.radians(rng.normal(angle_deg[0], angle_deg[1]))
        if axis == "v":
            ang += np.pi / 2
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        dx, dy = np.cos(ang), np.sin(ang)
        n = int(L * 1.5) + 2
        t = np.linspace(-L / 2, L / 2, n)
        amp = rng.uniform(0.4, 1.0)
        # taper both ends
        taper = np.sin(np.linspace(0, np.pi, n)) ** 0.5
        for k in range(n):
            x = cx + t[k] * dx
            y = cy + t[k] * dy
            r = int(np.ceil(wd)) + 1
            xi = np.arange(int(x) - r, int(x) + r + 1)
            yi = np.arange(int(y) - r, int(y) + r + 1)
            X, Y = np.meshgrid(xi, yi)
            d = np.hypot(X - x, Y - y)
            val = np.clip(1.0 - d / (wd * 0.5 + 0.5), 0, 1) * amp * taper[k]
            m[Y % h, X % w] = np.maximum(m[Y % h, X % w], val)
    return m


REPORT = {}


def save_set(name, bc_srgb, height_m, rough, px_m, ao=None, metal=0.0, extra=None):
    OUT.mkdir(parents=True, exist_ok=True)
    bc_srgb = np.clip(bc_srgb, 0, 1)
    nrm = normal_dx(height_m, px_m)
    patch = (extra or {}).pop("_patch_normals", None)
    if patch:   # r3: a periodic patch inside an atlas gets its own (wrapping) normals, so its lathe seam is clean
        r0, c0, ph = patch
        nrm[r0:r0 + ph.shape[0], c0:c0 + ph.shape[1]] = normal_dx(ph, px_m)
    ao = np.ones_like(rough) if ao is None else ao
    metal_map = metal if isinstance(metal, np.ndarray) else np.full_like(rough, metal)
    orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), np.clip(metal_map, 0, 1)])
    write_png(OUT / f"T_DKP_Taiko_{name}_BC.png", bc_srgb)
    write_png(OUT / f"T_DKP_Taiko_{name}_N.png", nrm)
    write_png(OUT / f"T_DKP_Taiko_{name}_ORM.png", orm)
    ang = np.degrees(np.arccos(np.clip(nrm[..., 2] * 2 - 1, -1, 1)))
    rep = {"size_px": [int(bc_srgb.shape[1]), int(bc_srgb.shape[0])],
           "tile_m": [round(bc_srgb.shape[1] * px_m, 4), round(bc_srgb.shape[0] * px_m, 4)],
           "px_per_cm": round(0.01 / px_m, 3), "source": "own procedural (numpy)",
           "mean_srgb_8bit": [int(round(float(x) * 255)) for x in bc_srgb.reshape(-1, 3).mean(0)],
           "albedo_max_srgb": round(float(bc_srgb.max()), 3),
           "rough_mean": round(float(np.clip(rough, 0.02, 1).mean()), 3), "ao_mean": round(float(ao.mean()), 3),
           "metal_mean": round(float(metal_map.mean()), 3),
           "normal_tilt_deg_mean_p95": [round(float(ang.mean()), 2), round(float(np.percentile(ang, 95)), 2)],
           "seam_score_bc_rows_cols": seam_score(bc_srgb), "seam_score_n_rows_cols": seam_score(nrm)}
    if extra:
        rep.update(extra)
    REPORT[name] = rep
    print(name, json.dumps(rep))



# --------------------------------------------------------------------------- f1 helpers

sys.path.insert(0, str(Path(__file__).resolve().parent))
import taiko_uv as UVL  # noqa: E402


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def crackle(h, w, cells_u, cells_v, seed, warp=0.18):
    """Periodic anisotropic Voronoi (craquelure). Returns (distance in PIXELS to the nearest cell border, F1 in cell
    units, a per-cell random value). Cells are cells_u across the width and cells_v down the height, so with fewer
    cells along u they are elongated along u (the drum axis). The border distance is measured in pixel space."""
    rng = np.random.default_rng(seed)
    jx = rng.uniform(0.1, 0.9, (cells_v, cells_u))
    jy = rng.uniform(0.1, 0.9, (cells_v, cells_u))
    cval = rng.uniform(0, 1, (cells_v, cells_u))
    su, sv = w / cells_u, h / cells_v                      # px per cell
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    wu = pnoise(h, w, 1.6, seed + 1, fmin=0.06) * warp
    wv = pnoise(h, w, 1.6, seed + 2, fmin=0.06) * warp
    cu = (xx + 0.5) / su + wu
    cv = (yy + 0.5) / sv + wv
    ix, iy = np.floor(cu).astype(np.int64), np.floor(cv).astype(np.int64)
    b0, b1 = np.full((h, w), 1e9), np.full((h, w), 1e9)
    p1x, p1y, p2x, p2y = (np.zeros((h, w)) for _ in range(4))
    val = np.zeros((h, w))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = ix + dx, iy + dy
            px_ = nx + jx[ny % cells_v, nx % cells_u]
            py_ = ny + jy[ny % cells_v, nx % cells_u]
            d = (cu - px_) ** 2 + (cv - py_) ** 2
            c1 = d < b0
            c2 = (~c1) & (d < b1)
            b1 = np.where(c1, b0, np.where(c2, d, b1))
            p2x = np.where(c1, p1x, np.where(c2, px_, p2x))
            p2y = np.where(c1, p1y, np.where(c2, py_, p2y))
            b0 = np.where(c1, d, b0)
            p1x = np.where(c1, px_, p1x)
            p1y = np.where(c1, py_, p1y)
            val = np.where(c1, cval[ny % cells_v, nx % cells_u], val)
    # distance to the bisector of p1, p2 measured in pixel space
    nxv, nyv = p2x - p1x, p2y - p1y
    c = 0.5 * ((p2x ** 2 + p2y ** 2) - (p1x ** 2 + p1y ** 2))
    num = np.abs(nxv * cu + nyv * cv - c)
    den = np.sqrt((nxv / su) ** 2 + (nyv / sv) ** 2) + 1e-9
    return num / den, np.sqrt(b0), val


def col_gauss(w, centre_u, width_u):
    """Periodic Gaussian bump along U (columns), shape (1, w)."""
    u = (np.arange(w) + 0.5) / w
    d = (u - centre_u + 0.5) % 1.0 - 0.5
    return np.exp(-(d / width_u) ** 2)[None, :]


# --------------------------------------------------------------------------- sets (f1)

def lacquer_f1(n=2048, seed=1101):
    """Red-brown urushi-style lacquer (f1, blind judge): warmer orange-red brown, satin (roughness about 0.40, no clear
    coat), a craquelure crackle elongated along the drum axis (normal + roughness), worn highlights on the bulge,
    edge wear next to both hide collars, no round blotches."""
    px = UVL.LAC_TILE / n
    base = to_lin(srgb("#3F1607"))   # f1 t1: #561F0D rendered 98,47,36 vs the sheet 72,34,21
    warm = to_lin(srgb("#5C250D"))          # thinned lacquer on the worn bulge
    wood = to_lin(srgb("#6E4226"))          # wood / ground coat showing through at worn edges and scratches
    dark = to_lin(srgb("#1E0904"))          # crack lines
    grain = pnoise(n, n, 1.2, seed + 1, stretch_u=28.0, fmin=0.08)
    streak = pnoise(n, n, 1.6, seed, stretch_u=5.0, fmin=0.05)   # soft variation along the axis, no round blotches
    fine = pnoise(n, n, 0.7, seed + 2, stretch_u=6.0)
    # craquelure: cells about 5 cm along the axis and 1.8 cm around (tile 2 m)
    bd, f1, cval = crackle(n, n, 38, 110, seed + 3)
    gate = np.clip(pnoise(n, n, 1.6, seed + 4, fmin=0.05) * 0.35 + 0.75, 0.35, 1.0)
    crack = np.clip(1.0 - bd / 1.3, 0, 1) * gate
    # position-aware wear (see taiko_uv): collars at x = +-X_COLLAR, the bulge at x = 0
    cu = [UVL.LAC_U0 + s * UVL.X_COLLAR / UVL.LAC_TILE for s in (1, -1)]
    edge = np.maximum(col_gauss(n, cu[0], 0.024), col_gauss(n, cu[1], 0.024))
    edge_n = np.clip(0.55 + 0.6 * pnoise(n, n, 1.3, seed + 8, fmin=0.08), 0, 1)
    wear_edge = np.clip(edge * edge_n * 1.3, 0, 1)
    bulge = col_gauss(n, UVL.LAC_U0, 0.10) * np.clip(0.45 + 0.5 * pnoise(n, n, 1.7, seed + 9, stretch_u=3.0,
                                                                           fmin=0.04), 0, 1)
    scr = stamp_lines(n, n, 1100, seed + 6, len_px=(12, 110), width_px=(0.9, 2.2), angle_deg=(0.0, 8.0))
    scr2 = stamp_lines(n, n, 220, seed + 7, len_px=(6, 40), width_px=(0.8, 1.6), angle_deg=(0.0, 60.0))
    scratches = np.clip(np.maximum(scr, scr2 * 0.8) * (0.7 + 0.8 * np.clip(wear_edge + bulge, 0, 1)), 0, 1)
    lum = 1.0 + 0.05 * streak + 0.05 * grain + 0.03 * fine + 0.06 * (cval - 0.5)
    col = base[None, None, :] * lum[..., None]
    b = (0.35 * bulge)[..., None]
    col = col * (1 - b) + warm[None, None, :] * b * lum[..., None]
    we = (0.55 * wear_edge)[..., None]
    col = col * (1 - we) + wood[None, None, :] * we * lum[..., None]
    s = (0.35 * scratches)[..., None]
    col = col * (1 - s) + wood[None, None, :] * 1.05 * s
    c = (0.85 * crack)[..., None]
    col = col * (1 - c) + dark[None, None, :] * c
    height = (0.00006 * np.clip(f1, 0, 1) - 0.00030 * crack - 0.00012 * scratches + 0.00003 * grain
              - 0.00008 * wear_edge)
    rough = (0.38 + 0.04 * fine + 0.03 * streak + 0.22 * crack + 0.14 * scratches + 0.12 * wear_edge
             - 0.04 * bulge)
    ao = ao_from_height(height, px, 4, 0.8)
    save_set("Lacquer", to_srgb(col), height, np.clip(rough, 0.3, 0.8), px, ao, 0.0,
             {"use": "drum body", "kind": "UNIQUE (collar edge wear baked at the drum's collar U columns)",
              "crackle_cells_uv": [38, 110]})


def lacquer(n=2048, seed=1811):
    """r2 (2026-09-28, prop material pass): the taiko body lacquer, built with the SHARED LIBRARY's generator
    primitives (Scripts/dojo/materials/dojo_tex_gen: pnoise, voronoi, _dashes, gblur) and the library's Lacquer recipe
    (craquelure network + short cracks along the staves + pale scratches), retuned to the judges' notes: warmer
    red-brown (hue about 15 deg, the sheet's lower body measured 74,35,22), SATIN not wet (roughness about 0.5, the
    library set is 0.33), NO water-spot blotches (the library's 0.10 low-frequency mottle and its contrast stretch are
    dropped: large-scale luminance std is capped), craquelure visible from mid distance, worn lighter highlights on
    the bulge (U of x = 0) and edge wear next to both hide collars. Tile 2 m, 10.24 px/cm (library hero density).
    The library set itself is untouched (T_DJ_Lacquer_* stays as it is for other users)."""
    sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
    import dojo_tex_gen as tg                     # numpy-only library generator (read only)
    px = UVL.LAC_TILE / n
    rng = np.random.default_rng(seed)
    base = to_lin(srgb("#391306"))                # warm red-brown; t2: #4A1F0E rendered 106,61,50 vs the sheet 76,37,23
    warm = to_lin(srgb("#58240F"))                # thinned, rubbed lacquer on the bulge
    wood = to_lin(srgb("#6E4226"))                # ground coat showing through at worn edges
    dark = to_lin(srgb("#170603"))                # crack lines
    pale = to_lin(srgb("#8C5B45"))                # pale fine scratches (library colour, darker)
    stave = tg.pnoise(n, n, 1.2, seed + 1, angle=0.0, aspect=18.0)   # faint lengthwise stave streaks, no blotches
    fine = tg.pnoise(n, n, 0.6, seed + 2)
    # craquelure: library-style Voronoi network (about 1.8 x 1.8 cm cells), gated so it is patchy, plus dense short
    # cracks mostly along U (the drum axis): the sheet's lacquer reads as many short dark lengthwise cracks
    F1, F2, _ID = tg.voronoi(n, n, 110, 110, 0.45, seed + 3)
    gate = np.clip((tg.pnoise(n, n, 1.8, seed + 4) + 0.5) * 0.9, 0, 1)
    net = np.clip(1 - (F2 - F1) / 0.040, 0, 1) ** 1.5 * gate      # t4: wider, so it reads at sheet distance
    # r2 t2: t1's 5200 soft 2 px dashes read as brushed hair; fewer, longer, crisp 1 px cracks with a wiggle
    short = tg.gblur(tg._dashes(n, n, rng, 1700, (30, 120), 0.08, 2), 0.45) * 1.9   # t4: 2 px (2 mm) cracks
    crk = np.clip(np.maximum(0.80 * net, short), 0, 1)
    scr = tg._dashes(n, n, rng, 2400, (8, 60), 0.5, 1)
    scr = np.maximum(scr, 0.7 * tg._dashes(n, n, rng, 400, (6, 40), 1.2, 1))
    # position-aware wear (taiko_uv): collars at x = +-X_COLLAR, the bulge at x = 0
    cu = [UVL.lac_u(s_ * UVL.X_COLLAR) for s_ in (1, -1)]   # t4: U by arc length along the bulged profile
    # t3 (judge round 3): the band sits at the new collar edge (X_COLLAR 0.600, the flap root; it was placed for the
    # r2 torn edge at 0.612) and is a soft, even darkening (the shade under the flap), no longer a pale worn band
    edge = np.maximum(col_gauss(n, cu[0], 0.012), col_gauss(n, cu[1], 0.012))
    edge_n = np.clip(0.75 + 0.3 * pnoise(n, n, 1.6, seed + 8, fmin=0.05), 0, 1)
    wear_edge = np.clip(edge * edge_n, 0, 1)
    # t3: clean, glossy lacquer within 60 mm of each collar edge (fading out by 90 mm): no stave streaks, cracks or
    # scratches there (the photo's barrel below the flap is clean). U distance = metres / LAC_TILE, periodic.
    uu = (np.arange(n) + 0.5) / n
    clean = np.zeros((1, n))
    for c_ in cu:
        du = np.abs((uu - c_ + 0.5) % 1.0 - 0.5) * UVL.LAC_TILE
        clean = np.maximum(clean, 1.0 - smooth(0.095, 0.125, du)[None, :])   # 60 mm below the tab hems (0.565)
    bulge = col_gauss(n, UVL.LAC_U0, 0.085) * np.clip(tg.pnoise(n, n, 1.5, seed + 9, angle=0.0, aspect=2.5) * 0.8
                                                     - 0.1, 0, 1)
    # r3 (round-2 judge blocker 4 + delta 3: 'glossy red-brown lacquer with fine craquelure and a strong specular
    # highlight; ours reads as matte wood grain with scratch strokes'): the stave streaks almost gone, the pale
    # scratches cut to a faint few, the gloss up (roughness about 0.28 between the cracks)
    stave = 0.35 * stave * (1 - clean)
    scr = 0.30 * scr * (1 - clean)
    crk = crk * (1 - clean)
    lum = 1.0 + 0.035 * stave + 0.02 * fine
    col = base[None, None, :] * lum[..., None]
    b = np.clip(0.60 * bulge, 0, 0.6)[..., None]
    col = col * (1 - b) + warm[None, None, :] * b * lum[..., None]
    we = (0.45 * wear_edge)[..., None]
    col = col * (1 - we) + to_lin(srgb("#1E0904"))[None, None, :] * we * lum[..., None]   # t3: darkening
    sc_ = (0.45 * scr * (0.8 + 0.6 * np.clip(bulge + wear_edge, 0, 1)))[..., None]
    col = col * (1 - np.clip(sc_, 0, 0.8)) + pale[None, None, :] * np.clip(sc_, 0, 0.8)
    c = (0.88 * crk)[..., None]
    col = col * (1 - c) + dark[None, None, :] * c
    height = -0.00030 * crk - 0.00010 * scr + 0.00002 * stave - 0.00008 * wear_edge + 0.00001 * fine
    rough = 0.27 + 0.02 * np.tanh(fine) + 0.22 * crk + 0.10 * scr + 0.05 * wear_edge - 0.05 * bulge
    ao = ao_from_height(height, px, 4, 0.8)
    lum_img = to_srgb(col).mean(2)
    big = blur(lum_img, 24.0)
    save_set("Lacquer", to_srgb(col), height, np.clip(rough, 0.22, 0.85), px, ao, 0.0,
             {"use": "drum body", "kind": "UNIQUE hero lacquer on the library graph (M_DJ_Lib_Opaque, UseWear on, "
              "TileM 2,2)", "generator": "library dojo_tex_gen primitives, retuned (see docstring)",
              "large_scale_lum_std_srgb": round(float(big.std()) * 255, 2),
              "large_scale_lum_std_library_lacquer_note": "library T_DJ_Lacquer measured separately in BUILD_NOTES",
              "crack_cover_frac": round(float((crk > 0.3).mean()), 4),
              "t3_collar_edge_x_m": UVL.X_COLLAR, "t3_clean_zone_m": [0.095, 0.125]})


def hide(n=2048, seed=1201):
    """Pale cow-hide drumheads (f1): mottled, dirty and fibrous, a darker ring near the rim of each head and a dark
    rolled lip. Both heads are planar discs inside one 2 m tile (taiko_uv.HEAD_CENTRE); the lip rolls are U strips."""
    px = UVL.HIDE_TILE / n
    # t3 (judge round 3 on the user's photo): near-white rawhide, sRGB about 235,233,226, soft sheen (roughness about
    # 0.45); the dark rim band, the tan mix and the stains are toned right down (r2-t2: #D4B996 pale tan)
    base = to_lin(srgb("#EBE9E2"))
    warm = to_lin(srgb("#E0D8C6"))
    grey = to_lin(srgb("#C9C6BE"))
    stain = to_lin(srgb("#CDBFA4"))
    rimc = to_lin(srgb("#D8D3C8"))          # t3: the rim and the lip roll stay near white
    mott = pnoise(n, n, 1.7, seed, fmin=0.05)
    cloud = pnoise(n, n, 1.3, seed + 1, fmin=0.2)
    fib = pnoise(n, n, 0.5, seed + 2, stretch_u=2.5)
    fib2 = pnoise(n, n, 0.5, seed + 12, stretch_v=2.5)
    fibre = np.clip(np.abs(fib) + np.abs(fib2), 0, 4)
    vein_n = pnoise(n, n, 1.5, seed + 3, fmin=0.08)
    vein = np.clip(1.0 - np.abs(vein_n) / 0.05, 0, 1) * np.clip(pnoise(n, n, 1.8, seed + 4, fmin=0.05), 0, 1)
    st = blur(np.clip((pnoise(n, n, 2.0, seed + 5, fmin=0.04) - 1.6) * 0.7, 0, 1), 4.0)
    sm = np.clip((pnoise(n, n, 1.9, seed + 6, fmin=0.05) - 0.8) * 0.9, 0, 1)
    speck = np.clip((pnoise(n, n, 0.3, seed + 7) - 2.3) * 2.0, 0, 1)
    # rim band per head (radial distance in metres from each head centre) and the lip strips
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    u = (xx + 0.5) / n
    v = 1.0 - (yy + 0.5) / n                 # PNG row 0 is the top: v = 1 at row 0
    rim = np.zeros((n, n))
    centre = np.zeros((n, n))
    for s, (cu, cv) in UVL.HEAD_CENTRE.items():
        d = np.hypot(u - cu, v - cv) * UVL.HIDE_TILE
        wob = 0.018 * pnoise(n, n, 1.5, seed + 20 + s, fmin=0.08)
        rim = np.maximum(rim, smooth(0.39, 0.485, d + wob) * (d < 0.50))
        centre = np.maximum(centre, (1 - smooth(0.05, 0.22, d)) * (d < 0.3))
    for s, u0 in UVL.LIP_U0.items():
        # t2 (the user's photo: the hide wraps white over the head edge): the lip strips 0.85 -> 0.25 rim grime
        rim = np.maximum(rim, ((u > u0 - 0.004) & (u < u0 + UVL.LIP_UW + 0.004)).astype(np.float64) * 0.25)
    rim = np.clip(rim * (0.75 + 0.35 * pnoise(n, n, 1.4, seed + 30, fmin=0.06)), 0, 1)
    lum = 1.0 + 0.035 * mott + 0.02 * cloud + 0.015 * fib       # t3: quieter (0.10 / 0.05 / 0.035)
    col = base[None, None, :] * lum[..., None]
    wmix = np.clip(0.10 + 0.10 * mott, 0, 1)[..., None]
    col = col * (1 - wmix) + warm[None, None, :] * wmix * lum[..., None]
    g = (0.20 * sm + 0.10 * centre)[..., None]
    col = col * (1 - g) + grey[None, None, :] * g
    col = col * (1 - 0.35 * st[..., None]) + stain[None, None, :] * 0.35 * st[..., None]
    r = (0.50 * rim)[..., None]
    col = col * (1 - r) + rimc[None, None, :] * r * lum[..., None]
    col = col * (1 - 0.06 * vein[..., None]) * (1 - 0.03 * fibre[..., None]) * (1 - 0.15 * speck[..., None])
    # t3: albedo cap 0.92 sRGB (235: the STYLE_GUIDE's 'no pure white, about sRGB 240'; 0.80 is the plaster rule)
    col = np.minimum(col, float(to_lin(0.92)))
    height = 0.00016 * fib + 0.00010 * fib2 + 0.00025 * blur(cloud, 3) + 0.00018 * vein
    rough = 0.45 + 0.03 * fib + 0.03 * st - 0.02 * sm + 0.02 * rim     # t3: soft sheen (was 0.72)
    ao = ao_from_height(height, px, 5, 0.5)
    bc = to_srgb(col)
    # r3: the drumsticks' wood on an unused patch of this atlas (taiko_uv.BACHI_*)
    pb, ph, pr, pa, info = bachi_patch(px)
    r0 = int(round((1.0 - UVL.BACHI_V0 - UVL.BACHI_VLEN) * n))
    c0 = UVL.BACHI_U0_PX
    hh, ww = ph.shape
    bc[r0:r0 + hh, c0:c0 + ww] = pb
    height[r0:r0 + hh, c0:c0 + ww] = ph
    rough[r0:r0 + hh, c0:c0 + ww] = pr
    ao[r0:r0 + hh, c0:c0 + ww] = pa
    # t2 (2026-10-02): the tacks' glossy black patch and the stand's felt patch (taiko_uv.TACK_PATCH / FELT_PATCH)
    extra_patches = {}
    metal = np.zeros((n, n))
    for key, rect, fn in (("tack_patch", UVL.TACK_PATCH, tack_patch), ("felt_patch", UVL.FELT_PATCH, felt_patch),
                          ("brass_patch", UVL.BRASS_PATCH, brass_patch)):   # t7: the ring washer's pale brass
        u0, v0, u1, v1 = rect
        q0, q1 = int(round(u0 * n)), int(round(u1 * n))
        s0, s1 = int(round((1.0 - v1) * n)), int(round((1.0 - v0) * n))
        pb_, ph_, pr_, pa_, inf_ = fn(s1 - s0, q1 - q0, px)
        bc[s0:s1, q0:q1] = pb_
        height[s0:s1, q0:q1] = ph_
        rough[s0:s1, q0:q1] = pr_
        ao[s0:s1, q0:q1] = pa_
        if key in ("tack_patch", "brass_patch"):
            metal[s0:s1, q0:q1] = TACK_METAL
        extra_patches[key] = dict(inf_, rows=[s0, s1], cols=[q0, q1])
    save_set("Hide", bc, height, rough, px, ao, metal,
             {"use": "drumheads and lip rolls; r3: the drumsticks' wood patch (taiko_uv.BACHI_*); t2: the tacks' "
                     "lacquered-black patch and the stand saddles' felt patch",
              "kind": "UNIQUE (head discs laid out per taiko_uv)", "bachi_patch": dict(info, rows=[r0, r0 + hh],
                                                                                        cols=[c0, c0 + ww]),
              **extra_patches,
              "_patch_normals": (r0, c0, ph)})


TACK_METAL = 1.0


def tack_patch(h, w, px):
    """t2 (judge round 2 on the user's photo): the byou are smooth, glossy jet-black domes with one clean highlight.
    An even lacquered black: BC 0.012 linear, roughness 0.15 (small, crisp highlights), dielectric, flat normal
    (height 0), AO 1."""
    # t3 (judge round 3: black to the edge, F0 about 0.012, roughness 0.28-0.30): the library graph (Blender and
    # M_DJ_Lib_Opaque) has no per-texel specular level, so the patch is METALLIC with base colour 0.012 linear, which
    # gives F0 = 0.012 (a dielectric's 0.04 reflected the bright studio and hide as grey); the diffuse a 0.008
    # dielectric would add is negligible
    lin, rgh = 0.012, 0.29
    bc = np.full((h, w, 3), float(to_srgb(lin)))
    return bc, np.zeros((h, w)), np.full((h, w), rgh), np.ones((h, w)), {
        "bc_linear": lin, "bc_srgb_8bit": int(round(float(to_srgb(lin)) * 255)), "roughness": rgh, "normal": "flat",
        "metallic": TACK_METAL, "f0": lin}


def brass_patch(h, w, px, seed=3501):
    """t7 (user: "also match the ring handle to the reference"): the chrysanthemum washer's pale brass (the photo's
    washer renders a pale, slightly green gold, median sRGB 111,101,74 in shade, 137,126,98 lit). Metallic; base colour
    = the brass F0 sRGB about 196,178,126 with a faint low-frequency patina; roughness 0.36-0.42; flat normal."""
    base = to_lin(srgb("#6E6040"))          # t7 test renders: #C4B27E / #968250 rendered ivory / cream in the photo light
    patina = pnoise(h, w, 1.8, seed, fmin=0.08)
    col = base[None, None, :] * (1.0 + 0.05 * patina[..., None])
    rough = np.clip(0.45 + 0.03 * patina, 0.35, 0.55)
    bc = to_srgb(col)
    return bc, np.zeros((h, w)), rough, np.ones((h, w)), {"bc_srgb_8bit": [int(round(float(x) * 255)) for x in bc.reshape(-1, 3).mean(0)],
                                                          "roughness_mean": round(float(rough.mean()), 3), "metallic": 1.0}


def felt_patch(h, w, px, seed=3401):
    """t2 (the user's stand question): the dark red wool felt that lines each cradle saddle. Deep red, a fine fuzz
    and a soft cloud, fully rough, a very low fibre bump."""
    base = to_lin(srgb("#47121A"))           # deep wine red (#5C1A1D rendered salmon-red)
    fuzz = pnoise(h, w, 0.35, seed)
    cloud = pnoise(h, w, 1.6, seed + 1, fmin=0.08)
    pill = np.clip((pnoise(h, w, 0.6, seed + 2) - 1.8) * 1.5, 0, 1)
    lum = 1.0 + 0.10 * fuzz + 0.07 * cloud + 0.10 * pill
    col = base[None, None, :] * lum[..., None]
    height = 0.00010 * fuzz + 0.00008 * blur(cloud, 2) + 0.00008 * pill
    rough = np.clip(0.92 + 0.03 * fuzz, 0.85, 1.0)
    ao = ao_from_height(height, px, 3, 0.5)
    bc = to_srgb(col)
    return bc, height, rough, ao, {"mean_srgb_8bit": [int(round(float(x) * 255)) for x in bc.reshape(-1, 3).mean(0)],
                                   "rough_mean": round(float(rough.mean()), 3)}


def bachi_patch(px):
    """r3 (round-2 judge blocker 1, the sheet's stick close-up): smooth, oiled, mid-brown turned wood with a soft
    low-contrast grain, darker end grain on the domed ends with faint concentric rings, a soft hand-polish band at
    the grip. Rows = V along the stick (arc length from the grip pole, top row = the far end of the reserved span),
    columns = U round the stick (periodic: one whole wrap, so the lathe seam has no step). The sheet's stick close-up
    measures 127,96,73 median sRGB under its studio light (10th/90th percentile 73,49,30 / 177,138,108)."""
    h = int(round(UVL.BACHI_VLEN * 2048))
    w = UVL.BACHI_UPX
    seed = 3301
    base = to_lin(srgb("#654732"))          # r3 t2 (t1 #7C5A41 rendered 163,127,103 vs the sheet 127,96,73)
    late = to_lin(srgb("#44301F"))          # latewood lines, soft
    endc = to_lin(srgb("#4A3424"))          # end grain drinks the oil: a little darker
    hand = to_lin(srgb("#5A4030"))
    s_m = ((np.arange(h)[::-1] + 0.5) / 2048.0 * UVL.HIDE_TILE)[:, None] * np.ones((1, w))   # arc length (m)
    grain = pnoise(h, w, 1.2, seed, stretch_v=30.0, fmin=0.06)           # long soft streaks along the stick
    lines = np.clip(1.0 - np.abs(pnoise(h, w, 1.0, seed + 1, stretch_v=40.0, fmin=0.1)) / 0.18, 0, 1)
    fine = pnoise(h, w, 0.7, seed + 2, stretch_v=10.0)
    pores = np.clip((pnoise(h, w, 0.2, seed + 3, stretch_v=6.0) - 1.9) * 1.2, 0, 1)
    cloud = pnoise(h, w, 1.8, seed + 4, fmin=0.05)
    arc = UVL.STICK_ARC
    dome0, dome1 = (0.85 * d for d in UVL.STICK_DOME_ARC)   # the darker end-grain face inside each dome's shoulder
    d_end = np.minimum(s_m, arc - s_m)
    endm = np.clip(1.0 - d_end / np.where(s_m < arc / 2, dome0, dome1), 0, 1) ** 0.8 * (s_m < arc + 0.01)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * d_end / 0.0022 + 0.8 * fine)
    g0, g1 = UVL.BACHI_GRIP_WEAR
    hw = smooth(g0, g0 + 0.03, s_m) * (1 - smooth(g1 - 0.05, g1, s_m))
    hw = np.clip(hw * (0.6 + 0.3 * cloud), 0, 1)
    fleck = np.clip((pnoise(h, w, 0.9, seed + 5, stretch_v=8.0) - 1.5) * 0.8, 0, 1)   # soft darker flecks (sheet)
    lum = 1.0 + 0.08 * grain + 0.03 * fine + 0.10 * cloud - 0.30 * fleck
    col = base[None, None, :] * lum[..., None]
    lm = (0.45 * lines * (1 - endm))[..., None]
    col = col * (1 - lm) + late[None, None, :] * lm * lum[..., None]
    em = (0.55 * endm)[..., None]
    col = col * (1 - em) + endc[None, None, :] * em * (1.0 - 0.10 * rings[..., None])
    hm = (0.30 * hw)[..., None]
    col = col * (1 - hm) + hand[None, None, :] * hm
    col = col * (1 - 0.25 * pores[..., None])
    height = 0.00008 * grain - 0.00006 * lines - 0.00010 * pores - 0.00004 * rings * endm
    rough = 0.40 + 0.03 * fine - 0.08 * hw + 0.06 * endm + 0.04 * pores
    ao = ao_from_height(height, px, 3, 0.4)
    bc = to_srgb(col)
    return bc, height, rough, ao, {"mean_srgb_8bit": [int(round(float(x) * 255)) for x in bc.reshape(-1, 3).mean(0)],
                                   "rough_mean": round(float(rough.mean()), 3)}


def collar(h=2048, w=512, seed=1251):
    """t2 (2026-10-02, judge round 2 on the user's photo References/Dojo/taiko_tacks_ref_user.webp): the hide is pale
    (as near white as the 0.80 albedo cap allows, a touch less yellow than the head) over the tack band and above it,
    with a soft tan flush down into the flap; the flap itself (U < taiko_uv.COLLAR_U_FLAP, the flared slit tabs) is
    golden tan rawhide with darker creases running along the tab length and a slightly darker raw cut edge at the tab
    tip (U ~0.03). Rows = V around the drum (2 whole tiles around), columns = U across the band (t4: 0.5 m, 512 px,
    the same 0.98 mm / px; t2-t3: 0.25 m, 256 px).
    t4 (judge round 3 item 4): the white-to-gold blend is ONE smooth ramp along U, GOLD_RAMP (0.4 d, 17 mm) long, from
    taiko_uv.COLLAR_U_GOLD (0.5 d below the tack band) down to COLLAR_U_GOLD_FULL; its line waves only at low frequency
    (about one gentle wave per flap, +-4 mm): no noise runs, no white wash, no high-frequency edge.
    t5 (judge t4 item 1): the gold darkens down the continuous skirt, darkest on its rolled hem lip (taiko_uv
    COLLAR_U_LIP_LO / HI, the last LIP_FADE = 1 d fading in), lightest just below the white ramp; 16 white streaks
    run 25-60 mm down into the gold.
    t6 (judge t5 items 2-3): the gold (every gold stop) shifted GOLD_HSV in sRGB HSV, tuned on renders (it rendered 216-221, 178-183, 139-141, hue 30 deg, s 0.50-0.54; the photo's mid gold 181-192,
    153-164, 109-122, hue 36-37 deg, s 0.33-0.36); the gold zone carries low-frequency mottling only (the crease and
    fibre streaks read as planks); the ramp's wave peak is taiko_uv.GOLD_WAVE (3 mm) and the ramp starts at least
    15 mm below the skirt root (taiko_uv.X_GOLD), so the white runs onto the sheet and the streaks cross the root."""
    px = UVL.COLLAR_TILE_U / w
    pale = to_lin(srgb("#EBE9E2"))          # t3: the head's near-white hide (t2: #D2C6AE)
    cream = to_lin(srgb("#E2DDD1"))
    tan = to_lin(srgb("#906622"))           # t3: golden tan (#A27A3E rendered 210,178,143 under the t1 studio, too
    tan_d = to_lin(srgb("#78521A"))         #     pale; the photo's flaps measure about 176,151,109; #C49E62 rendered
    #                                             228,205,177; t2: #B98448)
    grime = to_lin(srgb("#5A4630"))
    tan, tan_d = gold_adj(tan), gold_adj(tan_d)       # t6
    U = ((np.arange(w) + 0.5) / w)[None, :] * np.ones((h, 1))
    uf = UVL.COLLAR_U_FLAP
    mott = pnoise(h, w, 1.6, seed, fmin=0.05)
    bump = pnoise(h, w, 1.1, seed + 1, fmin=0.12)
    folds = pnoise(h, w, 1.4, seed + 2, stretch_u=5.0, fmin=0.08)
    fib = pnoise(h, w, 0.5, seed + 3, stretch_u=3.0)
    wob = 0.012 * pnoise(h, w, 1.5, seed + 6, fmin=0.1)
    crease = pnoise(h, w, 1.4, seed + 7, stretch_v=6.0, fmin=0.08)   # (t3-t5 creases along U; t6: not in the gold)
    mott_lf = pnoise(h, w, 2.0, seed + 10, fmax=2.5)   # t6: the gold's low-frequency mottling (patches >= ~10 cm)
    # t3: the gold covers the flaps and the lower collar up to COLLAR_U_GOLD (0.5 tack diameters below the band) and
    # fades into the white over about 12 mm, with soft white runs reaching down into it (the photo); no dark cut edge
    ug = UVL.COLLAR_U_GOLD
    ugf = UVL.COLLAR_U_GOLD_FULL
    # t4: the blend line's low-frequency wave along V: whole cycles per tile (seamless), 12-17 cycles per tile (24-34
    # round the drum, about one per flap) plus a slow 2-4 cycle undulation; peak +-4.3 mm (0.1 d)
    rng_w = np.random.default_rng(seed + 8)
    vv = (np.arange(h)[:, None] + 0.5) / h
    wave = np.zeros((h, 1))
    for k_, a_ in ((int(rng_w.integers(12, 18)), 1.0), (int(rng_w.integers(12, 18)), 0.6),
                   (int(rng_w.integers(2, 5)), 0.8)):
        wave += a_ * np.sin(2 * np.pi * (k_ * vv + rng_w.uniform()))
    wave = wave / np.abs(wave).max() * (UVL.GOLD_WAVE / UVL.COLLAR_TILE_U)   # t6: 3.0 mm (t4/t5: 4.3)
    # t7 (judge r6 item 3): the ramp starts right under the tack band (taiko_uv.X_GOLD, 0.12 d below its lower edge) and
    # runs 2.0 d (GOLD_RAMP) down to full gold, mostly on the skirt sheet; its line breaks up in low-frequency mottled
    # patches (the ramp position shifts +-0.3 of its length with a soft 2D noise, and a few soft white clouds reach down
    # into the upper half of the gold); the t5/t6 vertical white "drip" streaks are gone
    brk = pnoise(h, w, 2.2, seed + 11, fmax=3.0)
    brk = brk / (np.abs(brk).max() + 1e-9)
    clouds = np.clip((pnoise(h, w, 2.0, seed + 12, fmax=4.0) - 0.55) * 0.9, 0, 1)
    # The photo, front centre, its fitted camera: right under the band the hide is already a warm cream (luminance about
    # 200, saturation 0.08-0.14), deepening steadily to full gold (157 / 0.31) about 2 tack widths lower. Our pale hide
    # renders near white (238) until about a third of its linear-light colour is gold, so: from the band's lower edge
    # (U ug_b) the gold share rises within 0.12 d (to ug) to GOLD_TINT0, then eases on to full gold at ugf.
    ug_b = UVL.collar_u(UVL.X_BAND_LO)
    U_ = U - wave + 0.12 * (ug - ugf) * brk   # the ramp line wanders +-10 mm (low frequency)
    on = smooth(ug_b, ug, U_)
    t_r = np.clip((ug - U_) / (ug - ugf), 0, 1)
    flap = on * (GOLD_TINT0 + (1 - GOLD_TINT0) * (1.0 - (1.0 - t_r) ** 1.5))
    flap = flap * (1 - 0.45 * clouds * np.clip(1.6 * (1 - t_r), 0, 1))   # white clouds in the ramp's upper part only
    edge = np.zeros_like(U)
    lum = 1.0 + 0.03 * mott + 0.02 * bump * (1 - 0.5 * flap) + 0.015 * fib * (1 - flap)   # t6: no fibre streaks in the gold
    m = np.clip(0.15 + 0.15 * mott, 0, 1)[..., None]
    hide_c = pale[None, None, :] * (1 - m) + cream[None, None, :] * m
    c = np.clip(0.18 + 0.12 * mott_lf, 0, 1)[..., None]   # t6: low-frequency mottling only (t3-t5: + 0.06 crease + 0.10 mott)   # t3: softer creases   # soft creases (0.30 read as wood grain)
    # t5 (judge t4 item 1, colour): the gold is lightest just below the white ramp and darkens down the skirt, darkest
    # on the rolled hem lip (U <= COLLAR_U_LIP_LO .. COLLAR_U_LIP_HI), the last LIP_FADE (1 d) above the lip fading in
    g_top = 0.85 * tan + 0.15 * pale     # t6: 0.70 / 0.30 -> 0.85 / 0.15 (the gold zone is shorter: the light top stop read as
    #                                     grey-white over most of it; an sRGB-space mix rendered the mid gold 9 too blue)
    g_lip = gold_adj(to_lin(srgb("#6C4614")))   # t6: gold_adj
    # t7: the rolled lip (U below COLLAR_U_LIP_HI) only a touch darker than the full gold (the photo's rolls read the same
    # gold, darker only in their own shadow); full gold from the ramp's foot (ugf) down
    lip_c = 0.65 * tan + 0.35 * g_lip
    u_l1 = min(UVL.COLLAR_U_LIP_HI, ugf - 0.01)
    stops_u = [0.0, UVL.COLLAR_U_LIP_LO, u_l1, 1.0]
    stops_c = [lip_c, lip_c, tan, tan]          # t7: one gold (t6's lighter top stop g_top, 15 % pale in linear light, made a
    #                                             hard step at the ramp's foot); the ramp alone brings the white in
    gold = np.stack([np.interp(U[0], stops_u, [float(sc_[ch]) for sc_ in stops_c]) for ch in range(3)], -1)[None]
    gold_d = gold * (np.asarray(tan_d) / np.asarray(tan))[None, None, :]
    flap_c = gold * (1 - c) + gold_d * c
    fl = flap[..., None]
    col = (hide_c * (1 - fl) + flap_c * fl) * lum[..., None]
    col = col * (1 - 0.35 * edge[..., None]) + grime[None, None, :] * 0.35 * edge[..., None]
    col = np.minimum(col, float(to_lin(0.92)))    # t3: the hide's 0.92 cap (see hide())
    # t3: creases 0.6 -> 0.2 mm; the flap's satin hide gets a quarter of the bump (it rendered crinkled)
    height = (0.00030 * folds * (1 - flap) + 0.00012 * mott_lf * flap + 0.00025 * bump * (1 - 0.75 * flap)
              + 0.00010 * fib * (1 - 0.5 * flap))
    rough = 0.45 + 0.03 * fib * (1 - flap) + 0.17 * flap      # t6: the gold 0.55 -> 0.62 (its sheen washed the mid gold pale); t3: soft sheen (t2: 0.70); the gold flap a little more matte (0.55:
    #                                              the big review softboxes washed it pale at 0.40)
    ao = ao_from_height(height, px, 5, 0.8)
    save_set("Collar", to_srgb(col), height, rough, px, ao, 0.0,
             {"use": "hide collar over the barrel ends: pale hide (tack band) + the flared tan flap (tabs)",
              "kind": "UNIQUE (strip: U across the band, V around)",
              "layout": "rows = V around, 2 whole tiles; columns = U (%.2f m): the tabs by arc length below U %.2f, "
                        "white above U %.4f, a smooth ramp to full golden tan at U %.4f" % (UVL.COLLAR_TILE_U, uf, ug,
                                                                                         ugf),
              "t4_gold_ramp_mm": round(1000 * UVL.GOLD_RAMP, 1), "t4_blend_wave_peak_mm": 4.3,
              "t5_lip_u_lo_hi": [UVL.COLLAR_U_LIP_LO, UVL.COLLAR_U_LIP_HI], "t5_lip_fade_mm": 1000 * UVL.LIP_FADE,
              "t5_white_streaks": 0, "t7_gold_ramp_top_U_full_U": [round(ug, 4), round(ugf, 4)], "t7_gold_ramp_mm_design": round(1000 * UVL.GOLD_RAMP, 1), "t6_gold_hsv_shift": GOLD_HSV, "t6_gold_wave_mm": 1000 * UVL.GOLD_WAVE,
              "t6_gold_srgb_8bit": {"tan": [int(round(255 * float(x))) for x in to_srgb(tan)],
                                    "tan_dark": [int(round(255 * float(x))) for x in to_srgb(tan_d)],
                                    "lip": [int(round(255 * float(x))) for x in to_srgb(g_lip)]}})


def collar_r2(h=2048, w=256, seed=1251):
    """(r2-t1 collar with a torn edge, retired in t2) Hide collar lapped over the barrel (f1, blind judge): the head's pale cream about 12 % darker, dirtier toward
    the torn edge (U = 0), fibrous tatter at the edge, folds running across the band, bumpy tacked-down hide.
    Rows = V around the drum (2 whole tiles around), columns = U across the band (0.25 m)."""
    px = UVL.COLLAR_TILE_U / w
    base = to_lin(srgb("#BF9A70"))           # r2: the sheet's collar 188,150,115 vs head 201,176,150: tan, ~14 % darker
    warm = to_lin(srgb("#A07A4E"))
    grime = to_lin(srgb("#4E3B28"))
    smudge = np.clip((pnoise(h, w, 1.7, seed + 9, fmin=0.05) - 0.4) * 0.8, 0, 1)   # r2: grime smudges over the band
    u_m = ((np.arange(w) + 0.5) / w)[None, :] * UVL.COLLAR_TILE_U - UVL.COLLAR_U_EDGE * UVL.COLLAR_TILE_U   # m from edge
    mott = pnoise(h, w, 1.6, seed, fmin=0.05)
    bump = pnoise(h, w, 1.1, seed + 1, fmin=0.12)
    folds = pnoise(h, w, 1.4, seed + 2, stretch_u=5.0, fmin=0.08)
    fib = pnoise(h, w, 0.5, seed + 3, stretch_u=3.0)
    tat = pnoise(h, w, 0.8, seed + 4, stretch_u=0.4)      # short fibres across the edge
    edge = np.exp(-np.clip(u_m, 0, None) / 0.012)
    near = np.exp(-np.clip(u_m, 0, None) / 0.05)
    edge_brk = np.clip(0.7 + 0.5 * pnoise(h, w, 1.3, seed + 5, fmin=0.1), 0, 1.2)
    lum = 1.0 + 0.08 * mott + 0.05 * bump + 0.03 * fib
    col = base[None, None, :] * lum[..., None]
    wm = np.clip(0.22 + 0.15 * mott, 0, 1)[..., None]
    col = col * (1 - wm) + warm[None, None, :] * wm * lum[..., None]
    gm = np.clip(0.62 * edge * edge_brk + 0.30 * near * edge_brk + 0.14 * np.clip(-folds, 0, 2) + 0.30 * smudge,
                 0, 0.85)[..., None]
    col = col * (1 - gm) + grime[None, None, :] * gm
    step = np.broadcast_to((u_m < 0).astype(np.float64), (h, w))   # the lap edge's cut face: raw, dark
    col = col * (1 - 0.55 * step[..., None]) + grime[None, None, :] * 0.55 * step[..., None]
    col = col * (1 - 0.25 * (edge * np.clip(tat, 0, 2))[..., None])
    col = np.minimum(col, float(to_lin(0.80)))
    fold_w = 0.55 + 0.45 * near
    height = 0.00055 * folds * fold_w + 0.00030 * bump + 0.00010 * fib + 0.00025 * edge * tat
    rough = 0.74 + 0.05 * fib + 0.08 * edge
    ao = ao_from_height(height, px, 5, 0.8)
    save_set("Collar", to_srgb(col), height, rough, px, ao, 0.0,
             {"use": "hide collar lapped over the barrel", "kind": "UNIQUE (strip: U across the band, V around)",
              "layout": "rows = V around, 2 whole tiles; columns = U from the torn edge, 0.25 m"})


def timber(n=2048, seed=1301):
    """Dark weathered timber for the stand (f1, blind judge: darker about 35 %, deep grain, checking cracks, grey
    weathering, dirt in the recesses). Grain along U."""
    px = UVL.TIMBER_TILE / n
    base = to_lin(srgb("#34251A"))
    late = to_lin(srgb("#130C07"))
    grey = to_lin(srgb("#433B33"))
    dirt = to_lin(srgb("#1B140E"))
    raised = to_lin(srgb("#665545"))
    grain = pnoise(n, n, 1.3, seed, stretch_u=45.0, fmin=0.08)
    lines = np.clip(1.0 - np.abs(pnoise(n, n, 1.0, seed + 1, stretch_u=60.0, fmin=0.1)) / 0.25, 0, 1)
    fine = pnoise(n, n, 0.8, seed + 2, stretch_u=20.0)
    weather = pnoise(n, n, 1.7, seed + 3, stretch_u=3.0, fmin=0.06)
    ckn = pnoise(n, n, 1.0, seed + 4, stretch_u=70.0, fmin=0.1)
    ckgate = np.clip(pnoise(n, n, 1.6, seed + 5, stretch_u=6.0, fmin=0.05) - 0.3, 0, 1) * 1.8
    checks = np.clip(np.clip(1.0 - np.abs(ckn) / 0.07, 0, 1) * ckgate, 0, 1)
    deep = stamp_lines(n, n, 150, seed + 8, len_px=(160, 700), width_px=(2.5, 5.5), angle_deg=(0.0, 1.5))
    checks = np.maximum(checks, deep)          # f1: long deep checking cracks along the grain
    broad = pnoise(n, n, 2.0, seed + 9, stretch_u=8.0, fmin=0.02)
    ck_halo = np.clip(blur(checks, 3.0) * 2.5, 0, 1)
    scr = stamp_lines(n, n, 300, seed + 6, len_px=(10, 70), width_px=(0.8, 2.0), angle_deg=(0.0, 35.0))
    dmask = np.clip((pnoise(n, n, 1.5, seed + 7, stretch_u=4.0, fmin=0.05) - 0.4) * 0.8, 0, 1)
    lum = 1.0 + 0.16 * grain + 0.06 * fine + 0.12 * broad
    col = base[None, None, :] * lum[..., None]
    col = col * (1 - 0.55 * lines[..., None]) + late[None, None, :] * 0.55 * lines[..., None]
    wmix = np.clip(0.12 + 0.14 * weather, 0, 0.45)[..., None]
    col = col * (1 - wmix) + grey[None, None, :] * wmix * lum[..., None]
    d = (0.35 * dmask + 0.4 * ck_halo)[..., None]
    col = col * (1 - d) + dirt[None, None, :] * d
    hl = (0.30 * np.clip(grain, 0, 2) / 2 + 0.25 * np.clip(ck_halo - checks, 0, 1))[..., None]
    col = col * (1 - hl) + raised[None, None, :] * hl        # f1: lighter weathered raised grain, worn crack lips
    col = col * (1 + 0.30 * scr[..., None])
    col = col * (1 - 0.92 * checks[..., None])
    height = 0.0007 * grain - 0.0004 * lines + 0.0002 * fine - 0.0035 * checks - 0.0001 * scr
    rough = 0.82 + 0.05 * fine + 0.1 * checks - 0.05 * scr
    ao = ao_from_height(height, px, 5, 1.2)
    save_set("Timber", to_srgb(col), height, rough, px, ao, 0.0, {"use": "stand, side grain",
                                                                  "kind": "GENERIC dark timber"})


def timber_end(n=512, seed=1351):
    """End grain for the stand's post tops, beam ends and wedges (f1: split end grain; r0 stretched side grain over
    them). Growth rings around one point (periodic min-image distance), radial checks and a few long splits."""
    px = UVL.TIMBER_END_TILE / n
    base = to_lin(srgb("#2E2117"))
    ring_c = to_lin(srgb("#150E09"))
    grey = to_lin(srgb("#3D362F"))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    dx = ((xx + 0.5) / n - 0.43 + 0.5) % 1.0 - 0.5
    dy = ((yy + 0.5) / n - 0.57 + 0.5) % 1.0 - 0.5
    r_m = np.hypot(dx, dy) * UVL.TIMBER_END_TILE
    ang = np.arctan2(dy, dx)
    warp = 0.004 * pnoise(n, n, 2.2, seed, fmax=1.5)   # low-frequency only, or the rings scramble
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * (r_m + warp) / 0.0065)
    late = np.clip((rings - 0.50) * 2.5, 0, 1)
    rng = np.random.default_rng(seed + 1)
    checks = np.zeros((n, n))
    for k in range(9):
        a0 = rng.uniform(-np.pi, np.pi)
        width = rng.uniform(0.010, 0.022)
        r0, r1 = rng.uniform(0.0, 0.05), rng.uniform(0.07, 0.30)
        da = np.abs((ang - a0 + np.pi) % (2 * np.pi) - np.pi)
        wob = 0.01 * np.sin(r_m * 60 + k)
        line = np.clip(1 - np.abs(da + wob) * np.maximum(r_m, 0.02) / (width * 0.12), 0, 1)
        checks = np.maximum(checks, line * smooth(r0, r0 + 0.02, r_m) * (1 - smooth(r1 - 0.03, r1, r_m)))
    splits = stamp_lines(n, n, 7, seed + 2, len_px=(180, 420), width_px=(2.0, 3.5), angle_deg=(0.0, 90.0))
    cracks = np.clip(np.maximum(checks, splits), 0, 1)
    fine = pnoise(n, n, 0.7, seed + 3)
    weather = pnoise(n, n, 1.6, seed + 4, fmin=0.06)
    lum = 1.0 + 0.06 * fine
    col = base[None, None, :] * lum[..., None]
    col = col * (1 - 0.5 * late[..., None]) + ring_c[None, None, :] * 0.5 * late[..., None]
    wm = np.clip(0.18 + 0.12 * weather, 0, 0.4)[..., None]
    col = col * (1 - wm) + grey[None, None, :] * wm
    col = col * (1 - 0.85 * cracks[..., None])
    height = 0.0002 * rings + 0.00015 * fine - 0.004 * cracks
    rough = 0.86 + 0.04 * fine + 0.08 * cracks
    ao = ao_from_height(height, px, 4, 1.2)
    save_set("TimberEnd", to_srgb(col), height, rough, px, ao, 0.0,
             {"use": "stand end grain (post tops, beam ends, wedges)", "kind": "GENERIC dark timber end grain"})


def stickwood(h=256, w=1024, seed=1401):
    """Drumstick wood (f1, blind judge: mid-dark brown, less saturated, grime, darker hand-wear at the grip, visible
    pores and grain). Rows = V around (0.25 m, one whole tile around the stick), columns = U along (1 m)."""
    px = UVL.STICK_TILE_U / w
    base = to_lin(srgb("#503E30"))
    late = to_lin(srgb("#35271C"))
    grime = to_lin(srgb("#2B2019"))
    hand = to_lin(srgb("#2F241B"))
    grain = pnoise(h, w, 1.3, seed, stretch_u=35.0, fmin=0.08)
    lines = np.clip(1.0 - np.abs(pnoise(h, w, 1.0, seed + 1, stretch_u=45.0, fmin=0.1)) / 0.22, 0, 1)
    fine = pnoise(h, w, 0.8, seed + 2, stretch_u=12.0)
    gr = blur(np.clip((pnoise(h, w, 1.8, seed + 3, fmin=0.05) - 0.1) * 0.9, 0, 1), 2.0)   # f1: more grime
    pores = np.clip((pnoise(h, w, 0.2, seed + 5, stretch_u=4.0) - 1.6) * 1.5, 0, 1)
    dings = stamp_lines(h, w, 90, seed + 4, len_px=(3, 14), width_px=(1.0, 2.5), angle_deg=(90.0, 40.0))
    x_m = ((np.arange(w) + 0.5) / w - UVL.STICK_U0)[None, :] * UVL.STICK_TILE_U   # stick-local x
    g0, g1 = UVL.STICK_GRIP_WEAR
    hw = (smooth(g0 - 0.02, g0 + 0.02, x_m) * (1 - smooth(g1 - 0.06, g1, x_m)))
    hw = np.clip(hw * (0.65 + 0.5 * pnoise(h, w, 1.5, seed + 6, fmin=0.08)), 0, 1)
    strike = smooth(UVL.STICK_L - 0.12, UVL.STICK_L - 0.02, x_m) * (x_m < UVL.STICK_L + 0.02)
    lum = 1.0 + 0.14 * grain + 0.05 * fine
    col = base[None, None, :] * lum[..., None]
    col = col * (1 - 0.5 * lines[..., None]) + late[None, None, :] * 0.5 * lines[..., None]
    gm = (0.55 * gr + 0.20 * strike)[..., None]
    col = col * (1 - gm) + grime[None, None, :] * gm
    hm = (0.70 * hw)[..., None]
    col = col * (1 - hm) + hand[None, None, :] * hm
    col = col * (1 - 0.45 * pores[..., None]) * (1 - 0.35 * (dings * (0.5 + strike))[..., None])
    height = 0.00025 * grain - 0.00015 * lines - 0.00015 * pores - 0.0004 * dings
    rough = 0.60 + 0.05 * fine - 0.18 * hw + 0.12 * dings + 0.05 * gr
    ao = ao_from_height(height, px, 4, 0.8)
    save_set("StickWood", to_srgb(col), height, rough, px, ao, 0.0,
             {"use": "drumsticks", "kind": "UNIQUE-ish (grip wear baked at the stick's U); else GENERIC hardwood",
              "layout": "rows = V around (one whole tile, 0.25 m); columns = U along (1 m)"})


def iron(n=1024, seed=1501):
    """Old wrought iron (tacks, rings, straps, rivets). f1 (measurer, ASSET_GUIDELINES 3): no partial metallic;
    bare and oxide iron 0.96-1.0, rust 0.0 (a hard mask, so no in-between texels)."""
    px = 1.0 / n
    base = to_lin(srgb("#5C5854"))
    oxide = to_lin(srgb("#2E2A26"))
    rust = to_lin(srgb("#5C3A26"))
    ham = blur(pnoise(n, n, 1.0, seed, fmin=0.3), 2.0)
    mott = pnoise(n, n, 1.8, seed + 1, fmin=0.05)
    ox = np.clip(0.45 + 0.20 * mott, 0, 1)
    rn = pnoise(n, n, 1.6, seed + 2, fmin=0.08)
    ru = (rn > 2.0).astype(np.float64)       # hard rust mask
    fine = pnoise(n, n, 0.5, seed + 3)
    col = base[None, None, :] * (1 + 0.08 * fine)[..., None]
    col = col * (1 - ox[..., None]) + oxide[None, None, :] * ox[..., None]
    col = col * (1 - ru[..., None]) + rust[None, None, :] * (1 + 0.1 * fine)[..., None] * ru[..., None]
    height = 0.0004 * ham + 0.0003 * ru * np.abs(fine)
    rough = 0.52 + 0.18 * ox + 0.25 * ru + 0.04 * fine
    metal = np.where(ru > 0.5, 0.0, 1.0 - 0.04 * ox)
    ao = ao_from_height(height, px, 4, 0.6)
    partial = float(((metal > 0.05) & (metal < 0.95)).mean())
    save_set("Iron", to_srgb(col), height, rough, px, ao, metal,
             {"use": "tacks, rings, straps, rivets", "kind": "GENERIC iron",
              "metal_partial_fraction_0.05_0.95": round(partial, 5),
              "metal_min_on_metal": round(float(metal[metal > 0.5].min()), 3),
              "rust_fraction": round(float(ru.mean()), 4)})


# r2: Timber, TimberEnd, StickWood and Iron are retired: the stand, sticks and iron use the shared library
# (M_DJ_TimberDark / TimberDarkEnd / TimberAged / Iron). Their generators stay above for the record only.
SETS = {"Lacquer": lacquer, "Hide": hide, "Collar": collar}


def main():
    for key, fn in SETS.items():
        if ONLY and key not in ONLY:
            continue
        fn()
    WORK.mkdir(parents=True, exist_ok=True)
    rp = WORK / "textures_report.json"
    old = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    old.update(REPORT)
    rp.write_text(json.dumps(old, indent=1), encoding="utf-8")
    print("wrote", rp)


if __name__ == "__main__":
    main()
