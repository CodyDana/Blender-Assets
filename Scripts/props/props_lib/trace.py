#!/usr/bin/env python
"""props_lib.trace - vectorise the paper bomb's reference drawing, the user's own design.

WHY THIS MODULE EXISTS
----------------------
The paper bomb's design was authored by the user.  They fed it to ChatGPT, which re-rendered
it, and they supplied that re-render to us WITHOUT metadata (300 x 653 px, the version with
the real kanji).  Their instruction, in their words: "i wrote it, go ahead and match it
exactly."  So for this asset tracing the reference is the METHOD: every element this module
emits is derived directly from ONE source image, and the build records which file (path and
SHA-256) and how.  See ``provenance()``.

    ONE SOURCE ONLY.  ``SOURCE`` below is the single reference.  The older 1024 x 1536 file
    that carried a C2PA signature was removed from the reference set on the user's
    instruction and parked under WorkFiles/paperbomb/_removed_reference/; ``read_source``
    refuses any path under that folder, so nothing can be derived from it by accident.
    Re-tracing from a higher-resolution copy the user supplies later is ONE parameter:
    pass ``source=`` (or ``--trace-source`` on the build) and every element is re-derived.

WHAT IT DOES
------------
    read_source     decode the PNG ourselves (exact stored integers, no colour management),
                    hash it, refuse the removed folder
    fit_card        the card's four edges to sub-pixel accuracy (the rg_s1 instrument's
                    method, re-implemented here so the fit belongs to the source image) and
                    the bilinear map card-mm <-> source-px it implies
    unmix           per-pixel linear unmixing into paper / black ink / red ink.  RED IS
                    CLASSIFIED FIRST: a deep seal red is darker than any sensible black
                    threshold, so the red endmember is LOCAL (taken from nearby red cores)
                    and a dark red core unmixes as red, not as grey
    trace_element   the tracer: the ink-probability field is resampled onto a fine grid
                    with a separable kernel, contoured at its half level with sub-pixel
                    marching squares, split at its corners and fitted with clamped cubic
                    B-splines by least squares.  The result is resolution-independent
                    control points in CARD MILLIMETRES
    rasterise       exact-area scanline fill of those curves at any px/mm
    score_element   IoU and edge distance against the source at the source's own grid

Everything here is deterministic numpy: no randomness, no threads, no bpy.  The same
source bytes give the same curves bit for bit, which is what keeps the build's maps
byte-identical from one run to the next.
"""
from __future__ import annotations

import hashlib
import math
import os
import struct
import zlib
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

TRACE_VERSION = "1.0.0"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

#: THE one reference.  Byte-identical to the user's Downloads/paperbomb.png.
SOURCE = os.path.join(PROJECT_ROOT, "References", "PaperBomb",
                      "paperbomb_guide_v2_real_glyphs.png")
SOURCE_SHA256 = "670acbd782c9a43bb0b2838851ec6bec7aaae144f18aaeb5e8cf45ca7ef01099"

#: The folder the signed file was parked in.  Nothing may be read from it.
REMOVED_REFERENCE_FRAGMENT = "workfiles/paperbomb/_removed_reference"

CARD_W_MM = 70.0
CARD_H_MM = 162.29


class RemovedReference(RuntimeError):
    """Something asked to read the removed (C2PA-signed) reference.  Never allowed."""


# ===========================================================================
# 1.  The source image
# ===========================================================================

def _paeth_row(cur, prev, bpp):
    stride = len(cur)
    rl = [0] * stride
    for i in range(stride):
        if i >= bpp:
            a = rl[i - bpp]
            c = prev[i - bpp]
        else:
            a = 0
            c = 0
        b = prev[i]
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            pr = a
        elif pb <= pc:
            pr = b
        else:
            pr = c
        rl[i] = (cur[i] + pr) & 0xFF
    return rl


def decode_png(data: bytes) -> tuple[np.ndarray, dict]:
    """PNG bytes -> (uint8/uint16 array (H, W, C) of STORED values, info).

    8/16-bit, colour types 0/2/4/6, non-interlaced: what the reference is.  Decoding the
    IDAT ourselves gives the exact integers in the file with no colour management in the
    way, and records every ancillary chunk so the build can state the file carries no
    generator metadata.
    """
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos = 8
    idat = []
    info: dict = {"chunks": []}
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        info["chunks"].append(ctype.decode("latin-1"))
        if ctype == b"IHDR":
            w, h, bd, ct, _comp, _filt, inter = struct.unpack(">IIBBBBB", body)
            info.update(width=w, height=h, bit_depth=bd, colour_type=ct, interlace=inter)
            if inter != 0 or bd not in (8, 16) or ct not in (0, 2, 4, 6):
                raise ValueError("unsupported PNG layout %r" % ((bd, ct, inter),))
        elif ctype == b"IDAT":
            idat.append(body)
        elif ctype in (b"tEXt", b"iTXt", b"zTXt"):
            info.setdefault("text_keys", []).append(body.split(b"\x00", 1)[0].decode("latin-1"))
        elif ctype == b"IEND":
            break
    w, h, bd, ct = info["width"], info["height"], info["bit_depth"], info["colour_type"]
    nch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(b"".join(idat))
    stride = (w * nch * bd) // 8
    bpp = max(1, (nch * bd) // 8)
    buf = np.frombuffer(raw[:(stride + 1) * h], np.uint8).reshape(h, stride + 1)
    out = np.empty((h, stride), np.uint8)
    prev = np.zeros(stride, np.uint8)
    for y in range(h):
        f = int(buf[y, 0])
        cur = buf[y, 1:]
        if f == 0:
            rec = cur.copy()
        elif f == 1:
            rec = np.empty(stride, np.uint8)
            for k in range(bpp):
                rec[k::bpp] = (np.cumsum(cur[k::bpp].astype(np.uint32)) & 0xFF).astype(np.uint8)
        elif f == 2:
            rec = (cur.astype(np.uint16) + prev).astype(np.uint8)
        elif f == 3:
            cl = cur.tolist(); pl = prev.tolist(); rl = [0] * stride
            for i in range(stride):
                left = rl[i - bpp] if i >= bpp else 0
                rl[i] = (cl[i] + ((left + pl[i]) >> 1)) & 0xFF
            rec = np.array(rl, np.uint8)
        elif f == 4:
            rec = np.array(_paeth_row(cur.tolist(), prev.tolist(), bpp), np.uint8)
        else:
            raise ValueError("bad PNG filter %d" % f)
        out[y] = rec
        prev = rec
    if bd == 8:
        arr = out.reshape(h, w, nch)
    else:
        arr = ((out[:, 0::2].astype(np.uint16) << 8) | out[:, 1::2]).reshape(h, w, nch)
    return arr, info


@dataclass
class Source:
    path: str
    sha256: str
    nbytes: int
    rgb: np.ndarray            # (H, W, 3) float64 STORED sRGB 0..1, row 0 = top
    info: dict

    @property
    def H(self) -> int:
        return int(self.rgb.shape[0])

    @property
    def W(self) -> int:
        return int(self.rgb.shape[1])

    def record(self) -> dict:
        meta = [c for c in self.info.get("chunks", [])
                if c not in ("IHDR", "IDAT", "IEND", "PLTE", "tRNS")]
        return {
            "path": os.path.relpath(self.path, PROJECT_ROOT).replace("\\", "/"),
            "sha256": self.sha256,
            "bytes": self.nbytes,
            "width": self.W, "height": self.H,
            "bit_depth": self.info.get("bit_depth"),
            "colour_type": self.info.get("colour_type"),
            "ancillary_chunks": meta,
            "text_chunks": list(self.info.get("text_keys", [])),
            "has_c2pa_or_text_metadata": bool(self.info.get("text_keys"))
                                         or any(c in ("caBX", "iTXt", "zTXt", "tEXt", "eXIf")
                                                for c in meta),
        }


def _normpath(p: str) -> str:
    return os.path.abspath(os.fspath(p)).replace("\\", "/").lower()


def read_source(path: str | None = None) -> Source:
    """Read THE reference (or the one ``path`` names) and hash it."""
    p = os.fspath(path or SOURCE)
    if REMOVED_REFERENCE_FRAGMENT in _normpath(p):
        raise RemovedReference(
            "%r is under the removed-reference folder.  The user removed that file from the "
            "reference set; nothing may be traced, sampled or measured from it." % p)
    with open(p, "rb") as fh:
        data = fh.read()
    arr, info = decode_png(data)
    scale = 65535.0 if arr.dtype == np.uint16 else 255.0
    a = arr.astype(np.float64) / scale
    if a.shape[2] in (1, 2):
        a = np.repeat(a[..., :1], 3, axis=2)
    return Source(path=os.path.abspath(p), sha256=hashlib.sha256(data).hexdigest(),
                  nbytes=len(data), rgb=np.ascontiguousarray(a[..., :3]), info=info)


# ===========================================================================
# 2.  Colour helpers
# ===========================================================================

def srgb_to_linear(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def srgb_to_lab(rgb_stored) -> np.ndarray:
    """Stored sRGB -> CIELAB (D65).  The perceptual space the colour gates use."""
    lin = srgb_to_linear(rgb_stored)
    M = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    white = np.array([0.95047, 1.0, 1.08883])
    t = xyz / white
    d = 6.0 / 29.0
    f = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4.0 / 29.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def delta_e2000(lab1, lab2) -> np.ndarray:
    """CIEDE2000 between two Lab arrays (broadcasting)."""
    L1, a1, b1 = np.moveaxis(np.asarray(lab1, np.float64), -1, 0)
    L2, a2, b2 = np.moveaxis(np.asarray(lab2, np.float64), -1, 0)
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2)
    Cb = 0.5 * (C1 + C2)
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p = (1 + G) * a1; a2p = (1 + G) * a2
    C1p = np.hypot(a1p, b1); C2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(C1p * C2p == 0, 0.0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh) / 2)
    Lbp = 0.5 * (L1 + L2)
    Cbp = 0.5 * (C1p + C2p)
    hsum = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hsum,
                   np.where(np.abs(h1p - h2p) <= 180, hsum / 2,
                            np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                   + Rt * (dCp / Sc) * (dHp / Sh))


