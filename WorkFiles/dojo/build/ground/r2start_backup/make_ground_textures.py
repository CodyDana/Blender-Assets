"""Kit 2 (dojo ground) tiling textures: raked sand (straight tile + edge strip), paving granite, soil, edging timber,
the graded CC0 gravel scan and a macro variation mask.

Every procedural map is built from periodic FFT noise and periodic line functions, so each tile repeats with no seam
(the seam test at the end measures it). All tiles are 2048 px over 4.0 m = 5.12 px/cm (STYLE_GUIDE section 6, mid
pieces on tiling materials); the sand edge strip is 2048 x 256 px over 4.0 x 0.5 m (the same density).

Writes Exports/DojoKit/Ground/Textures/T_DKG_<Set>_{BC,N,ORM}.png (BC sRGB; N DirectX green, linear; ORM = AO,
roughness, metal, linear) plus T_DKG_Macro_M.png, and WorkFiles/dojo/build/ground/textures_report.json.

Sources: everything is OUR OWN procedural work EXCEPT T_DKG_Gravel_* (the Poly Haven gravel_floor_02 scan) and the
fines bed of T_DKG_GravelCoarse_* (our own pebbles over that scan)
(CC0 1.0, Assets/Dojo/SourceTextures/PolyHaven/gravel_floor_02/SOURCE.md), colour-graded and repacked here.

Run (headless Blender, for its bundled numpy and JPG loader):
  blender -b --factory-startup --python Scripts/dojo/ground/make_ground_textures.py -- [--only Sand,Gravel]
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "Exports" / "DojoKit" / "Ground" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "ground"
GRAVEL_SRC = ROOT / "Assets" / "Dojo" / "SourceTextures" / "PolyHaven" / "gravel_floor_02"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(ARGS[ARGS.index("--only") + 1].split(",")) if "--only" in ARGS else None

N = 2048
TILE_M = 4.0                    # every tile covers 4.0 m: 2048 px / 400 cm = 5.12 px/cm
PX_M = TILE_M / N               # 1.953 mm per pixel
# Rake spacing, measured on dojo1_reference2 (see BUILD_NOTES_GROUND.md): 0.166-0.204 m, median 0.179 m, through the
# fitted gate camera. 22 lines per 4 m tile = 0.1818 m, the nearest whole number of lines per tile.
RAKE_LINES = 22
RAKE_P = TILE_M / RAKE_LINES
RAKE_DEPTH = 0.018              # crest to furrow bottom, metres (real raked beds 2-3 cm; r0: 2.2 cm read as corrugated sheet at eye height)


# --------------------------------------------------------------------------- helpers

def write_png(path, rgb):
    """8-bit RGB PNG writer (zlib only). rgb rows run top to bottom (PNG order)."""
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
    """Periodic gaussian blur (FFT), radius = sigma in pixels."""
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


def normal_dx(height_m, px_m=PX_M):
    """Height in METRES (rows top to bottom) to a DirectX tangent-space normal map (UE convention): true slopes."""
    du = (np.roll(height_m, -1, 1) - np.roll(height_m, 1, 1)) / (2 * px_m)
    dv = -(np.roll(height_m, -1, 0) - np.roll(height_m, 1, 0)) / (2 * px_m)   # +v is up, rows go down
    nx, ny, nz = -du, -dv, np.ones_like(height_m)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / ln * 0.5 + 0.5, -ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5])   # DX: green flipped


def seam_score(a):
    """Mean |difference| across the wrap seam divided by the mean |difference| between neighbouring interior rows /
    columns. About 1.0 means the wrap is as smooth as any interior step (seamless); a seam shows as >> 1."""
    a = a.mean(2) if a.ndim == 3 else a
    rows = np.abs(a[0] - a[-1]).mean() / (np.abs(np.diff(a, axis=0)).mean() + 1e-12)
    cols = np.abs(a[:, 0] - a[:, -1]).mean() / (np.abs(np.diff(a, axis=1)).mean() + 1e-12)
    return round(float(rows), 3), round(float(cols), 3)


REPORT = {}


def save_set(name, bc_srgb, height_m, rough, ao=None, metal=0.0, px_m=PX_M, source="own procedural",
             normal=None, extra=None, wrap_v=True):
    OUT.mkdir(parents=True, exist_ok=True)
    bc_srgb = np.clip(bc_srgb, 0, 1)
    nrm = normal if normal is not None else normal_dx(height_m, px_m)
    ao = np.ones_like(rough) if ao is None else ao
    orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), np.full_like(rough, metal)])
    write_png(OUT / f"T_DKG_{name}_BC.png", bc_srgb)
    write_png(OUT / f"T_DKG_{name}_N.png", nrm)
    write_png(OUT / f"T_DKG_{name}_ORM.png", orm)
    ang = np.degrees(np.arccos(np.clip(nrm[..., 2] * 2 - 1, -1, 1)))
    rep = {"size_px": [int(bc_srgb.shape[1]), int(bc_srgb.shape[0])], "tile_m": [round(bc_srgb.shape[1] * px_m, 4),
                                                                                  round(bc_srgb.shape[0] * px_m, 4)],
           "px_per_cm": round(0.01 / px_m, 3), "source": source,
           "mean_srgb": [round(float(x), 3) for x in bc_srgb.reshape(-1, 3).mean(0)],
           "mean_srgb_8bit": [int(round(float(x) * 255)) for x in bc_srgb.reshape(-1, 3).mean(0)],
           "albedo_max_srgb": round(float(bc_srgb.max()), 3),
           "rough_mean": round(float(np.clip(rough, 0.02, 1).mean()), 3), "ao_mean": round(float(ao.mean()), 3),
           "normal_tilt_deg_mean_p95": [round(float(ang.mean()), 2), round(float(np.percentile(ang, 95)), 2)],
           "seam_score_bc_rows_cols": seam_score(bc_srgb), "seam_score_n_rows_cols": seam_score(nrm),
           # f1 (measurer): ORM is scored too, per channel (a 3-channel mean hid the gravel AO seam)
           "seam_score_orm_rows_cols": {"ao": seam_score(orm[..., 0]), "rough": seam_score(orm[..., 1])},
           "wraps_in_v": wrap_v}
    if extra:
        rep.update(extra)
    REPORT[name] = rep
    print(name, json.dumps(rep))


# --------------------------------------------------------------------------- raked sand

# f1 (judge): the r0 sand (#B3A791, STYLE_GUIDE 3) rendered DARKER than the gravel at sunset (171/141/118 against
# reference 2's far sand 203/165/138), so the courtyard lost its bright centre. Raised to a warm cream; a deliberate
# deviation from the palette swatch, logged in BUILD_NOTES_GROUND.md (it is still the pale backdrop the palette asks for).
SAND_BASE = "#DEC9A7"   # f1 test 1: #D2BE9E rendered lit 184/152/127 (target 195-205)
WOBBLE_STD_M = 0.005            # f1: per-line wobble, std 5 mm (peaks about 1.5 cm), 1-3 m along the line (test: 7 mm read as dune ripples at eye height)
WOBBLE_EDGE_TILE = 0.12         # the wobble fades to 0 within 0.12 tile (0.48 m) of every tile u edge (see sand_raked)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def knoise(h, w, ku, kv, seed):
    """Periodic gaussian-band noise, frequencies in CYCLES PER TILE (ku along u = columns, kv along v = rows)."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fv = np.fft.fftfreq(h)[:, None] * h
    fu = np.fft.fftfreq(w)[None, :] * w
    F = F * np.exp(-(fu / ku) ** 2 - (fv / kv) ** 2)
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n - n.mean()) / (n.std() + 1e-12)


