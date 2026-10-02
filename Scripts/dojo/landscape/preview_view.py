"""LANDSCAPE ROUND: a quick numpy ray-march preview of the two heightmaps through a camera (a design check before the
Unreal build; not a deliverable). usage: py -3 -B preview_view.py <camera> <out.png>   cameras: ref | gate | peaks"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ls_geo as G  # noqa: E402

TER = G.WORLD / "terrain"
V = np.fromfile(TER / "LS_Valley.r16", dtype="<u2").reshape(2017, 2017)
F = np.fromfile(TER / "LS_Far.r16", dtype="<u2").reshape(2017, 2017)
VZ, FZ = G.u16_to_z(V, G.LS_VALLEY), G.u16_to_z(F, G.LS_FAR)
vx, vy = G.grid_axes(G.LS_VALLEY)
fx, fy = G.grid_axes(G.LS_FAR)


def samp(Z, xs, ys, sp, x, y):
    c = np.clip((x - xs[0]) / sp, 0, 2015.999)
    r = np.clip((ys[0] - y) / sp, 0, 2015.999)
    c0, r0 = c.astype(int), r.astype(int)
    a, b = c - c0, r - r0
    return (Z[r0, c0] * (1 - a) * (1 - b) + Z[r0, c0 + 1] * a * (1 - b) + Z[r0 + 1, c0] * (1 - a) * b
            + Z[r0 + 1, c0 + 1] * a * b)


def height(x, y):
    inside = (np.abs(x - 22) < 503) & (np.abs(y - 18) < 503)
    return np.where(inside, np.maximum(samp(VZ, vx, vy, 0.5, x, y), samp(FZ, fx, fy, 8.0, x, y)), samp(FZ, fx, fy, 8.0, x, y))


CAMS = {"ref": ((4.8, -61.6, 12.9), 24.2, -3.7, 60.0, (256, 384)),
        "gate": ((22.0, -6.5, 1.2), 12.0, 3.0, 60.0, (384, 216)),
        "valley": ((22.0, 18.0, 30.0), 30.0, -4.0, 80.0, (384, 216))}


def main():
    name = sys.argv[1]
    (cx, cy, cz), yaw, pitch, hfov, (W, H) = CAMS[name]
    f = (W / 2) / math.tan(math.radians(hfov / 2))
    u = (np.arange(W) - W / 2 + 0.5)[None, :]
    v = (H / 2 - np.arange(H) - 0.5)[:, None]
    fwd = np.array([math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
                    math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), math.sin(math.radians(pitch))])
    right = np.array([math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0.0])
    up = np.cross(right, fwd)
    d = fwd[None, None, :] * f + right[None, None, :] * u[..., None] + up[None, None, :] * v[..., None]
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    t = np.full((H, W), 0.5)
    hit = np.zeros((H, W), bool)
    dist = np.full((H, W), np.inf)
    for i in range(900):
        x, y, z = cx + d[..., 0] * t, cy + d[..., 1] * t, cz + d[..., 2] * t
        hz = height(x, y)
        new = (~hit) & (z <= hz)
        dist[new] = t[new]
        hit |= new
        t = np.where(hit, t, t + np.maximum(0.25, t * 0.012))
        if (t > 16000).all() or hit.all():
            break
    x, y = cx + d[..., 0] * dist, cy + d[..., 1] * dist
    e = 1.0
    gx = (height(x + e, y) - height(x - e, y)) / (2 * e)
    gy = (height(x, y + e) - height(x, y - e)) / (2 * e)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array([-0.98, -0.05, 0.16])
    L /= np.linalg.norm(L)
    sh = np.clip((n * L).sum(-1), 0, 1) * 0.8 + 0.2
    zz = height(x, y)
    snow = (zz > 1100).astype(float)
    col = np.stack([0.3 + 0.6 * snow, 0.45 + 0.45 * snow, 0.3 + 0.6 * snow], -1) * sh[..., None]

    fog = 1 - np.exp(-np.nan_to_num(dist, posinf=1e9) / 6000.0)
    sky = np.array([0.55, 0.6, 0.75])
    img = np.where(hit[..., None], col * (1 - fog[..., None]) + sky * fog[..., None], sky)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((W * 2, H * 2)).save(sys.argv[2])


main()