# ===========================================================================
# 3.  Small image operators (numpy only)
# ===========================================================================

def gauss_blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian with reflected borders."""
    if sigma <= 0:
        return np.asarray(a, np.float64).copy()
    r = max(1, int(math.ceil(3.0 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = np.asarray(a, np.float64)
    for axis in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="reflect")
        acc = np.zeros_like(out)
        n = out.shape[axis]
        for i, w in enumerate(k):
            sl = [slice(None)] * out.ndim
            sl[axis] = slice(i, i + n)
            acc += w * p[tuple(sl)]
        out = acc
    return out


def norm_conv(values: np.ndarray, weight: np.ndarray, sigma: float, fallback) -> np.ndarray:
    """Normalised convolution: a weighted local mean that fills where weight is 0."""
    w = np.asarray(weight, np.float64)
    if values.ndim == 3:
        num = np.stack([gauss_blur(values[..., c] * w, sigma) for c in range(values.shape[2])], -1)
        den = gauss_blur(w, sigma)[..., None]
    else:
        num = gauss_blur(values * w, sigma)
        den = gauss_blur(w, sigma)
    fb = np.asarray(fallback, np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 1e-4, num / np.maximum(den, 1e-12), fb)
    return out


def dilate(m: np.ndarray, r: int = 1) -> np.ndarray:
    m = np.asarray(m, bool)
    for _ in range(r):
        p = np.pad(m, 1)
        acc = np.zeros_like(m)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                acc |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
        m = acc
    return m


def erode(m: np.ndarray, r: int = 1) -> np.ndarray:
    return ~dilate(~np.asarray(m, bool), r)


def label(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """8-connected components by iterative union-find over runs (deterministic)."""
    mask = np.asarray(mask, bool)
    h, w = mask.shape
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    rows = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            rows.append([])
            continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1)
        runs = []
        prev = rows[y - 1] if y else []
        pi = 0
        for s, e in zip(st.tolist(), en.tolist()):
            lbl = 0
            while pi < len(prev) and prev[pi][1] < s:
                pi += 1
            j = pi
            while j < len(prev) and prev[j][0] <= e:
                if lbl == 0:
                    lbl = find(prev[j][2])
                else:
                    ra, rb = find(lbl), find(prev[j][2])
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
                        lbl = min(ra, rb)
                j += 1
            if lbl == 0:
                lbl = len(parent)
                parent.append(lbl)
            runs.append((s, e, lbl))
        rows.append(runs)
    lab = np.zeros((h, w), np.int32)
    remap: dict = {}
    for y, runs in enumerate(rows):
        for s, e, l in runs:
            r = find(l)
            if r not in remap:
                remap[r] = len(remap) + 1
            lab[y, s:e] = remap[r]
    return lab, len(remap)


# ===========================================================================
# 4.  The card: four edges, four corners, one map
# ===========================================================================

def _robust_line(t: np.ndarray, p: np.ndarray, iters: int = 4, k: float = 2.5):
    keep = np.ones(len(t), bool)
    a = b = 0.0
    for _ in range(iters + 1):
        A = np.stack([t[keep], np.ones(int(keep.sum()))], 1)
        (a, b), *_ = np.linalg.lstsq(A, p[keep], rcond=None)
        res = p - (a * t + b)
        s = float(np.std(res[keep]))
        if s < 1e-9:
            break
        nk = np.abs(res) < k * s
        if nk.sum() < 8 or np.array_equal(nk, keep):
            break
        keep = nk
    res = p - (a * t + b)
    return float(a), float(b), float(np.sqrt((res[keep] ** 2).mean())), int(keep.sum())


@dataclass
class CardFit:
    """Where the card sits in the source image, to sub-pixel accuracy.

    Coordinates are CONTINUOUS source pixels: pixel (i, j) covers [j, j+1) x [i, i+1) and
    its centre is (j + 0.5, i + 0.5).  The four corners are the intersections of the four
    fitted straight edges (the chamfers are cut off them, exactly as REFERENCE_SPEC does).
    """
    sides: dict
    TL: tuple
    TR: tuple
    BL: tuple
    BR: tuple
    W: int
    H: int

    @property
    def ppmm(self) -> float:
        return 0.5 * ((self.TR[0] - self.TL[0]) + (self.BR[0] - self.BL[0])) / CARD_W_MM

    @property
    def aspect(self) -> float:
        w = 0.5 * ((self.TR[0] - self.TL[0]) + (self.BR[0] - self.BL[0]))
        h = 0.5 * ((self.BL[1] - self.TL[1]) + (self.BR[1] - self.TR[1]))
        return w / h

    def mm_to_px(self, x_mm, y_mm):
        """Card mm (x from left, y from top) -> continuous source px (bilinear in corners)."""
        u = np.asarray(x_mm, np.float64) / CARD_W_MM
        v = np.asarray(y_mm, np.float64) / CARD_H_MM
        TL, TR, BL, BR = (np.array(c, np.float64) for c in (self.TL, self.TR, self.BL, self.BR))
        px = ((1 - u) * (1 - v) * TL[0] + u * (1 - v) * TR[0]
              + (1 - u) * v * BL[0] + u * v * BR[0])
        py = ((1 - u) * (1 - v) * TL[1] + u * (1 - v) * TR[1]
              + (1 - u) * v * BL[1] + u * v * BR[1])
        return px, py

    def px_to_mm(self, px, py):
        """Inverse of ``mm_to_px`` by Newton iteration (the map is within 0.1 % of affine)."""
        px = np.asarray(px, np.float64); py = np.asarray(py, np.float64)
        x = (px - self.TL[0]) / self.ppmm
        y = (py - self.TL[1]) / self.ppmm
        for _ in range(6):
            fx, fy = self.mm_to_px(x, y)
            ex, ey = px - fx, py - fy
            h = 1e-3
            ax, ay = self.mm_to_px(x + h, y)
            bx, by = self.mm_to_px(x, y + h)
            j11 = (ax - fx) / h; j21 = (ay - fy) / h
            j12 = (bx - fx) / h; j22 = (by - fy) / h
            det = j11 * j22 - j12 * j21
            x = x + (j22 * ex - j12 * ey) / det
            y = y + (-j21 * ex + j11 * ey) / det
        return x, y

    def record(self) -> dict:
        return {
            "corners_px": {k: [round(float(v[0]), 4), round(float(v[1]), 4)]
                           for k, v in (("TL", self.TL), ("TR", self.TR),
                                        ("BL", self.BL), ("BR", self.BR))},
            "sides": self.sides,
            "ppmm": round(self.ppmm, 5),
            "aspect_w_over_h": round(self.aspect, 5),
            "card_mm": [CARD_W_MM, CARD_H_MM],
            "method": ("each edge: half-level crossing of warmth (R-B) between the "
                       "background and the paper on every scanline of the middle 64 %, "
                       "robust straight-line fit; corners are the edge intersections; "
                       "card mm -> source px is bilinear in the four corners"),
        }


def fit_card(src: Source) -> CardFit:
    w = src.rgb[..., 0] - src.rgb[..., 2]          # warmth: paper ~0.2, background ~0
    H, W = w.shape
    corners = np.concatenate([w[:8, :8].ravel(), w[:8, -8:].ravel(),
                              w[-8:, :8].ravel(), w[-8:, -8:].ravel()])
    lo = float(np.median(corners))
    core = w[int(0.06 * H):int(0.94 * H), int(0.10 * W):int(0.90 * W)]
    hi = float(np.median(core[core > lo + 0.05]))
    half = lo + 0.5 * (hi - lo)

    def crossings(side):
        vert = side in ("L", "R")
        n_lines = H if vert else W
        # a first pass over the whole card to find its extent on the other axis
        T, P = [], []
        for t in range(n_lines):
            line = w[t] if vert else w[:, t]
            above = np.flatnonzero(line > half)
            if len(above) < 8:
                continue
            e = int(above[0]) if side in ("L", "T") else int(above[-1])
            sgn = 1 if side in ("L", "T") else -1
            n = len(line)
            ins = [e + sgn * k for k in range(3, 9) if 0 <= e + sgn * k < n]
            outs = [e - sgn * k for k in range(1, 7) if 0 <= e - sgn * k < n]
            if len(ins) < 3 or len(outs) < 3:
                continue
            vi = float(np.median(line[ins])); vo = float(np.median(line[outs]))
            if vi - vo < 0.02:
                continue
            tgt = 0.5 * (vi + vo)
            c = None
            for k in range(8, -9, -1):
                k0 = e - sgn * k; k1 = e - sgn * (k - 1)
                if not (0 <= k0 < n and 0 <= k1 < n):
                    continue
                v0, v1 = line[k0], line[k1]
                if v0 <= tgt < v1:
                    f = 0.0 if v1 == v0 else (tgt - v0) / (v1 - v0)
                    c = k0 + f * (k1 - k0)
                    break
            if c is None:
                continue
            T.append(float(t)); P.append(float(c) + 0.5)
        return np.array(T), np.array(P)

    raw = {s: crossings(s) for s in ("L", "R", "T", "B")}
    # the middle 64 % of each side: clear of the chamfers
    ext_y = (raw["L"][0].min(), raw["L"][0].max())
    ext_x = (raw["T"][0].min(), raw["T"][0].max())
    sides = {}
    for s, (T, P) in raw.items():
        a0, a1 = ext_y if s in ("L", "R") else ext_x
        lo_t = a0 + 0.18 * (a1 - a0); hi_t = a0 + 0.82 * (a1 - a0)
        sel = (T >= lo_t) & (T <= hi_t)
        a, b, rms, n = _robust_line(T[sel] + 0.5, P[sel])
        sides[s] = {"a": round(a, 7), "b": round(b, 5), "rms_px": round(rms, 4), "n": n}

    def isect(sv, sh):
        av, bv = sides[sv]["a"], sides[sv]["b"]       # x = av*y + bv
        ah, bh = sides[sh]["a"], sides[sh]["b"]       # y = ah*x + bh
        y = (ah * bv + bh) / (1 - ah * av)
        return (av * y + bv, y)

    return CardFit(sides=sides, TL=isect("L", "T"), TR=isect("R", "T"),
                   BL=isect("L", "B"), BR=isect("R", "B"), W=W, H=H)


# ===========================================================================
# 5.  Unmixing: paper, black ink, red ink - red first
# ===========================================================================

#: Global black endmember, stored sRGB (REFERENCE_SPEC's black core, #080907).
BLACK_STORED = (0.0314, 0.0353, 0.0275)
#: Fallback red endmember (the ring's median, #D1190C) where no red core is near.
RED_STORED = (0.8196, 0.0980, 0.0471)
#: Fallback paper (#F6E4C1).
PAPER_STORED = (0.9647, 0.8941, 0.7569)


@dataclass
class Unmixed:
    alpha_k: np.ndarray        # black coverage 0..1
    alpha_r: np.ndarray        # red coverage 0..1
    paper: np.ndarray          # local paper colour (stored sRGB)
    red: np.ndarray            # local red endmember (stored sRGB)
    residual: np.ndarray       # per-pixel unmixing residual (stored units)
    red_first: np.ndarray      # bool: pixels decided red by chroma before unmixing


def unmix(src: Source, card_mask: np.ndarray | None = None) -> Unmixed:
    """Per-pixel least-squares unmixing into paper + black + red, red classified first.

    1. RED FIRST.  Black ink in this file is neutral (R - G within +-0.02 on 99 % of its
       pixels) and red ink is strongly chromatic (R - G > 0.35 on every red core).  Any
       pixel with R - G > 0.30 is a red core; the red endmember at every pixel is the
       normalised-convolution mean of the red cores near it (sigma 2.5 px), so a deep
       seal red (R 0.45) unmixes against a deep red and comes out as red at full
       coverage, not as half-black.
    2. PAPER.  The local paper colour is the normalised-convolution mean of pixels that
       are confidently paper (sigma 4 px), so the mottle does not read as ink.
    3. UNMIX.  pixel = P + ak (K - P) + ar (R - P), least squares over the three channels,
       projected onto ak, ar >= 0, ak + ar <= 1.
    """
    rgb = src.rgb
    H, W = rgb.shape[:2]
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    chroma = R - G
    lum = 0.2126 * R + 0.7152 * G + 0.0722 * B
    if card_mask is None:
        card_mask = np.ones((H, W), bool)
    red_core = card_mask & (chroma > 0.30) & (G < 0.30)
    red_first = card_mask & (chroma > 0.30)
    red_local = norm_conv(rgb, red_core.astype(np.float64), 2.5, RED_STORED)
    # widen the reach for pixels far from any core (anti-aliased fringes of thin reds)
    red_far = norm_conv(rgb, red_core.astype(np.float64), 8.0, RED_STORED)
    near = gauss_blur(red_core.astype(np.float64), 2.5) > 1e-3
    red_local = np.where(near[..., None], red_local, red_far)

    paper_px = card_mask & (lum > 0.80) & (np.abs(chroma - 0.07) < 0.06)
    paper_px = erode(paper_px, 1)
    paper = norm_conv(rgb, paper_px.astype(np.float64), 4.0, PAPER_STORED)
    paper_far = norm_conv(rgb, paper_px.astype(np.float64), 12.0, PAPER_STORED)
    near_p = gauss_blur(paper_px.astype(np.float64), 4.0) > 0.02
    paper = np.where(near_p[..., None], paper, paper_far)

    K = np.array(BLACK_STORED, np.float64)
    ek = K[None, None, :] - paper                  # black direction
    er = red_local - paper                         # red direction
    d = rgb - paper
    a11 = (ek * ek).sum(-1); a22 = (er * er).sum(-1); a12 = (ek * er).sum(-1)
    b1 = (ek * d).sum(-1); b2 = (er * d).sum(-1)
    det = a11 * a22 - a12 * a12
    det = np.where(np.abs(det) < 1e-12, 1e-12, det)
    ak = (a22 * b1 - a12 * b2) / det
    ar = (a11 * b2 - a12 * b1) / det

    def resid(k, r):
        return np.sqrt(((d - k[..., None] * ek - r[..., None] * er) ** 2).sum(-1))

    # projection onto the simplex {ak>=0, ar>=0, ak+ar<=1}: evaluate the interior
    # solution and the three edge solutions, keep the feasible one with least residual
    cands = []
    inside = (ak >= 0) & (ar >= 0) & (ak + ar <= 1)
    cands.append((np.where(inside, ak, np.nan), np.where(inside, ar, np.nan)))
    k_only = np.clip(b1 / np.maximum(a11, 1e-12), 0, 1)
    cands.append((k_only, np.zeros_like(k_only)))
    r_only = np.clip(b2 / np.maximum(a22, 1e-12), 0, 1)
    cands.append((np.zeros_like(r_only), r_only))
    # the ak + ar = 1 edge: pixel = K + t (R - K)
    ekr = er - ek
    t = np.clip(((d - ek) * ekr).sum(-1) / np.maximum((ekr * ekr).sum(-1), 1e-12), 0, 1)
    cands.append((1 - t, t))
    best_k = np.zeros((H, W)); best_r = np.zeros((H, W)); best_e = np.full((H, W), np.inf)
    for k, r in cands:
        ok = np.isfinite(k)
        e = np.where(ok, resid(np.nan_to_num(k), np.nan_to_num(r)), np.inf)
        better = e < best_e
        best_k = np.where(better, np.nan_to_num(k), best_k)
        best_r = np.where(better, np.nan_to_num(r), best_r)
        best_e = np.where(better, e, best_e)
    # RED FIRST: a red core is red.  Its darkness is the red's own value, carried by the
    # local red endmember, and never becomes black coverage.
    best_r = np.where(red_core, np.maximum(best_r, np.clip(best_k + best_r, 0, 1)), best_r)
    best_k = np.where(red_core, 0.0, best_k)
    best_k = np.where(card_mask, best_k, 0.0)
    best_r = np.where(card_mask, best_r, 0.0)
    return Unmixed(alpha_k=best_k, alpha_r=best_r, paper=paper, red=red_local,
                   residual=best_e, red_first=red_first)


def ink_layers(src: Source, fit: CardFit, unm: Unmixed | None = None):
    """(alpha_k, alpha_r_behind, unm): black coverage, and red coverage AS IF the black
    were not over it.  In the source, black sits on top of red wherever the hero glyph
    crosses the ring, so the observed red there is ``(1 - ak) * ar_behind``.  Dividing that
    back out and inpainting under solid black is what stops a paper-coloured seam
    opening between a black stroke and the red it was painted over once both are drawn
    at 3x the source's resolution."""
    H, W = src.H, src.W
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    xm, ym = fit.px_to_mm(xx, yy)
    inside = (xm > -0.3) & (xm < CARD_W_MM + 0.3) & (ym > -0.3) & (ym < CARD_H_MM + 0.3)
    if unm is None:
        unm = unmix(src, card_mask=inside)
    ak = unm.alpha_k
    with np.errstate(invalid="ignore", divide="ignore"):
        behind = np.where(ak < 0.85, unm.alpha_r / np.maximum(1.0 - ak, 1e-6), np.nan)
    behind = np.clip(behind, 0.0, 1.0)
    known = np.isfinite(behind)
    fill = norm_conv(np.nan_to_num(behind), known.astype(np.float64), 1.5, 0.0)
    behind = np.where(known, behind, fill)
    return ak, behind, unm


