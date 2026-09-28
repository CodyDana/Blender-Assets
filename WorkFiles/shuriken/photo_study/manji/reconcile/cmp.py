import numpy as np, json, os, sys
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
OUT = D + "reconcile/"

A = np.load(D + "radial/mask.npy")
B = np.load(D + "contour/mask_final.npy")
if A.ndim == 1:
    A = np.unpackbits(A)[: B.size].reshape(B.shape)
print("A", A.shape, A.dtype, A.min(), A.max())
print("B", B.shape, B.dtype, B.min(), B.max())
A = A.astype(bool); B = B.astype(bool)
if A.shape != B.shape:
    print("SHAPE MISMATCH"); sys.exit(1)
aA = A.sum(); aB = B.sum()
inter = (A & B).sum(); union = (A | B).sum()
print("areaA %d areaB %d  ratio %.4f" % (aA, aB, aB / aA))
print("IoU %.5f  A\\B %d  B\\A %d" % (inter / union, (A & ~B).sum(), (B & ~A).sum()))

def centroid(M):
    ys, xs = np.nonzero(M)
    return xs.mean(), ys.mean()
print("centroid A", centroid(A), "B", centroid(B))

# radial profiles from a common centre
cx = (centroid(A)[0] + centroid(B)[0]) / 2.0
cy = (centroid(A)[1] + centroid(B)[1]) / 2.0
print("common centre", cx, cy)

H, W = A.shape
th = np.arange(0, 360, 0.05)
rad = np.deg2rad(th)
# ray march: sample along each ray, find last inside
rr = np.arange(0, 1600, 0.25)
res = {}
for name, M in (("A", A), ("B", B)):
    X = cx + np.outer(np.cos(rad), rr)
    Y = cy - np.outer(np.sin(rad), rr)   # y-up angle convention (image row grows downward)
    xi = np.clip(np.round(X).astype(int), 0, W - 1)
    yi = np.clip(np.round(Y).astype(int), 0, H - 1)
    inside = M[yi, xi]
    # last True index per row
    idx = inside.shape[1] - 1 - np.argmax(inside[:, ::-1], axis=1)
    idx = np.where(inside.any(axis=1), idx, 0)
    res[name] = rr[idx]
np.save(OUT + "rtheta_AB.npy", np.stack([th, res["A"], res["B"]]))
dA, dB = res["A"], res["B"]
d = dA - dB
print("r(theta): meanA %.2f meanB %.2f  mean diff %.3f px  median %.3f  p05 %.2f p95 %.2f  max|d| %.2f"
      % (dA.mean(), dB.mean(), d.mean(), np.median(d), np.percentile(d, 5), np.percentile(d, 95), np.abs(d).max()))

# where do they differ most? bin by direction of outward normal approximated by theta
for lo in range(0, 360, 30):
    m = (th >= lo) & (th < lo + 30)
    print("  theta %3d-%3d : diff mean %+6.2f  med %+6.2f  p95 %+6.2f" % (lo, lo + 30, d[m].mean(), np.median(d[m]), np.percentile(d[m], 95)))

# tips: max r per lobe
tips = {}
for name in ("A", "B"):
    r = res[name]
    t = []
    for k in range(4):
        m = (th >= k * 90 - 45 + 0) & (th < k * 90 + 45)
        sub_th = th[m]; sub_r = r[m]
        j = np.argmax(sub_r)
        t.append((sub_th[j], sub_r[j]))
    tips[name] = t
    print(name, "tips (theta,r):", ["(%.2f, %.1f)" % x for x in t])
json.dump({"areaA": int(aA), "areaB": int(aB), "IoU": float(inter / union),
           "centroidA": centroid(A), "centroidB": centroid(B),
           "tipsA": tips["A"], "tipsB": tips["B"]}, open(OUT + "cmp.json", "w"), indent=1, default=float)
