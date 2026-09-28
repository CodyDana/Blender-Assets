"""Minimal numpy PNG writer/reader (8-bit RGB/RGBA, non-interlaced). No PIL needed.
Run with Blender's bundled python: "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"."""
import zlib, struct, numpy as np

def write(path, arr):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2: a = np.stack([a]*3, -1)
    h, w, c = a.shape
    ct = {3: 2, 4: 6}[c]
    raw = np.concatenate([np.zeros((h, 1), np.uint8), a.reshape(h, w*c)], 1).tobytes()
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))

def read(path):
    d = open(path, "rb").read(); p = 8; idat = b""
    while p < len(d):
        n = struct.unpack(">I", d[p:p+4])[0]; t = d[p+4:p+8]; body = d[p+8:p+8+n]; p += 12 + n
        if t == b"IHDR": w, h, bd, ct = struct.unpack(">IIBB", body[:10])
        elif t == b"IDAT": idat += body
    assert bd == 8 and ct in (2, 6), (bd, ct)
    c = 3 if ct == 2 else 4; st = w*c
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, st+1)
    out = np.zeros((h, st), np.int32); prev = np.zeros(st, np.int32)
    for y in range(h):
        f = raw[y, 0]; line = raw[y, 1:].astype(np.int32)
        if f == 0: cur = line
        elif f == 2: cur = (line + prev) & 255
        else:
            cur = np.zeros(st, np.int32)
            for x in range(st):
                a = cur[x-c] if x >= c else 0; b = prev[x]; cc = prev[x-c] if x >= c else 0
                if f == 1: pr = a
                elif f == 3: pr = (a + b) >> 1
                else:
                    pa, pb, pc = abs(b-cc), abs(a-cc), abs(a+b-2*cc)
                    pr = a if pa <= pb and pa <= pc else (b if pb <= pc else cc)
                cur[x] = (line[x] + pr) & 255
        out[y] = cur; prev = cur
    return out.reshape(h, w, c).astype(np.uint8)