# ===========================================================================
# 6.  Resampling onto a fine grid
# ===========================================================================

def _kernel(kind: str, x: np.ndarray) -> np.ndarray:
    ax = np.abs(x)
    if kind == "linear":
        return np.clip(1.0 - ax, 0.0, None)
    if kind in ("catmull", "keys"):
        a = -0.5 if kind == "catmull" else -0.75
        return np.where(ax < 1, (a + 2) * ax ** 3 - (a + 3) * ax ** 2 + 1,
                        np.where(ax < 2, a * ax ** 3 - 5 * a * ax ** 2 + 8 * a * ax - 4 * a, 0.0))
    if kind == "bspline":          # the cubic B-spline itself (applied to prefiltered data)
        return np.where(ax < 1, (4 - 6 * ax ** 2 + 3 * ax ** 3) / 6,
                        np.where(ax < 2, (2 - ax) ** 3 / 6, 0.0))
    if kind == "lanczos3":
        return np.where(ax < 3, np.sinc(x) * np.sinc(x / 3.0), 0.0)
    raise ValueError(kind)


_SUPPORT = {"linear": 1, "catmull": 2, "keys": 2, "bspline": 2, "lanczos3": 3}


def resample_matrix(n_in: int, pos: np.ndarray, kind: str) -> np.ndarray:
    """Weights (len(pos), n_in) sampling a 1-D signal at index positions ``pos``
    (sample i sits at position i), edge-replicated at the borders."""
    s = _SUPPORT[kind]
    base = np.floor(pos).astype(np.int64)
    Wm = np.zeros((len(pos), n_in))
    rows = np.arange(len(pos))
    for off in range(-s + 1, s + 1):
        idx = base + off
        w = _kernel(kind, pos - idx)
        np.add.at(Wm, (rows, np.clip(idx, 0, n_in - 1)), w)
    if kind == "lanczos3":
        Wm /= Wm.sum(1, keepdims=True)
    return Wm


