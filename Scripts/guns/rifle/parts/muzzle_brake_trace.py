"""MUZZLE BRAKE detail round 2b: hand trace of c3 (panel px, read off luminance tables of the panel) and its
back-projection onto the brake's outer surface through the brake-only c3 camera (scratch/detail/muzzle_brake/cameras).

    py -3 -B Scripts/guns/rifle/parts/muzzle_brake_trace.py table  x0 x1 y0 y1     luminance table of the panel
    py -3 -B Scripts/guns/rifle/parts/muzzle_brake_trace.py back                   back-project the traced points
    py -3 -B Scripts/guns/rifle/parts/muzzle_brake_trace.py proj                   project our model's landmarks

The traced points are the reference's own edges in c3 (the slot's dark interior against the lit web / body, the rim's
outer highlight). Back-projection: the nearest point on the surface rho = R(x) on the camera side (-Y, z from -r..r)
whose projection hits the traced pixel.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

# c3 panel px (read off a luminance table of the panel png, whose rows are 1 px below the kit panel's: PNG_DY corrects): the slot (rear edge top -> bottom, bottom, front edge bottom -> top) and the rim's
# outer highlight (its rear boundary against the web), top -> bottom
C3 = {
    "slot_rear": [(192.0, 167.0), (191.0, 170.0), (190.5, 175.0), (190.0, 180.0), (190.0, 185.0), (190.5, 190.0),
                  (191.5, 195.0), (194.0, 199.0), (197.0, 202.0), (200.0, 205.0), (203.0, 207.5)],
    "slot_bottom": [(203.0, 207.5), (206.0, 209.0), (209.0, 209.5), (212.0, 209.5)],
    "slot_front": [(212.0, 209.5), (212.5, 205.0), (211.5, 200.0), (210.5, 196.0), (209.5, 192.0), (208.5, 189.0),
                   (207.5, 186.0), (206.5, 183.0), (205.5, 180.0), (204.5, 177.0), (204.0, 174.0), (203.5, 172.0),
                   (202.5, 169.0), (201.0, 167.0)],
    "slot_top": [(192.0, 167.0), (194.0, 166.0), (196.5, 165.8), (199.0, 166.0), (201.0, 167.0)],
    "rim_back": [(206.0, 160.0), (206.0, 170.0), (207.5, 175.0), (209.5, 180.0), (211.5, 185.0), (213.5, 189.0),
                 (215.0, 192.0), (217.5, 196.0), (220.0, 200.0), (223.5, 204.0)],
}


PNG_DY = -1.0


def kit():
    import muzzle_brake_dev as D
    return D.kit()


def table(x0, x1, y0, y1):
    K = kit()
    P = K.panel("c3").astype(float).mean(2).astype(int)
    print("     " + " ".join("%3d" % x for x in range(x0, x1)))
    for y in range(y0, y1):
        print("%3d: " % y + " ".join("%3d" % v for v in P[y, x0:x1]))


def surface_grid(R_of, x=(840.0, 885.0), n=901):
    X = np.linspace(x[0], x[1], n)
    PH = np.radians(np.linspace(-89.5, 89.5, 359))
    XX, PP = np.meshgrid(X, PH)
    r = R_of(XX.ravel())
    return np.c_[XX.ravel(), -r * np.cos(PP.ravel()), r * np.sin(PP.ravel())]


def back():
    import parts.muzzle_brake as MB
    K = kit()
    cam = K.part_camera("muzzle_brake", "c3")
    P3 = surface_grid(lambda x: np.asarray(MB.R_at(x)))
    UV = cam.project(P3)
    out = {}
    for name, pts in C3.items():
        rows = []
        for u, v in pts:
            v = v + PNG_DY
            d = np.hypot(UV[:, 0] - u, UV[:, 1] - v)
            i = int(np.argmin(d))
            rows.append([round(float(P3[i, 0]), 2), round(float(P3[i, 2]), 2), round(float(d[i]), 2)])
        out[name] = rows
        print(name, rows)
    return out


def proj():
    """Project our model's rim outer edge (face plane x outer surface) and slot outline into c3 panel px."""
    import parts.muzzle_brake as MB
    K = kit()
    cam = K.part_camera("muzzle_brake", "c3")
    print("slot outline (X, Z) -> px")
    for x, z in MB.SLOT[::3]:
        r = float(MB.R_at(x))
        y = -np.sqrt(max(r * r - z * z, 0.0))
        print("  (%.1f, %.1f) -> %s" % (x, z, np.round(cam.project(np.array([[x, y, z]]))[0], 1)))
    print("rim outer edge (Z) -> px")
    for z in (9.0, 7.0, 5.0, 3.0, 0.0, -3.0, -5.0, -7.0, -9.0):
        r = getattr(MB, "LIP_R", 10.1)
        y = -np.sqrt(max(r * r - z * z, 0.0))
        x = MB.plane_x(z)
        print("  Z %.1f X %.2f -> %s" % (z, x, np.round(cam.project(np.array([[x, y, z]]))[0], 1)))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "table":
        table(*[int(a) for a in sys.argv[2:6]])
    elif cmd == "back":
        print(json.dumps(back()))
    elif cmd == "proj":
        proj()