def rake_profile(d):
    """d = distance from the ridge crest in half-periods (0 crest .. 1 furrow middle) -> height 0..1.
    f1 (judge): the r0 profile was a soft sine ("corrugated plastic"). Now a sharp crest and a wide flat trough:
    (1 - d)^1.5, the crest cusp rounded afterwards by a 1.5 px (3 mm) blur."""
    return (1.0 - np.clip(d, 0.0, 1.0)) ** 1.5


def sand_common(h, w, seed, px_m=PX_M):
    """The sand body shared by the field tile and the edge strip: grain height (m), albedo noise, specks, roughness."""
    grain = pnoise(h, w, 0.10, seed, fmin=0.35) * 0.0009             # single grains (f1: 0.6 -> 0.9 mm, reads granular)
    crumb = pnoise(h, w, 0.6, seed + 6, fmin=0.12) * 0.0012           # 1-2 cm crumbs along the ridges
    lumps = pnoise(h, w, 1.1, seed + 1, fmin=0.02) * 0.0010           # soft lumps, 2-6 cm
    alb = (0.06 * pnoise(h, w, 0.2, seed + 2, fmin=0.3)              # grain-to-grain colour
           + 0.012 * pnoise(h, w, 1.6, seed + 3))                     # soft patches (f1: 0.020, the judge saw mottling)
    rng = np.random.default_rng(seed + 4)
    specks = rng.random((h, w))
    dark = (specks < 0.03).astype(float) * 0.30 + (specks > 0.985).astype(float) * -0.15   # dark / bright grains
    sparkle = (specks > 0.992).astype(float)                                                # quartz grains: glossier
    rough = 0.90 + 0.04 * pnoise(h, w, 0.8, seed + 5) - 0.30 * sparkle
    return grain + crumb + lumps, alb, dark, rough


