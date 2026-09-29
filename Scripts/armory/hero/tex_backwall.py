"""Textures of the hero rear bay (hero_backwall.py), all NEW files (never overwrites another set):

  T_AK_HScreen_BC / _ORM / _N.png   the rear screens' damask (back_wall.png; final r2): a LARGE irregular leaf damask
                                    - a domain-warped Voronoi net of wandering dark veins (two to three leaf cells
                                    across a screen), each leaf darkening toward its outline, a sparse finer crackle
                                    inside - on a cool grey-taupe ground. 1024 x 2048 = 0.52 x 1.04 m, tileable in
                                    both directions.
  T_AK_HHalo_BC / _ORM / _N.png     the painting's backlight halo (fix r4): a 1D warm falloff (u = 0 at the paper edge
                                    to u = 1 at the surround), used as an emissive picture (emit_image) on the halo
                                    ring and the pilasters' / rails' inner returns, so the glow spills softly outward.
  T_AK_HPaintingTall_BC / _ORM / _N  final r1 (blind judge: the paper must run from the table top to under the canopy
                                    and fill the bay): the user's pine painting (T_AK_HPainting_BC, cut from
                                    back_wall.png by tex_painting.py) set on one tall sheet of backlit paper that spans
                                    the painting panel AND the new SM_AK_H_PaintingBase under it (hero_backwall
                                    PAPER_Z0-PAPER_Z1): the pine's ground sits just above the hero table's top, plain
                                    paper (the sheet's own plain rows, mirrored) continues above the crown and below the
                                    ground, the sheet's edge bloom is kept at the new top and bottom edges. 2048 x 4096.
                                    Needs bpy to read the source PNG: blender -b --factory-startup --python
                                    Scripts/armory/hero/tex_backwall.py -- tall

numpy only (runs under Blender's bundled python or with blender -b --python). The normal maps are DirectX (green down),
like every kit map (build_armory_kit flips green for Blender).
Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_backwall.py
"""
import math
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TEX = ROOT / "Exports" / "ArmoryKit" / "Textures"
SCREEN_W, SCREEN_H = 0.52, 1.04        # metres covered by one screen tile (hero_backwall.SCREEN_TILE)
RES = 1024 / SCREEN_W                  # px per metre (isotropic)
# final r2 (blind judge: the r1 net read as a small, dense, regular quilting of rosettes and bows; back_wall.png's
# screens carry a LARGE, irregular leafy damask - two to three leaf cells across the panel, outlined by wandering dark
# veins, a finer crackle of veins inside them - on a cooler grey-taupe ground): an organic, domain-warped Voronoi leaf
# net (8 cells per tile, ~0.25 m across) plus a sparse inner crackle, no mirror symmetry (tileable both ways)
LEAF_COLS, LEAF_ROWS = 2, 4          # leaf cells per tile (hex-offset rows)
VEIN_COLS, VEIN_ROWS = 5, 10         # the inner crackle


def write_png(path, arr):
    arr = np.ascontiguousarray(np.clip(arr, 0, 255).astype(np.uint8))
    h, w, ch = arr.shape
    ct = {1: 0, 3: 2, 4: 6}[ch]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def blur(img, sigma_px):
    """Periodic Gaussian blur (FFT): the tile stays seamless."""
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def noise(h, w, sigma_px, seed):
    """Periodic smooth noise in [-1, 1]."""
    r = np.random.default_rng(seed).standard_normal((h, w))
    n = blur(r, sigma_px)
    return n / (np.abs(n).max() + 1e-9)


def fbm(h, w, seed, scales=(90, 40, 16, 6), amps=(1.0, 0.6, 0.35, 0.2)):
    out = sum(a * noise(h, w, s, seed + i) for i, (s, a) in enumerate(zip(scales, amps)))
    return out / sum(amps)