def _bspline_prefilter(a: np.ndarray, axis: int) -> np.ndarray:
    """Cubic B-spline interpolation prefilter (Unser), mirror boundaries, along one axis."""
    z = math.sqrt(3.0) - 2.0
    a = np.moveaxis(np.asarray(a, np.float64), axis, 0).copy()
    n = a.shape[0]
    a *= 6.0
    horizon = min(n, int(math.ceil(math.log(1e-9) / math.log(abs(z)))))
    zk = z ** np.arange(horizon)
    c0 = np.tensordot(zk, a[:horizon], axes=(0, 0))
    out = np.empty_like(a)
    out[0] = c0
    for k in range(1, n):
        out[k] = a[k] + z * out[k - 1]
    out[n - 1] = (z / (z * z - 1.0)) * (out[n - 1] + z * out[n - 2])
    for k in range(n - 2, -1, -1):
        out[k] = z * (out[k + 1] - out[k])
    return np.moveaxis(out, 0, axis)


def upsample_window(field: np.ndarray, x0: int, y0: int, x1: int, y1: int,
                    factor: int, kind: str = "catmull", margin: int = 4):
    """Resample ``field[y0:y1, x0:x1]`` onto a grid ``factor`` times finer.

    Returns (fine, gx0, gy0, step): fine node (i, j) sits at continuous source position
    (gx0 + j * step, gy0 + i * step).  A ``margin`` of source pixels is read around the
    window so the kernel never sees an artificial edge.
    """
    H, W = field.shape
    X0 = max(0, x0 - margin); Y0 = max(0, y0 - margin)
    X1 = min(W, x1 + margin); Y1 = min(H, y1 + margin)
    sub = np.asarray(field[Y0:Y1, X0:X1], np.float64)
    if kind == "bspline":
        sub = _bspline_prefilter(_bspline_prefilter(sub, 0), 1)
    step = 1.0 / factor
    nx = (x1 - x0) * factor
    ny = (y1 - y0) * factor
    cx = x0 + (np.arange(nx) + 0.5) * step          # continuous source coords
    cy = y0 + (np.arange(ny) + 0.5) * step
    Wx = resample_matrix(sub.shape[1], cx - 0.5 - X0, kind)
    Wy = resample_matrix(sub.shape[0], cy - 0.5 - Y0, kind)
    fine = Wy @ sub @ Wx.T
    return fine, float(cx[0]), float(cy[0]), step