def sand_colour(hnorm, alb, dark):
    """hnorm: 0 furrow .. 1 crest. f1: crest/furrow tone baked stronger (+-6 %) plus furrow occlusion (-9 %), so the
    rake lines keep their contrast at distance where the normal map averages out (judge delta 3)."""
    base = srgb(SAND_BASE)
    lum = (1.0 + 0.12 * (hnorm - 0.5) + alb - dark) * (1.0 - 0.09 * (1.0 - hnorm) ** 2)
    tint = np.dstack([1.0 + 0.012 * (hnorm - 0.5), np.ones_like(hnorm), 1.0 - 0.02 * (hnorm - 0.5)])
    return base[None, None, :] * lum[..., None] * tint


def sand_raked(seed=301):
    """Straight raked tile: rake lines run along U (texture rows), crests at v = k / 22 (k integer) where the wobble is
    0. The wobble (per-line, 1-3 m wavelength) fades out within 0.48 m of u = 0 (mod 1): the field piece puts u = 0 at
    its path-side edge (and u is 0.025 from an integer at the board side), so the ridges meet the edge strips, whose
    lines are straight, in phase."""
    rows, cols = np.arange(N), np.arange(N)
    v = (N - 1 - rows + 0.5) / N                                   # texture v of each PNG row (row 0 = top = v 1)
    u = (cols + 0.5) / N
    V, U = np.meshgrid(v, u, indexing="ij")
    du = np.minimum(U % 1.0, 1.0 - U % 1.0)
    win = smoothstep(0.0, WOBBLE_EDGE_TILE, du)
    wob = WOBBLE_STD_M * knoise(N, N, 2.5, 7.0, seed + 20) * win   # metres; 2.5 cycles / 4 m along, 7 / 4 m across
    phase = ((V + wob / TILE_M) * RAKE_LINES) % 1.0
    d = np.minimum(phase, 1.0 - phase) * 2.0                       # 0 at a crest, 1 midway (the furrow)
    # the tines are not a machine: furrow depth and crest width drift along each line and differ line to line
    depth_var = 1.0 + 0.18 * pnoise(N, N, 1.8, seed + 10, stretch_u=6.0, stretch_v=0.25)
    width_var = 0.06 * pnoise(N, N, 1.8, seed + 11, stretch_u=6.0, stretch_v=0.25)
    hn = blur(rake_profile(np.clip(d * (1.0 + width_var), 0, 1)), 1.5)
    body, alb, dark, rough = sand_common(N, N, seed)
    height = RAKE_DEPTH * depth_var * hn + body
    bc = sand_colour(hn, alb, dark)
    ao = 1.0 - 0.25 * (1.0 - hn) ** 2
    relief = float(height.max() - height.min())
    save_set("SandRaked", bc, height, rough - 0.06 * hn + 0.03 * (1 - hn), ao,
             extra={"rake_lines_per_tile": RAKE_LINES, "rake_spacing_m": round(RAKE_P, 4),
                    "groove_depth_m": RAKE_DEPTH, "profile": "(1-d)^1.5, sharp crest, wide trough, 3 mm crest round",
                    "wobble_std_m": WOBBLE_STD_M, "wobble_peak_m": round(float(np.abs(wob).max()), 4),
                    "depth_var_line_to_line": 0.18,
                    "encoded_relief_m_max_min": round(relief, 4),
                    "encoded_relief_m_p1_p99": round(float(np.percentile(height, 99) - np.percentile(height, 1)), 4),
                    "lines_run_along": "U (texture rows); crests at v = k/22 (wobble 0 at u = 0 mod 1)"})


