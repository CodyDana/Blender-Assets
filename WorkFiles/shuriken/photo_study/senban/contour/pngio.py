# Minimal PNG writer (no PIL available in any Python here).
import zlib, struct, numpy as np
def write_png(path, arr):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = np.clip(a, 0, 255).astype(np.uint8)
    if a.ndim == 2:
        ct, a3 = 0, a[..., None]
    elif a.shape[2] == 3:
        ct, a3 = 2, a
    else:
        ct, a3 = 6, a
    h, w, c = a3.shape
    raw = b"".join(b"\x00" + a3[y].tobytes() for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)
