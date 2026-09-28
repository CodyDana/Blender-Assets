"""Minimal PNG read/write for numpy arrays (no PIL on this machine). 8-bit RGB/RGBA, top-down rows."""
import struct, zlib
import numpy as np


def write_png(path, arr):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, 2)
    h, w, c = a.shape
    ctype = {3: 2, 4: 6}[c]
    raw = b''.join(b'\x00' + a[r].tobytes() for r in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def upscale(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)