# ===========================================================================
# 7.  Marching squares -> closed, consistently oriented loops
# ===========================================================================

def _ms_table():
    """Segments per case as (from_edge, to_edge).  Edges: 0 top, 1 right, 2 bottom,
    3 left; corners: 0 TL, 1 TR, 2 BR, 3 BL (corner c lies between edges c-1 and c).
    Rule: each maximal run of inside corners c_first..c_last contributes the segment
    edge(c_last) -> edge(c_first - 1), so the inside is always on the same side."""
    table = {}
    for case in range(16):
        inside = [(case >> (3 - c)) & 1 for c in range(4)]    # bit3 TL ... bit0 BL
        if all(inside) or not any(inside):
            table[case] = ([], [])
            continue
        runs = []
        for c in range(4):
            if inside[c] and not inside[(c - 1) % 4]:
                last = c
                while inside[(last + 1) % 4]:
                    last = (last + 1) % 4
                runs.append((c, last))
        segs = [(last, (first - 1) % 4) for first, last in runs]
        # saddle, centre inside: the two inside corners join; cut off each OUTSIDE corner
        alt = []
        if len(runs) == 2:
            outs = [c for c in range(4) if not inside[c]]
            alt = [((o - 1) % 4, o) for o in outs]
        table[case] = (segs, alt)
    return table


_MS = _ms_table()


def marching_squares(f: np.ndarray, iso: float):
    """Closed loops of the ``iso`` level of ``f`` (grid coords: x = column, y = row).

    The field is padded with a below-iso border so every loop closes.  Loops are
    oriented consistently (outer boundaries and holes wind opposite ways), so a nonzero
    fill of the output reproduces the region with its holes.
    """
    f = np.pad(np.asarray(f, np.float64), 1, constant_values=min(float(f.min()), iso) - 1.0)
    h, w = f.shape
    b = f > iso
    TL = b[:-1, :-1]; TR = b[:-1, 1:]; BR = b[1:, 1:]; BL = b[1:, :-1]
    case = ((TL.astype(np.int8) << 3) | (TR.astype(np.int8) << 2)
            | (BR.astype(np.int8) << 1) | BL.astype(np.int8))
    centre = 0.25 * (f[:-1, :-1] + f[:-1, 1:] + f[1:, 1:] + f[1:, :-1]) > iso

    def edge_pt(i, j, e):
        if e == 0:
            a, c = f[i, j], f[i, j + 1]; t = (iso - a) / (c - a)
            return j + t, i.astype(np.float64)
        if e == 1:
            a, c = f[i, j + 1], f[i + 1, j + 1]; t = (iso - a) / (c - a)
            return (j + 1).astype(np.float64), i + t
        if e == 2:
            a, c = f[i + 1, j], f[i + 1, j + 1]; t = (iso - a) / (c - a)
            return j + t, (i + 1).astype(np.float64)
        a, c = f[i, j], f[i + 1, j]; t = (iso - a) / (c - a)
        return j.astype(np.float64), i + t

    def edge_id(i, j, e):
        if e == 0:
            return (i * w + j) * 2
        if e == 2:
            return ((i + 1) * w + j) * 2
        if e == 3:
            return (i * w + j) * 2 + 1
        return (i * w + j + 1) * 2 + 1

    starts, ends, sx, sy = [], [], [], []
    for cs in range(1, 15):
        sel = case == cs
        if not sel.any():
            continue
        ii, jj = np.nonzero(sel)
        segs, alt = _MS[cs]
        if alt:
            cen = centre[ii, jj]
            groups = ((~cen, segs), (cen, alt))
        else:
            groups = ((np.ones(len(ii), bool), segs),)
        for m, sg in groups:
            if not m.any():
                continue
            i2, j2 = ii[m], jj[m]
            for ea, eb in sg:
                starts.append(edge_id(i2, j2, ea)); ends.append(edge_id(i2, j2, eb))
                px, py = edge_pt(i2, j2, ea)
                sx.append(px); sy.append(py)
    if not starts:
        return []
    starts = np.concatenate(starts); ends = np.concatenate(ends)
    sx = np.concatenate(sx) - 1.0; sy = np.concatenate(sy) - 1.0       # undo the pad
    order = np.argsort(starts, kind="stable")
    starts_sorted = starts[order]
    nxt = order[np.searchsorted(starts_sorted, ends)]                  # seg -> following seg
    seen = np.zeros(len(starts), bool)
    loops = []
    for s0 in range(len(starts)):
        if seen[s0]:
            continue
        idx = []
        s = s0
        while not seen[s]:
            seen[s] = True
            idx.append(s)
            s = int(nxt[s])
        idx = np.array(idx)
        loops.append(np.stack([sx[idx], sy[idx]], 1))
    return loops


def signed_area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


# ===========================================================================
# 8.  Splines: corners, clamped cubic B-splines, least squares
# ===========================================================================

