# Inspect edge-normal profiles (averaged along the edge) for the bevel band, per side.
import sys, json, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run
from geom import bilinear

R = run()
A = R["_arrays"]
L, Yw = A["L"], A["Yw"]
corners, fits = A["corners"], A["fits"]
np.set_printoptions(linewidth=260)


def station(k, t, half=10.0, d0=-10, d1=60, step=1.0):
    """point on fitted arc of side k at fraction t (by angle), inward normal, tangential-averaged profile"""
    f = fits[k]; C = np.array([f["cx"], f["cy"]]); Rr = f["R"]
    A0, B0 = corners[k], corners[(k + 1) % 4]
    a0 = math.atan2(*(A0 - C)[::-1]); a1 = math.atan2(*(B0 - C)[::-1])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    ang = a0 + t * da
    P = C + Rr * np.array([math.cos(ang), math.sin(ang)])
    nin = (C - P) / Rr * -1.0          # centre is outside the plate -> inward = away from centre
    tang = np.array([-nin[1], nin[0]])
    ds = np.arange(d0, d1 + 1e-9, step)
    offs = np.arange(-half, half + 1e-9, 1.0)
    Lp = np.zeros(len(ds)); Yp = np.zeros(len(ds))
    for o in offs:
        xs = P[0] + o * tang[0] + ds * nin[0]; ys = P[1] + o * tang[1] + ds * nin[1]
        Lp += bilinear(L, xs, ys); Yp += bilinear(Yw, xs, ys)
    return P, nin, ds, Lp / len(offs), Yp / len(offs)


if __name__ == "__main__":
    for k, nm in enumerate(["top", "right", "bottom", "left"]):
        for t in (0.25, 0.5, 0.75):
            P, n, ds, Lp, Yp = station(k, t)
            print(f"{nm} t={t} P=({P[0]:.0f},{P[1]:.0f}) n=({n[0]:.2f},{n[1]:.2f})")
            print("  d ", ds[::1].astype(int))
            print("  L ", Lp.round(0).astype(int))
            print("  Yw", Yp.round(0).astype(int))
