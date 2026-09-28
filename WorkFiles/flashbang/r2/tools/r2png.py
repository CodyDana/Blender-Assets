"""Tiny PNG read/write (numpy only) for round-2 tooling. 8/16-bit grey/RGB/RGBA, all filters."""
import zlib, struct
import numpy as np

def read_png(path):
    b = open(path, "rb").read()
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    i = 8; idat = []; w = h = bd = ct = None
    while i < len(b):
        n = struct.unpack(">I", b[i:i+4])[0]; t = b[i+4:i+8]; d = b[i+8:i+8+n]; i += 12 + n
        if t == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", d[:10])
        elif t == b"IDAT":
            idat.append(d)
        elif t == b"IEND":
            break
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    bpp = ch * bd // 8
    raw = zlib.decompress(b"".join(idat))
    stride = w * bpp
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    pos = 0
    for y in range(h):
        f = raw[pos]; line = np.frombuffer(raw, np.uint8, stride, pos + 1).astype(np.int32); pos += 1 + stride
        if f == 0:
            cur = line
        elif f == 2:
            cur = (line + prev) & 255
        elif f in (1, 3, 4):
            cur = np.zeros(stride, np.int32)
            for x in range(stride):
                a = cur[x - bpp] if x >= bpp else 0
                if f == 1:
                    p = a
                elif f == 3:
                    p = (a + prev[x]) >> 1
                else:
                    bb = prev[x]; c = prev[x - bpp] if x >= bpp else 0
                    pa, pb, pc = abs(bb - c), abs(a - c), abs(a + bb - 2 * c)
                    p = a if (pa <= pb and pa <= pc) else (bb if pb <= pc else c)
                cur[x] = (line[x] + p) & 255
        else:
            raise ValueError(f)
        out[y] = cur; prev = cur
    if bd == 16:
        a = out.reshape(h, w * ch, 2).astype(np.uint16)
        a = (a[..., 0] << 8 | a[..., 1]).reshape(h, w, ch).astype(np.float32) / 65535.0 * 255.0
    else:
        a = out.reshape(h, w, ch).astype(np.float32)
    return a

def write_png(path, arr):
    a = np.clip(np.rint(np.asarray(arr, np.float32)), 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    a = a[..., :3]
    h, w, _ = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    open(path, "wb").write(png)

def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)

def crop(a, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    return a[max(0, y0):y1, max(0, x0):x1]
