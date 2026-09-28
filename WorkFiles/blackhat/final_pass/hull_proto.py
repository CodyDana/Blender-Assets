import itertools
import math
import numpy as np

P = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/UnrealVerify_indep_v1/truth_SM_BlackHat_LOD0_verts_cm.npy") * 10
body = P[(P[:, 2] > -0.5) & (np.hypot(P[:, 0], P[:, 1]) < 302)]


def support_vertices(P, dirs, margin):
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    h = (P @ dirs.T).max(0) + margin
    tri = np.array(list(itertools.combinations(range(len(dirs)), 3)))
    A = dirs[tri]
    b = h[tri]
    det = np.linalg.det(A)
    ok = np.abs(det) > 1e-6
    v = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]
    inside = (v @ dirs.T <= h + 1e-6).all(1)
    v = v[inside]
    v = np.unique(np.round(v, 4), axis=0)
    # merge near duplicates
    keep = []
    for p in v:
        if all(np.linalg.norm(p - q) > 0.05 for q in keep):
            keep.append(p)
    return np.array(keep), dirs, h


def dirs_set(n_az, elevs, extra=()):
    d = []
    for e in elevs:
        for i in range(n_az):
            ph = (i + 0.5) * 2 * math.pi / n_az
            d.append((math.cos(ph) * math.cos(math.radians(e)), math.sin(ph) * math.cos(math.radians(e)), math.sin(math.radians(e))))
    d += [(0, 0, -1), (0, 0, 1)] + list(extra)
    return np.array(d, float)


rng = np.random.default_rng(1)
T = rng.normal(size=(4000, 3))
T /= np.linalg.norm(T, axis=1, keepdims=True)
hp = (body @ T.T).max(0)
for n_az, elevs in ((16, (0, 64)), (20, (0, 64)), (24, (0, 64)), (20, (0, 64, 40)), (16, (0, 64, 45, 80)), (20, (0, 50, 64, 78))):
    V, dirs, h = support_vertices(body, dirs_set(n_az, elevs), 1.5)
    hh = (V @ T.T).max(0)
    gap = hh - hp
    print(n_az, elevs, "verts", len(V), "gap max %.2f p95 %.2f mean %.2f" % (gap.max(), np.percentile(gap, 95), gap.mean()),
          "ztop over %.2f" % (V[:, 2].max() - body[:, 2].max()), "zbot %.2f" % (body[:, 2].min() - V[:, 2].min()),
          "worst dir", T[np.argmax(gap)].round(2))

print("greedy")
for base_az, target in ((12, 3.5), (16, 3.5), (16, 4.0), (20, 3.0)):
    dirs = dirs_set(base_az, (0, 64))
    for it in range(80):
        V, dn, h = support_vertices(body, dirs, 1.0)
        gap = (V @ T.T).max(0) - hp
        if gap.max() <= target:
            break
        dirs = np.vstack([dirs, T[np.argmax(gap)]])
    print(base_az, target, "planes", len(dirs), "verts", len(V), "gap max %.2f p95 %.2f mean %.2f" % (gap.max(), np.percentile(gap, 95), gap.mean()))

print("greedy capped at 50 vertices")
for base_az in (10, 12, 13, 14, 15, 16):
    for off in (0.0, 0.5):
        dirs = dirs_set(base_az, (0, 64))
        best = None
        for it in range(30):
            V, dn, h = support_vertices(body, dirs, 1.0)
            if len(V) > 50:
                break
            gap = (V @ T.T).max(0) - hp
            best = (len(dirs), len(V), gap.max(), np.percentile(gap, 95), gap.mean())
            dirs = np.vstack([dirs, T[np.argmax(gap)]])
        print(base_az, "planes %d verts %d gap max %.2f p95 %.2f mean %.2f" % best)
        break
