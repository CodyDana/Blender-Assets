"""Project every case box (plinth + glass corners) through a Blender-style camera (sensor 36 mm wide, level up = +Z,
look-at, lens, shift_y) at 1600 x 900; flag cases cut by the frame. Usage: py -3 cam_check.py"""
import itertools, sys
import numpy as np
from solve import CASES as SC

CASES = dict(SC, L=(1.8, 1.3, 0.50, 0.70), LN=(1.6, 1.0, 0.45, 0.75), M=(1.8, 1.2, 0.70, 0.55))
TABLE = [("1", "L", 6.0, 4.00, 0), ("2", "M", 6.0, 8.70, 0), ("3", "LN", 6.0, 13.40, 0),
         ("5", "S", 2.90, 3.31, 0), ("4", "Tall", 3.15, 5.02, 0), ("G1", "S", 3.27, 7.08, 90), ("G3", "Tall", 2.91, 9.84, 0),
         ("8", "SF", 9.06, 3.30, -90), ("7", "S", 9.26, 5.10, 0), ("6", "MT", 8.98, 7.30, 0), ("G2", "Tall", 8.97, 9.90, 0)]


def corners(t, x, y, rot):
    W, D, H, G = CASES[t]
    ex, ey = (D, W) if rot in (90, -90) else (W, D)
    return np.array([(x + sx * a, y + sy * b, z) for (a, b, z0, z1) in ((ex / 2, ey / 2, 0.0, H),
                     (ex / 2 - 0.022, ey / 2 - 0.022, H, H + G)) for sx, sy, z in itertools.product((-1, 1), (-1, 1), (z0, z1))])


def project(cam, pts, res=(1600, 900)):
    loc, look, lens = np.array(cam[0], float), np.array(cam[1], float), cam[2]
    shift = cam[3] if len(cam) > 3 else 0.0
    f = look - loc; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    W, H = res
    k = lens / 36.0 * W
    out = []
    for p in pts:
        d = p - loc
        z = d @ f
        if z <= 0.05:
            out.append((np.nan, np.nan)); continue
        out.append((W / 2 + k * (d @ r) / z, H / 2 - k * (d @ u) / z + shift * W))
    return np.array(out)


def check(name, cam, res=(1600, 900), table=TABLE):
    print(name, cam)
    for lab, t, x, y, rot in table:
        p = project(cam, corners(t, x, y, rot), res)
        if np.isnan(p).any():
            print("   %-3s behind camera" % lab); continue
        b = [p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()]
        if b[1] < 0 or b[0] > res[0] or b[3] < 0 or b[2] > res[1]:
            continue
        cut = [s for s, c in (("L", b[0] < 0), ("R", b[1] > res[0]), ("T", b[2] < 0), ("B", b[3] > res[1])) if c]
        print("   %-3s %-4s box %s %s" % (lab, t, [round(v) for v in b], "CUT " + "".join(cut) if cut else ""))


if __name__ == "__main__":
    check("C1 1448x1086", ((6.0, -4.18, 3.39), (6.0, 20.0, 3.39), 40.0, -0.315), (1448, 1086))
    for a in sys.argv[1:]:
        c = eval(a)
        check("cam", c)
