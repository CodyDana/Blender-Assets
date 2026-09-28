"""Shared helpers for the pack's recolour-map generators (Scripts/unreal/materials/maps/).

Pure numpy + zlib, plus two bpy helpers that are imported lazily (the generators run inside headless Blender 5.2, whose
bundled Python has numpy; the system Python has neither numpy nor PIL).

What lives here:
    sRGB <-> linear (the exact IEC 61966-2-1 piecewise curve, float64)
    a PNG writer for 16-bit greyscale and 8-bit RGBA (no colour chunks: data maps never self-describe as sRGB) and a
        reader for the files it writes (filter types 0/1/2), so every written file is decoded back and compared
    bpy PNG loading (Non-Color, row 0 at the TOP), used to read the shipped maps and to cross-check our own files
        through a second, independent decoder
    Unreal's mip chain as the generators model it: TMGS_FROM_TEXTURE_GROUP = SimpleAverage, a 2x2 box in LINEAR light
        (an sRGB texture is decoded before filtering), each level stored in the texture's own format
    the MF_TintDetail + MF_AlbedoRollOff twin (MATERIAL_PLAN.md section 4, material_spec.json material_functions) and
        the fitting of its per-part constants (Detail Mean, Highlight Ratio, cubic moments)
    the V3 banding / clip / detail metrics and CIEDE2000
"""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[4]
EXPORTS = PROJECT / "Exports"
WORK = PROJECT / "WorkFiles" / "materials"
LUM = np.array([0.2126, 0.7152, 0.0722])

# MF_TintDetail / MF_AlbedoRollOff constants (material_spec.json masters.M_Fabric_Master, MATERIAL_PLAN.md 3.2 / 4)
ALBEDO_CEILING = 0.9
DARK_FOLLOW = 0.5
KNEE, LIMIT = 0.85, 0.95
MOMENT_POINTS = (0.0, 0.5, 1.0, 1.5)

# V3 stress colours (linear), material_spec.json verification.V3_recolour_stress
STRESS = {"white": (0.8, 0.8, 0.8), "cream": (0.8, 0.7, 0.5), "pastel_pink": (0.85, 0.6, 0.7),
          "saturated_red": (0.8, 0.02, 0.02), "saturated_blue": (0.02, 0.05, 0.8), "yellow": (0.85, 0.75, 0.05),
          "mid_grey": (0.18, 0.18, 0.18), "near_black": (0.01, 0.01, 0.01)}
REPORT_ONLY = {"extreme_white": (0.95, 0.95, 0.95)}


# =========================================================================== colour


def s2l(x):
    x = np.asarray(x, np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def q8_srgb(linear):
    """Linear -> stored 8-bit sRGB level (0..255, int16 so differences never wrap)."""
    return np.rint(l2s(linear) * 255.0).astype(np.int16)


def q8_linear(x):
    return np.rint(np.clip(np.asarray(x, np.float64), 0.0, 1.0) * 255.0).astype(np.int16)


def q16_linear(x):
    return np.rint(np.clip(np.asarray(x, np.float64), 0.0, 1.0) * 65535.0).astype(np.int32)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path) -> str:
    return Path(path).resolve().relative_to(PROJECT).as_posix()


def rnd(v, n=6):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [rnd(x, n) for x in v]
    return round(float(v), n)


# =========================================================================== PNG


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)


