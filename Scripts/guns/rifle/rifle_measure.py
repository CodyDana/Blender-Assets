"""AR-01 measure stage (gates L3 features and L4 dimensions) on the built geometry, frame M (mm):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_measure.py

Features are measured by ray scans of the built meshes (side rays along +Y from the right, top rays along -Z), never
from the build numbers; dimensions from part bounds and ray hits. Results -> scratch/measure_result.json.
L3 tolerance: 2 sheet px = 2 / 0.8225 = 2.43 mm on the side views.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SPEC, GRIP, SCRATCH  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from gunlib import bl  # noqa: E402

PXMM = 0.822479
TOL_MM = 2.0 / PXMM
objs = {o.name: o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")}
GEO = {n: bl.tris_np(o, GRIP) for n, o in objs.items()}                 # frame M mm


def tree(names):
    V, T, n = [], [], 0
    for nm in names:
        v, t = GEO[nm]
        V.append(v)
        T.append(t + n)
        n += len(v)
    V, T = np.vstack(V), np.vstack(T)
    return BVHTree.FromPolygons([tuple(p) for p in V], [tuple(int(i) for i in t) for t in T], all_triangles=True)


ALL = tree(list(GEO))


def ray(t, o, d, dist=1e4):
    h = t.ray_cast(Vector(o), Vector(d), dist)
    return None if h[0] is None else np.array(h[0])


def side_y(x, z, t=ALL):
    """First hit Y of a ray from the right (-Y) at (x, z); None = see-through."""
    h = ray(t, (x, -200.0, z), (0, 1, 0))
    return None if h is None else float(h[1])


def edges_1d(vals, xs, pred):
    """Positions where pred(value) switches along xs (linear-midpoint)."""
    flags = np.array([pred(v) for v in vals])
    out = []
    for i in range(1, len(xs)):
        if flags[i] != flags[i - 1]:
            out.append(round(float(0.5 * (xs[i] + xs[i - 1])), 2))
    return out


res = {"L3": [], "L4": [], "tol_mm_side": round(TOL_MM, 3)}


def l3(name, measured, spec, err, note=""):
    res["L3"].append({"feature": name, "measured": measured, "spec": spec, "error_mm": None if err is None else
                      round(float(err), 3), "pass": err is not None and err <= TOL_MM, "note": note})


# ---- ejection port: scan Z at X 400 and X at Z 10 (first hit deeper than the wall = opening)
SHELL = tree(["receiver", "dust_cover"])            # the opening = rays that pass the receiver wall and cover
zs = np.arange(-2.0, 22.0, 0.05)
ys = [side_y(400.0, z, SHELL) for z in zs]
e = edges_1d(ys, zs, lambda y: y is None or y > 0.0)
xs = np.arange(330.0, 460.0, 0.05)
ysx = [side_y(x, 10.0, SHELL) for x in xs]
ex = edges_1d(ysx, xs, lambda y: y is None or y > 0.0)
pz = [e[0], e[-1]] if len(e) >= 2 else None
px = [ex[0], ex[-1]] if len(ex) >= 2 else None
err = None if not pz or not px else max(abs(pz[0] - 3.0), abs(pz[1] - 17.0), abs(px[0] - 338.0), abs(px[1] - 452.0))
l3("ejection port corners (X, Z)", {"X": px, "Z": pz}, "X 338 / 452, Z 3 / 17", err,
   "opening = rays reaching the carrier / interior behind the wall plane")

# ---- side dimple centre: deepest point of the right wall around (397, -17)
best = None
for x in np.arange(385.0, 409.0, 0.25):
    for z in np.arange(-24.0, -10.0, 0.25):
        y = side_y(x, z)
        if y is not None and (best is None or y > best[2]):
            best = (x, z, y)
dc = None
if best:
    # centroid of the points within 0.05 of the deepest
    pts = []
    for x in np.arange(best[0] - 3, best[0] + 3, 0.25):
        for z in np.arange(best[1] - 3, best[1] + 3, 0.25):
            y = side_y(x, z)
            if y is not None and y > best[2] - 0.05:
                pts.append((x, z))
    dc = np.mean(pts, axis=0)
    l3("side dimple centre", [round(dc[0], 2), round(dc[1], 2)], [397.0, -17.0],
       float(np.hypot(dc[0] - 397.0, dc[1] + 17.0)), "depth %.2f mm" % (best[2] + 20.75))

# ---- rivets (right): apex of each head near its spec position
riv = SPEC.feature("receiver", "rivets_right")["XZ"]
errs, meas = [], []
for (x0, z0) in riv:
    # detail fix: the heads are flat-topped (and one spot is the stamped detent plate): the apex is the CENTROID of the
    # points within 0.05 mm of the most proud one in the window (was: the first most-proud point found)
    hits = []
    for x in np.arange(x0 - 3, x0 + 3.01, 0.2):
        for z in np.arange(z0 - 3, z0 + 3.01, 0.2):
            y = side_y(x, z)
            if y is not None and y < -21.0:
                hits.append((x, z, y))
    best = None
    if hits:
        H = np.array(hits)
        top = H[H[:, 2] < H[:, 2].min() + 0.05]
        best = (float(top[:, 0].mean()), float(top[:, 1].mean()), float(H[:, 2].min()))
    if best:
        meas.append([round(best[0], 1), round(best[1], 1)])
        errs.append(math.hypot(best[0] - x0, best[1] - z0))
    else:
        meas.append(None)
        errs.append(99.0)
l3("right rivets (9)", meas, riv, max(errs), "head apex position; max error over the 9")

# ---- ledge seam: the groove between the receiver wall and the guard flange at X 255 / 300 / 360
seam = SPEC.part("receiver")["dims"]["ledge_seam_XZ"]
errs, meas = [], []
for (x0, z0) in seam:
    zz = np.arange(z0 - 1.5, z0 + 1.5, 0.02)
    yv = [side_y(x0, z) for z in zz]
    k = int(np.nanargmax([(-1e9 if y is None else y) for y in yv]))       # deepest = the seam groove
    meas.append([x0, round(float(zz[k]), 2)])
    errs.append(abs(zz[k] - z0))
l3("trigger-guard flange ledge seam", meas, seam, max(errs))

# ---- selector pivot: boss apex
best = None
for x in np.arange(278.0, 288.0, 0.1):
    for z in np.arange(-13.0, -3.0, 0.1):
        y = side_y(x, z)
        if y is not None and (best is None or y < best[2]):
            best = (x, z, y)
if best:
    pts = []
    for x in np.arange(278.0, 288.0, 0.1):
        for z in np.arange(-13.0, -3.0, 0.1):
            y = side_y(x, z)
            if y is not None and y < best[2] + 0.03:
                pts.append((x, z))
    c = np.mean(pts, axis=0)
    l3("selector pivot", [round(c[0], 2), round(c[1], 2)], [282.8, -7.8], math.hypot(c[0] - 282.8, c[1] + 7.8))

# ---- leaf rear end / notch plate top (top rays down, Y = +4 beside the notch)
xs = np.arange(445.0, 453.0, 0.02)
tops = [ray(ALL, (x, 4.0, 200.0), (0, 0, -1)) for x in xs]
zt = [None if h is None else float(h[2]) for h in tops]
rear = next((xs[i] for i in range(len(xs)) if zt[i] is not None and zt[i] > 44.0), None)
ztop = max(z for z in zt if z is not None)
l3("leaf rear end / notch plate", [None if rear is None else round(float(rear), 2), round(ztop, 2)], [448.7, 48.0],
   None if rear is None else max(abs(rear - 448.7), abs(ztop - 48.0)))

# ---- slider X extent and top
xs = np.arange(454.0, 470.0, 0.02)
zz = [ray(ALL, (x, 6.6, 200.0), (0, 0, -1)) for x in xs]
on = [h is not None and h[2] > 46.5 for h in zz]
xx = [float(xs[i]) for i in range(len(xs)) if on[i]]
st = max(float(h[2]) for h in zz if h is not None)
l3("rear sight slider", {"X": [round(min(xx), 2), round(max(xx), 2)] if xx else None, "top": round(st, 2)},
   "X 457.5-465.5, top 48.5", None if not xx else max(abs(min(xx) - 457.5), abs(max(xx) - 465.5), abs(st - 48.5)))

# ---- see-through regions (side): gap under the leaf, ear window, guard opening
def see_through_bbox(x0, x1, z0, z1, step=0.1, seed=None):
    """bbox of the see-through region (rays from the right that hit nothing); with a seed, only the connected
    region containing it (4-neighbour flood fill on the scan grid)."""
    X = np.arange(x0, x1, step)
    Z = np.arange(z0, z1, step)
    M = np.array([[side_y(x, z) is None for z in Z] for x in X])
    if seed is not None:
        from collections import deque
        i0 = int(np.argmin(np.abs(X - seed[0])))
        j0 = int(np.argmin(np.abs(Z - seed[1])))
        if not M[i0, j0]:
            return None
        keep = np.zeros_like(M)
        q = deque([(i0, j0)])
        keep[i0, j0] = True
        while q:
            i, j = q.popleft()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < len(X) and 0 <= b < len(Z) and M[a, b] and not keep[a, b]:
                    keep[a, b] = True
                    q.append((a, b))
        M = keep
    ii, jj = np.nonzero(M)
    if not len(ii):
        return None
    P = np.c_[X[ii], Z[jj]]
    return [round(float(P[:, 0].min()), 2), round(float(P[:, 0].max()), 2), round(float(P[:, 1].min()), 2),
            round(float(P[:, 1].max()), 2)]


# seed inside the traced slit (Z 38.7-40.9); round 0 seeded (473.0, 38.5), inside its old wedge
b = see_through_bbox(460.0, 495.0, 32.0, 43.0, 0.1, (470.0, 39.8))
l3("gap under the leaf (see-through bbox X0 X1 Z0 Z1)", b, [465.8, 487.5, 34.8, 40.9],
   None if b is None else max(abs(b[0] - 465.8), abs(b[1] - 487.5), abs(b[2] - 34.8), abs(b[3] - 40.9)),
   "the trace's hole is a thin sliver (37 px); bbox compared")
b = see_through_bbox(812.0, 831.0, 9.0, 23.5, 0.1, (822.0, 15.0))
l3("front sight ear window (bbox)", b, [813.7, 827.2, 11.8, 21.6],
   None if b is None else max(abs(b[0] - 813.7), abs(b[1] - 827.2), abs(b[2] - 11.8), abs(b[3] - 21.6)))

# ---- ear boss centre (raised drum boss on the right ear; detail fix: measured against the tapered ear face; before
# the fix the -10.75 threshold sat above the r2b boss and the feature was silently skipped)
from parts import front_sight as _FS  # noqa: E402
best = []
for x in np.arange(820.0, 829.5, 0.1):
    for z in np.arange(25.5, 34.5, 0.1):
        y = side_y(x, z)
        if y is not None and y < -(_FS.ear_out_y(z) + 0.5):        # detail fix: proud of the TAPERED ear face
            best.append((x, z))
if best:
    c = np.mean(best, axis=0)
    l3("front sight ear boss + hole", [round(c[0], 2), round(c[1], 2)], [824.7, 29.9], math.hypot(c[0] - 824.7, c[1] - 29.9))

# ---- handguard side slot ends (the dark pockets: rays reach deeper than the guard surface at Z 15)
xs = np.arange(535.0, 635.0, 0.05)
yv = [side_y(x, 15.0) for x in xs]
ee = edges_1d(yv, xs, lambda y: y is not None and y > -14.0)
spec_ends = [543.0, 571.0, 595.0, 623.0]
if len(ee) >= 4:
    err = max(abs(a - b) for a, b in zip(ee[:4], spec_ends))
else:
    err = None
l3("handguard side slot ends (X at Z 15)", ee, spec_ends, err)

# ---- gas tube vents (rays reach the piston, deeper than the tube wall)
xs = np.arange(655.0, 685.0, 0.05)
yv = [side_y(x, 24.2) for x in xs]
ve = edges_1d(yv, xs, lambda y: y is not None and y > -9.0)
l3("gas tube vent slots (X span)", [ve[0], ve[-1]] if ve else None, [662.0, 680.0],
   None if not ve else max(abs(ve[0] - 662.0), abs(ve[-1] - 680.0)), "low-confidence feature (3 px)")

# ---- trigger guard opening vs the trace hole bbox
b = see_through_bbox(296.0, 356.0, -70.0, -30.0, 0.15, (338.0, -60.0))
jl = json.loads((Path(__file__).resolve().parents[3] / "WorkFiles/guns/rifle/trace/LEFT_outline.json").read_text())
hole = None
for r in jl["silhouette"]:                       # the traced see-through hole inside the guard
    mm = np.array(r["mm"])
    if r["area_px"] < 0 and 295 < mm[:, 0].mean() < 356 and -70 < mm[:, 1].mean() < -30:
        hole = [round(float(mm[:, 0].min()), 2), round(float(mm[:, 0].max()), 2), round(float(mm[:, 1].min()), 2),
                round(float(mm[:, 1].max()), 2)]
l3("trigger-guard opening (see-through bbox)", b, hole,
   None if (b is None or hole is None) else max(abs(a - c) for a, c in zip(b, hole)),
   "the trigger blade sits inside the opening, so the bbox spans the whole hole")

# ---- magazine rib top tips (Z of the highest rib point on the right side)
V, T = GEO["magazine"]
rib = V[(V[:, 1] < -(float(SPEC.key["magazine"]["thickness"]) / 2 + 0.5))]      # right-side ribs (body face at -T/2)
l3("magazine rib top tips (Z)", round(float(rib[:, 2].max()), 2) if len(rib) else None, -38.5,
   None if not len(rib) else abs(rib[:, 2].max() + 38.5), "spec tolerance +-1.5")

# ---- butt plate screws (centre line Z on the rear face)
V, T = GEO["butt_screws"]
zc = sorted({round(float(z), 1) for z in [V[V[:, 2] > -50, 2].mean(), V[V[:, 2] < -50, 2].mean()]})
l3("butt-plate screws (Z)", zc, [-87.5, -10.0], max(abs(zc[0] + 87.5), abs(zc[1] + 10.0)), "close-up rule 1 mm")


# ======================================================================================== L4 dimensions
def bb(names):
    V = np.vstack([GEO[n][0] for n in names])
    return V.min(0), V.max(0)


K = SPEC.key
lo, hi = bb(list(GEO))
lo_nm, hi_nm = bb([n for n in GEO if not n.startswith("magazine")])


def l4(name, measured, spec, how):
    err = abs(measured - spec)
    res["L4"].append({"dimension": name, "measured": round(float(measured), 3), "spec": spec,
                      "error_mm": round(float(err), 3), "pass": err <= 0.05, "how": how})


l4("overall_length", hi[0] - lo[0], K["overall_length"], "bounds X of all parts")
l4("overall_height_with_mag", hi[2] - lo[2], K["overall_height_with_mag"], "bounds Z with the magazine")
l4("overall_height_without_mag", hi_nm[2] - lo_nm[2], K["overall_height_without_mag"], "bounds Z without it")
b0, b1 = bb(["barrel"])
l4("barrel_length", b1[0] - b0[0], K["barrel_length"], "barrel bounds X")
l4("barrel_dia", b1[2] - b0[2], K["barrel_dia"], "barrel bounds Z")
r0, r1 = bb(["receiver"])
l4("barrel_exposed_from_receiver_face", b1[0] - r1[0], K["barrel_exposed_from_receiver_face"],
   "crown X - receiver front face X")
t0, t1 = bb(["rear_trunnion"])
l4("receiver_length", r1[0] - t0[0], K["receiver_length"], "receiver front face - rear trunnion rear face")
l4("receiver_width_walls", r1[1] - r0[1], K["receiver_width_walls"], "receiver bounds Y")
c0, c1 = bb(["dust_cover"])
l4("dust_cover_width", c1[1] - c0[1], K["dust_cover_width"], "dust cover bounds Y")
l4("dust_cover_crown_Z", c1[2], K["dust_cover_crown_Z"], "dust cover top")
zb = [ray(ALL, (x, -19.0, -60.0), (0, 0, 1)) for x in np.arange(433.0, 484.5, 0.5)]
zbm = float(np.mean([h[2] for h in zb if h is not None]))
l4("receiver_bottom_Z", zbm, K["receiver_bottom_Z"], "mean wall-bottom Z over X 433-484 (the traced line)")
l4("receiver_height_incl_cover", c1[2] - zbm, K["receiver_height_incl_cover"], "crown - mean bottom ahead of the well")
lf0, lf1 = bb(["rear_sight_leaf"])
l4("rear_sight_leaf_top_Z", lf1[2], K["rear_sight_leaf_top_Z"], "leaf (notch plate) top")
f0, f1 = bb(["front_sight_block"])
l4("front_sight_ear_top_Z", f1[2], K["front_sight_ear_top_Z"], "front sight block top")
# notch bottom and post tip
nb = ray(tree(["rear_sight_leaf"]), (449.9, 0.0, 60.0), (0, 0, -1))
l4("sight_line.notch_Z", nb[2], K["sight_line"]["notch_M"][2], "ray down the notch centre")
pt = ray(tree(["front_sight_post"]), (825.3, 0.0, 60.0), (0, 0, -1))
l4("sight_line.post_tip_Z", pt[2], K["sight_line"]["post_tip_M"][2], "ray down the post")
g0, g1 = bb(["pistol_grip"])
l4("grip.bottom_Z", g0[2], K["grip"]["bottom_Z"], "grip bounds")
s0, s1 = bb(["buttstock"])
l4("stock_length", s1[0], K["stock_length"], "stock max X (from the butt heel X 0)")
p0, p1 = bb(["butt_plate"])
l4("butt_height", p1[2] - p0[2], K["butt_height"], "butt plate bounds Z")
l4("butt_width", p1[1] - p0[1], K["butt_width"], "butt plate bounds Y")
h0, h1 = bb(["lower_handguard"])
l4("handguard_lower_length", h1[0] - h0[0], K["handguard_lower_length"], "lower handguard bounds X (incl. tenon)")
u0, u1 = bb(["upper_handguard"])
l4("handguard_upper_length", u1[0] - u0[0], K["handguard_upper_length"], "upper handguard bounds X (incl. tenon)")
m0, m1 = bb(["magazine", "magazine_floor_plate"])
from parts import magazine as _MAGP                    # detail fix: the ribs are RIB_H proud (0.75 since the detail fix)
l4("magazine.thickness", bb(["magazine"])[1][1] - bb(["magazine"])[0][1] - 2.0 * _MAGP.RIB_H, K["magazine"]["thickness"],
   "body bounds Y minus the two ribs (2 x RIB_H %.2f)" % _MAGP.RIB_H)
l4("magazine.bottom_Z", m0[2], K["magazine"]["bottom_Z"], "magazine + floor plate bounds")
# the brake BODY (the sheet's length / diameter): without the small detent knob on top at the junction (|Y| < 2.7,
# Z > 8.5, X < 853.5), which the side views do not show (detail round 2 added it from c3); diameter = 2 x the largest
# radius about the bore axis
Vb = GEO["muzzle_brake"][0]
knob = (np.abs(Vb[:, 1]) < 2.7) & (Vb[:, 2] > 8.5) & (Vb[:, 0] < 853.5)
Vb = Vb[~knob]
l4("muzzle_brake.length", Vb[:, 0].max() - Vb[:, 0].min(), K["muzzle_brake"]["length"],
   "brake body bounds X (detent knob excluded)")
l4("muzzle_brake.dia", 2.0 * float(np.hypot(Vb[:, 1], Vb[:, 2]).max()), K["muzzle_brake"]["dia"],
   "brake body: 2 x max radius about the bore (detent knob excluded)")
res["L3_pass"] = all(f["pass"] for f in res["L3"])
res["L4_pass"] = all(d["pass"] for d in res["L4"])
(SCRATCH / "measure_result.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
for f in res["L3"]:
    print("[L3]", f["pass"], f["feature"], f["measured"], "err", f["error_mm"])
for d in res["L4"]:
    print("[L4]", d["pass"], d["dimension"], d["measured"], d["spec"], d["error_mm"])
