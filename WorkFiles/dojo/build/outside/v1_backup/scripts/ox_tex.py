"""ROUND 5 OUTSIDE track: the approach road's cobble texture set T_DKX_Cobble (numpy only, no bpy).

dojo1_reference1 (AI-generated modelling reference, References/Dojo/REFERENCE_LOG.md) shows the approach road outside the
south gate as a grey, rough stone surface of small rounded cobbles with dark joints (measured under its dusk light:
median sRGB (67-75, 66-75, 77-87)). No pixel of the reference is used: the set is built from periodic Voronoi cells and
periodic FFT noise with the shared library's helpers (Scripts/dojo/materials/dojo_tex_gen.py, imported read-only).

Sets (Exports/DojoKit/Outside/Textures/), plus T_DKX_Kawara_* (kawara(): the library RoofTile maps with tile courses):
  T_DKX_Cobble_BC   2048 x 2048 sRGB, one tile = 4 x 4 m (5.12 px/cm, STYLE_GUIDE 6)
  T_DKX_Cobble_N    DirectX tangent normal (green = -Y), linear
  T_DKX_Cobble_ORM  R AO, G roughness, B metallic (0), linear
Cobbles: a jittered 25 x 25 Voronoi per tile (about 16 cm stones), each stone pillowed (height to its cell edge), tilted
and lifted at random, its own grey (granite greys, a few bluish and warm stones), a fine grain; joints 1.5-3 cm of dark
sandy dirt, a little moss in the widest joints; crowns worn smoother (lower roughness).
Sampled on world XY / 400 cm by the ground XY master (M_DJ_GroundXY_Master), so road pieces join seamlessly.

Run: py -3 Scripts/dojo/outside/ox_tex.py [--only Cobble,Kawara]      (numpy; PIL reads the library maps for Kawara)
Report: WorkFiles/dojo/build/outside/textures_report.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_tex_gen as T  # noqa: E402  (read-only use of the library's helpers)

OUT = ROOT / "Exports" / "DojoKit" / "Outside" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "outside"
N = 2048
TILE_M = 4.0
CELLS = 25                 # 4 m / 25 = 16 cm stones
TARGET_MEDIAN = "#67645F"  # sRGB albedo median: grey granite cobbles + dark joints (road under dusk light (67-75, 66-75, 77-87))


def cobble():
    t0 = time.time()
    F1, F2, ID, PX, PY = T.voronoi(N, N, CELLS, CELLS, 0.42, 5151, with_pos=True)
    edge = (F2 - F1) * 0.5                       # distance to the cell border, in cell units (1 cell = 16 cm)
    rng = np.random.default_rng(77)
    n_id = CELLS * CELLS
    lift = rng.normal(0.0, 0.0035, n_id)          # m
    tilt_u = rng.normal(0.0, 0.05, n_id)          # m per cell unit
    tilt_v = rng.normal(0.0, 0.05, n_id)
    gap = rng.uniform(0.028, 0.060, n_id)         # joint half-width, cell units (0.45-1.0 cm)
    tone = rng.uniform(-1.0, 1.0, n_id)
    kind = rng.uniform(0.0, 1.0, n_id)
    g = gap[ID]
    # rounded cobbles: the cell's inner distance field blurred (about 1.6 cm), so the Voronoi corners round off and
    # every stone reads as a rounded cobble rather than crazy paving
    d = T.gblur(edge - g, 8.0) + 0.02 * T.gblur(T.pnoise(N, N, 1.4, 10), 3.0)
    inside = np.clip(d / 0.34, 0.0, 1.0)
    dome = np.sqrt(inside) * (1.0 - 0.30 * inside)            # rounded top
    grain = T.pnoise(N, N, 1.1, 11) * 0.0008
    h_stone = 0.028 * dome + lift[ID] + (tilt_u[ID] * PX + tilt_v[ID] * PY) * 0.02 + grain
    joint_fill = T.gblur(T.pnoise(N, N, 1.6, 12), 2.0) * 0.002 - 0.004
    stone_mask = np.clip(d / 0.03, 0.0, 1.0)
    height = h_stone * stone_mask + joint_fill * (1.0 - stone_mask)
    # ---- colour (sRGB), per stone: granite greys, only a hint of blue or warm on a few stones
    grey_lo, grey_hi = T.srgb("#65625E"), T.srgb("#7F7B75")
    t = (tone[ID] * 0.5 + 0.5)[..., None]
    col = grey_lo * (1 - t) + grey_hi * t
    blu = (kind[ID] < 0.15)[..., None]
    warm = (kind[ID] > 0.88)[..., None]
    col = np.where(blu, col * np.array([0.975, 0.99, 1.025]), col)
    col = np.where(warm, col * np.array([1.03, 1.00, 0.965]), col)
    speck = T.pnoise(N, N, 0.35, 13)
    mottle = T.gblur(T.pnoise(N, N, 1.2, 17), 4.0)
    col = col * (1.0 + 0.04 * speck + 0.05 * mottle)[..., None]
    crown = np.clip(dome, 0, 1)[..., None]
    col = col * (0.86 + 0.18 * crown)                             # worn, paler crowns; darker at the stone foot
    # joints: dark sandy dirt, a little dull moss in the widest
    dirt = T.srgb("#3C3631") * (1.0 + 0.10 * T.pnoise(N, N, 0.8, 14))[..., None]
    moss_n = T.gblur(T.pnoise(N, N, 1.8, 15), 3.0)
    moss = np.clip((moss_n - 1.2) * 1.2, 0, 1) * (g > 0.050)
    dirt = dirt * (1 - moss[..., None] * 0.5) + T.srgb("#3E4233") * (moss[..., None] * 0.5)
    col = col * stone_mask[..., None] + dirt * (1 - stone_mask[..., None])
    # grime near the joints on the stone edges
    rim = np.clip(1.0 - d / 0.10, 0, 1) * stone_mask
    col = col * (1.0 - 0.18 * rim[..., None])
    col = T.grade_median(np.clip(col, 0, 1), TARGET_MEDIAN)
    col = np.clip(col, 0.03, 0.80)
    # ---- ORM
    cav = T.cavity(height, 6.0)
    ao = np.clip(1.0 - 0.55 * cav, 0.35, 1.0)
    rough = 0.80 - 0.16 * crown[..., 0] * stone_mask + 0.03 * T.pnoise(N, N, 0.6, 16)
    rough = rough * stone_mask + 0.93 * (1 - stone_mask)
    px_m = TILE_M / N
    OUT.mkdir(parents=True, exist_ok=True)
    T.write_png(OUT / "T_DKX_Cobble_BC.png", col)
    T.write_png(OUT / "T_DKX_Cobble_N.png", T.normal_dx(height / px_m, 0.85))
    T.write_png(OUT / "T_DKX_Cobble_ORM.png", np.dstack([ao, np.clip(rough, 0.05, 1), np.zeros_like(ao)]))
    lum = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    return {"set": "Cobble", "size_px": [N, N], "tile_m": [TILE_M, TILE_M], "texel_px_per_cm": round(N / (TILE_M * 100), 3),
            "stone_cm": round(TILE_M / CELLS * 100, 1),
            "median_srgb": [int(round(x * 255)) for x in np.median(col.reshape(-1, 3), 0)],
            "stone_share": round(float(stone_mask.mean()), 3),
            "lum_p10_p50_p90": [round(float(np.percentile(lum, q)) * 255, 1) for q in (10, 50, 90)],
            "rough_p5_p50_p95": [round(float(np.percentile(rough, q)), 3) for q in (5, 50, 95)],
            "height_cm_p1_p99": [round(float(np.percentile(height, q)) * 100, 2) for q in (1, 99)],
            "seam_rank_bc": T.seam_rank(col), "seam_rank_height": T.seam_rank(height),
            "seconds": round(time.time() - t0, 1)}


KAWARA_N = 15              # courses and rolls per 4 m tile: 0.2667 m, the pitch build_outside.P_TILE uses


def _read(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float64) / 255.0


def kawara():
    """T_DKX_Kawara: the shared library's RoofTile maps (T_DJ_RoofTile_*, read only) with kawara COURSES laid over them,
    for the low-detail town roofs (their rolls are geometry at the same 0.2667 m pitch, UVs aligned by the builder):
    every course's lower lip sits proud on the course below (a step, a dark gap line under it), the tile surface sinks
    toward the next course, the pan between two rolls is shaded a little darker, and each tile gets its own small
    tone shift. U = along the eave (rolls), V = up the slope (courses); 4 x 4 m, 2048 px (5.12 px/cm)."""
    t0 = time.time()
    lib = ROOT / "Exports" / "DojoKit" / "Materials" / "Textures"
    bc = _read(lib / "T_DJ_RoofTile_BC.png")
    orm = _read(lib / "T_DJ_RoofTile_ORM.png")
    nrm = _read(lib / "T_DJ_RoofTile_N.png")
    n = bc.shape[0]
    v, u = np.mgrid[0:n, 0:n].astype(np.float64)
    V = 1.0 - (v + 0.5) / n                      # image rows run down = -V; V 0 at the bottom (eave side)
    U = (u + 0.5) / n
    tc = (V * KAWARA_N + 0.5) % 1.0              # 0 at a course's lower lip -> 1 at the next lip (the wrap falls mid-course)
    tr = (U * KAWARA_N) % 1.0                    # 0 / 1 = pan centre, 0.5 = roll crest
    course = np.floor(V * KAWARA_N + 0.5).astype(int)
    col_i = np.floor(U * KAWARA_N + 0.5).astype(int)     # tile boundaries under the roll crests (the wrap is mid-pan)
    # height (m): the lip step (0.018) sinking along the course, the lip rounded over 8 % of the course
    h = 0.018 * (1.0 - tc) + 0.006 * np.clip(1.0 - tc / 0.08, 0, 1) ** 2
    h += 0.010 * (0.5 - 0.5 * np.cos(2 * np.pi * tr))            # roll curvature (the geometry carries the rest)
    rng = np.random.default_rng(15)
    tile_tone = rng.normal(0.0, 0.035, (KAWARA_N, KAWARA_N))[course % KAWARA_N, col_i % KAWARA_N]
    shade = 0.74 + 0.36 * (1.0 - tc) ** 1.5 + tile_tone          # the lip catches the light, the tucked end is darker
    gap = np.clip(1.0 - (1.0 - tc) / 0.06, 0, 1)                 # the shadow line just under the next course's lip
    shade *= 1.0 - 0.62 * gap
    pan = 0.86 + 0.14 * (0.5 - 0.5 * np.cos(2 * np.pi * tr))
    col = np.clip(bc * (shade * pan)[..., None], 0.02, 0.8)
    px_m = TILE_M / n
    n_course = T.normal_dx(h / px_m, 1.0)
    # combine the library normal (detail) with the course normal (whiteout-style: add xy, keep z)
    a = n_course * 2 - 1
    b = nrm * 2 - 1
    comb = np.dstack([a[..., 0] + b[..., 0], a[..., 1] + b[..., 1], a[..., 2] * b[..., 2]])
    comb /= np.linalg.norm(comb, axis=2, keepdims=True)
    ao = np.clip(orm[..., 0] * (1.0 - 0.35 * gap), 0, 1)
    rough = orm[..., 1]
    T.write_png(OUT / "T_DKX_Kawara_BC.png", col)
    T.write_png(OUT / "T_DKX_Kawara_N.png", comb * 0.5 + 0.5)
    T.write_png(OUT / "T_DKX_Kawara_ORM.png", np.dstack([ao, rough, orm[..., 2]]))
    return {"set": "Kawara", "size_px": [n, n], "tile_m": [TILE_M, TILE_M], "courses_per_tile": KAWARA_N,
            "pitch_m": round(TILE_M / KAWARA_N, 4), "base": "T_DJ_RoofTile_* (shared library, read only)",
            "median_srgb": [int(round(x * 255)) for x in np.median(col.reshape(-1, 3), 0)],
            "library_median_srgb": [int(round(x * 255)) for x in np.median(bc.reshape(-1, 3), 0)],
            "seam_rank_bc": T.seam_rank(col), "seconds": round(time.time() - t0, 1)}


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["Cobble", "Kawara"]
    rep = {}
    if "Cobble" in only:
        rep["Cobble"] = cobble()
    if "Kawara" in only:
        rep["Kawara"] = kawara()
    old = json.loads((WORK / "textures_report.json").read_text(encoding="utf-8")) \
        if (WORK / "textures_report.json").exists() else {}
    old.update(rep)
    rep = old
    (WORK / "textures_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))
