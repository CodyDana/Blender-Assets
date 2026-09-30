"""Kit 8 (courtyard stone + wooden climb props) textures: granite, granite ground-contact moss trim, dark weathered
timber, forged iron, hemp rope and the lantern's warm glow panes.

All OUR OWN procedural work (periodic FFT noise, the armory / kit 2 approach): no photo, scan or third-party source.
Tiling sets wrap in U and V (the seam score in the report measures it); the moss trim wraps in U only (V runs from the
ground line up 1.0 m); the glow pane is a unique 0-1 picture per pane.

Density (STYLE_GUIDE 6, hero / near pieces 5.12 px/cm): granite and timber 1024 px over 2.0 m, the moss trim 1024 x 512
over 2.0 x 1.0 m, iron 512 px over 1.0 m, rope 512 px along 0.25 m (U) x 256 px around the strand.

Writes Exports/DojoKit/Props/stone/Textures/T_DKP_Stone_<Set>_{BC,N,ORM}.png (BC sRGB; N DirectX green, linear;
ORM = AO, roughness, metal, linear) and WorkFiles/dojo/build/props/stone/textures_report.json.

Run: py -3 Scripts/dojo/props/stone/make_stone_textures.py      (numpy only)
"""
import json
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "Exports" / "DojoKit" / "Props" / "stone" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "stone"
REPORT = {}


# --------------------------------------------------------------------------- helpers (copied from kit 2's
# make_ground_textures.py, read-only reuse)

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
    """Periodic 1/f^beta noise, zero mean, unit std (rows = v, columns = u). stretch_u > 1 elongates along u."""
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


def shear(a, k=1):
    """Periodic diagonal shear: features stretched along u become stretched along the (u, v) diagonal."""
    h, w = a.shape
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    return a[(r + k * c * h // w) % h, c]


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


def save_set(name, bc_srgb, height_m, rough, px_m, ao=None, metal=0.0, generic=True, note="", wrap_v=True):
    OUT.mkdir(parents=True, exist_ok=True)
    bc_srgb = np.clip(bc_srgb, 0, 1)
    nrm = normal_dx(height_m, px_m)
    ao = np.ones_like(rough) if ao is None else ao
    metal = np.full_like(rough, metal) if np.isscalar(metal) else metal
    orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), np.clip(metal, 0, 1)])
    write_png(OUT / f"T_DKP_Stone_{name}_BC.png", bc_srgb)
    write_png(OUT / f"T_DKP_Stone_{name}_N.png", nrm)
    write_png(OUT / f"T_DKP_Stone_{name}_ORM.png", orm)
    h, w = bc_srgb.shape[:2]
    ang = np.degrees(np.arccos(np.clip(nrm[..., 2] * 2 - 1, -1, 1)))
    REPORT[name] = {
        "size_px": [w, h], "tile_m": [round(w * px_m, 4), round(h * px_m, 4)], "px_per_cm": round(0.01 / px_m, 3),
        "source": "own procedural (numpy FFT noise)", "generic_or_unique": "generic" if generic else "unique",
        "mean_srgb_8bit": [int(round(float(x) * 255)) for x in bc_srgb.reshape(-1, 3).mean(0)],
        "albedo_max_srgb": round(float(bc_srgb.max()), 3), "rough_mean": round(float(np.clip(rough, 0.02, 1).mean()), 3),
        "metal_mean": round(float(metal.mean()), 3), "ao_mean": round(float(ao.mean()), 3),
        "normal_tilt_deg_mean_p95": [round(float(ang.mean()), 2), round(float(np.percentile(ang, 95)), 2)],
        "seam_score_bc_rows_cols": seam_score(bc_srgb), "wraps_in_v": wrap_v, "note": note}
    print(name, json.dumps(REPORT[name]))


