import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load().astype(np.float64)
bg = np.load(ROOT + "bgfit.npy").astype(np.float64)
L = rgb @ np.array([0.2126, 0.7152, 0.0722]); v, S = hsv(rgb)
Pr = np.load(ROOT + "contour_initial.npy"); N = np.load(ROOT + "contour_normals.npy")
M = np.load(ROOT + "M.npy").astype(np.float64)
targets = [(640, 450), (300, 755), (1100, 540), (795, 1100), (1100, 725), (575, 150), (770, 150)]
ts = np.arange(-14, 16.01, 1.0)
for tx, ty in targets:
    i = np.argmin(np.hypot(Pr[:, 0] - tx, Pr[:, 1] - ty))
    p, n = Pr[i], N[i]
    X = p[0] + ts * n[0]; Y = p[1] + ts * n[1]
    l = bilinear(L, X, Y); s = bilinear(S, X, Y); m = bilinear(M, X, Y)
    print(f"pt {p.round(1)} normal {n.round(2)}")
    print("  t :", " ".join(f"{t:5.0f}" for t in ts))
    print("  L :", " ".join(f"{a:5.2f}" for a in l))
    print("  S :", " ".join(f"{a:5.2f}" for a in s))
    print("  M :", " ".join(f"{a:5.1f}" for a in m))