def sand_edge(seed=311):
    """Edge strip, 2048 x 256 px = 4.0 m along the edge (U) x 0.5 m across (V). U continues the field's rake phase
    (crest at u = k/22); V = 0 joins the field, V = 1 is the edge (the board or the path slab). Each ridge runs into
    the edge and stops in a round cap, with a low heaped margin between the caps and the edge; f1: a darker contact
    band in the last 3 cm (the sand shaded against the slab / board)."""
    h, w = 256, N
    rows = np.arange(h)
    e_d = (rows + 0.5) * PX_M                                      # distance from the edge (row 0 = top = V 1 = edge)
    cols = np.arange(w)
    a = (cols + 0.5) * PX_M                                        # along the edge, metres (0 - 4 m)
    ph = (a / RAKE_P) % 1.0
    da = np.minimum(ph, 1.0 - ph) * RAKE_P                          # distance to the nearest crest line, metres
    cap = 0.5 * RAKE_P * 0.95 + 0.012                               # ridge end-cap centre, metres from the edge
    E, DA = np.meshgrid(e_d, da, indexing="ij")
    dist = np.where(E >= cap, DA, np.sqrt(DA * DA + (cap - E) ** 2))
    width_var = 0.06 * pnoise(h, w, 1.8, seed + 11, stretch_u=0.25, stretch_v=6.0)
    hn = blur(rake_profile(np.clip(dist / (0.5 * RAKE_P) * (1.0 + width_var), 0, 1)), 1.5)
    margin = 0.30 * np.clip(1.0 - E / cap, 0, 1) ** 0.5            # the sand heaped against the edge
    hn = np.maximum(hn, margin)
    depth_var = 1.0 + 0.18 * pnoise(h, w, 1.8, seed + 10, stretch_u=0.25, stretch_v=6.0)
    body, alb, dark, rough = sand_common(h, w, seed)
    height = RAKE_DEPTH * depth_var * hn + body
    bc = sand_colour(hn, alb, dark)
    contact = 1.0 - 0.14 * np.clip(1.0 - E / 0.03, 0, 1) ** 1.5     # contact shade against the edge
    bc = bc * contact[..., None]
    ao = (1.0 - 0.25 * (1.0 - hn) ** 2) * contact
    save_set("SandEdge", bc, height, rough - 0.06 * hn + 0.03 * (1 - hn), ao, wrap_v=False,
             extra={"strip_m": [4.0, 0.5], "cap_centre_from_edge_m": round(cap, 4), "contact_band_m": 0.03,
                    "v0": "joins the field", "v1": "the edge"})


# --------------------------------------------------------------------------- granite

def speckle(seed, n=N):
    """Granite crystals: black mica specks (about 9 %) and white feldspar flecks (about 7 %)."""
    crystal = pnoise(n, n, 0.35, seed + 1, fmin=0.25)
    crystal2 = pnoise(n, n, 0.35, seed + 2, fmin=0.25)
    return crystal, np.clip((crystal - 1.35) * 2.5, 0, 1), np.clip((crystal2 - 1.45) * 2.5, 0, 1)


def granite(seed=401):
    """Paving granite for the path slabs (STYLE_GUIDE 3 granite #8A8680): mauve-grey mottling, black mica specks,
    white feldspar flecks, a FLAMED surface (f1: fine crystal pits over the cleft relief) with smoother worn patches.
    Per-slab value and hue shifts come from the material (per-instance random), the arris darkening from 'Wear'."""
    base = to_lin(srgb("#8A8680"))
    mott = pnoise(N, N, 1.5, seed, fmin=0.05)                       # 5-80 cm mottling
    crystal, mica, felds = speckle(seed)
    fine = pnoise(N, N, 0.05, seed + 3, fmin=0.5)
    lum = 1.0 + 0.11 * mott + 0.05 * fine
    col = base[None, None, :] * lum[..., None]
    hue = np.clip(0.08 + 0.025 * pnoise(N, N, 1.5, seed + 4, fmin=0.05), 0.0, 0.14)
    col = col * np.dstack([1 - 0.3 * hue, 1 - 0.2 * hue, 1 + 1.2 * hue])
    col = col * (1 - 0.72 * mica[..., None]) + to_lin(srgb("#E4DFD6"))[None, None, :] * 0.55 * felds[..., None]
    worn = np.clip(pnoise(N, N, 1.5, seed + 5, fmin=0.10) - 0.6, 0, 1)
    col = col * (1 - 0.06 * worn[..., None])
    # flamed finish: the torch pops out crystals, leaving 2-6 mm pits over the whole face
    flame = blur(np.clip((pnoise(N, N, 0.3, seed + 7, fmin=0.4) - 1.3) * 2.0, 0, 1), 0.8)
    col = col * (1 - 0.18 * flame[..., None])
    cleft = pnoise(N, N, 1.25, seed + 6, fmin=0.03) * 0.0025
    height = cleft * (1 - 0.6 * worn) + 0.00025 * crystal - 0.0002 * mica - 0.0009 * flame
    rough = 0.72 + 0.06 * fine - 0.18 * worn + 0.05 * mica - 0.08 * felds + 0.06 * flame
    ao = (1.0 - 0.10 * np.clip(-pnoise(N, N, 1.25, seed + 6, fmin=0.03), 0, 3) / 3) * (1 - 0.25 * flame)
    col = col * (base.mean() / col.mean())
    save_set("Granite", to_srgb(col), height, rough, ao,
             extra={"note": "flamed paving finish; arris darkening from the slab 'Wear' vertex colour; per-slab "
                            "tone and hue from the material's per-instance random"})