def chips(n, cell, seed, warp=0.0):
    """Periodic Voronoi chips (the tooled / hammer-dressed face on the sheet's granite): F1 and F2 distances in pixels
    to jittered points, one per cell, plus a random value and a random tilt per chip. warp (in cells) domain-warps the
    lookup with periodic noise, so the flakes are irregular instead of a paving pattern (f1)."""
    G = max(1, int(round(n / cell)))
    cell = n / G                      # f1: a whole number of cells per tile, so the pattern wraps for any cell size
    rng = np.random.default_rng(seed)
    pt = rng.uniform(0.1, 0.9, (G, G, 2))
    val = rng.uniform(0, 1, (G, G))
    tilt = rng.normal(0, 1, (G, G, 2))
    ii, jj = np.mgrid[0:n, 0:n].astype(float)
    if warp:
        ii = ii + warp * cell * 0.5 * pnoise(n, n, 1.6, seed + 101, fmin=0.02)
        jj = jj + warp * cell * 0.5 * pnoise(n, n, 1.6, seed + 102, fmin=0.02)
    ci, cj = np.floor(ii / cell).astype(int), np.floor(jj / cell).astype(int)
    F1 = np.full((n, n), 1e9)
    F2 = np.full((n, n), 1e9)
    V = np.zeros((n, n))
    TI = np.zeros((n, n))
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ni, nj = ci + di, cj + dj
            wi, wj = ni % G, nj % G
            py = (ni + pt[wi, wj, 0]) * cell
            px = (nj + pt[wi, wj, 1]) * cell
            dy, dx = ii - py, jj - px
            d = np.sqrt(dx * dx + dy * dy)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            V = np.where(closer, val[wi, wj], V)
            TI = np.where(closer, (dx * tilt[wi, wj, 1] + dy * tilt[wi, wj, 0]) / cell, TI)
            F1 = np.where(closer, d, F1)
    return F1 / cell, F2 / cell, V, TI


# --------------------------------------------------------------------------- shared field helpers

