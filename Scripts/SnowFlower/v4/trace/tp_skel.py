"""Trace pilot stage 2b: vectorise the SILVER RIMS / FILIGREE as centre-lines + widths.

Tracing a painted reference's light/dark areas gives blobby outlines; the design underneath is made of bands of
near-constant width.  So the rims are traced as the medial axis of the cleaned silver mask (tp_trace's classes):
Zhang-Suen thinning -> branch graph -> spur pruning -> smoothed polylines, width = 2 x distance-to-edge along the
axis.  The build sweeps a rounded band along each.  Plate outlines (region / inner) come from the same masks.
Output: work/trace_rims.json (ref px)."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G, tp_rois as RO

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
seg = np.load(OUT + "/seg.npz")
R0, C0 = int(seg["R0"]), int(seg["C0"])
rgb = seg["rgb"]; lum = seg["lum"]; bg = seg["bg"]
H, W = lum.shape
S = 4
lum_u = tp_img.resize(lum, S, kind='linear')
br_u = tp_img.resize(rgb[..., 2] - rgb[..., 0], S, kind='linear')
sil_u = tp_img.resize((~bg).astype(np.float32), S, kind='linear')
lum_s = G.gauss(lum_u, 0.3 * S)
br_s = G.gauss(br_u, 0.45 * S)
sil_s = G.gauss(sil_u, 0.25 * S)
X, Y = G.grid(R0, R0 + H, C0, C0 + W, S)
ENAMEL = np.maximum(np.minimum((br_s - 0.012) / 0.012, (0.62 - lum_s) / 0.1), (0.16 - lum_s) / 0.05)
FIL = (lum_s - 0.36) / 0.1
FILIGREE = {"crestT", "crestB", "sprigU", "sprigL", "lace"}
MIN_SPUR = {"plate": 3.0, "fil": 1.6}          # ref px


def mirror(poly): return [(2 * RO.AXIS - x, y) for x, y in poly]


elements = []
for roi in RO.ROIS:
    name, kind = roi[0], roi[1]
    if roi[2] == "circle":
        (cx, cy), r = roi[3], roi[4]
        L = [(cx + r * np.cos(t), cy + r * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    else:
        L = list(roi[2])
    if kind == "pair":
        polys = [(f"{name}_L", L), (f"{name}_R", mirror(L))]
    else:
        polys = [(name, L + mirror(L)[::-1][1:-1])]
    for ename, poly in polys:
        elements.append((ename, name, np.array(poly, float)))


def thin(m):
    m = m.astype(np.uint8).copy()
    while True:
        changed = False
        for step in (0, 1):
            P = np.pad(m, 1)
            p2, p3, p4, p5 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:]
            p6, p7, p8, p9 = P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]
            Bn = p2.astype(int) + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rem = (m == 1) & (Bn >= 2) & (Bn <= 6) & (A == 1) & c
            if rem.any():
                m[rem] = 0; changed = True
        if not changed:
            return m.astype(bool)


NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def branches(sk):
    pts = set(zip(*np.nonzero(sk)))
    def nbrs(p): return [(p[0] + a, p[1] + b) for a, b in NB if (p[0] + a, p[1] + b) in pts]
    deg = {p: len(nbrs(p)) for p in pts}
    nodes = {p for p, d in deg.items() if d != 2}
    used = set(); out = []
    for n in nodes:
        for q in nbrs(n):
            if (n, q) in used:
                continue
            path = [n, q]; used.add((n, q)); used.add((q, n))
            prev, cur = n, q
            while cur not in nodes:
                nx = [r for r in nbrs(cur) if r != prev and (cur, r) not in used]
                if not nx:
                    break
                used.add((cur, nx[0])); used.add((nx[0], cur))
                prev, cur = cur, nx[0]; path.append(cur)
            out.append({"px": path, "a": deg[path[0]], "b": deg.get(path[-1], 2)})
    # pure loops (no nodes)
    rest = pts - {p for b in out for p in b["px"]}
    while rest:
        s0 = next(iter(rest)); path = [s0]; prev = None; cur = s0
        while True:
            nx = [r for r in nbrs(cur) if r != prev and r in rest and r not in path]
            if not nx:
                break
            prev, cur = cur, nx[0]; path.append(cur)
        rest -= set(path)
        if len(path) > 6:
            out.append({"px": path + [path[0]], "a": 2, "b": 2, "loop": True})
    return out


def prune(sk, min_len_fine):
    """remove spurs: branches with a free end (degree 1) whose other end is a junction, shorter than min_len_fine."""
    sk = sk.copy()
    for _ in range(4):
        cut = False
        for b in branches(sk):
            if len(b["px"]) >= min_len_fine:
                continue
            a_free, b_free = b["a"] == 1, b["b"] == 1
            if a_free and b_free:
                if len(b["px"]) < min_len_fine * 0.7:        # tiny isolated bit
                    for p in b["px"]: sk[p] = False
                    cut = True
                continue
            if a_free or b_free:
                body = b["px"][:-1] if a_free else b["px"][1:]
                for p in body: sk[p] = False
                cut = True
        if not cut:
            break
        sk = thin(sk)
    return sk


def smooth_poly(P, it=3):
    P = P.copy()
    for _ in range(it):
        P[1:-1] = P[1:-1] + 0.5 * (0.5 * (P[:-2] + P[2:]) - P[1:-1])
    return P


def resample_open(P, step):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if d[-1] < 1e-6:
        return P[:1]
    n = max(int(d[-1] / step), 2)
    t = np.linspace(0, d[-1], n + 1)
    return np.c_[np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])], t, d


def loops_of(field, min_area_px=1.5):
    out = []
    for lp in G.marching_squares(field, 0.0):
        P = np.c_[C0 + (lp[:, 0] + 0.5) / S, R0 + (lp[:, 1] + 0.5) / S]
        A = G.signed_area(P)
        if abs(A) < min_area_px:
            continue
        P = G.smooth_closed(G.resample_closed(P, 0.3), 3, 0.5)
        out.append({"pts": np.round(P, 3).tolist(), "area": float(A)})
    return out


def drop_small(m, min_px2):
    lab, n = G.label(m)
    if n == 0:
        return m
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    small = cnt < min_px2 * S * S; small[0] = False
    return m & ~small[lab]


res = {"source": "References/SnowFlower/SnowFlower_sheath_reference.png", "S": S, "elements": []}
for en, base, poly in elements:
    mine = G.pip(X, Y, poly)
    reg = np.minimum(G.gauss(mine.astype(np.float32), 0.35 * S) - 0.5, sil_s - 0.5)
    ys, xs = np.nonzero(reg > -0.45)
    y0, y1, x0, x1 = max(ys.min() - 6, 0), min(ys.max() + 7, reg.shape[0]), max(xs.min() - 6, 0), min(xs.max() + 7, reg.shape[1])
    w = (slice(y0, y1), slice(x0, x1))
    Rw = reg[w] > 0
    fil = base in FILIGREE
    if fil:
        sv = (FIL[w] > 0) & Rw
        sv = drop_small(sv, 1.2)
    else:
        sv = (ENAMEL[w] <= 0) & Rw
        sv = G.dilate(G.erode(sv, int(round(0.6 * S))), int(round(0.6 * S)))
        sv = drop_small(sv, 10.0)
        dk = Rw & ~sv
        dk = drop_small(dk, 5.0)
        sv = Rw & ~dk
    # widths from the distance transform; the element border counts as an edge only where the silhouette is
    dist = G.edt(np.pad(sv, 1))[1:-1, 1:-1]
    sk = thin(sv)
    sk = prune(sk, MIN_SPUR["fil" if fil else "plate"] * S)
    bl = []
    for b in branches(sk):
        pp = np.array(b["px"], float)
        if len(pp) < 3:
            continue
        wid = np.array([dist[int(p[0]), int(p[1])] for p in pp]) * 2 / S
        P = np.c_[C0 + (pp[:, 1] + x0 + 0.5) / S, R0 + (pp[:, 0] + y0 + 0.5) / S]
        P = smooth_poly(P, 6)
        Q, t, d = resample_open(P, 0.35)
        wq = np.interp(t, d, np.convolve(np.pad(wid, 3, mode='edge'), np.ones(7) / 7, 'valid'))
        L = d[-1]
        if L < (1.2 if fil else 2.0):
            continue
        wq = np.clip(wq, 0.9 if fil else 1.6, 3.2 if fil else 6.5)
        bl.append({"pts": np.round(Q, 3).tolist(), "w": np.round(wq, 3).tolist(), "len": float(L),
                   "ends": [int(b["a"]), int(b["b"])]})
    # plate outline + an inner outline 0.8 px in (the enamel sits inside the silver slab's edge)
    regw = np.full(reg.shape, -1.0, np.float32); regw[w] = reg[w]
    inner = np.full(reg.shape, -1.0, np.float32)
    inner[w] = G.gauss(G.erode(Rw, int(round(0.8 * S))).astype(np.float32), 0.25 * S) - 0.5
    darkf = np.full(reg.shape, -1.0, np.float32)
    darkf[w] = G.gauss((Rw & ~sv).astype(np.float32), 0.25 * S) - 0.5
    e = {"name": en, "kind": base, "roi": poly.tolist(), "branches": bl,
         "region": loops_of(regw[w]) if False else [], "inner": [], "dark": []}
    # contour on the window only (speed), then shift
    for key, fld in (("region", regw), ("inner", inner), ("dark", darkf)):
        f = fld[w]
        out = []
        for lp in G.marching_squares(f, 0.0):
            P = np.c_[C0 + (lp[:, 0] + x0 + 0.5) / S, R0 + (lp[:, 1] + y0 + 0.5) / S]
            A = G.signed_area(P)
            if abs(A) < 2.0:
                continue
            P = G.smooth_closed(G.resample_closed(P, 0.3), 3, 0.5)
            out.append({"pts": np.round(P, 3).tolist(), "area": float(A)})
        e[key] = out
    print(en, "branches", len(bl), "total len px", round(sum(b["len"] for b in bl), 1),
          "mean w", round(float(np.mean([np.mean(b["w"]) for b in bl])) if bl else 0, 2), flush=True)
    res["elements"].append(e)
json.dump(res, open(OUT + "/trace_rims.json", "w"))
# overlay: centre-lines + width on the reference (x6)
V = 6
big = tp_img.resize(rgb, V, kind='linear') * 0.55 + 0.45
for e in res["elements"]:
    for b in e["branches"]:
        P = np.array(b["pts"]); wv = np.array(b["w"])
        for (x, y), ww in zip(P, wv):
            xi, yi = int((x - C0) * V), int((y - R0) * V)
            r = max(int(ww * V / 2), 1)
            big[max(yi - r, 0):yi + r + 1, max(xi - r, 0):xi + r + 1, :3] = big[max(yi - r, 0):yi + r + 1, max(xi - r, 0):xi + r + 1, :3] * 0.6 + 0.4 * np.array([1, 0.4, 0.2])
        for x, y in P:
            xi, yi = int((x - C0) * V), int((y - R0) * V)
            big[yi, xi, :3] = [0.6, 0, 0]
    for l in e["inner"]:
        for x, y in l["pts"]:
            xi, yi = int((x - C0) * V), int((y - R0) * V)
            big[yi, xi, :3] = [0, 0.2, 1]
tp_img.save(OUT + "/rims_overlay_x6.png", big)
