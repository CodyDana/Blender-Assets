"""Minimal PNG read/write (8-bit RGB/RGBA/Gray) with numpy + zlib. Crop helper:
python pngio.py in.png out.png x0 y0 x1 y1 [scale]"""
import struct
import sys
import zlib

import numpy as np


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w = 8, b"", None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", chunk[:10])
            assert bd == 8, bd
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + ln
    ch = {0: 1, 2: 3, 6: 4, 4: 2}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    p = 0
    for y in range(h):
        f = raw[p]
        line = np.frombuffer(raw, np.uint8, stride, p + 1).astype(np.int32)
        p += 1 + stride
        if f == 0:
            cur = line
        elif f == 1:
            cur = line.copy()
            for i in range(ch, stride, ch):
                cur[i:i + ch] = (cur[i:i + ch] + cur[i - ch:i]) & 255
            # vectorised via cumulative sum per channel
        elif f == 2:
            cur = (line + prev) & 255
        elif f == 3:
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        out[y] = cur
        prev = cur
    return out.reshape(h, w, ch)


def write_png(path, arr):
    arr = np.ascontiguousarray(arr.astype(np.uint8))
    if arr.ndim == 2:
        arr = arr[:, :, None]
    h, w, ch = arr.shape
    ct = {1: 0, 3: 2, 4: 6}[ch]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


if __name__ == "__main__":
    a = read_png(sys.argv[1])
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    c = a[y0:y1, x0:x1]
    s = int(sys.argv[7]) if len(sys.argv) > 7 else 1
    if s > 1:
        c = np.repeat(np.repeat(c, s, 0), s, 1)
    write_png(sys.argv[2], c)
    print(a.shape, c.shape)