def blur(a, sigma_px):
    """Periodic Gaussian blur (FFT), so blurred fields still tile."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def mix(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


# --------------------------------------------------------------------------- granite

def granite_fields(n, px_m, seed):
    """f1 (fix round): rough, bush-hammered granite. The r0 set was a smooth marbled noise that read as concrete at game
    distance. Now: two scales of pillowed flakes (periodic Voronoi, 4.4 cm and 2.2 cm) with deep dark crevices between
    them, dense hammer pits, a gentle large undulation, cavity darkening from the height itself, granite crystals, and
    lichen / moss specks that gather in the recesses. Grey with a slight blue cast in the shadows (the sheet).
    Returns linear colour, height (m), roughness, AO and the cavity field (for the moss sets)."""
    # crumpled, hammer-dressed face: two scales of tilted facets (periodic warped Voronoi), their borders only partly
    # open; a few jagged fissures (zero crossings of band-limited noise, jittered); block-scale lumps; hammer pits
    f1, f2, cv, ct = chips(n, 20, seed + 12, warp=0.35)
    g1, g2, gv, gt = chips(n, 9, seed + 13, warp=0.3)
    gate_f = np.clip(pnoise(n, n, 1.4, seed + 19, fmin=0.01) * 0.9 + 0.1, 0, 1)
    edge_f = np.clip(1 - (f2 - f1) / 0.08, 0, 1) ** 2 * gate_f
    jit = 0.35 * pnoise(n, n, 1.0, seed + 20, fmin=0.15, fmax=0.5)
    c1 = pnoise(n, n, 1.0, seed + 14, fmin=0.03, fmax=0.10) + jit
    c2 = pnoise(n, n, 1.0, seed + 15, fmin=0.06, fmax=0.18) + jit
    gate1 = np.clip(pnoise(n, n, 1.6, seed + 17, fmin=0.01) * 0.9 + 0.2, 0, 1)
    gate2 = np.clip(pnoise(n, n, 1.4, seed + 18, fmin=0.01) * 0.9 - 0.1, 0, 1)
    crack1 = np.clip(1 - np.abs(c1) / 0.09, 0, 1) ** 1.5 * gate1
    crack2 = np.clip(1 - np.abs(c2) / 0.07, 0, 1) ** 1.5 * gate2
    pit_n = pnoise(n, n, 0.2, seed + 4, fmin=0.35)
    pits = np.clip((pit_n - 1.1) * 0.9, 0, 1)
    lump = pnoise(n, n, 1.0, seed + 16, fmin=0.01, fmax=0.05)
    und = pnoise(n, n, 1.9, seed + 10, fmin=0.004, fmax=0.02)
    fine = pnoise(n, n, 0.1, seed + 3, fmin=0.4)
    height = (0.0012 * und + 0.0018 * lump + 0.0024 * ct * (0.5 + cv) + 0.0009 * gt * (0.5 + gv)
              - 0.0010 * f1 ** 2 - 0.0012 * edge_f - 0.0030 * crack1 - 0.0015 * crack2 - 0.0007 * pits
              + 0.00008 * fine)
    cav = height - blur(height, 9)
    cav = cav / (cav.std() + 1e-12)
    # colour: pale warm-grey highs, mid grey body, slightly cool dark lows (the sheet's granite)
    hi_c, mid_c, lo_c = to_lin(srgb("#A09C95")), to_lin(srgb("#6F6B66")), to_lin(srgb("#3C3D40"))
    t = np.clip(0.60 + 0.16 * cav + 0.08 * lump + 0.22 * (cv - 0.5) + 0.10 * (gv - 0.5), 0, 1)
    col = np.where((t < 0.5)[..., None], mix(lo_c[None, None, :], mid_c[None, None, :], t * 2),
                   mix(mid_c[None, None, :], hi_c[None, None, :], (t - 0.5) * 2))
    crystal = pnoise(n, n, 0.35, seed + 1, fmin=0.25)
    crystal2 = pnoise(n, n, 0.35, seed + 2, fmin=0.25)
    mica = np.clip((crystal - 1.7) * 2.5, 0, 1)
    felds = np.clip((crystal2 - 1.4) * 2.5, 0, 1)
    col = col * (1 + 0.06 * fine)[..., None]
    col = col * (1 - 0.45 * mica[..., None]) + to_lin(srgb("#E4E1DA"))[None, None, :] * 0.25 * felds[..., None]
    col = col * (1 - np.clip(0.80 * crack1 + 0.55 * crack2 + 0.35 * edge_f, 0, 0.85))[..., None] * (1 - 0.5 * pits)[..., None]
    blot = np.clip(pnoise(n, n, 1.3, seed + 11, fmin=0.06) - 1.1, 0, 1.5) / 1.5
    col = col * (1 - 0.30 * blot[..., None])
    patch = pnoise(n, n, 1.8, seed + 7, fmin=0.02)
    speck = pnoise(n, n, 0.4, seed + 8, fmin=0.2)
    crust = np.clip((patch - 1.0) * 1.2, 0, 1) * np.clip((speck + 0.5) * 0.8, 0, 1)
    col = mix(col, to_lin(srgb("#A3A493"))[None, None, :], 0.40 * crust)
    rec = np.clip(-cav * 0.5 + 0.6 * crack1, 0, 1)
    ylich = np.clip((speck - 1.2) * 1.6, 0, 1) * np.clip(patch + 0.9, 0, 1) * (0.25 + 0.75 * rec)
    col = mix(col, to_lin(srgb("#827A30"))[None, None, :], 0.85 * np.clip(ylich, 0, 1))
    crev_l, crev_s = crack1, crack2
    rough = np.clip(0.84 + 0.05 * fine + 0.08 * pits - 0.08 * felds + 0.04 * crust, 0, 1)
    ao = np.clip(1.0 - 0.42 * crev_l - 0.22 * crev_s - 0.35 * pits - 0.10 * np.clip(-cav, 0, 3), 0.2, 1)
    return col, height, rough, ao, cav


def granite(seed=801):
    n, px_m = 1024, 2.0 / 1024
    col, height, rough, ao, cav = granite_fields(n, px_m, seed)
    save_set("Granite", to_srgb(col), height, rough, px_m, ao,
             note="GENERIC: rough bush-hammered lantern and well-block granite (f1); look pass: unify with kit 2's T_DKG_Granite")
    return col, height, rough, ao, cav


def moss_layer(h, w, seed):
    """Moss colour, height and fibre fields (the clumps the sheet puts on ledges and at the ground)."""
    fib = pnoise(h, w, 0.5, seed + 3, fmin=0.2)
    tuft = pnoise(h, w, 1.1, seed + 2, fmin=0.05)
    dark, mid, lite = to_lin(srgb("#3B4022")), to_lin(srgb("#63622E")), to_lin(srgb("#8E873E"))
    t = np.clip(0.5 + 0.35 * fib + 0.2 * tuft, 0, 1)
    mcol = mix(dark[None, None, :], mid[None, None, :], t)
    mcol = mix(mcol, lite[None, None, :], np.clip((fib - 0.9) * 0.8, 0, 0.7))
    mh = 0.004 * (0.55 + 0.30 * np.clip(fib, -1, 2) + 0.25 * np.clip(tuft, -1, 2))
    return mcol, mh, fib, tuft


def granite_ledge(g, seed=871):
    """NEW (f1): granite with moss clumps and lichen, for the TOP-facing faces of the lantern plinth steps, base tiers
    and cap (the sheet shows moss on every ledge). Tiles 2 x 2 m like the granite, so the two meet cleanly."""
    col, height, rough, ao, cav = g
    n = col.shape[0]
    px_m = 2.0 / n
    mcol, mh, fib, tuft = moss_layer(n, n, seed)
    patch = pnoise(n, n, 1.5, seed + 5, fmin=0.03)
    cover = np.clip((patch + 0.35 * np.clip(-cav, 0, 3) + 0.30 * fib - 1.15) * 1.4, 0, 1)
    col = mix(col, mcol, cover)
    height = height + mh * cover
    rough = np.clip(rough * (1 - cover) + 0.95 * cover, 0, 1)
    ao = ao * (1 - 0.25 * cover * np.clip(-fib, 0, 1))
    save_set("GraniteLedge", to_srgb(col), height, rough, px_m, ao, generic=False,
             note="UNIQUE-ish: granite + moss clumps for up-facing ledges (tiers, plinth steps, cap); tiles with Granite")


def granite_moss(g, seed=851):
    """Ground-contact trim: the granite of the tiling set (so trimmed and plain faces match), with moss, grass-stain
    grime and damp darkening rising from the ground line. U wraps (2.0 m), V = height above the ground 0-1.0 m
    (v = 0 is the ground line, the bottom image row)."""
    col, height, rough, ao, cav = [a[512:] for a in g]
    h, w = col.shape[:2]
    px_m = 2.0 / 1024
    z = (h - 1 - np.arange(h))[:, None] * px_m * np.ones((1, w))
    edge = 0.10 + 0.05 * pnoise(1, w, 1.6, seed)[0][None, :] + 0.03 * pnoise(1, w, 0.8, seed + 1)[0][None, :]
    mcol, mh, fib, tuft = moss_layer(h, w, seed)
    reach = edge + 0.14 * np.clip(tuft - 0.5, 0, 3) + 0.04 * np.clip(-cav, 0, 3)
    moss = np.clip((reach - z) / 0.03, 0, 1)
    moss = np.clip(moss * (0.75 + 0.35 * fib), 0, 1)
    damp = np.exp(-z / 0.22)
    col = col * (1 - 0.30 * damp[..., None])
    col = mix(col, mcol, moss)
    height = height + mh * moss
    rough = np.clip(rough * (1 - moss) + 0.95 * moss - 0.05 * damp, 0, 1)
    ao = ao * (1 - 0.25 * damp) * (1 - 0.2 * moss * np.clip(-fib, 0, 1))
    save_set("GraniteMoss", to_srgb(col), height, rough, px_m, ao, generic=False, wrap_v=False,
             note="UNIQUE-ish trim: ground-contact granite with moss; U wraps 2.0 m, V = 0-1.0 m above the ground")


# --------------------------------------------------------------------------- timber

def timber_fields(n, seed):
    """Rough-sawn aged timber (f1): periodic grain lines along U (sharp dark latewood), bent round 14 knots with dark
    cores, silver-grey weathering on the raised earlywood, long end-grain splits and checks, darker stains. Every field
    is periodic (FFT noise, wrapped knots), so the tile wraps. Returns masks; the caller applies the palette."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bend = np.zeros((n, n))
    knot = np.zeros((n, n))
    for _ in range(14):
        cx, cy = rng.uniform(0, n), rng.uniform(0, n)
        rx, ry = rng.uniform(9, 20), rng.uniform(5, 10)
        dx = (xx - cx + n / 2) % n - n / 2
        dy = (yy - cy + n / 2) % n - n / 2
        d = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
        knot = np.maximum(knot, np.clip(1.25 - d, 0, 1) * (0.75 + 0.25 * np.cos(d * 10)))
        bend += np.tanh(dy / ry) * np.exp(-((dx / (rx * 3.0)) ** 2 + (dy / (ry * 2.5)) ** 2))
    # grain: periodic noise stretched hard along U, rows displaced round the knots (a periodic row shift)
    lines = pnoise(n, n, 1.1, seed + 9, stretch_u=45.0, fmin=0.05)
    shift = np.round(bend * 6).astype(int)
    rows = (np.arange(n)[:, None] + shift) % n
    lines = lines[rows, np.arange(n)[None, :]]
    late = np.clip((lines - 0.55) / 0.9, 0, 1) ** 1.3
    fine = pnoise(n, n, 0.7, seed + 3, stretch_u=25.0)
    weather = pnoise(n, n, 1.6, seed + 4, stretch_u=5.0, fmin=0.03)
    ck = pnoise(n, n, 1.0, seed + 5, stretch_u=70.0)
    split_mask = np.clip(pnoise(n, n, 1.6, seed + 6, stretch_u=8.0) - 0.5, 0, 1)
    checks = np.clip((np.abs(ck) < 0.05).astype(float) * split_mask * 3.0, 0, 1)
    checks = np.clip(blur(checks, 0.6) * 1.5, 0, 1)
    stain = np.clip(pnoise(n, n, 1.7, seed + 7, fmin=0.03) - 0.6, 0, 1.5) / 1.5
    return late, fine, weather, checks, knot, stain


