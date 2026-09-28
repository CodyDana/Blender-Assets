# -*- coding: utf-8 -*-
"""Minimal PNG decoder -> numpy array of STORED sample values.

Why: bpy.data.images.load + .pixels goes through Blender's colour management and
a PNG carries no colourspace tag, so "stored vs linear" becomes ambiguous.
Decoding the IDAT ourselves gives the exact integers in the file. Everything this
module returns is a STORED (file-encoded) value.

Returns (arr, info) where arr is uint8/uint16, shape (H, W, C), C in 1..4.
Supports bit depth 8 and 16, colour types 0/2/3/4/6, non-interlaced.
"""
import struct
import zlib

import numpy as np

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)

    pos = 8
    idat = []
    info = {"path": path}
    plte = None
    trns = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            w, h, bd, ct, comp, filt, inter = struct.unpack(">IIBBBBB", body)
            info.update(width=w, height=h, bit_depth=bd, colour_type=ct,
                        interlace=inter)
            if inter != 0:
                raise ValueError("interlaced PNG unsupported")
            if bd not in (8, 16):
                if ct != 3:
                    raise ValueError("bit depth %d unsupported" % bd)
        elif ctype == b"PLTE":
            plte = np.frombuffer(body, dtype=np.uint8).reshape(-1, 3)
        elif ctype == b"tRNS":
            trns = np.frombuffer(body, dtype=np.uint8)
        elif ctype == b"IDAT":
            idat.append(body)
        elif ctype == b"gAMA":
            info["gAMA"] = struct.unpack(">I", body)[0] / 100000.0
        elif ctype == b"sRGB":
            info["sRGB_chunk"] = body[0]
        elif ctype == b"iCCP":
            info["iCCP"] = body.split(b"\x00", 1)[0].decode("latin-1")
        elif ctype == b"pHYs":
            px, py, unit = struct.unpack(">IIB", body)
            info["pHYs"] = (px, py, unit)
        elif ctype in (b"tEXt", b"iTXt"):
            info.setdefault("text_keys", []).append(
                body.split(b"\x00", 1)[0].decode("latin-1"))
        elif ctype == b"IEND":
            break

    w, h, bd, ct = info["width"], info["height"], info["bit_depth"], info["colour_type"]
    nch = _CHANNELS[ct]

    raw = zlib.decompress(b"".join(idat))

    if ct == 3 and bd < 8:
        # sub-byte palette indices
        per_row = (w * bd + 7) // 8
        stride = per_row
        bpp = 1
    else:
        stride = (w * nch * bd) // 8
        bpp = max(1, (nch * bd) // 8)

    expect = (stride + 1) * h
    if len(raw) < expect:
        raise ValueError("short IDAT: %d < %d" % (len(raw), expect))

    buf = np.frombuffer(raw[:expect], dtype=np.uint8).reshape(h, stride + 1)
    filters = buf[:, 0].copy()
    lines = buf[:, 1:].astype(np.uint8).copy()

    prev = np.zeros(stride, dtype=np.uint8)
    out = np.empty((h, stride), dtype=np.uint8)
    idx = np.arange(stride)
    for y in range(h):
        f = filters[y]
        cur = lines[y]
        if f == 0:
            rec = cur
        elif f == 1:
            # Sub: rec[i] = cur[i] + rec[i-bpp]  -> cumsum on each bpp-strided lane
            rec = np.empty(stride, dtype=np.uint8)
            for k in range(bpp):
                lane = cur[k::bpp].astype(np.uint32)
                rec[k::bpp] = (np.cumsum(lane) & 0xFF).astype(np.uint8)
        elif f == 2:
            rec = (cur.astype(np.uint16) + prev.astype(np.uint16)).astype(np.uint8)
        elif f == 3:
            rec = np.empty(stride, dtype=np.uint8)
            cl = cur.tolist()
            pl = prev.tolist()
            rl = [0] * stride
            for i in range(stride):
                left = rl[i - bpp] if i >= bpp else 0
                rl[i] = (cl[i] + ((left + pl[i]) >> 1)) & 0xFF
            rec[:] = rl
        elif f == 4:
            rec = np.empty(stride, dtype=np.uint8)
            cl = cur.tolist()
            pl = prev.tolist()
            rl = [0] * stride
            for i in range(stride):
                if i >= bpp:
                    a = rl[i - bpp]
                    c = pl[i - bpp]
                else:
                    a = 0
                    c = 0
                b = pl[i]
                rl[i] = (cl[i] + _paeth(a, b, c)) & 0xFF
            rec[:] = rl
        else:
            raise ValueError("bad filter %d on row %d" % (f, y))
        out[y] = rec
        prev = rec

    if ct == 3:
        if bd == 8:
            ids = out[:, :w]
        else:
            bits = np.unpackbits(out, axis=1)
            per = bd
            ids = np.zeros((h, w), dtype=np.uint8)
            for b in range(per):
                ids = (ids << 1) | bits[:, b::per][:, :w]
        arr = plte[ids]
        if trns is not None:
            a = np.full(ids.shape, 255, dtype=np.uint8)
            n = min(len(trns), plte.shape[0])
            lut = np.full(plte.shape[0], 255, dtype=np.uint8)
            lut[:n] = trns[:n]
            a = lut[ids]
            arr = np.concatenate([arr, a[:, :, None]], axis=2)
        info["channels"] = arr.shape[2]
        info["max_value"] = 255
        return arr, info

    if bd == 8:
        arr = out.reshape(h, w, nch)
        info["max_value"] = 255
    else:
        hi = out[:, 0::2].astype(np.uint16)
        lo = out[:, 1::2].astype(np.uint16)
        arr = ((hi << 8) | lo).reshape(h, w, nch)
        info["max_value"] = 65535
    info["channels"] = nch
    return arr, info


def to_float(arr, info):
    """Stored integers -> stored floats in 0..1 (NO transfer function applied)."""
    return arr.astype(np.float64) / float(info["max_value"])


def srgb_to_linear(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def rgb_to_hsv(rgb):
    """rgb: (...,3) in 0..1 -> h in degrees 0..360, s, v in 0..1."""
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    mx = np.max(rgb[..., :3], axis=-1)
    mn = np.min(rgb[..., :3], axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = (d > 1e-12) & (mx == r)
        h[m] = (60 * ((g[m] - b[m]) / d[m])) % 360
        m = (d > 1e-12) & (mx == g)
        h[m] = (60 * ((b[m] - r[m]) / d[m]) + 120) % 360
        m = (d > 1e-12) & (mx == b)
        h[m] = (60 * ((r[m] - g[m]) / d[m]) + 240) % 360
        s = np.where(mx > 1e-12, d / np.maximum(mx, 1e-12), 0.0)
    return h, s, mx


def luma_srgb(rgb01):
    """Rec.709 luma from LINEAR rgb."""
    return 0.2126 * rgb01[..., 0] + 0.7152 * rgb01[..., 1] + 0.0722 * rgb01[..., 2]
