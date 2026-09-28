# Unwrap each side's edge band into a straight strip (rows = depth along the inward normal of the
# fitted side circle, cols = position along the side) so the bevel crease can be seen and traced.
import sys, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run
from geom import bilinear
from pngio import write_png


def unwrap(A, k, d0=-15, d1=60, ncol=900, img=None):
    fits, corners = A["fits"], A["corners"]
    f = fits[k]; C = np.array([f["cx"], f["cy"]]); Rr = f["R"]
    P0, P1 = corners[k], corners[(k + 1) % 4]
    a0 = math.atan2(P0[1] - C[1], P0[0] - C[0]); a1 = math.atan2(P1[1] - C[1], P1[0] - C[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    ts = np.linspace(0, 1, ncol)
    ang = a0 + ts * da
    ds = np.arange(d0, d1 + 1e-9, 1.0)
    # inward normal = away from the circle centre (centre lies outside the plate)
    ux, uy = np.cos(ang), np.sin(ang)
    X = C[0] + (Rr + ds[:, None]) * ux[None, :]
    Y = C[1] + (Rr + ds[:, None]) * uy[None, :]
    out = {}
    for key, im in img.items():
        out[key] = bilinear(im, X.ravel(), Y.ravel()).reshape(X.shape)
    return ts, ds, out, (X, Y)


if __name__ == "__main__":
    R = run(); A = R["_arrays"]
    rgb = np.load(D + "cache/senban_rgb.npy").astype(float)
    imgs = dict(r=rgb[..., 0], g=rgb[..., 1], b=rgb[..., 2])
    for k, nm in enumerate(["top", "right", "bottom", "left"]):
        ts, ds, o, _ = unwrap(A, k, ncol=880, img=imgs)
        s = np.dstack([o["r"], o["g"], o["b"]])
        s = 255 * (np.clip(s, 0, 255) / 255.0) ** 0.6
        s = np.repeat(s, 4, 0)          # stretch depth x4 for visibility
        # mark depth 0 (threshold outline) with a thin red tick every 20 columns
        z = int((0 - ds[0]) * 4)
        s[z, ::20] = [255, 0, 0]
        write_png(D + f"cache/strip_{nm}.png", s.astype(np.uint8))
    print("ok")
