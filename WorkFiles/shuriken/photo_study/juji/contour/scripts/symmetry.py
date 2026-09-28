"""Rotational / mirror symmetry of the refined silhouette: IoU of the mask with rotated / reflected copies of the contour
about the fitted centre (region y < 30 excluded, since the top tip is cut by the image edge)."""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
Q = np.load(ROOT + "contour_refined.npy")
O = json.load(open(ROOT + "outline_measurements.json"))
c0 = np.array(O["centre_px"])
ax = np.radians(O["axes"]["right"]["dir_deg_imagecoords"])
H, W = 1363, 1370
base = poly_fill(Q, H, W)
valid = np.ones((H, W), bool); valid[:30] = False
def rot(P, a):
    ca, sa = np.cos(a), np.sin(a); rel = P - c0
    return c0 + np.stack([ca * rel[:, 0] - sa * rel[:, 1], sa * rel[:, 0] + ca * rel[:, 1]], 1)
def refl(P, a):   # reflect about the line through c0 at angle a
    d = np.array([np.cos(a), np.sin(a)]); rel = P - c0
    return c0 + 2 * (rel @ d)[:, None] * d - rel
res = {}
for k, a in (("rot90", np.pi / 2), ("rot180", np.pi), ("rot270", 3 * np.pi / 2)):
    m2 = poly_fill(rot(Q, a), H, W)
    v = valid & (poly_fill(rot(np.array([[0, 0], [W, 0], [W, 30], [0, 30]], float), a), H, W) == 0)
    inter = (base & m2 & v).sum(); uni = ((base | m2) & v).sum()
    res[k] = round(float(inter / uni), 4)
for k, a in (("mirror_horizontal_axis", ax), ("mirror_vertical_axis", ax + np.pi / 2), ("mirror_diag45", ax + np.pi / 4), ("mirror_diag135", ax + 3 * np.pi / 4)):
    m2 = poly_fill(refl(Q, a), H, W)
    v = valid & (poly_fill(refl(np.array([[0, 0], [W, 0], [W, 30], [0, 30]], float), a), H, W) == 0)
    inter = (base & m2 & v).sum(); uni = ((base | m2) & v).sum()
    res[k] = round(float(inter / uni), 4)
# boundary distance: mean |distance| between contour and rotated contour (symmetric chamfer on sampled points)
def chamfer(A, B):
    d = []
    for i in range(0, len(A), 4):
        d.append(np.min(np.hypot(B[:, 0] - A[i, 0], B[:, 1] - A[i, 1])))
    return float(np.mean(d)), float(np.percentile(d, 95))
ok = Q[:, 1] > 30
for k, a in (("rot90", np.pi / 2), ("rot180", np.pi)):
    B = rot(Q, a); Bk = B[B[:, 1] > 30]
    mc, p95 = chamfer(Q[ok], Bk)
    res[k + "_mean_boundary_dev_px"] = round(mc, 2); res[k + "_p95_boundary_dev_px"] = round(p95, 2)
json.dump(res, open(ROOT + "symmetry.json", "w"), indent=1)
print(res)
