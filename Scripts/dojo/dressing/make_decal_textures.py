"""ROUND 5 (2026-09-29): the weathering + moss DEFERRED DECAL textures (T_DKD_Decal_*), numpy only, our own procedural
work (no photo, scan or third-party pixel; the references are AI-generated modelling references and are only looked at).

Six decals, each a set of four maps (power of two, full mips in Unreal):
  _BC   sRGB colour (the colour the decal lays over the surface where the mask is on)
  _N    tangent normal, DirectX (green = -Y, Unreal native), linear
  _ORM  R = AO (1), G = roughness, B = metallic (0), linear
  _M    the OPACITY MASK, linear grey (0 = the surface untouched)
Image orientation: the image TOP is the decal's 'up' (decals.json gives every placement's up vector); a wall decal's
bottom row sits at the wall foot, a ground decal's bottom row at the wall / downpipe / stair side.

  Name        px           nominal m    what
  MossFoot    2048 x 512   4.0 x 1.0    moss cushions and damp at a wall foot / footing: dense at the bottom row, a
                                        ragged upper edge, a damp darkening band above the moss
  RainStreak  1024 x 512   2.0 x 1.0    dirt runoff streaks hanging from a drip line (wall caps, eaves): a faint top band,
                                        thin irregular streaks fading down
  Grime       1024 x 1024  1.0 x 1.0    splash-back grime at post bases and door thresholds: dense at the bottom row,
                                        speckle and smears fading up
  Lichen      1024 x 1024  1.0 x 1.0    crustose lichen rosettes (pale grey-green, ochre) in loose clusters, for roof
                                        tiles and stone lanterns
  WaterStain  1024 x 1024  1.0 x 1.0    the ground stain under a downpipe shoe: dark algae core at the bottom-centre
                                        (the shoe side), tide lines spreading up the image (away from the wall)
  WornPath    1024 x 1024  1.5 x 1.5    trodden gravel: packed fine grit, a flatter normal (the decal flattens the
                                        gravel's own relief), soft oval mask with a ragged edge

Colours are set against the surfaces they land on (measured medians of our own sets: plaster 192/170/144, rubble
86/82/76, gravel 157/141/122, roof tile 64/67/74, granite 115/111/106) and the style guide's moss #4F5A35.
Run (Blender's bundled Python has numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/dressing/make_decal_textures.py
Out: Exports/DojoKit/Dressing/Textures/T_DKD_Decal_*_{BC,N,ORM,M}.png, WorkFiles/dojo/build/dressing/decal_textures.json,
     WorkFiles/dojo/build/dressing/renders/decal_textures_sheet.png (a review sheet: each decal over its surface colour)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_tex_gen as T  # noqa: E402  (read-only use of the library's helpers: write_png, pnoise, gblur, normal_dx)

OUT = ROOT / "Exports" / "DojoKit" / "Dressing" / "Textures"
DW = ROOT / "WorkFiles" / "dojo" / "build" / "dressing"
SURF = {"plaster": (192, 170, 144), "rubble": (86, 82, 76), "gravel": (157, 141, 122), "tile": (64, 67, 74),
        "granite": (115, 111, 106), "timber": (74, 62, 54)}


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def grid(h, w):
    """u 0..1 left->right, t 0..1 bottom->top (row 0 of the image is the TOP, t = 1)."""
    v, u = np.mgrid[0:h, 0:w].astype(np.float64)
    return u / (w - 1), 1.0 - v / (h - 1)


def col(hexs):
    return T.srgb(hexs)


def side_fade(u, k=0.06):
    return ss(0.0, k, u) * ss(0.0, k, 1.0 - u)


def rows1d(w, beta, seed):
    n = T.pnoise(8, w, beta, seed)[0]
    return n / (np.abs(n).max() + 1e-9)


def save(name, bc, height, nstr, rough, mask, rep):
    OUT.mkdir(parents=True, exist_ok=True)
    h, w = mask.shape
    assert (h & (h - 1)) == 0 and (w & (w - 1)) == 0, (name, w, h)
    bc = np.clip(bc, 0, 1)
    mask = np.clip(mask, 0, 1)
    T.write_png(OUT / f"T_DKD_Decal_{name}_BC.png", bc)
    T.write_png(OUT / f"T_DKD_Decal_{name}_N.png", T.normal_dx(height, nstr))
    T.write_png(OUT / f"T_DKD_Decal_{name}_ORM.png", np.dstack([np.ones_like(mask), np.clip(rough, 0.05, 1),
                                                                 np.zeros_like(mask)]))
    T.write_png(OUT / f"T_DKD_Decal_{name}_M.png", mask)
    on = mask > 0.5
    rep[name] = {"size_px": [w, h], "coverage_mask_gt_0.5": round(float(on.mean()), 4),
                 "mask_mean": round(float(mask.mean()), 4), "mask_max": round(float(mask.max()), 3),
                 "bc_median_where_mask_gt_0.5_srgb": [int(round(x * 255)) for x in
                                                       (np.median(bc[on].reshape(-1, 3), 0) if on.any() else [0, 0, 0])],
                 "rough_median_where_on": round(float(np.median(rough[on])) if on.any() else 0.0, 3),
                 "edge_max_mask": round(float(max(mask[0].max(), mask[-1].max(), mask[:, 0].max(),
                                                  mask[:, -1].max())), 3)}
    return bc, mask


# ------------------------------------------------------------------------------------------------ decals
def moss_foot(rep):
    """r2: cushion moss as clumps of small domes (periodic Voronoi cells, about 3.5 cm), thick at the bottom row and
    along a ragged upper edge, with bare stone between clumps; a faint damp darkening band above the moss."""
    h, w = 512, 2048
    u, t = grid(h, w)
    edge = 0.34 + 0.12 * rows1d(w, 1.6, 5101)[None, :] + 0.05 * rows1d(w, 1.1, 5102)[None, :]   # moss top line
    damp_top = edge + 0.18 + 0.08 * rows1d(w, 1.4, 5103)[None, :]
    clump = T.gblur(T.pnoise(h, w, 1.0, 5104), 9.0)
    clump = 0.6 * clump / (clump.std() + 1e-9) + 0.4 * T.pnoise(h, w, 2.0, 5110)   # 15-40 cm clumps on a slow drift
    F1, F2, ID = T.voronoi(h, w, 114, 28, 0.45, 5105)                  # 4 m / 114 = 3.5 cm cells
    cell_r = np.random.default_rng(5108).uniform(0, 1, 114 * 28)[ID]
    dome = np.clip(1.0 - F1 / 0.62, 0, 1) ** 0.7                        # a rounded cushion in each cell
    grow = np.clip(1.0 - t / np.clip(edge, 0.05, None), 0, 1)           # 1 at the bottom row -> 0 at the edge
    density = (grow * 0.55 + 0.55 * clump + 0.15 * (cell_r - 0.5)) * ss(0.0, 0.12, grow)
    present = ss(0.40, 0.50, density)                                   # which cushions exist (crisp clump edges)
    moss = T.gblur(present, 1.2) * (0.80 + 0.20 * ss(0.0, 0.5, dome))  # a continuous mat, bumpy cushions in it
    damp = ss(0.0, 0.10, damp_top - t) * (0.45 + 0.25 * ss(-1, 1, T.pnoise(h, w, 2.2, 5106)))
    sfade = side_fade(u, 0.07)
    mask = np.clip(np.maximum(moss * 0.98, damp * 0.30), 0, 1) * sfade
    m_dark, m_mid, m_light, m_tip = col("#2F3820"), col("#4F5A35"), col("#6E7843"), col("#86834C")
    mc = T.lerp(m_dark[None, None, :] * np.ones((h, w, 3)), m_mid, ss(0.0, 0.6, dome))
    mc = T.lerp(mc, m_light, ss(0.55, 1.0, dome) * (0.4 + 0.6 * cell_r))
    mc = T.lerp(mc, m_tip, ss(0.75, 1.0, cell_r) * ss(0.5, 1.0, dome) * 0.6)
    mc = mc * (0.85 + 0.3 * ss(-2, 2, T.pnoise(h, w, 0.7, 5107)))[..., None]
    dampc = np.ones((h, w, 3)) * col("#3E3B35")[None, None, :]
    wmoss = np.clip(moss / np.clip(np.maximum(moss, damp * 0.30), 1e-4, None), 0, 1)
    bc = T.lerp(dampc, mc, wmoss)
    height = moss * dome * 3.0 + T.gblur(T.pnoise(h, w, 0.5, 5109), 0.6) * 0.3 * moss
    rough = 0.74 + 0.20 * moss - 0.08 * damp * (1 - moss)
    save("MossFoot", bc, height, 3.0, rough, mask, rep)


def rain_streak(rep):
    """r2 (after the first sheet read as a comb): fewer, softer runoff smudges of mixed widths, starting at slightly
    different depths under a broken drip band, blurred edges; thin lines are a minority."""
    h, w = 512, 1024
    u, t = grid(h, w)
    rng = np.random.default_rng(5201)
    band_n = rows1d(w, 1.3, 5202)[None, :]
    top_band = ss(0.0, 0.08, t - (0.88 + 0.03 * band_n)) * (0.20 + 0.10 * band_n) *         (0.6 + 0.4 * ss(-1, 1, T.pnoise(h, w, 1.6, 5204)))
    mask = top_band.copy()
    xs = np.arange(w)[None, :]
    for k in range(30):
        x0 = rng.uniform(0.05, 0.95) * w
        wid = rng.uniform(5.0, 22.0) if k % 3 else rng.uniform(1.5, 4.0)   # px (5.12 px/cm): 1-4 cm smudges, a few lines
        start = rng.uniform(0.0, 0.12)
        length = rng.uniform(0.20, 0.85)
        strength = rng.uniform(0.10, 0.34)
        drift = np.cumsum(rng.normal(0, 0.12, h))
        drift -= drift[0]
        cx = x0 + drift[:, None]
        prof = np.exp(-0.5 * ((xs - cx) / wid) ** 2)
        tt = t[:, :1]
        along = np.clip((1.0 - tt - start) / length, -1, 1.5)
        fade = (1 - ss(0.35, 1.0, along)) * ss(-0.05, 0.05, along)
        breakup = 0.55 + 0.45 * ss(-1, 1, T.pnoise(h, 8, 1.5, int(rng.integers(1e6)))[:, :1])
        mask = mask + prof * fade * breakup * strength * (1 - mask)
    mask = T.gblur(mask, 1.5)
    mask *= side_fade(u, 0.08)
    mask = np.clip(mask * (0.80 + 0.20 * ss(-1, 1, T.pnoise(h, w, 1.0, 5203))), 0, 1)
    bc = np.ones((h, w, 3)) * col("#5E574D")[None, None, :]
    bc = T.lerp(bc, col("#4D483F"), ss(0.15, 0.45, mask) * 0.6)
    height = -mask * 0.3
    rough = 0.80 + 0.08 * mask
    save("RainStreak", bc, height, 1.0, rough, mask, rep)


def grime(rep):
    h, w = 1024, 1024
    u, t = grid(h, w)
    rng = np.random.default_rng(5301)
    line = 0.22 + 0.07 * rows1d(w, 1.5, 5302)[None, :]
    base = ss(0.0, 1.0, 1.0 - t / np.clip(line + 0.18, 0.05, None)) ** 1.4
    smear = ss(-0.6, 1.2, T.pnoise(h, w, 1.8, 5303, stretch_v=0.4))
    dots = np.zeros((h, w))
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(900):                                      # rain splash specks, denser low
        ty = rng.beta(1.2, 4.0)
        cy, cx = (1 - ty) * (h - 1), rng.uniform(0.05, 0.95) * w
        r = rng.uniform(0.8, 3.2)
        y0, y1 = int(max(0, cy - 5)), int(min(h, cy + 6))
        x0, x1 = int(max(0, cx - 5)), int(min(w, cx + 6))
        d = np.hypot(yy[y0:y1, x0:x1] - cy, xx[y0:y1, x0:x1] - cx)
        dots[y0:y1, x0:x1] = np.maximum(dots[y0:y1, x0:x1], ss(r + 0.8, r - 0.8, d) * rng.uniform(0.3, 0.8))
    mask = np.clip(base * (0.55 + 0.45 * smear) * 0.80 + dots * 0.55 * ss(0.75, 0.0, t), 0, 1)
    mask *= side_fade(u, 0.10) * ss(1.0, 0.72, t)
    bc = np.ones((h, w, 3)) * col("#56493B")[None, None, :]
    bc = T.lerp(bc, col("#3F362D"), ss(0.4, 0.9, mask) * 0.7)
    bc = T.lerp(bc, col("#6B5E4E"), ss(-1, 1, T.pnoise(h, w, 1.2, 5304)) * 0.35)
    height = T.gblur(dots, 0.8) * 0.8 + smear * base * 0.3
    rough = 0.86 + 0.06 * mask
    save("Grime", bc, height, 1.4, rough, mask, rep)


def lichen(rep):
    h, w = 1024, 1024
    u, t = grid(h, w)
    rng = np.random.default_rng(5401)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    mask = np.zeros((h, w))
    shade = np.zeros((h, w))
    ring = np.zeros((h, w))
    clusters = [(rng.uniform(0.28, 0.72) * w, rng.uniform(0.28, 0.72) * h, rng.uniform(80, 170)) for _ in range(5)]
    for k in range(150):
        cx0, cy0, spread = clusters[k % len(clusters)]
        cx, cy = cx0 + rng.normal(0, spread), cy0 + rng.normal(0, spread)
        r = float(np.clip(rng.lognormal(np.log(10.0), 0.55), 3.0, 30.0))          # px: 0.6-6 cm rosettes
        lob = rng.integers(4, 7)
        ph = rng.uniform(0, 6.3)
        ph2 = rng.uniform(0, 6.3)
        R = int(r * 1.5) + 3
        y0, y1, x0, x1 = int(max(0, cy - R)), int(min(h, cy + R)), int(max(0, cx - R)), int(min(w, cx + R))
        if y1 <= y0 or x1 <= x0:
            continue
        dy, dx = yy[y0:y1, x0:x1] - cy, xx[y0:y1, x0:x1] - cx
        ang = np.arctan2(dy, dx)
        rr = r * (1 + 0.10 * np.sin(lob * ang + ph) + 0.07 * np.sin((2 * lob + 1) * ang + ph2)
                  + 0.05 * np.sin(3 * ang + 2 * ph))
        d = np.hypot(dx, dy)
        inside = ss(rr + 1.0, rr - 1.0, d)
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], inside * rng.uniform(0.75, 0.97))
        shade[y0:y1, x0:x1] = np.where(inside > 0.5, rng.uniform(0, 1), shade[y0:y1, x0:x1])
        ring[y0:y1, x0:x1] = np.maximum(ring[y0:y1, x0:x1], inside * ss(rr * 0.55, rr * 0.95, d))
    region = ss(0.50, 0.32, np.hypot(u - 0.5, t - 0.5))
    mask *= region
    grey, ochre, dark = col("#8F9481"), col("#8E8156"), col("#686D5F")      # r2: a step darker (r1 read as paint chips)
    bc = T.lerp(grey[None, None, :] * np.ones((h, w, 3)), ochre, ss(0.55, 0.9, shade))
    bc = T.lerp(bc, dark, (1 - ring) * 0.22)
    bc = T.lerp(bc, bc * 0.85, ss(-1, 1, T.pnoise(h, w, 0.9, 5402)) * 0.5)
    mask = T.gblur(mask, 0.8)
    height = T.gblur(mask, 1.0) * 0.5 + ring * 0.3
    rough = 0.88 + 0.06 * ring
    save("Lichen", bc, height, 1.6, rough, mask, rep)


def water_stain(rep):
    h, w = 1024, 1024
    u, t = grid(h, w)
    wob = T.pnoise(h, w, 1.7, 5501)
    # distance from the source at the bottom-centre, the stain stretched away from the wall (up the image)
    d = np.hypot((u - 0.5) / 0.46, (t - 0.02) / 0.80)
    d = d * (1 + 0.10 * wob)
    core = ss(0.42, 0.10, d)
    body = ss(0.95, 0.55, d)
    tide = np.zeros_like(d)
    for rr, a in ((0.70, 0.10), (0.88, 0.07)):
        tide = np.maximum(tide, a * np.exp(-0.5 * ((d - rr) / 0.025) ** 2))
    tide = T.gblur(tide, 2.0)
    mask = np.clip(body * 0.62 + core * 0.35 + tide, 0, 1) * ss(0.0, 0.02, t)
    bc = np.ones((h, w, 3)) * col("#4E4940")[None, None, :]
    bc = T.lerp(bc, col("#2F332A"), core * 0.75)                   # algae core
    bc = T.lerp(bc, col("#3B3730"), ss(0.0, 1.0, tide / 0.10) * 0.6)
    bc = T.lerp(bc, bc * 1.12, ss(-1, 1, T.pnoise(h, w, 1.1, 5502)) * 0.4)
    height = T.gblur(core, 3.0) * 0.4 + T.pnoise(h, w, 0.8, 5503) * 0.05 * body
    rough = 0.80 - 0.22 * core - 0.06 * body
    save("WaterStain", bc, height, 1.2, rough, mask, rep)


def worn_path(rep):
    """r2: the stones pushed aside expose packed fines: a touch LIGHTER and smoother than the loose gravel (r1's darker
    brown oval read as a wet patch), fine grit and scattered small stones left in it, a soft ragged edge."""
    h, w = 1024, 1024
    u, t = grid(h, w)
    rng = np.random.default_rng(5605)
    wob = T.pnoise(h, w, 1.8, 5601)
    d = np.hypot((u - 0.5) / 0.46, (t - 0.5) / 0.46) * (1 + 0.16 * wob)
    mask = ss(1.0, 0.50, d) * 0.72
    mask = mask * (0.75 + 0.25 * ss(-1.5, 1.5, T.pnoise(h, w, 1.0, 5602)))
    grit = T.pnoise(h, w, 0.4, 5603)
    stones = np.zeros((h, w))
    F1, F2, ID = T.voronoi(h, w, 150, 150, 0.45, 5606)             # 1 cm cells: the odd small stone left behind
    keep = rng.uniform(0, 1, 150 * 150)[ID] < 0.10
    stones = keep * ss(0.45, 0.25, F1)
    mask = np.clip(mask * (1 - 0.8 * stones), 0, 1)                 # the gravel's own stones show through there
    bc = np.ones((h, w, 3)) * col("#A8977F")[None, None, :]
    bc = T.lerp(bc, col("#BCAC95"), ss(0.8, 2.2, grit) * 0.5)
    bc = T.lerp(bc, col("#857663"), ss(-0.8, -2.2, grit) * 0.5)
    bc = T.lerp(bc, bc * 0.94, ss(-1, 1, T.pnoise(h, w, 1.5, 5604)) * 0.5)
    height = grit * 0.10
    rough = 0.90 + 0.04 * ss(-1, 1, grit)
    save("WornPath", bc, height, 1.0, rough, mask, rep)


def sheet(rep):
    """Review sheet: each decal composited over its target surface colour (alpha-over, as a DBuffer decal blends)."""
    from dojo_tex_gen import write_png  # noqa: F401
    tiles = []
    for name, surf in (("MossFoot", "rubble"), ("RainStreak", "plaster"), ("Grime", "timber"), ("Lichen", "tile"),
                       ("WaterStain", "gravel"), ("WornPath", "gravel")):
        bc = read_png(OUT / f"T_DKD_Decal_{name}_BC.png")
        m = read_png(OUT / f"T_DKD_Decal_{name}_M.png")
        if m.ndim == 3:
            m = m[..., 0]
        base = np.ones_like(bc) * (np.array(SURF[surf]) / 255.0)[None, None, :]
        comp = base * (1 - m[..., None]) + bc * m[..., None]
        hh = 256
        step = max(1, comp.shape[0] // hh)
        small = comp[::step, ::step]
        tiles.append(small)
    wmax = sum(x.shape[1] for x in tiles) + 8 * (len(tiles) + 1)
    hmax = max(x.shape[0] for x in tiles) + 16
    canvas = np.ones((hmax, wmax, 3)) * 0.12
    x = 8
    for tl in tiles:
        canvas[8:8 + tl.shape[0], x:x + tl.shape[1]] = tl
        x += tl.shape[1] + 8
    (DW / "renders").mkdir(parents=True, exist_ok=True)
    T.write_png(DW / "renders" / "decal_textures_sheet.png", canvas)


def read_png(path):
    """Minimal PNG reader for our own 8-bit, non-interlaced, filter-typed PNGs (grey or RGB)."""
    import struct
    import zlib
    data = path.read_bytes()
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, bd, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    ch = {0: 1, 2: 3}[ctype]
    raw = zlib.decompress(idat)
    stride = w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    for r in range(h):
        f = raw[r * (stride + 1)]
        line = np.frombuffer(raw[r * (stride + 1) + 1:(r + 1) * (stride + 1)], np.uint8).astype(np.int32)
        if f == 0:
            cur = line
        elif f == 2:
            cur = (line + prev) & 255
        else:                                   # sub / average / paeth (not written by write_png, which uses 0)
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                if f == 1:
                    cur[i] = (line[i] + a) & 255
                elif f == 3:
                    cur[i] = (line[i] + (a + b) // 2) & 255
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                    cur[i] = (line[i] + pr) & 255
        out[r] = cur
        prev = cur
    a = out.reshape(h, w, ch).astype(np.float64) / 255.0
    return a[..., 0] if ch == 1 else a


def main():
    t0 = time.time()
    rep = {}
    for fn in (moss_foot, rain_streak, grime, lichen, water_stain, worn_path):
        fn(rep)
        print("DECAL", fn.__name__, json.dumps(rep[list(rep)[-1]]), flush=True)
    sheet(rep)
    DW.mkdir(parents=True, exist_ok=True)
    (DW / "decal_textures.json").write_text(json.dumps({"date": "2026-09-29", "textures": rep,
                                                        "surfaces_srgb": SURF, "sec": round(time.time() - t0, 1)},
                                                       indent=1), encoding="utf-8")
    print("DONE", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
