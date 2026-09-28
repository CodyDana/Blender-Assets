"""Look-match round 1 (sword): tiny numpy image helpers (no PIL on this machine).
read_png: 8-bit (or 16-bit) non-interlaced PNG -> float32 HxWxC in 0..1, row 0 = top."""
import struct, zlib
import numpy as np
from sfv4_png import write_png  # noqa: F401


def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    idat = b''
    w = h = bd = ct = il = None
    plte = None
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos + 4])[0]
        t = data[pos + 4:pos + 8]
        d = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if t == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', d)
        elif t == b'IDAT':
            idat += d
        elif t == b'PLTE':
            plte = np.frombuffer(d, np.uint8).reshape(-1, 3)
        elif t == b'IEND':
            break
    assert il == 0, 'interlaced png unsupported'
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    bpp = ch * bd // 8
    stride = w * bpp
    raw = np.frombuffer(zlib.decompress(idat), np.uint8)
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    p = 0
    for r in range(h):
        f = raw[p]
        line = raw[p + 1:p + 1 + stride].astype(np.int32)
        p += 1 + stride
        if f == 0:
            cur = line
        elif f == 1:
            cur = line.copy()
            for i in range(bpp, stride, bpp):
                pass
            cur = _sub(line, bpp)
        elif f == 2:
            cur = (line + prev) & 255
        elif f == 3:
            cur = _avg(line, prev, bpp)
        else:
            cur = _paeth(line, prev, bpp)
        out[r] = cur
        prev = cur.astype(np.int32)
    if bd == 16:
        a = out.reshape(h, w * ch, 2).astype(np.uint16)
        a = (a[..., 0] << 8 | a[..., 1]).reshape(h, w, ch).astype(np.float32) / 65535.0
    else:
        a = out.reshape(h, w, ch).astype(np.float32) / 255.0
    if ct == 3:
        a = plte[out.reshape(h, w)].astype(np.float32) / 255.0
    return a


def _sub(line, bpp):
    cur = line.copy()
    n = len(cur)
    for i in range(bpp, n):
        cur[i] = (cur[i] + cur[i - bpp]) & 255
    return cur


def _avg(line, prev, bpp):
    cur = line.copy()
    for i in range(len(cur)):
        left = cur[i - bpp] if i >= bpp else 0
        cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
    return cur


def _paeth(line, prev, bpp):
    cur = line.copy()
    for i in range(len(cur)):
        a = cur[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        pp = a + b - c
        pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
        pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
        cur[i] = (cur[i] + pr) & 255
    return cur


def resize(a, h=None, w=None):
    H, W = a.shape[:2]
    if h is None:
        h = int(round(H * w / W))
    if w is None:
        w = int(round(W * h / H))
    y = (np.arange(h) + 0.5) * H / h - 0.5
    x = (np.arange(w) + 0.5) * W / w - 0.5
    y0 = np.clip(np.floor(y).astype(int), 0, H - 1); y1 = np.clip(y0 + 1, 0, H - 1); fy = np.clip(y - y0, 0, 1)
    x0 = np.clip(np.floor(x).astype(int), 0, W - 1); x1 = np.clip(x0 + 1, 0, W - 1); fx = np.clip(x - x0, 0, 1)
    r0 = a[y0] * (1 - fy)[:, None, None] + a[y1] * fy[:, None, None]
    return r0[:, x0] * (1 - fx)[None, :, None] + r0[:, x1] * fx[None, :, None]


def rgb(a, bg=1.0):
    if a.shape[2] == 4:
        return a[..., :3] * a[..., 3:] + bg * (1 - a[..., 3:])
    if a.shape[2] == 1:
        return np.repeat(a, 3, 2)
    return a[..., :3]


def hcat(imgs, h, gap=8, gapv=0.8):
    parts = []
    for i, im in enumerate(imgs):
        if i:
            parts.append(np.full((h, gap, 3), gapv, np.float32))
        parts.append(resize(rgb(im), h=h))
    return np.concatenate(parts, 1)