def granite_hewn(seed=451):
    """f1 (judge delta 7): rough-hewn granite for the kerbs (the gate band and the bed kerbs): hewn facets (5-30 cm,
    +-5 mm), deep pitting (3-10 mm pits, about 14 % of the face), pick marks, the same crystal speckle as the slabs,
    darker and warmer grey than the paving. The raised crowns are worn smoother (roughness down: the sunset sheen)."""
    base = to_lin(srgb("#7C7773"))
    facets = pnoise(N, N, 1.7, seed, fmin=0.04)
    crystal, mica, felds = speckle(seed + 20)
    pits = blur(np.clip((pnoise(N, N, 0.45, seed + 1, fmin=0.18) - 1.05) * 1.6, 0, 1), 1.0)
    pick = pnoise(N, N, 0.9, seed + 2, stretch_u=0.2, stretch_v=3.0, fmin=0.1)     # short pick strokes along v
    marks = np.clip(0.30 - np.abs(pick), 0, 1) / 0.30
    fine = pnoise(N, N, 0.05, seed + 3, fmin=0.5)
    crown = np.clip(facets, 0, 2.5) / 2.5
    lum = (1.0 + 0.10 * facets + 0.05 * fine) * (1 - 0.40 * pits) * (1 - 0.08 * marks)
    col = base[None, None, :] * lum[..., None]
    col = col * np.dstack([np.full_like(lum, 1.02), np.ones_like(lum), np.full_like(lum, 0.97)])
    col = col * (1 - 0.70 * mica[..., None]) + to_lin(srgb("#DAD4CA"))[None, None, :] * 0.45 * felds[..., None]
    height = 0.005 * facets - 0.006 * pits - 0.0012 * marks + 0.0003 * crystal
    rough = 0.82 - 0.20 * crown + 0.12 * pits + 0.03 * fine
    ao = (1 - 0.45 * pits) * (1 - 0.10 * marks) * (1 - 0.12 * np.clip(-facets, 0, 2.5) / 2.5)
    col = col * (base.mean() / col.mean())
    save_set("GraniteHewn", to_srgb(col), height, rough, ao,
             extra={"note": "kerb stone: hewn facets, pits, pick marks; crowns glossier"})


# --------------------------------------------------------------------------- soil

def soil(seed=501):
    """Garden-bed soil: f1 (judge delta 10) a mid-brown loam (r0 #4E3E30 rendered near black), crumb clods, small grey
    stones, dead organic bits, damp patches."""
    base = to_lin(srgb("#735B44"))
    clod = pnoise(N, N, 1.3, seed, fmin=0.03)
    crumb = pnoise(N, N, 0.6, seed + 1, fmin=0.2)
    st = blur(pnoise(N, N, 0.3, seed + 2, fmin=0.3), 2.5)
    st = (st - st.mean()) / st.std()
    stones = np.clip((st - 2.3) * 3.0, 0, 1)
    org = np.clip((pnoise(N, N, 0.8, seed + 3, fmin=0.15, stretch_u=3.0) - 1.9) * 2.0, 0, 1)
    damp = pnoise(N, N, 2.0, seed + 4)
    lum = 1.0 + 0.10 * clod + 0.10 * crumb - 0.08 * np.clip(damp, 0, 2)
    col = base[None, None, :] * lum[..., None]
    col = col * (1 - stones[..., None]) + to_lin(srgb("#9C968C"))[None, None, :] * stones[..., None] * (0.9 + 0.1 * crumb[..., None])
    col = col * (1 - org[..., None]) + to_lin(srgb("#4A3624"))[None, None, :] * org[..., None]
    height = 0.0022 * clod + 0.0005 * crumb + 0.004 * stones ** 0.5
    rough = 0.93 - 0.10 * np.clip(damp, 0, 2) / 2 - 0.25 * stones
    ao = 1.0 - 0.18 * np.clip(-clod, 0, 3) / 3 - 0.10 * np.clip(-crumb, 0, 3) / 3
    save_set("Soil", to_srgb(col), height, rough, ao)