def timber_set(name, seed, base_hex, late_hex, silver_hex, silver_amt, note, generic=True):
    n, px_m = 1024, 2.0 / 1024
    late, fine, weather, checks, knot, stain = timber_fields(n, seed)
    base = to_lin(srgb(base_hex))
    col = base[None, None, :] * (1.0 + 0.10 * fine)[..., None]
    silver = np.clip(silver_amt + 0.18 * weather + 0.10 * fine, 0, 0.85) * (1 - late * 0.8)
    col = mix(col, to_lin(srgb(silver_hex))[None, None, :] * (1 + 0.08 * fine[..., None]), silver)
    col = mix(col, to_lin(srgb(late_hex))[None, None, :], np.clip(late * 0.85, 0, 1))
    col = mix(col, to_lin(srgb("#1E150E"))[None, None, :], np.clip(knot * 0.8, 0, 1))
    col = col * (1 - 0.35 * stain[..., None])
    col = col * (1 - 0.8 * checks[..., None])
    height = 0.0007 * (1 - late) + 0.0003 * fine - 0.0022 * checks - 0.0005 * knot + 0.0004 * weather
    rough = np.clip(0.80 + 0.05 * fine + 0.10 * checks - 0.05 * knot + 0.05 * silver, 0, 1)
    ao = np.clip(1 - 0.45 * checks - 0.12 * late, 0.3, 1)
    save_set(name, to_srgb(col), height, rough, px_m, ao, generic=generic, note=note)


