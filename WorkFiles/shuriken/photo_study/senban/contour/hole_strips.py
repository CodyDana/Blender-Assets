# Unwrap the square hole's four sides (fitted lines) into strips; depth measured OUTWARD from the
# hole (into the metal) from -35 (inside the see-through area) to +30.
import sys, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run
from geom import bilinear
from pngio import write_png


def hole_unwrap(A, k, d0=-35, d1=30, img=None, ext=0.0):
    hcor = A["hcor"]
    P0, P1 = hcor[k], hcor[(k + 1) % 4]
    L = np.hypot(*(P1 - P0)); u = (P1 - P0) / L
    nout = np.array([u[1], -u[0]])       # clockwise contour of the hole region: outward = (ty, -tx)
    ts = np.arange(-ext, L + ext + 1e-9, 1.0)
    ds = np.arange(d0, d1 + 1e-9, 1.0)
    X = P0[0] + ts[None, :] * u[0] + ds[:, None] * nout[0]
    Y = P0[1] + ts[None, :] * u[1] + ds[:, None] * nout[1]
    out = {key: bilinear(im, X.ravel(), Y.ravel()).reshape(X.shape) for key, im in img.items()}
    return ts, ds, out, nout, u


if __name__ == "__main__":
    R = run(); A = R["_arrays"]
    rgb = np.load(D + "cache/senban_rgb.npy").astype(float)
    imgs = dict(r=rgb[..., 0], g=rgb[..., 1], b=rgb[..., 2])
    rows = []
    for k, nm in enumerate(["top", "right", "bottom", "left"]):
        ts, ds, o, _, _ = hole_unwrap(A, k, img=imgs, ext=12)
        s = np.dstack([o["r"], o["g"], o["b"]])
        s = 255 * (np.clip(s, 0, 255) / 255.0) ** 0.6
        s = np.repeat(np.repeat(s, 3, 0), 3, 1)
        z = int((0 - ds[0]) * 3)
        s[z, ::12] = [255, 0, 0]
        s = s[:, :3 * 240] if s.shape[1] >= 720 else np.pad(s, ((0, 0), (0, 720 - s.shape[1]), (0, 0)))
        rows.append(s); rows.append(np.full((6, 720, 3), 255.0))
    write_png(D + "cache/hole_strips.png", np.vstack(rows).astype(np.uint8))
    print("ok")
