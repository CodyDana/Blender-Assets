import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2_ring_fit import *
import math
px, pz = 15.4, 156.5
def aspect(alpha, tau, v, yaw=None):
    u = np.array([math.cos(math.radians(alpha)), math.sin(math.radians(alpha)), 0.0])
    zz = np.array([0, 0, 1.0]); ux = np.cross(u, zz)
    w = -math.cos(math.radians(tau)) * zz + math.sin(math.radians(tau)) * ux
    c = np.array([px, -21.5, pz]) + 21.9 * w
    a = np.linspace(0, 2 * math.pi, 360)[:, None]
    pts = c + 21.9 * (np.cos(a) * u + np.sin(a) * (-w))
    xy, _ = project(pts, v, yaw)
    return (xy[:, 0].max() - xy[:, 0].min()) / (xy[:, 1].max() - xy[:, 1].min())
for alpha in (-50, -40, -35, -30, -20, 0, 10):
    for tau in (0, 10, 20, 30):
        s, per = score((px, -21.5, pz), alpha, tau)
        asp = {v: round(aspect(alpha, tau, v), 2) for v in VIEW_X_PX}
        print(alpha, tau, round(s, 2), per, asp)