def periodic_voronoi(X, Z, seeds, lobes=None):
    """F1 / F2 distances (metres) to periodic seeds over the SCREEN_W x SCREEN_H tile, the owning seed's index and the
    angle / distance to it. lobes: per seed (n, phase, amplitude) - the distance is scaled by 1 - a cos(n theta - phase),
    so every cell grows n rounded lobes (a leaf outline) instead of straight Voronoi edges."""
    f1 = np.full(X.shape, 9.0, np.float32)
    f2 = np.full(X.shape, 9.0, np.float32)
    idx = np.zeros(X.shape, np.int32)
    ang = np.zeros(X.shape, np.float32)
    rad = np.zeros(X.shape, np.float32)
    for k, (sx, sz) in enumerate(seeds):
        for ox in (-SCREEN_W, 0.0, SCREEN_W):
            for oz in (-SCREEN_H, 0.0, SCREEN_H):
                dx, dz = X - (sx + ox), Z - (sz + oz)
                r = np.hypot(dx, dz).astype(np.float32)
                th = np.arctan2(dz, dx).astype(np.float32)
                d = r
                if lobes is not None:
                    n, ph, am = lobes[k]
                    d = r * (1.0 - am * np.cos(n * th - ph))
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                idx = np.where(closer, k, idx)
                ang = np.where(closer, th, ang)
                rad = np.where(closer, r, rad)
                f1 = np.where(closer, d, f1)
    return f1, f2, idx, ang, rad


def jittered(cols, rows, jit, seed):
    r = np.random.default_rng(seed)
    cw, rh = SCREEN_W / cols, SCREEN_H / rows
    return [(((c + 0.5 + 0.5 * (j % 2)) * cw + r.uniform(-jit, jit) * cw) % SCREEN_W,
             ((j + 0.5) * rh + r.uniform(-jit, jit) * rh) % SCREEN_H) for j in range(rows) for c in range(cols)]


def screen():
    """The leaf damask (see LEAF_COLS): Voronoi cell edges on a domain-warped plane are the leaf outlines (soft,
    blotchy dark veins of varying width), each cell darkens a little toward its outline (a puffy leaf), a sparse finer
    crackle of veins runs inside the cells, all over a mottled cool grey-taupe ground. Periodic noise and periodic
    Voronoi keep the tile seamless."""
    h, w = int(round(SCREEN_H * RES)), int(round(SCREEN_W * RES))
    zz, xx = np.meshgrid((np.arange(h) + 0.5) / RES, (np.arange(w) + 0.5) / RES, indexing="ij")
    warp = 0.022
    X = xx + warp * fbm(h, w, 41, scales=(160, 50, 18), amps=(1.0, 0.6, 0.25))
    Z = zz + warp * fbm(h, w, 43, scales=(160, 50, 18), amps=(1.0, 0.6, 0.25))
    seeds = jittered(LEAF_COLS, LEAF_ROWS, 0.25, 7)
    r_ = np.random.default_rng(13)
    lobes = [(int(r_.integers(4, 7)), r_.uniform(0, 2 * math.pi), r_.uniform(0.10, 0.16)) for _ in seeds]
    f1, f2, idx, ang, rad = periodic_voronoi(X, Z, seeds, lobes)
    e = f2 - f1                                                   # ~ the distance to the leaf outline
    wid = 0.0065 * np.clip(1.0 + 0.6 * fbm(h, w, 51, scales=(60, 20), amps=(1.0, 0.5)) / 0.5, 0.3, 1.8)
    vein = np.exp(-(e / wid) ** 2)
    rim = np.exp(-e / 0.045)                                       # the leaf darkening toward its outline
    # the leaf's own veins: n_k ribs radiating from its heart between the lobes, fading out toward the outline
    nk = np.asarray([l[0] for l in lobes])[idx]
    phk = np.asarray([l[1] for l in lobes])[idx]
    seg = 2 * math.pi / nk
    dth = np.mod(ang - phk / nk + seg / 2, seg) - seg / 2
    rib = np.exp(-((rad * np.sin(dth)) / 0.0028) ** 2) * np.clip(rad / 0.025, 0, 1) * np.clip(e / 0.03, 0, 1)
    rib *= np.clip(0.4 + 0.9 * fbm(h, w, 81, scales=(40, 15), amps=(1.0, 0.5)) / 0.5, 0, 1)
    X2 = xx + 0.012 * fbm(h, w, 61, scales=(50, 18), amps=(1.0, 0.5))
    Z2 = zz + 0.012 * fbm(h, w, 63, scales=(50, 18), amps=(1.0, 0.5))
    g1, g2 = periodic_voronoi(X2, Z2, jittered(VEIN_COLS, VEIN_ROWS, 0.4, 9))[:2]
    crack = np.exp(-((g2 - g1) / 0.0028) ** 2)
    crack *= np.clip(0.2 + 0.9 * fbm(h, w, 71, scales=(90, 35), amps=(1.0, 0.5)) / 0.5, 0, 1)   # sparse, broken
    crack *= np.clip(e / 0.02, 0, 1)
    blot = fbm(h, w, 11, scales=(40, 16, 6), amps=(1.0, 0.8, 0.5))
    blot = blot / blot.std()
    mott = fbm(h, w, 17, scales=(160, 70, 30), amps=(1.0, 0.7, 0.5))
    mott = mott / mott.std()
    fine = fbm(h, w, 23, scales=(8, 3, 1.2), amps=(1.0, 0.7, 0.5))
    fine = fine / fine.std()
    cell = np.random.default_rng(3).uniform(-1, 1, LEAF_COLS * LEAF_ROWS)[idx]   # each leaf a slightly other tone
    ink_amt = (0.95 * vein + 0.7 * rib + 0.4 * crack) * np.clip(0.75 + 0.35 * blot, 0.25, 1.3) + 0.28 * rim
    ink_amt = np.clip(blur(ink_amt, 1.6), 0, 1)                   # a printed, slightly soft edge
    ground = np.array([88.0, 81.0, 74.0])                          # cool grey-taupe
    ink = np.array([52.0, 46.0, 41.0])
    tone = 1.0 + 0.035 * cell[..., None] + 0.045 * mott[..., None] + 0.018 * fine[..., None]
    t = ink_amt[..., None]
    bc = (ground * (1 - t) + ink * t) * tone
    height = -0.5 * vein - 0.3 * rib - 0.2 * crack - 0.15 * rim + 0.04 * fine
    rough = 0.84 + 0.06 * ink_amt + 0.01 * fine
    occ = 1 - 0.15 * np.clip(-height * 2, 0, 1)
    orm = np.stack([255 * occ, 255 * rough, np.zeros_like(rough)], -1)
    return bc, orm, normal_map(height, 1.0)