def png_write(path, data: np.ndarray, bits: int) -> str:
    """Write integer ``data`` (H, W) grey or (H, W, 4) RGBA, ROW 0 AT THE TOP, as a PNG with NO colour chunks.

    bits 16 -> big-endian 16-bit samples; bits 8 -> 8-bit.  Every row uses PNG filter 2 (Up), which compresses the
    smooth detail maps well and which ``png_read`` decodes exactly."""
    a = np.asarray(data)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    colour_type = {1: 0, 3: 2, 4: 6}[c]
    maxv = (1 << bits) - 1
    if a.min() < 0 or a.max() > maxv:
        raise ValueError(f"{path}: samples outside 0..{maxv}")
    raw = a.astype(">u2" if bits == 16 else "u1").reshape(h, w * c).view(np.uint8).reshape(h, -1)
    up = raw.copy()
    up[1:] = (raw[1:].astype(np.int16) - raw[:-1].astype(np.int16)).astype(np.uint8)   # mod 256
    rows = np.concatenate([np.full((h, 1), 2, np.uint8), up], axis=1)
    rows[0, 0] = 0                                    # row 0 has no row above: filter None
    rows[0, 1:] = raw[0]
    ihdr = struct.pack(">IIBBBBB", w, h, bits, colour_type, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(rows.tobytes(), 9))
            + _chunk(b"IEND", b""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(blob)
    return str(path)


def png_chunks(path) -> list:
    data = Path(path).read_bytes()
    out, i = [], 8
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        out.append(data[i + 4:i + 8].decode("latin-1"))
        i += 12 + length
    return out


def png_read(path) -> tuple:
    """Decode a non-interlaced PNG whose rows use filters 0 / 1 / 2 (what ``png_write`` emits).

    Returns (integer array (H, W[, C]) row 0 at the top, bit depth, colour type)."""
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{path} is not a PNG")
    i, idat, ihdr = 8, [], None
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        tag, body = data[i + 4:i + 8], data[i + 8:i + 8 + length]
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat.append(body)
        i += 12 + length
    w, h, bits, colour_type, _c, _f, interlace = ihdr
    if interlace:
        raise ValueError("interlaced PNG not supported")
    c = {0: 1, 2: 3, 4: 2, 6: 4}[colour_type]
    bpp = c * bits // 8
    stride = w * bpp
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(h, stride + 1)
    filt, rows = raw[:, 0], raw[:, 1:].astype(np.int32)
    out = np.empty((h, stride), np.uint8)
    for y in range(h):
        f = int(filt[y])
        r = rows[y]
        if f == 0:
            out[y] = r
        elif f == 1:
            v = r.reshape(-1, bpp)
            out[y] = (np.cumsum(v, axis=0) & 0xFF).reshape(-1)
        elif f == 2:
            out[y] = (r + (out[y - 1] if y else 0)) & 0xFF
        else:
            raise ValueError(f"{path}: row {y} uses PNG filter {f}, which this reader does not decode")
    if bits == 16:
        arr = out.view(">u2").reshape(h, w, c).astype(np.int32)
    else:
        arr = out.reshape(h, w, c).astype(np.int32)
    return (arr[..., 0] if c == 1 else arr), bits, colour_type


def load_png_bpy(path) -> np.ndarray:
    """(H, W, 4) float32 stored values (Non-Color: no transfer applied), ROW 0 AT THE TOP."""
    import bpy
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        return px.reshape(h, w, 4)[::-1].copy()
    finally:
        bpy.data.images.remove(img)


def load_levels8(path) -> np.ndarray:
    """A shipped 8-bit PNG as integer levels (H, W, 4), row 0 at the top."""
    return np.rint(load_png_bpy(path).astype(np.float64) * 255.0).astype(np.int16)


# =========================================================================== mips


def block_mean(a: np.ndarray, f: int) -> np.ndarray:
    if f == 1:
        return a
    h, w = a.shape[:2]
    return a.reshape(h // f, f, w // f, f, *a.shape[2:]).mean(axis=(1, 3))


def mip_factors(h: int, w: int):
    f, out = 1, []
    while h // f >= 1 and w // f >= 1:
        out.append(f)
        if h // f == 1 and w // f == 1:
            break
        f *= 2
    return out


# =========================================================================== MF_TintDetail twin


def cubic_through(xs, ys):
    """Coefficients (a0, a1, a2, a3), ASCENDING, of the cubic through the four points (exact)."""
    v = np.vander(np.asarray(xs, np.float64), 4, increasing=True)
    return np.linalg.solve(v, np.asarray(ys, np.float64))


def fabric_constants(n: np.ndarray) -> dict:
    """Detail Mean, Detail Highlight Ratio and the two moment cubics of the detail multiple ``n`` (mean ~1)."""
    n = np.asarray(n, np.float64).ravel()
    lo = n <= 1.0
    nn = np.maximum(n, 1e-6)
    vals_lo, vals_hi = [], []
    for c in MOMENT_POINTS:
        p = np.power(nn, c) if c else np.ones_like(nn)
        vals_lo.append(float(np.where(lo, p, 0.0).mean()))
        vals_hi.append(float(np.where(lo, 0.0, p).mean()))
    return {"mean": float(n.mean()), "highlight_ratio": float(np.percentile(n, 99.9)),
            "moments_low": [float(v) for v in cubic_through(MOMENT_POINTS, vals_lo)],
            "moments_high": [float(v) for v in cubic_through(MOMENT_POINTS, vals_hi)],
            "moment_samples_low": vals_lo, "moment_samples_high": vals_hi,
            "n_min": float(n.min()), "n_max": float(n.max()), "fraction_n_le_1": float(lo.mean())}


def _cubic(coef, c):
    return coef[0] + coef[1] * c + coef[2] * c * c + coef[3] * c * c * c


def tint_detail(n, colour, k: dict, strength=1.0, follow=DARK_FOLLOW, ceiling=ALBEDO_CEILING):
    """MF_TintDetail: returns ((N, 3) albedo before the roll-off, info)."""
    col = np.asarray(colour, np.float64)[:3]
    n = np.asarray(n, np.float64).ravel()
    h = np.log(ceiling / max(col.max(), 1e-4)) / np.log(k["highlight_ratio"])
    c_hi = min(strength, max(h, 0.0))
    c_lo = strength + (c_hi - strength) * follow
    nn = np.maximum(n, 1e-6)
    npr = np.where(n <= 1.0, np.power(nn, c_lo), np.power(nn, c_hi))
    e = _cubic(k["moments_low"], c_lo) + _cubic(k["moments_high"], c_hi)
    albedo = col[None, :] * (npr * (k["mean"] / e))[:, None]
    return albedo, {"H": float(h), "C_hi": float(c_hi), "C_lo": float(c_lo), "E": float(e)}


def rolloff(a, knee=KNEE, limit=LIMIT):
    a = np.asarray(a, np.float64)
    m = a.max(axis=-1, keepdims=True)
    if knee >= limit:
        return np.minimum(a, limit)
    t = np.maximum(m - knee, 0.0)
    mm = knee + (limit - knee) * (1.0 - np.exp(-t / (limit - knee)))
    return np.where(m > knee, a * (mm / np.maximum(m, 1e-12)), a)


# =========================================================================== metrics


def banding(s8: np.ndarray, dom: int) -> dict:
    """V3 banding metric on the 8-bit sRGB output's dominant channel inside its p1..p99 range."""
    ch = s8[:, dom]
    lo, hi = np.percentile(ch, 1), np.percentile(ch, 99)
    occ = np.unique(ch[(ch >= lo) & (ch <= hi)])
    gap = int(np.diff(occ).max()) if len(occ) > 1 else 0
    span = float(hi - lo)
    return {"max_gap_levels": gap, "levels_used": int(len(occ)), "p1_p99_span_levels": span,
            "occupied_fraction_of_span": round(len(occ) / max(span, 1.0), 4),
            "pass": bool(gap <= 3 and len(occ) >= 0.5 * span)}


def _lab(linear):
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = np.asarray(linear, np.float64) @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de2000(lin1, lin2) -> np.ndarray:
    """CIEDE2000 between two (..., 3) LINEAR sRGB arrays (D65)."""
    l1, l2 = _lab(lin1), _lab(lin2)
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    cm = (c1 + c2) / 2
    g = 0.5 * (1 - np.sqrt(cm ** 7 / (cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dL, dC = L2 - L1, c2p - c1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(c1p * c2p == 0, 0, dh)
    dH = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))
    Lm, Cm = (L1 + L2) / 2, (c1p + c2p) / 2
    hs = h1p + h2p
    hm = np.where(c1p * c2p == 0, hs,
                  np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    t = (1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm))
         + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.20 * np.cos(np.radians(4 * hm - 63)))
    dth = 30 * np.exp(-(((hm - 275) / 25) ** 2))
    rc = 2 * np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7))
    sl = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    sc, sh = 1 + 0.045 * Cm, 1 + 0.015 * Cm * t
    rt = -np.sin(np.radians(2 * dth)) * rc
    return np.sqrt((dL / sl) ** 2 + (dC / sc) ** 2 + (dH / sh) ** 2 + rt * (dC / sc) * (dH / sh))