def timber(seed=901):
    timber_set("Timber", seed, "#5A4130", "#281A11", "#8A7D70", 0.10,
               "GENERIC: dark weathered brown timber (well frame, cover, cistern, crates, bucket); grain along U")
    timber_set("TimberGrey", seed + 50, "#6A625A", "#302A25", "#A39B90", 0.30,
               "GENERIC-ish: silver-grey sun-weathered roof boards (both well roofs; the sheet's roofs are grey)")


# --------------------------------------------------------------------------- iron

def iron(seed=951):
    """Forged iron (f1, measurer): BARE iron is metal 1.0, black mill scale and rust are metal 0.0, nothing between
    (ASSET_GUIDELINES: metals 0.95-1.0, no partial metallic). Bare iron shows on the hammered highs."""
    n, px_m = 512, 1.0 / 512
    ham = pnoise(n, n, 1.2, seed, fmin=0.08)
    fine = pnoise(n, n, 0.4, seed + 1, fmin=0.3)
    rp = pnoise(n, n, 1.5, seed + 2, fmin=0.04)
    rust = np.clip((rp - 1.5) * 1.2, 0, 1) * np.clip(pnoise(n, n, 0.6, seed + 3, fmin=0.15) + 0.8, 0, 1)
    scale_f = pnoise(n, n, 1.7, seed + 4, fmin=0.03) + 0.35 * ham
    bare = (scale_f > 0.15) & (rust < 0.25)                       # hard mask: metal is 0 or 1
    bare_col = to_lin(srgb("#66625E"))
    scale_col = to_lin(srgb("#36322F"))
    rust_col = to_lin(srgb("#6A3E25"))
    col = np.where(bare[..., None], bare_col[None, None, :], scale_col[None, None, :])
    col = col * (1 + 0.12 * ham + 0.06 * fine)[..., None]
    col = mix(col, rust_col[None, None, :] * (1 + 0.2 * fine[..., None]), np.clip(rust * 1.3, 0, 1))
    height = 0.0005 * ham + 0.0001 * fine + 0.0003 * rust + 0.0002 * (~bare)
    rough = np.where(bare, 0.48 + 0.08 * ham, 0.74 + 0.05 * fine) + 0.18 * rust
    metal = bare.astype(float)
    save_set("Iron", to_srgb(col), height, np.clip(rough, 0, 1), px_m, 1 - 0.1 * np.clip(-ham, 0, 2), metal=metal,
             note="GENERIC: forged iron; metal 1.0 on bare iron, 0.0 on mill scale and rust, no partial values")