# --------------------------------------------------------------------------- edging timber

def edge_timber(seed=601):
    """Sand-field edging boards. f1 (judge delta 8): the r0 worn pale timber (#9C8466) read as an orange varnished
    trim; now sun-bleached silver-cream timber close to the sand's value, so the edge is a light, low-contrast line
    (reference 2). Grain along U; fine checks along the grain."""
    base = to_lin(srgb("#BCAE96"))
    grain = pnoise(N, N, 1.4, seed, stretch_u=40.0, fmin=0.06)
    fine = pnoise(N, N, 0.8, seed + 1, stretch_u=25.0)
    weather = pnoise(N, N, 1.6, seed + 2, stretch_u=4.0, fmin=0.08)
    ck = pnoise(N, N, 1.0, seed + 3, stretch_u=60.0)
    checks = np.clip((np.abs(ck) < 0.03).astype(float) * np.clip(pnoise(N, N, 1.5, seed + 4, stretch_u=5.0) - 0.8, 0, 1) * 3, 0, 1)
    lum = 1.0 + 0.07 * grain + 0.04 * fine
    col = base[None, None, :] * lum[..., None]
    grey = to_lin(srgb("#B1AA9E"))
    wmix = np.clip(0.45 + 0.25 * weather, 0, 1)[..., None]
    col = col * (1 - wmix) + grey[None, None, :] * wmix * lum[..., None]
    col = col * (1 - 0.55 * checks[..., None])
    height = 0.0005 * grain + 0.0002 * fine - 0.0015 * checks
    rough = 0.82 + 0.05 * fine + 0.1 * checks
    ao = 1 - 0.35 * checks
    save_set("EdgeTimber", to_srgb(col), height, rough, ao)


# --------------------------------------------------------------------------- CC0 gravel (graded)

# f1 (judge delta 4): the one r0 gravel (#8A8789) read cool lavender "asphalt" and sat at the sand's value. Split:
#  - Gravel (surround): the CC0 scan graded to a pale warm beige-grey decomposed-granite tone;
#  - GravelCoarse (the gate strip): our own 1-4 cm pebbles over the scan as the fines bed (below).
GRAVEL_TARGET = "#ABA59E"   # f1 test 1: #AFA491 rendered lit 166/132/103, too orange under the 2700 K sun
GRAVEL_SAT = 0.40        # keep 40 % of the scan's chroma (f1 test 1: 55 %)


def load_rgb(path):
    """Load an image with Blender (headless), return float rows top to bottom (PNG order), RGB, file values."""
    import bpy
    im = bpy.data.images.load(str(path))
    im.colorspace_settings.name = "Non-Color"            # raw file values (no transform)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(im)
    return px.astype(np.float64)