def resample_closed(p: np.ndarray, step: float) -> np.ndarray:
    q = np.vstack([p, p[:1]])
    seg = np.hypot(*np.diff(q, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = s[-1]
    n = max(8, int(round(L / step)))
    t = np.arange(n) * (L / n)
    return np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)


def turning(p: np.ndarray, m: int) -> np.ndarray:
    v1 = p - np.roll(p, m, axis=0)
    v2 = np.roll(p, -m, axis=0) - p
    a1 = np.arctan2(v1[:, 1], v1[:, 0]); a2 = np.arctan2(v2[:, 1], v2[:, 0])
    return np.degrees(np.abs((a2 - a1 + np.pi) % (2 * np.pi) - np.pi))


def find_corners(p: np.ndarray, step: float, arm: float, min_turn_deg: float) -> list[int]:
    """Indices of corners on a closed, uniformly resampled loop: turning angle over a
    +-``arm`` arc above ``min_turn_deg`` and the largest within that arc."""
    n = len(p)
    m = max(2, int(round(arm / step)))
    if n < 4 * m:
        return []
    turn = turning(p, m)
    out: list[int] = []
    for i in np.argsort(-turn, kind="stable"):
        if turn[i] < min_turn_deg:
            break
        if all(min((i - j) % n, (j - i) % n) > 2 * m for j in out):
            out.append(int(i))
    return sorted(out)


class _Basis:
    """A cubic B-spline basis matrix stored SPARSE: four (index, weight) pairs per sample.

    ``B @ c`` evaluates the curve; ``gram()`` / ``rhs(q)`` build the normal equations
    directly, so a long contour never needs the dense (samples x control points) matrix
    (the first version built it dense, and a 2000 px loop needed gigabytes).
    """

    def __init__(self, idx: np.ndarray, w: np.ndarray, nc: int):
        self.idx = idx
        self.w = w
        self.nc = nc

    @property
    def shape(self):
        return (len(self.idx), self.nc)

    def __matmul__(self, c):
        c = np.asarray(c, np.float64)
        return np.einsum("nk,nkd->nd", self.w, c[self.idx])

    def gram(self) -> np.ndarray:
        A = np.zeros((self.nc, self.nc))
        for a in range(4):
            for b in range(4):
                np.add.at(A, (self.idx[:, a], self.idx[:, b]), self.w[:, a] * self.w[:, b])
        return A

    def rhs(self, q: np.ndarray) -> np.ndarray:
        R = np.zeros((self.nc, q.shape[1]))
        for a in range(4):
            np.add.at(R, self.idx[:, a], self.w[:, a, None] * q)
        return R


def _clamped_basis(nspan: int, t: np.ndarray) -> _Basis:
    """Cubic B-spline basis on the clamped uniform knot vector over [0, 1] with ``nspan``
    spans (nspan + 3 control points).  De Boor's local recursion, vectorised over t."""
    inner = np.arange(1, nspan) / nspan
    knots = np.concatenate([[0.0] * 4, inner, [1.0] * 4])
    t = np.clip(np.asarray(t, np.float64), 0.0, 1.0 - 1e-12)
    i = np.minimum(np.floor(t * nspan).astype(np.int64), nspan - 1) + 3
    i = np.where(t < knots[i], i - 1, i)                 # float edge: knots[i] <= t
    i = np.clip(i, 3, nspan + 2)
    i = np.where(t >= knots[i + 1], i + 1, i)            # ...and t < knots[i + 1]
    i = np.clip(i, 3, nspan + 2)
    n = len(t)
    N = np.zeros((n, 4)); N[:, 0] = 1.0
    left = np.zeros((n, 4)); right = np.zeros((n, 4))
    for j in range(1, 4):
        left[:, j] = t - knots[i + 1 - j]
        right[:, j] = knots[i + j] - t
        saved = np.zeros(n)
        for r in range(j):
            den = right[:, r + 1] + left[:, j - r]
            ok = den > 0
            temp = np.where(ok, N[:, r] / np.where(ok, den, 1.0), 0.0)
            N[:, r] = saved + right[:, r + 1] * temp
            saved = left[:, j - r] * temp
        N[:, j] = saved
    idx = (i - 3)[:, None] + np.arange(4)[None, :]
    return _Basis(idx, N, nspan + 3)


def _periodic_basis(n: int, s: np.ndarray) -> _Basis:
    """Uniform periodic cubic B-spline basis, ``n`` control points, parameter s in [0, n)."""
    s = np.asarray(s, np.float64) % n
    i = np.floor(s).astype(np.int64)
    t = s - i
    w = np.stack([(1 - t) ** 3 / 6, (3 * t ** 3 - 6 * t ** 2 + 4) / 6,
                  (-3 * t ** 3 + 3 * t ** 2 + 3 * t + 1) / 6, t ** 3 / 6], 1)
    idx = (i[:, None] - 1 + np.arange(4)[None, :]) % n
    return _Basis(idx, w, n)


def _second_diff_gram(n: int, periodic: bool) -> np.ndarray:
    """D^T D of the second-difference operator, built directly."""
    S = np.zeros((n, n))
    rows = np.arange(n) if periodic else np.arange(max(0, n - 2))
    if len(rows) == 0:
        return S
    cols = [(rows - 1) % n, rows, (rows + 1) % n] if periodic else [rows, rows + 1, rows + 2]
    coef = (1.0, -2.0, 1.0)
    for a in range(3):
        for b in range(3):
            np.add.at(S, (cols[a], cols[b]), coef[a] * coef[b])
    return S


def _solve_clamped(B: _Basis, seg: np.ndarray, P0, P1, smooth: float) -> np.ndarray:
    """Least squares with the two end control points pinned to P0, P1."""
    M = B.gram() + smooth * _second_diff_gram(B.nc, False)
    R = B.rhs(np.asarray(seg, np.float64))
    P0 = np.asarray(P0, np.float64); P1 = np.asarray(P1, np.float64)
    rhs = R[1:-1] - np.outer(M[1:-1, 0], P0) - np.outer(M[1:-1, -1], P1)
    if B.nc <= 2:
        return np.vstack([P0, P1])
    ci = np.linalg.solve(M[1:-1, 1:-1], rhs)
    return np.vstack([P0, ci, P1])


def _solve_periodic(B: _Basis, q: np.ndarray, smooth: float) -> np.ndarray:
    return np.linalg.solve(B.gram() + smooth * _second_diff_gram(B.nc, True),
                           B.rhs(np.asarray(q, np.float64)))


@dataclass
class Curve:
    """One closed loop as a chain of cubic B-spline pieces (units: whatever it was fitted
    in; the element store keeps CARD MILLIMETRES).

    With no corners the loop is one uniform PERIODIC spline (``periodic=True``, one
    piece); otherwise each piece is a CLAMPED spline running corner to corner, so the
    tips of the flame stay sharp while everything between them is smooth.
    """
    pieces: list
    periodic: bool

    def sample(self, step: float) -> np.ndarray:
        if self.periodic:
            c = np.asarray(self.pieces[0])
            n = len(c)
            L = float(np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T).sum())
            m = max(16, int(math.ceil(L / step)) * 2)
            s = np.arange(m) * (n / m)
            return _periodic_basis(n, s) @ c
        pts = []
        for c in self.pieces:
            c = np.asarray(c)
            L = float(np.hypot(*np.diff(c, axis=0).T).sum())
            m = max(4, int(math.ceil(L / step)) * 2)
            t = np.arange(m) / m                     # the piece's end is the next's start
            pts.append(_clamped_basis(len(c) - 3, t) @ c)
        return np.vstack(pts)

    def mapped(self, fn) -> "Curve":
        return Curve([fn(np.asarray(c)) for c in self.pieces], self.periodic)

    def to_json(self) -> dict:
        return {"periodic": self.periodic,
                "pieces": [np.round(np.asarray(c), 5).tolist() for c in self.pieces]}