def level_diff_stats(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(np.asarray(a, np.int32) - np.asarray(b, np.int32))
    if d.ndim == 3 or (d.ndim == 2 and d.shape[-1] in (3, 4) and d.shape[0] > 4):
        d = d.max(axis=-1)                           # per texel: the worst channel
    return {"max": int(d.max()), "mean": round(float(d.mean()), 5), "texels_diff_gt0": int((d > 0).sum()),
            "texels_diff_gt1": int((d > 1).sum()), "texels": int(d.size)}


def stress_fabric(n, k: dict, colours: dict, default_colour) -> dict:
    """Run the MF twin (tint + roll-off) for every stress colour; V3 metrics per colour."""
    base, _ = tint_detail(n, default_colour, k)
    ly0 = np.log(np.maximum(base @ LUM, 1e-7))
    out = {}
    for name, col in colours.items():
        a, info = tint_detail(n, col, k)
        a = rolloff(a)
        s8 = q8_srgb(a)
        dom = int(np.argmax(col))
        ly = np.log(np.maximum(a @ LUM, 1e-7))
        mean_a = a.mean(axis=0)
        target = np.asarray(col[:3]) * k["mean"]
        r = {**{kk: round(v, 5) for kk, v in info.items()}, "clip_frac": round(float((a >= 0.949).any(axis=1).mean()), 6),
             **banding(s8, dom), "std_ratio_logL": round(float(ly.std() / ly0.std()), 4),
             "corr_logL": round(float(np.corrcoef(ly, ly0)[0, 1]), 5),
             "mean_albedo": rnd(mean_a, 5), "target_mean": rnd(target, 5),
             "dE00_mean_vs_target": round(float(de2000(mean_a, target)), 3)}
        r["pass"] = bool(r["clip_frac"] <= 0.001 and r["pass"] and r["std_ratio_logL"] >= 0.25
                         and (max(col) > 0.85 or r["dE00_mean_vs_target"] <= 3.0))
        out[name] = r
    return out


def write_json(path, obj) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")
    return str(path)
