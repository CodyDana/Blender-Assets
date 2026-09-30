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
    cu = [UVL.LAC_U0 + s_ * UVL.X_COLLAR / UVL.LAC_TILE for s_ in (1, -1)]
    edge = np.maximum(col_gauss(n, cu[0], 0.020), col_gauss(n, cu[1], 0.020))
    edge_n = np.clip(0.55 + 0.6 * pnoise(n, n, 1.3, seed + 8, fmin=0.08), 0, 1)
    wear_edge = np.clip(edge * edge_n * 1.3, 0, 1)
    bulge = col_gauss(n, UVL.LAC_U0, 0.085) * np.clip(tg.pnoise(n, n, 1.5, seed + 9, angle=0.0, aspect=2.5) * 0.8
                                                     - 0.1, 0, 1)
    # r3 (round-2 judge blocker 4 + delta 3: 'glossy red-brown lacquer with fine craquelure and a strong specular
    # highlight; ours reads as matte wood grain with scratch strokes'): the stave streaks almost gone, the pale
    # scratches cut to a faint few, the gloss up (roughness about 0.28 between the cracks)
    stave = 0.35 * stave
    scr = 0.30 * scr
    lum = 1.0 + 0.035 * stave + 0.02 * fine
    col = base[None, None, :] * lum[..., None]
    b = np.clip(0.60 * bulge, 0, 0.6)[..., None]
    col = col * (1 - b) + warm[None, None, :] * b * lum[..., None]
    we = (0.55 * wear_edge)[..., None]
    col = col * (1 - we) + wood[None, None, :] * we * lum[..., None]
    sc_ = (0.45 * scr * (0.8 + 0.6 * np.clip(bulge + wear_edge, 0, 1)))[..., None]
    col = col * (1 - np.clip(sc_, 0, 0.8)) + pale[None, None, :] * np.clip(sc_, 0, 0.8)
    c = (0.88 * crk)[..., None]
    col = col * (1 - c) + dark[None, None, :] * c
    height = -0.00030 * crk - 0.00010 * scr + 0.00002 * stave - 0.00008 * wear_edge + 0.00001 * fine
    rough = 0.27 + 0.02 * np.tanh(fine) + 0.22 * crk + 0.10 * scr + 0.14 * wear_edge - 0.05 * bulge
    ao = ao_from_height(height, px, 4, 0.8)
    lum_img = to_srgb(col).mean(2)
    big = blur(lum_img, 24.0)
    save_set("Lacquer", to_srgb(col), height, np.clip(rough, 0.22, 0.85), px, ao, 0.0,
             {"use": "drum body", "kind": "UNIQUE hero lacquer on the library graph (M_DJ_Lib_Opaque, UseWear on, "
              "TileM 2,2)", "generator": "library dojo_tex_gen primitives, retuned (see docstring)",
              "large_scale_lum_std_srgb": round(float(big.std()) * 255, 2),
              "large_scale_lum_std_library_lacquer_note": "library T_DJ_Lacquer measured separately in BUILD_NOTES",
              "crack_cover_frac": round(float((crk > 0.3).mean()), 4)})


def hide(n=2048, seed=1201):
    """Pale cow-hide drumheads (f1): mottled, dirty and fibrous, a darker ring near the rim of each head and a dark
    rolled lip. Both heads are planar discs inside one 2 m tile (taiko_uv.HEAD_CENTRE); the lip rolls are U strips."""
    px = UVL.HIDE_TILE / n
    base = to_lin(srgb("#D4B996"))          # sheet head face, de-lit (f1 t1: #CBB08F rendered 179 vs the sheet 201)
    warm = to_lin(srgb("#B08A5A"))
    grey = to_lin(srgb("#8F8676"))
    stain = to_lin(srgb("#86633F"))
    rimc = to_lin(srgb("#7E6446"))          # grimy rim band and lip
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
        rim = np.maximum(rim, ((u > u0 - 0.004) & (u < u0 + UVL.LIP_UW + 0.004)).astype(np.float64) * 0.85)
    rim = np.clip(rim * (0.75 + 0.35 * pnoise(n, n, 1.4, seed + 30, fmin=0.06)), 0, 1)
    lum = 1.0 + 0.10 * mott + 0.05 * cloud + 0.035 * fib
    col = base[None, None, :] * lum[..., None]
    wmix = np.clip(0.20 + 0.16 * mott, 0, 1)[..., None]
    col = col * (1 - wmix) + warm[None, None, :] * wmix * lum[..., None]
    g = (0.20 * sm + 0.10 * centre)[..., None]
    col = col * (1 - g) + grey[None, None, :] * g
    col = col * (1 - 0.35 * st[..., None]) + stain[None, None, :] * 0.35 * st[..., None]
    r = (0.50 * rim)[..., None]
    col = col * (1 - r) + rimc[None, None, :] * r * lum[..., None]
    col = col * (1 - 0.18 * vein[..., None]) * (1 - 0.06 * fibre[..., None]) * (1 - 0.35 * speck[..., None])
    col = np.minimum(col, float(to_lin(0.80)))   # albedo cap 0.80 sRGB (STYLE_GUIDE 3, paper / plaster rule)
    height = 0.00016 * fib + 0.00010 * fib2 + 0.00025 * blur(cloud, 3) + 0.00018 * vein
    rough = 0.72 + 0.05 * fib + 0.06 * st - 0.05 * sm + 0.05 * rim
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
    save_set("Hide", bc, height, rough, px, ao, 0.0,
             {"use": "drumheads and lip rolls; r3: the drumsticks' wood patch (taiko_uv.BACHI_*)",
              "kind": "UNIQUE (head discs laid out per taiko_uv)", "bachi_patch": dict(info, rows=[r0, r0 + hh],
                                                                                        cols=[c0, c0 + ww]),
              "_patch_normals": (r0, c0, ph)})


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


def collar(h=2048, w=256, seed=1251):
    """Hide collar lapped over the barrel (f1, blind judge): the head's pale cream about 12 % darker, dirtier toward
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