#: longest stretch of contour fitted as one spline piece (source px); see ``fit_loop``
MAX_PIECE_PX = 2500.0


def fit_loop(p: np.ndarray, knot_px: float, step_px: float = 0.05,
             corner_arm_px: float = 0.6, corner_deg: float = 60.0,
             smooth: float = 1e-3, corner_pts=None) -> tuple[Curve, dict]:
    """Least-squares cubic B-spline fit of one closed contour (source px).

    ``knot_px`` is the span length, i.e. the finest wiggle the fit can follow; the
    second-difference penalty ``smooth`` only keeps short spans well conditioned.
    ``corner_pts`` (xy points) replaces the corner search: the nearest contour sample to
    each becomes a corner (the two-pass tracer finds them on a first, stiff fit).
    """
    q = resample_closed(p, step_px)
    n = len(q)
    if corner_pts is not None:
        corners = sorted({int(np.argmin(np.hypot(q[:, 0] - c[0], q[:, 1] - c[1])))
                          for c in corner_pts})
    else:
        corners = find_corners(q, step_px, corner_arm_px, corner_deg)
    n_true_corners = len(corners)
    # BOUNDED PIECES.  The basis is sparse (``_Basis``) but the normal equations are solved
    # dense, so a stretch longer than ``MAX_PIECE_PX`` between corners (none on this card)
    # is split at evenly spaced joints.  A joint pins the curve without carrying the
    # tangent across, so it can show as a kink (``joint_kink_deg`` in the stats): 40 px
    # joints did exactly that on the emblem's hooks, hence a limit above any real contour.
    joints: list[int] = []
    maxn = max(8, int(round(MAX_PIECE_PX / step_px)))
    if not corners and n > maxn:
        k = int(math.ceil(n / maxn))
        joints = [int(round(i * n / k)) % n for i in range(k)]
    elif corners:
        for a, b in zip(corners, corners[1:] + [corners[0] + n]):
            if b - a > maxn:
                k = int(math.ceil((b - a) / maxn))
                joints += [(a + int(round(i * (b - a) / k))) % n for i in range(1, k)]
    if joints:
        corners = sorted(set(corners) | set(joints))
    pieces = []
    fitted = np.zeros_like(q)
    if not corners:
        L = n * step_px
        nc = max(4, int(round(L / knot_px)))
        s = np.arange(n) * (nc / n)
        B = _periodic_basis(nc, s)
        c = _solve_periodic(B, q, smooth)
        pieces.append(c)
        fitted = B @ c
        curve = Curve(pieces, True)
    else:
        for a, b in zip(corners, corners[1:] + [corners[0] + n]):
            idx = np.arange(a, b + 1) % n
            seg = q[idx]
            L = (b - a) * step_px
            nspan = max(1, int(round(L / knot_px)))
            t = np.arange(len(seg)) / (len(seg) - 1)
            B = _clamped_basis(nspan, t)
            P0, P1 = seg[0], seg[-1]
            c = _solve_clamped(B, seg, P0, P1, smooth)
            pieces.append(c)
            fitted[idx[:-1]] = (B @ c)[:-1]
        curve = Curve(pieces, False)
    err = np.hypot(*(fitted - q).T)
    kink = 0.0
    if joints and not curve.periodic:
        jset = set(joints)
        for i in range(len(pieces)):
            a_ = pieces[i - 1]; b_ = pieces[i]
            if corners[i] % n not in jset:
                continue
            t1 = a_[-1] - a_[-2]; t2 = b_[1] - b_[0]
            ang = abs(math.degrees(math.atan2(t1[0] * t2[1] - t1[1] * t2[0],
                                              float(np.dot(t1, t2)))))
            kink = max(kink, ang)
    return curve, {"points": n, "corners": n_true_corners,
                   "joints": len(joints), "joint_kink_deg": round(kink, 3),
                   "rms_px": float(np.sqrt((err ** 2).mean())), "max_px": float(err.max())}


# ===========================================================================
# 9.  Rasterising curves: exact-area scanline fill
# ===========================================================================

def fill_polys(polys: Sequence[np.ndarray], H: int, W: int, ss: int = 8,
               window: tuple | None = None) -> np.ndarray:
    """Nonzero-winding fill with exact fractional x coverage and ``ss`` sub-rows per row.

    ``polys`` are in PIXELS of the target grid (pixel (i, j) covers [j, j+1) x [i, i+1)).
    ``window`` = (x0, y0, x1, y1) limits the work to a sub-rectangle; the full (H, W)
    array is returned either way.
    """
    out = np.zeros((H, W), np.float32)
    polys = [np.asarray(p, np.float64) for p in polys if len(p) >= 3]
    if not polys:
        return out
    a = np.concatenate(polys, 0)
    b = np.concatenate([np.roll(p, -1, 0) for p in polys], 0)
    bx0 = max(0, int(math.floor(a[:, 0].min())) - 1)
    bx1 = min(W, int(math.ceil(a[:, 0].max())) + 2)
    by0 = max(0, int(math.floor(a[:, 1].min())) - 1)
    by1 = min(H, int(math.ceil(a[:, 1].max())) + 2)
    if window is not None:
        bx0 = max(bx0, window[0]); by0 = max(by0, window[1])
        bx1 = min(bx1, window[2]); by1 = min(by1, window[3])
    if bx1 <= bx0 or by1 <= by0:
        return out
    ww, hh = bx1 - bx0, by1 - by0
    x0, y0 = a[:, 0] - bx0, a[:, 1] - by0
    x1, y1 = b[:, 0] - bx0, b[:, 1] - by0
    dy = y1 - y0
    keep = dy != 0.0
    x0, y0, x1, y1, dy = x0[keep], y0[keep], x1[keep], y1[keep], dy[keep]
    direction = np.sign(dy)
    rows = hh * ss
    cols = ww + 3
    acc = np.zeros(rows * cols, np.float64)
    j0 = np.clip(np.ceil(np.minimum(y0, y1) * ss - 0.5).astype(np.int64), 0, rows)
    j1 = np.clip(np.ceil(np.maximum(y0, y1) * ss - 0.5).astype(np.int64), 0, rows)
    cnt = np.maximum(j1 - j0, 0)
    csum = np.cumsum(cnt)
    chunk = 3_000_000
    seg_lo = 0
    nseg = len(cnt)
    while seg_lo < nseg:
        base = int(csum[seg_lo - 1]) if seg_lo else 0
        seg_hi = int(np.searchsorted(csum, base + chunk, side="right"))
        seg_hi = min(nseg, max(seg_hi, seg_lo + 1))
        c = cnt[seg_lo:seg_hi]
        tot = int(c.sum())
        if tot:
            si = np.repeat(np.arange(seg_lo, seg_hi), c)
            jj = np.repeat(j0[seg_lo:seg_hi], c) + (np.arange(tot) - np.repeat(np.cumsum(c) - c, c))
            t = (((jj + 0.5) / ss) - y0[si]) / dy[si]
            xc = np.clip(x0[si] + t * (x1[si] - x0[si]), -1.0, ww + 1.0)
            ixf = np.floor(xc)
            fx = xc - ixf
            ix = ixf.astype(np.int64) + 1
            d = direction[si]
            flat = jj * cols
            acc += np.bincount(flat + np.clip(ix, 0, cols - 1), weights=d * (1.0 - fx),
                               minlength=rows * cols)
            acc += np.bincount(flat + np.clip(ix + 1, 0, cols - 1), weights=d * fx,
                               minlength=rows * cols)
        seg_lo = seg_hi
    wind = np.cumsum(acc.reshape(rows, cols), axis=1)
    cov = np.clip(np.abs(wind[:, 1:ww + 1]), 0.0, 1.0)
    out[by0:by1, bx0:bx1] = cov.reshape(hh, ss, ww).mean(axis=1)
    return out


