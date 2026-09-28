"""Trace pilot stage 2c: PEN-TOOL trace of the plates (the method a tracer uses on a painted reference).

The painted reference's light/dark regions are blobby (reflections, AI-paint noise), but the design under them is a
set of clean, thick leaf plates.  So each plate is traced by hand as control points placed on the labelled 13-15x
zooms (work/z3_*.png: col/row grid every 2 px) - LEFT half and centre - and then:
    1. a closed Catmull-Rom spline through the control points (0.25 px spacing),
    2. SNAPPED to the reference's own edges: points within 1.8 px of the silhouette go to its sub-pixel iso line;
       inset points go to the zero crossing of the enamel field (blue-shifted / near-black) within +-1.4 px,
    3. lightly smoothed.
The right half is the mirrored control polygon snapped to the RIGHT side's own pixels, so the reference's small
asymmetries are traced, not copied.  Output: work/trace_plates.json (ref px) + work/plates_overlay_x6.png."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
AXIS = 505.5

# ------------------------------------------------------------------ hand-placed control points (col, row)
PLATES = {
    # name: (kind 'pair'|'centre', outer, inset or None)
    "t2": ("pair",
           [(449.2, 68.5), (450.5, 66.0), (453.0, 65.0), (457.0, 64.8), (461.0, 66.5), (466.0, 71.0), (471.0, 76.0),
            (474.0, 80.5), (471.0, 84.0), (458.0, 84.0), (451.0, 82.0), (449.5, 77.0), (449.0, 72.0)],
           [(452.5, 72.5), (456.0, 71.3), (460.0, 71.5), (464.0, 73.5), (468.0, 77.0), (470.5, 80.5), (466.0, 83.0),
            (455.0, 83.0), (452.5, 79.0)]),
    "t1": ("pair",
           [(450.8, 43.8), (455.0, 42.9), (460.0, 42.4), (466.0, 42.1), (472.0, 42.0), (478.0, 42.2), (484.0, 44.5),
            (489.0, 49.0), (492.0, 55.0), (493.0, 62.0), (491.0, 70.0), (486.0, 76.0), (481.0, 80.0), (477.0, 79.5),
            (472.0, 77.5), (468.0, 74.5), (464.5, 70.5), (461.5, 66.5), (458.5, 63.5), (456.0, 60.0), (454.5, 56.0),
            (452.5, 53.0), (451.0, 50.5), (450.5, 47.0)],
           [(461.5, 53.3), (466.0, 53.8), (471.0, 55.5), (476.0, 58.0), (480.5, 61.0), (484.0, 64.5), (485.0, 68.5),
            (483.5, 73.0), (481.0, 76.5), (477.0, 76.5), (472.5, 72.5), (468.5, 67.5), (465.5, 62.5), (463.0, 57.5)]),
    "flare": ("pair",
              [(431.5, 88.3), (436.0, 86.9), (441.0, 85.8), (446.0, 85.2), (449.5, 85.2), (449.2, 95.0), (449.0, 110.0),
               (449.0, 125.0), (448.8, 130.0), (446.5, 124.5), (442.4, 114.5), (437.4, 103.8), (432.8, 93.5)],
              [(437.8, 92.8), (442.0, 91.5), (446.5, 90.5), (447.0, 100.0), (446.8, 110.0), (446.3, 121.0), (443.0, 114.0),
               (439.5, 103.5), (436.5, 96.0)]),
    "lat": ("pair",
            [(448.9, 85.9), (451.7, 83.4), (456.0, 82.4), (460.3, 81.9), (465.0, 81.6), (469.6, 81.9), (473.1, 83.0),
             (477.0, 85.0), (481.0, 89.0), (484.5, 95.0), (486.5, 103.0), (487.5, 111.0), (487.8, 116.5), (487.5, 119.5),
             (484.0, 122.0), (480.0, 124.4), (475.0, 127.0), (470.0, 129.4), (465.0, 132.3), (460.3, 135.1), (456.5, 137.6),
             (453.9, 139.4), (450.5, 141.5), (449.0, 136.0), (448.4, 125.0), (448.2, 110.0), (448.2, 95.0)],
            [(453.2, 97.0), (456.7, 93.0), (461.0, 89.8), (466.0, 88.7), (471.7, 89.4), (474.6, 91.6), (479.0, 97.0),
             (482.5, 105.0), (484.5, 113.0), (483.1, 117.3), (476.7, 120.9), (469.6, 124.4), (461.7, 127.3), (455.3, 129.4),
             (453.3, 129.8), (453.0, 120.0), (453.0, 108.0)]),
    "sleeve": ("pair",
               [(454.2, 136.0), (459.5, 136.0), (460.2, 150.0), (460.5, 168.0), (455.0, 168.0), (454.6, 150.0)],
               None),
    "drop": ("centre",
             [(505.5, 121.5), (496.0, 122.0), (486.1, 124.0), (486.1, 128.0), (487.6, 136.6), (491.9, 145.1), (496.9, 153.7),
              (501.9, 160.9), (506.0, 166.3)],
             [(506.0, 125.5), (498.0, 125.5), (491.9, 126.5), (492.2, 131.0), (493.0, 136.0), (495.4, 143.0), (499.7, 150.9),
              (503.5, 155.5), (506.1, 158.0)]),
    "crestB": ("centre",
               [(505.8, 116.0), (503.5, 119.0), (500.5, 119.5), (496.0, 120.5), (492.4, 122.8), (494.0, 126.5), (496.5, 129.5),
                (499.7, 132.3), (503.0, 135.0), (506.1, 138.3)],
               None),
    "crestT": ("centre",
               [(504.8, 41.0), (501.5, 45.5), (497.0, 49.5), (493.5, 48.5), (490.5, 51.0), (488.5, 57.0), (491.0, 62.0),
                (499.0, 59.0), (505.5, 56.0)],
               None),
}
# the drop plate's tip and the crest's axis points are traced on the axis; centre loops are closed by mirroring the
# left path about the axis (the right half then snaps to its own pixels).

# ------------------------------------------------------------------ image fields
seg = np.load(OUT + "/seg.npz")
R0, C0 = int(seg["R0"]), int(seg["C0"])
rgb = seg["rgb"]; lum = seg["lum"]; bg = seg["bg"]
H, W = lum.shape
S = 6
lum_s = G.gauss(tp_img.resize(lum, S, kind='linear'), 0.35 * S)
br_s = G.gauss(tp_img.resize(rgb[..., 2] - rgb[..., 0], S, kind='linear'), 0.5 * S)
sil_s = G.gauss(tp_img.resize((~bg).astype(np.float32), S, kind='linear'), 0.3 * S)
ENAMEL = np.maximum(np.minimum((br_s - 0.012) / 0.012, (0.62 - lum_s) / 0.1), (0.16 - lum_s) / 0.05)


def sample(F, P):
    """bilinear sample of a fine-grid field at ref px points."""
    x = (P[:, 0] - C0) * S - 0.5; y = (P[:, 1] - R0) * S - 0.5
    x0 = np.clip(np.floor(x).astype(int), 0, F.shape[1] - 2); y0 = np.clip(np.floor(y).astype(int), 0, F.shape[0] - 2)
    fx = np.clip(x - x0, 0, 1); fy = np.clip(y - y0, 0, 1)
    return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x0 + 1] * fx * (1 - fy) + F[y0 + 1, x0] * (1 - fx) * fy
            + F[y0 + 1, x0 + 1] * fx * fy)


def catmull_closed(C, step=0.25):
    C = np.asarray(C, float); n = len(C); out = []
    for i in range(n):
        p0, p1, p2, p3 = C[i - 1], C[i], C[(i + 1) % n], C[(i + 2) % n]
        L = np.linalg.norm(p2 - p1); m = max(int(L / step), 1)
        for t in np.arange(m) / m:
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def normals(P):
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    return np.c_[T[:, 1], -T[:, 0]]


def snap(P, F, level, reach, only=None):
    """move each point along its normal to the nearest crossing of F = level within +-reach px."""
    N = normals(P)
    ts = np.linspace(-reach, reach, int(reach * 2 / 0.05) + 1)
    vals = np.stack([sample(F, P + t * N) - level for t in ts], 1)       # (n, k)
    out = P.copy(); moved = np.zeros(len(P), bool)
    for i in range(len(P)):
        if only is not None and not only[i]:
            continue
        v = vals[i]; s = np.sign(v)
        idx = np.nonzero(s[:-1] * s[1:] < 0)[0]
        if len(idx) == 0:
            continue
        k = idx[np.argmin(np.abs(ts[idx]))]
        t = ts[k] + (ts[k + 1] - ts[k]) * v[k] / (v[k] - v[k + 1])
        out[i] = P[i] + t * N[i]; moved[i] = True
    return out, moved


def smooth(P, it=4):
    for _ in range(it):
        P = P + 0.5 * (0.5 * (np.roll(P, 1, 0) + np.roll(P, -1, 0)) - P)
    return P


def mirror(pts): return [(2 * AXIS - x, y) for x, y in pts]


def trace_loop(ctrl, inset):
    P = catmull_closed(ctrl)
    if inset:
        P2, mv = snap(P, ENAMEL, 0.0, 1.1)
    else:
        near = np.abs(sample(sil_s, P) - 0.5) < 0.49
        # only points whose outward side is background (silhouette edges) snap
        P2, mv = snap(P, sil_s, 0.5, 1.8, only=near)
    P2 = smooth(P2, 14 if inset else 6)
    return P2, float(mv.mean())


res = {"source": "References/SnowFlower/SnowFlower_sheath_reference.png", "plates": {}}
for name, (kind, outer, inset) in PLATES.items():
    sides = {}
    if kind == "pair":
        sides[name + "_L"] = (outer, inset)
        sides[name + "_R"] = (mirror(outer), mirror(inset) if inset else None)
    else:
        full_o = list(outer) + mirror(outer)[::-1][1:-1]
        full_i = (list(inset) + mirror(inset)[::-1][1:-1]) if inset else None
        sides[name] = (full_o, full_i)
    for nm, (o, i) in sides.items():
        Po, fo = trace_loop(o, False)
        ent = {"outer": np.round(Po, 3).tolist(), "outer_ctrl": [list(map(float, p)) for p in o], "outer_snapped": fo}
        if i:
            Pi, fi = trace_loop(i, True)
            ent.update({"inset": np.round(Pi, 3).tolist(), "inset_ctrl": [list(map(float, p)) for p in i], "inset_snapped": fi})
        res["plates"][nm] = ent
        print(nm, "outer pts", len(Po), f"snapped {fo:.0%}", ("inset snapped %.0f%%" % (100 * ent["inset_snapped"])) if i else "")
json.dump(res, open(OUT + "/trace_plates.json", "w"))
# overlay
V = 6
big = tp_img.resize(rgb, V, kind='linear')
def draw(P, col, r=1):
    for x, y in P:
        xi, yi = int((x - C0) * V), int((y - R0) * V)
        if 0 <= xi < big.shape[1] and 0 <= yi < big.shape[0]:
            big[yi - r:yi + r + 1, xi - r:xi + r + 1, :3] = col
for nm, e in res["plates"].items():
    draw(e["outer"], [0, 1, 0.2])
    if "inset" in e: draw(e["inset"], [1, 0.2, 1])
tp_img.save(OUT + "/plates_overlay_x6.png", big)