def normal_map(height, strength):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * strength
    gz = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * strength     # rows run up (z)
    n = np.stack([-gx, -gz, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1                                    # DirectX: green down
    return (n * 0.5 + 0.5) * 255


def srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055) * 255


def halo():
    """u = 0 at the paper edge: a warm cream at full strength, falling off smoothly to a dark amber at u = 1."""
    w, h = 256, 16
    u = (np.arange(w) + 0.5) / w
    f = np.exp(-1.2 * u) * (1 - u) ** 1.3 + 0.002       # a broad soft falloff (5-8 cm of glow)
    hot = np.array([1.0, 0.68, 0.32])                  # linear warm cream-amber (the backlit paper)
    warm = np.array([1.0, 0.46, 0.10])                 # linear amber (the spill on the surround)
    mixw = np.clip(u * 1.6, 0, 1)[:, None]
    col = (hot * (1 - mixw) + warm * mixw) * f[:, None]
    row = srgb(col)
    bc = np.repeat(row[None, :, :], h, 0)
    orm = np.zeros((h, w, 3))
    orm[..., 0], orm[..., 1] = 255, 230
    nrm = np.zeros((h, w, 3))
    nrm[..., 0], nrm[..., 1], nrm[..., 2] = 128, 128, 255
    return bc, orm, nrm


def save(name, bc, orm, nrm, flip=True):
    import sys
    # r20 (2026-09-28): --out DIR writes a trial set into a test copy's Textures (build_armory_kit --preview-dir reads
    # <dir>/Textures first), so trial sets never land in Exports/ArmoryKit/Textures
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else TEX
    out.mkdir(parents=True, exist_ok=True)
    for suf, a in (("BC", bc), ("ORM", orm), ("N", nrm)):
        path = out / f"T_AK_H{name}_{suf}.png"
        write_png(path, a[::-1] if flip else a)       # rows were built bottom-up (v up)
        print("wrote", path, a.shape)


def painting_tall():
    """The tall paper sheet (see the module docstring). Rows are built bottom-up (v up), like the other sets."""
    import sys
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hero_backwall as HB
    im = bpy.data.images.load(str(TEX / "T_AK_HPainting_BC.png"))
    sw, sh = im.size
    src = np.array(im.pixels[:], dtype=np.float32).reshape(sh, sw, 4)[..., :3]      # bottom-up, 0-1 sRGB values
    bpy.data.images.remove(im)
    img_h = HB.PAPER_IMG_W / HB.PAINT_ASPECT               # the painting's height on the wall (m; r20 fix round: the
    # picture keeps the 2.08 m paper's height scale; the wider 2.48 m paper spreads it 1.19x across by its U)
    OW, OH = 2048, 4096
    z = HB.PAPER_Z0 + (np.arange(OH) + 0.5) / OH * (HB.PAPER_Z1 - HB.PAPER_Z0)
    s = (z - HB.IMG_Z0) / img_h * sh - 0.5                  # fractional source row
    EB, P0 = 58, 1760                                      # the top edge band; the plain-paper band P0-P1
    P1 = sh - EB - 1
    extra = (HB.PAPER_Z1 - HB.IMG_Z0) / img_h * sh - sh    # rows of plain paper above the sheet
    assert extra / 2 < P1 - P0, "not enough plain paper above the crown"
    s_bot = (HB.PAPER_Z0 - HB.IMG_Z0) / img_h * sh          # the new bottom edge (negative)

    def filler(u):                                         # u rows up from the new bottom edge
        if u < EB:
            return sh - 1 - u                              # the edge band, flipped (bloom at the new bottom edge)
        k = (u - EB) % (2 * (P1 - P0))
        return P1 - k if k < P1 - P0 else P0 + (k - (P1 - P0))
    s_top = (HB.PAPER_Z1 - HB.IMG_Z0) / img_h * sh           # final r2: the paper ends inside the picture: its plain top
    cut, XF = sh - s_top, 40.0                              # rows are cut, its top edge band kept (shifted down)
    # r16 fix round: the paper must end inside the picture; the mirrored filler above the sheet showed as a smeared
    # ghost band across the paper's top (r16 final C10), so hero_backwall's IMG_Z0 / PAPER_IMG_W must keep cut > 0
    assert cut > 0, f"painting_tall: the picture ends {-cut:.0f} rows under the paper's top (raise PAPER_IMG_W)"
    rows_a, rows_b, wts = [], [], []
    for si in s:
        if cut > 0 and si >= s_top - EB - XF:              # final r2: direct rows cross-faded into the shifted band
            a = float(np.clip((si - (s_top - EB - XF)) / XF, 0, 1))
            a = a * a * (3 - 2 * a)
            rows_a.append(si), rows_b.append(min(si + cut, sh - 1)), wts.append(a)
        elif si >= P1 + 1:                                   # above the plain band: filler, then the top edge band
            t = si - (P1 + 1)
            if t >= extra:
                r = P1 + 1 + (t - extra)
            elif t < extra / 2:
                r = P1 - t
            else:
                r = P1 - (extra - t)
            rows_a.append(r), rows_b.append(r), wts.append(0.0)
        elif si < 0:                                       # below the sheet: its bottom rows mirrored (no seam),
            f = filler(si - s_bot)                         # cross-faded into plain paper over 40 rows
            a = float(np.clip(1.0 + si / 40.0, 0, 1))
            a = a * a * (3 - 2 * a)
            rows_a.append(f), rows_b.append(-si), wts.append(a)
        else:
            rows_a.append(si), rows_b.append(si), wts.append(1.0)

    def sample(rows):
        r = np.clip(np.asarray(rows, dtype=np.float64), 0, sh - 1)
        r0 = np.floor(r).astype(int)
        r1 = np.clip(r0 + 1, 0, sh - 1)
        f = (r - r0)[:, None, None]
        return src[r0] * (1 - f) + src[r1] * f
    A, B = sample(rows_a), sample(rows_b)
    wv = np.asarray(wts)[:, None, None]
    out = A * (1 - wv) + B * wv
    if sw != OW:
        xs = (np.arange(OW) + 0.5) * sw / OW - 0.5
        x0 = np.clip(np.floor(xs).astype(int), 0, sw - 1)
        x1 = np.clip(x0 + 1, 0, sw - 1)
        fx = (xs - x0)[None, :, None]
        out = out[:, x0] * (1 - fx) + out[:, x1] * fx
    bc = out * 255.0
    flat_orm = np.zeros((64, 64, 3))
    flat_orm[..., 0], flat_orm[..., 1] = 255, 217
    flat_n = np.zeros((64, 64, 3))
    flat_n[..., 0], flat_n[..., 1], flat_n[..., 2] = 128, 128, 255
    return bc, flat_orm, flat_n


if __name__ == "__main__":
    import sys
    if "tall" in sys.argv:
        save("PaintingTall", *painting_tall())
    else:
        save("Screen", *screen())
        save("Halo", *halo(), flip=False)