# ===========================================================================
# 10.  Analysis by synthesis: move the curves until they RE-RENDER as the source
# ===========================================================================

#: The source's own point-spread, measured on the flame emblem's edges: a box (the pixel)
#: convolved with a Gaussian of 0.4 px.  Box alone leaves a band MAE of 0.043 against the
#: source's edge pixels; box + 0.4 px gives 0.028, and 0.3 / 0.5 px are both worse.
SOURCE_PSF_SIGMA_PX = 0.4


def _bilinear(field: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Sample a pixel-centred field at continuous coords (x, y)."""
    H, W = field.shape
    x = np.clip(pts[:, 0] - 0.5, 0, W - 1.000001)
    y = np.clip(pts[:, 1] - 0.5, 0, H - 1.000001)
    i = np.floor(y).astype(np.int64); j = np.floor(x).astype(np.int64)
    fy = y - i; fx = x - j
    i1 = np.minimum(i + 1, H - 1); j1 = np.minimum(j + 1, W - 1)
    return ((1 - fy) * ((1 - fx) * field[i, j] + fx * field[i, j1])
            + fy * ((1 - fx) * field[i1, j] + fx * field[i1, j1]))


def _tangents(p: np.ndarray, closed: bool) -> np.ndarray:
    if closed:
        d = np.roll(p, -1, 0) - np.roll(p, 1, 0)
    else:
        d = np.gradient(p, axis=0)
    n = np.hypot(d[:, 0], d[:, 1])[:, None]
    return d / np.maximum(n, 1e-12)


def _fit_piece(pts: np.ndarray, P0, P1, knot: float, smooth: float) -> np.ndarray:
    """Clamped cubic B-spline through fixed ends P0, P1, least squares to ``pts``."""
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = max(s[-1], 1e-9)
    t = s / L
    nspan = max(1, int(round(L / knot)))
    B = _clamped_basis(nspan, t)
    return _solve_clamped(B, pts, P0, P1, smooth)


def _fit_periodic(pts: np.ndarray, knot: float, smooth: float) -> np.ndarray:
    q = resample_closed(pts, 0.05)
    n = len(q)
    nc = max(4, int(round(n * 0.05 / knot)))
    B = _periodic_basis(nc, np.arange(n) * (nc / n))
    return _solve_periodic(B, q, smooth)


def render_source_grid(curves: Sequence[Curve], H: int, W: int, sigma: float,
                       window: tuple | None = None) -> np.ndarray:
    """What the source's camera would have recorded for these curves: exact box
    coverage on its pixel grid, then its Gaussian."""
    polys = [c.sample(0.05) for c in curves]
    cov = fill_polys(polys, H, W, ss=16, window=window).astype(np.float64)
    return gauss_blur(cov, sigma) if sigma > 0 else cov


def refine_curves(curves: list, obs: np.ndarray, density: np.ndarray, region: np.ndarray,
                  knot: float, smooth: float, iters: int = 12, gain: float = 0.8,
                  sigma: float = SOURCE_PSF_SIGMA_PX, max_step: float = 0.25,
                  max_total: float = 2.0) -> tuple[list, list]:
    """Move every boundary point along its outward normal by the local residual.

    The residual is (rendered - observed), pulled back through the PSF (its adjoint is
    itself - a symmetric Gaussian).  A boundary point where the rendering has too much
    ink moves in; where the source shows ink the curve does not cover - a tapered tip
    thinner than half a pixel, which a half-level contour always cuts short - it moves
    out.  The spline refit after every step is the smoothness prior.  Corners move
    along their bisector, so tips lengthen and notches deepen without rounding.
    """
    H, W = obs.shape
    ys, xs = np.nonzero(region)
    win = (int(xs.min()) - 2, int(ys.min()) - 2, int(xs.max()) + 3, int(ys.max()) + 3)
    hist = []
    moved = [np.zeros(0) for _ in curves]
    for it in range(iters + 1):
        pred = render_source_grid(curves, H, W, sigma, win) * density
        r = np.where(region, pred - obs, 0.0)
        hist.append(float(np.abs(r[region]).mean()))
        if it == iters:
            break
        rb = gauss_blur(r, sigma) if sigma > 0 else r
        new = []
        for ci, c in enumerate(curves):
            if c.periodic:
                pts = c.sample(0.05)
                tg = _tangents(pts, True)
                nrm = np.stack([tg[:, 1], -tg[:, 0]], 1)
                d = np.clip(-gain * _bilinear(rb, pts), -max_step, max_step)
                new.append(Curve([_fit_periodic(pts + d[:, None] * nrm, knot, smooth)], True))
                continue
            # clamped pieces: displace interiors along normals, corners along bisectors
            pieces = [np.asarray(p) for p in c.pieces]
            k = len(pieces)
            samples = []
            for p in pieces:
                L = float(np.hypot(*np.diff(p, axis=0).T).sum())
                m = max(8, int(math.ceil(L / 0.05)))
                samples.append(_clamped_basis(len(p) - 3, np.linspace(0, 1, m)) @ p)
            corners = []
            for i in range(k):
                prev = samples[i - 1]; cur = samples[i]
                t_in = prev[-1] - prev[-3]; t_out = cur[2] - cur[0]
                t_in /= max(np.hypot(*t_in), 1e-12); t_out /= max(np.hypot(*t_out), 1e-12)
                n_in = np.array([t_in[1], -t_in[0]]); n_out = np.array([t_out[1], -t_out[0]])
                bis = t_in - t_out
                nb = np.hypot(*bis)
                if nb < 1e-6:
                    bis = n_in + n_out
                    nb = max(np.hypot(*bis), 1e-12)
                bis = bis / nb
                if np.dot(bis, n_in + n_out) < 0:
                    bis = -bis                       # reflex corner: outward is the other way
                dv = float(np.clip(-gain * _bilinear(rb, cur[:1])[0], -max_step, max_step))
                corners.append(cur[0] + dv * bis)
            pieces2 = []
            for i in range(k):
                pts = samples[i]
                tg = _tangents(pts, False)
                nrm = np.stack([tg[:, 1], -tg[:, 0]], 1)
                d = np.clip(-gain * _bilinear(rb, pts), -max_step, max_step)
                pts2 = pts + d[:, None] * nrm
                P0 = corners[i]; P1 = corners[(i + 1) % k]
                pts2[0] = P0; pts2[-1] = P1
                pieces2.append(_fit_piece(pts2, P0, P1, knot, smooth))
            new.append(Curve(pieces2, False))
        curves = new
    return curves, hist