def seam_repair(chan, predictors, band=24):
    """f1 (measurer): the scan's ARM map does not wrap (AO seam 1.88 / 1.82, roughness 1.49 / 1.53), while its diff,
    nor_dx and disp maps do. Fit the channel from seamless predictors of the same pebbles (disp cavities at four
    scales, disp, diff luminance; least squares) plus the scan's residual from mid-tile, then cross-fade to that in
    a 24 px (4.7 cm) band at each wrap edge: aligned with the pebbles in BC and N, and it keeps the scan's grain.
    Returns (repaired, r2 of the fit)."""
    X = np.stack([p.ravel() for p in predictors] + [np.ones(chan.size)], 1)
    coef, *_ = np.linalg.lstsq(X, chan.ravel(), rcond=None)
    pred = (X @ coef).reshape(chan.shape)
    r2 = 1 - ((chan - pred) ** 2).mean() / chan.var()
    # the fit alone is smoother than the scan (a calm band, seam score 0.6); add back the scan's own residual taken
    # from the middle of the tile (rolled by half a tile), which is continuous across the wrap edges
    n = chan.shape[0]
    pred = pred + np.roll(chan - pred, (n // 2, n // 2), axis=(0, 1))
    idx = np.arange(n)
    dist = np.minimum(idx + 0.5, n - idx - 0.5)
    w1 = 1.0 - smoothstep(0.0, band, dist)
    w = np.maximum(w1[:, None], w1[None, :])
    return chan * (1 - w) + pred * w, float(r2)


def gravel_scan():
    diff = load_rgb(GRAVEL_SRC / "gravel_floor_02_diff_2k.jpg")
    nrm = load_rgb(GRAVEL_SRC / "gravel_floor_02_nor_dx_2k.jpg")        # already DirectX (Poly Haven nor_dx)
    arm = load_rgb(GRAVEL_SRC / "gravel_floor_02_arm_2k.jpg")           # AO, roughness, metal: our ORM order
    disp = load_rgb(GRAVEL_SRC / "gravel_floor_02_disp_2k.jpg")[..., 0]
    return diff, nrm, arm, disp


def gravel(scan):
    diff, nrm, arm, disp = scan
    lin = to_lin(diff)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    grey = lum[..., None]
    graded = grey + GRAVEL_SAT * (lin - grey)
    tgt = to_lin(srgb(GRAVEL_TARGET))
    graded = graded * (tgt / graded.reshape(-1, 3).mean(0))[None, None, :]
    bc = to_srgb(graded)
    n = nrm * 2 - 1
    n = n / np.linalg.norm(n, axis=2, keepdims=True)
    preds = [disp - blur(disp, r) for r in (2, 4, 8, 16)] + [disp, lum]
    ao, r2a = seam_repair(arm[..., 0], preds)
    rough, r2r = seam_repair(arm[..., 1], preds)
    save_set("Gravel", bc, None, rough, ao, metal=0.0, normal=n * 0.5 + 0.5,
             source="Poly Haven gravel_floor_02, CC0 1.0 (NOT our own work): graded to "
                    f"{GRAVEL_TARGET} at {GRAVEL_SAT:.0%} chroma, repacked BC/N/ORM, ORM wrap seam repaired",
             extra={"scan_mean_srgb_8bit": [int(round(float(x) * 255)) for x in diff.reshape(-1, 3).mean(0)],
                    "scan_arm_seam_rows_cols": {"ao": seam_score(arm[..., 0]), "rough": seam_score(arm[..., 1])},
                    "seam_repair": {"band_px": 24, "fit_r2_ao": round(r2a, 3), "fit_r2_rough": round(r2r, 3)},
                    "pebble_size_note": "scan autocorrelation half-width 5 px -> pebbles about 10-15 px = 2.0-2.9 cm "
                                        "at the 4 m tile"})


def pebble_layer(cells, rmin, rmax, seed, n=N):
    """Periodic pebble field on a jittered grid (one pebble per cell, cells x cells per tile): elliptical domes of
    random size, aspect and angle. Returns (height in px units, pebble id) where the tallest dome wins."""
    rng = np.random.default_rng(seed)
    cs = n / cells
    jx, jy = rng.random((cells, cells)), rng.random((cells, cells))
    rad = rng.uniform(rmin, rmax, (cells, cells)) * cs
    ang = rng.uniform(0, np.pi, (cells, cells))
    asp = rng.uniform(0.6, 1.0, (cells, cells))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    ci, cj = (yy // cs).astype(np.int32), (xx // cs).astype(np.int32)
    best = np.zeros((n, n), np.float32)
    bid = np.full((n, n), -1, np.int32)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ii, jj = (ci + di) % cells, (cj + dj) % cells
            py = (ci + di + jy[ii, jj]) * cs
            px = (cj + dj + jx[ii, jj]) * cs
            dy, dx = yy - py, xx - px
            ca, sa = np.cos(ang[ii, jj]), np.sin(ang[ii, jj])
            uu = dx * ca + dy * sa
            vv = (-dx * sa + dy * ca) / asp[ii, jj]
            r = rad[ii, jj]
            q = (uu * uu + vv * vv) / (r * r)
            hgt = np.where(q < 1, r * np.sqrt(np.clip(1 - q, 0, 1)), 0).astype(np.float32)
            m = hgt > best
            best = np.where(m, hgt, best)
            bid = np.where(m, ii * cells + jj, bid)
    return best, bid


def gravel_coarse(scan, seed=801):
    """OUR OWN coarse pebble gravel for the gate strip (judge delta 4: reference 2's strip is a darker, coarser
    grey-brown pebble with individual stones and micro-shadow): two pebble layers, 2.2-3.8 cm and 1.0-1.8 cm, sitting
    on the CC0 scan as the fines bed (graded darker). Pebble tones grey / brown-grey / dark / pale per stone; the
    gaps and each pebble's rim are baked darker (micro-shadow that holds at distance)."""
    diff = scan[0]
    big, bid_b = pebble_layer(128, 0.36, 0.62, seed)          # cell 3.1 cm
    small, bid_s = pebble_layer(224, 0.30, 0.52, seed + 1)    # cell 1.8 cm
    hb = big * 0.55 + (big > 0) * 2.0                          # big pebbles sit higher (px units)
    hs = small * 0.55 + (small > 0) * 1.0
    top_big = hb >= hs
    hpx = np.where(top_big, hb, hs)
    pid = np.where(top_big, bid_b, bid_s + 128 * 128)
    peb = (hpx > 0).astype(float)
    rng = np.random.default_rng(seed + 2)
    palette = to_lin(np.array([srgb(c) for c in ("#78767A", "#827770", "#5C5B5E", "#9A9794", "#6C6560", "#8A8B8C")]))
    choice = rng.integers(0, len(palette), 128 * 128 + 224 * 224)
    val = rng.normal(1.0, 0.10, 128 * 128 + 224 * 224)
    stone = palette[choice[pid]] * np.clip(val[pid], 0.7, 1.3)[..., None]
    # fines between the stones: the scan, darker and warmer
    lin = to_lin(diff)
    fines = lin * (to_lin(srgb("#58534F")) / lin.reshape(-1, 3).mean(0))[None, None, :]
    rim = np.clip(hpx / 6.0, 0, 1) ** 0.5                     # 0 at a pebble's edge, 1 on its crown
    col = np.where(peb[..., None] > 0, stone * (0.62 + 0.38 * rim[..., None]), fines * 0.85)
    speck = pnoise(N, N, 0.2, seed + 3, fmin=0.4)
    col = col * (1 + 0.05 * speck[..., None])
    height_m = hpx * PX_M + 0.0008 * pnoise(N, N, 0.6, seed + 4, fmin=0.2)
    height_m = blur(height_m, 0.7)
    rough = np.where(peb > 0, 0.74 + 0.06 * speck - 0.08 * rim, 0.95)
    ao = np.where(peb > 0, 0.70 + 0.30 * rim, 0.45)
    save_set("GravelCoarse", to_srgb(col), height_m, rough, ao,
             source="OUR OWN procedural pebbles over the CC0 Poly Haven gravel_floor_02 diff as the fines bed "
                    "(graded darker); mixed provenance: list as CC0-derived",
             extra={"pebbles_m": {"big": [round(2 * 0.36 * 4.0 / 128, 4), round(2 * 0.62 * 4.0 / 128, 4)],
                                  "small": [round(2 * 0.30 * 4.0 / 224, 4), round(2 * 0.52 * 4.0 / 224, 4)]},
                    "pebble_cover": round(float(peb.mean()), 3)})


# --------------------------------------------------------------------------- macro variation

def macro(n=1024, seed=701):
    """Large-scale variation mask, sampled at world XY / 32 m (Unreal: WorldPosition / 3200 cm). R = albedo tint,
    G = roughness offset, B = a patchier dirt/wear mask. 0.5 = neutral for R and G."""
    r = 0.5 + 0.18 * pnoise(n, n, 1.9, seed)
    g = 0.5 + 0.18 * pnoise(n, n, 1.7, seed + 1)
    b = np.clip(0.5 + 0.25 * pnoise(n, n, 1.5, seed + 2), 0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    img = np.dstack([np.clip(r, 0, 1), np.clip(g, 0, 1), b])
    write_png(OUT / "T_DKG_Macro_M.png", img)
    REPORT["Macro"] = {"size_px": [n, n], "tile_m": [32.0, 32.0], "px_per_cm": round(n / 3200.0, 3),
                       "channels": "R albedo tint, G roughness offset, B dirt/wear (0.5 neutral)",
                       "seam_score_rows_cols": seam_score(img), "source": "own procedural"}
    print("Macro", REPORT["Macro"])


def _gravels():
    scan = gravel_scan()
    gravel(scan)
    gravel_coarse(scan)


SETS = {"Sand": (sand_raked, sand_edge), "Granite": (granite, granite_hewn), "Soil": (soil,), "Timber": (edge_timber,),
        "Gravel": (_gravels,), "Macro": (macro,)}


def main():
    for key, fns in SETS.items():
        if ONLY and key not in ONLY:
            continue
        for fn in fns:
            fn()
    WORK.mkdir(parents=True, exist_ok=True)
    rp = WORK / "textures_report.json"
    old = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    old.update(REPORT)
    rp.write_text(json.dumps(old, indent=1), encoding="utf-8")
    print("wrote", rp)


main()