# --------------------------------------------------------------------------- rope

def rope(seed=971):
    """Three-strand hemp rope. U runs along the rope (512 px = 0.25 m, 20.48 px/cm), V around it (128 px = one
    circumference of the 2.2 cm rope, 18.5 px/cm). 12 lays per 0.25 m and 3 strands round: both integers, so the helix
    wraps in U and V."""
    w, h = 512, 128
    v, u = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    s = (u * 12 + v * 3) % 1.0
    prof = np.sin(np.pi * s) ** 0.7
    fib = pnoise(h, w, 0.6, seed, fmin=0.2)
    fibs = shear(pnoise(h, w, 0.8, seed + 1, stretch_u=8.0), 1)
    col = to_lin(srgb("#8A6D46"))[None, None, :] * (0.55 + 0.55 * prof + 0.10 * fibs + 0.05 * fib)[..., None]
    col = col * (1 - 0.25 * np.clip(pnoise(h, w, 1.8, seed + 2), 0, 2)[..., None] / 2)
    height = 0.0020 * prof + 0.0002 * fibs
    rough = 0.85 + 0.05 * fib
    ao = 0.55 + 0.45 * prof
    save_set("Rope", to_srgb(col), height, rough, 0.25 / w, ao,
             note="GENERIC-ish: hemp rope (M_Fabric_Master candidate); U along the rope 20.48 px/cm, V around 18.5 px/cm")
    REPORT["Rope"]["px_per_cm_around"] = round(128 / (2 * np.pi * 0.011) / 100, 2)
    REPORT["Rope"]["density_note"] = ("nominal 20.48 px/cm along U and 18.52 around (V); the area-weighted value ON THE "
                                      "MESH is in measure.json (SM_DKP_Stone_WellRope texel, f1: 19.93). r0 claimed 20.48 "
                                      "while its 256 px V gave 27.75 on the mesh (the measurer's figure)")


