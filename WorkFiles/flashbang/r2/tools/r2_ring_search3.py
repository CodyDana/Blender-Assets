import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2_ring_fit import *
import math
def aspect(top, alpha, tau, v):
    u = np.array([math.cos(math.radians(alpha)), math.sin(math.radians(alpha)), 0.0])
    zz = np.array([0, 0, 1.0]); ux = np.cross(u, zz)
    w = -math.cos(math.radians(tau)) * zz + math.sin(math.radians(tau)) * ux
    c = np.array(top) + 21.9 * w
    a = np.linspace(0, 2 * math.pi, 360)[:, None]
    pts = c + 21.9 * (np.cos(a) * u + np.sin(a) * (-w))
    xy, _ = project(pts, v)
    return (xy[:, 0].max() - xy[:, 0].min()) / (xy[:, 1].max() - xy[:, 1].min())
res = []
for px in (11.0, 12.5, 14.0, 15.4):
    for py in (-16.5, -18.5, -20.5):
        for pz in (155.0, 156.5, 158.0):
            for alpha in (-45, -35, -25, -15):
                for tau in (0, 10, 20):
                    s, per = score((px, py, pz), alpha, tau)
                    a1, a2, a3 = aspect((px, py, pz), alpha, tau, "v1"), aspect((px, py, pz), alpha, tau, "v2"), aspect((px, py, pz), alpha, tau, "v3")
                    pen = 10 * max(0, 0.95 - a1) + 10 * max(0, 0.9 - a3) + 10 * max(0, a2 - 0.35)
                    res.append((round(s + pen, 2), round(s, 2), px, py, pz, alpha, tau, per, round(a1, 2), round(a2, 2), round(a3, 2)))
res.sort(key=lambda t: t[0])
for r in res[:15]:
    print(r)