# --------------------------------------------------------------------------- lantern glow pane

def glow(seed=991):
    """Warm glowing paper pane, one per window pane (unique 0-1 UV). f1: deeper amber (the sheet's windows measure
    sRGB 229, 190, 139; r0 rendered 237, 201, 168). Used as the EMISSION colour; albedo is dark."""
    n = 256
    v, u = np.mgrid[0:n, 0:n] / (n - 1.0)
    r = np.sqrt(((u - 0.5) / 0.55) ** 2 + ((v - 0.52) / 0.62) ** 2)
    core = np.exp(-r * r * 2.2)
    fib = pnoise(n, n, 0.9, seed, stretch_u=3.0)
    t = np.clip(core * (1 + 0.04 * fib), 0, 1)[..., None]
    hot, deep = to_lin(srgb("#FFC468")), to_lin(srgb("#D9580A"))
    col = deep[None, None, :] * (1 - t) + hot[None, None, :] * t
    col = col * (0.55 + 0.45 * t)
    rough = np.full((n, n), 0.9)
    save_set("LanternGlow", to_srgb(col), 0.00005 * fib, rough, 0.25 / n, None, generic=False, wrap_v=False,
             note="UNIQUE: emissive pane picture (emission colour); strength lives in the material")


def moss(seed=881):
    """r2 (library pass): the ONLY stone-kit texture left. Granite, timber, iron, rope and the lantern glass now come
    from the shared dojo library (Scripts/dojo/materials). Moss is modelled as real cushions on the ledges, cap valleys
    and at the ground (build_stone_props.moss_pads); this set is their surface: olive clumps (the sheet's moss measures
    sRGB median (80, 80, 61), p20 (58, 59, 37), p80 (114, 113, 92) on the stone sheet), fibre relief, rough and dull.
    512 px over 1.0 m (5.12 px/cm), wraps in U and V."""
    n = 512
    px_m = 1.0 / n
    fib = pnoise(n, n, 0.45, seed + 3, fmin=0.25)
    tuft = pnoise(n, n, 1.2, seed + 2, fmin=0.04)
    speck = pnoise(n, n, 0.2, seed + 7, fmin=0.4)
    dark, mid, lite, dry = (to_lin(srgb(h)) for h in ("#34381C", "#555430", "#7E7A44", "#7A7258"))
    t = np.clip(0.5 + 0.30 * fib + 0.28 * tuft, 0, 1)
    col = mix(dark[None, None, :], mid[None, None, :], t)
    col = mix(col, lite[None, None, :], np.clip((fib + 0.4 * tuft - 0.8) * 0.7, 0, 0.6))
    col = mix(col, dry[None, None, :], np.clip((speck - 1.3) * 0.6, 0, 0.35))
    height = 0.0022 * (0.5 + 0.35 * np.clip(fib, -1.5, 2.5) + 0.30 * np.clip(tuft, -1.5, 2.5))
    rough = np.clip(0.90 + 0.05 * fib, 0.8, 1.0)
    ao = np.clip(0.80 + 0.10 * fib + 0.08 * tuft, 0.45, 1.0)
    save_set("Moss", to_srgb(col), height, rough, px_m, ao, generic=True,
             note="generic moss cushion surface (own procedural); tile 1.0 m; for the modelled moss pads")


def main():
    # r2: the granite / timber / iron / rope / glow sets are superseded by the shared dojo library
    # (Exports/DojoKit/Materials/Textures/T_DJ_*); their generators stay above for the record.
    moss()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "textures_report.json").write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    print("wrote", len(REPORT), "sets to", OUT)


if __name__ == "__main__":
    main()
