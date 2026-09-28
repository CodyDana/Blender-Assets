"""Stage B: the shoe body in the local frame (right shoe, mm): upper (ribs between the feather line and the traced
topline), insole, sole, stiletto, top-lift. Reads r1/cache/last_r.npz + camera.json; writes r1/cache/body_r.npz.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_b_body.py
"""
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402
import hb_geo as G  # noqa: E402

T0 = time.time()


def log(*a):
    print(f"[B {time.time() - T0:6.1f}s]", *a, flush=True)


def load_cam():
    p = C.CACHE / "camera.json"
    if p.exists():
        d = json.loads(p.read_text())
        return HC.Cam(d["az"], d["el"], d["s"], d["tx"], d["ty"], d.get("roll", 0.0))
    return HC.Cam(53.03, 33.05, 3.52, 145.02, 928.65, 0.0)


def main():
    z = np.load(C.CACHE / "last_r.npz")
    last = G.Surf(z["last_v"], z["last_q"].tolist())
    fs = G.grid_sampler(z)
    zs = G.zins_sampler(z)
    cam = load_cam()
    spec = C.load_json(C.SPEC)
    tr = spec["traces"]
    cdir, _, _ = cam.basis()

    def closest(o, d):
        ts = np.linspace(1500, 2600, 1101)
        pts = o[None] + d[None] * ts[:, None]
        f = fs(pts)
        k = int(np.argmin(f))
        q, _ = last.nearest(pts[k:k + 1])
        print("  ray miss -> closest approach", round(float(f[k]), 2))
        return q[0]

    def _hits(xy):
        o, d = cam.ray(np.array(xy, dtype=float))
        h = [x for x in last.hits(o, d, max_hits=12) if x[0][2] < 288.0]
        return o, d, h

    def near(xy):
        o, d, h = _hits(xy)
        h = [x for x in h if np.dot(x[1], cdir) > 0]
        return h[0][0] if h else closest(o, d)

    def far(xy):
        o, d, h = _hits(xy)
        h = [x for x in h if np.dot(x[1], cdir) < 0]
        return h[0][0] if h else closest(o, d)

    # ---------------- feather line on the last
    outline = z["outline"]
    om = C.resample_polyline(outline, step=1.2, closed=True)
    tang = np.roll(om, -1, 0) - np.roll(om, 1, 0)
    n2 = np.stack([tang[:, 1], -tang[:, 0]], 1)
    n2 /= np.linalg.norm(n2, axis=1, keepdims=True)
    if ((om - om.mean(0)) * n2).sum() < 0:
        n2 = -n2
    F = []
    for p, n in zip(om, n2):
        ss = np.linspace(-8, 6, 141)
        q = p[None] + n[None] * ss[:, None]
        w = zs(q[:, 0], q[:, 1]) + 1.4
        f = fs(np.column_stack([q, w]))
        k = np.nonzero((f[:-1] <= 0) & (f[1:] > 0))[0]
        if len(k) == 0:
            k = [int(np.argmin(np.abs(f)))]
            t = 0.0
        else:
            k = k[-1:]
            t = f[k[0]] / (f[k[0]] - f[k[0] + 1])
        i = k[0]
        qq = q[i] + (q[min(i + 1, len(q) - 1)] - q[i]) * t
        F.append([qq[0], qq[1], zs(qq[0], qq[1]) + 1.4])
    F = np.array(F)
    # orientation: CW in (u, v) so it runs lateral-rear -> heel -> medial -> toe -> lateral
    area = 0.5 * np.sum(F[:, 0] * np.roll(F[:, 1], -1) - np.roll(F[:, 0], -1) * F[:, 1])
    if area > 0:
        F = F[::-1]
    log("feather", len(F))

    # ---------------- topline from the traces
    band = np.array(tr["A.front_branch_band"]["pts"], dtype=float)
    # counter front edge: band centre line + 6 px toward the opening, bottom -> top, then up behind the crest spike
    t1_img = [(b[0] + 6.0, b[1]) for b in band[::-1] if 190 <= b[1] <= 590]
    t1_img = sorted(t1_img, key=lambda q: -q[1])
    t1_img += [(150.0, 150.0), (151.0, 105.0), (151.0, 72.0)]
    T1 = np.array([near(q) for q in t1_img])
    far_img = np.array(tr["A.far_panel_topline"]["pts"], dtype=float)
    T3 = np.array([far(q) for q in far_img])
    # back arc: around the back of the leg from the near wing top to the far collar start, level-ish
    a, b = T1[-1], T3[0]
    wm = 0.5 * (a[2] + b[2])
    sl = last.v[np.abs(last.v[:, 2] - wm) < 3.0]
    ctr = sl[:, :2].mean(0)
    th_a = math.atan2(a[1] - ctr[1], a[0] - ctr[0])
    th_b = math.atan2(b[1] - ctr[1], b[0] - ctr[0])
    # go around the back (through angle pi, i.e. -u)
    if th_a < 0:
        th_a += 2 * math.pi
    if th_b < 0:
        th_b += 2 * math.pi
    ths = np.linspace(th_a, th_b, 24)
    T2 = []
    for k, th in enumerate(ths[1:-1], 1):
        s = k / (len(ths) - 1)
        w = a[2] * (1 - s) + b[2] * s + 6.0 * math.sin(math.pi * s)
        o = np.array([ctr[0], ctr[1], w])
        d = np.array([math.cos(th), math.sin(th), 0.0])
        h = last.hits(o, d)
        if h:
            T2.append(h[0][0])
    T2 = np.array(T2)
    # throat front: arc over the vamp from the far throat to the piping end
    p_far = T3[-1]
    pip_img = np.array(tr["A.topline_piping"]["pts"], dtype=float)
    T5 = np.array([near(q) for q in pip_img[::-1]])
    p_near = T5[0]
    arc = []
    for s in np.linspace(0, 1, 10)[1:-1]:
        q = p_far * (1 - s) + p_near * s + np.array([0, 0, 8.0 * math.sin(math.pi * s)])
        arc.append(q)
    T4, _ = last.nearest(np.array(arc))
    segs = [T1, T2, T3, T4, T5]
    # snap the two ends onto the feather line
    iP1 = int(np.argmin(np.linalg.norm(F - T1[0], axis=1)))
    iP2 = int(np.argmin(np.linalg.norm(F - T5[-1], axis=1)))
    log("P1", F[iP1].round(1), "T0", T1[0].round(1), "P2", F[iP2].round(1), "Tend", T5[-1].round(1))
    # feather run P1 -> ... -> P2 along F's orientation
    if iP2 >= iP1:
        Fr = F[iP1:iP2 + 1]
    else:
        Fr = np.vstack([F[iP1:], F[:iP2 + 1]])
    segs = [Fr[0][None]] + segs + [Fr[-1][None]]
    Tl, Ll = [], []
    for lab, sg in enumerate(segs):
        Tl.append(sg)
        Ll += [lab] * len(sg)
    Traw = np.vstack(Tl)
    Lraw = np.array(Ll)
    T = C.resample_polyline(Traw, step=1.5)
    # label of each resampled point = label of the nearest raw point
    T_lab = Lraw[np.argmin(np.linalg.norm(T[:, None] - Traw[None], axis=2), axis=1)]
    Fr = C.resample_polyline(Fr, step=1.5)
    # smooth T lightly (trace jitter), keep ends; reproject
    for _ in range(4):
        T[1:-1] = (T[:-2] + 2 * T[1:-1] + T[2:]) / 4.0
        T[1:-1], _n = last.nearest(T[1:-1])
    log("T", len(T), "Fr", len(Fr))

    # ---------------- rib correspondence by DTW (shortest total rib length, monotone)
    nF, nT = len(Fr), len(T)
    cost = np.linalg.norm(Fr[:, None, :] - T[None, :, :], axis=2)
    acc = np.full((nF, nT), np.inf)
    acc[0, 0] = cost[0, 0]
    for i in range(nF):
        for j in range(nT):
            if i == 0 and j == 0:
                continue
            best = min(acc[i - 1, j] if i else np.inf, acc[i, j - 1] if j else np.inf,
                       acc[i - 1, j - 1] if (i and j) else np.inf)
            acc[i, j] = cost[i, j] + best
    i, j = nF - 1, nT - 1
    path = [(i, j)]
    while i or j:
        cands = []
        if i and j:
            cands.append((acc[i - 1, j - 1], i - 1, j - 1))
        if i:
            cands.append((acc[i - 1, j], i - 1, j))
        if j:
            cands.append((acc[i, j - 1], i, j - 1))
        _, i, j = min(cands)
        path.append((i, j))
    path = path[::-1]
    # rib parameter along the path (combined arc length), resample to a rib count
    fi = np.array([p[0] for p in path], dtype=float)
    tj = np.array([p[1] for p in path], dtype=float)
    lens = np.abs(np.diff(fi)) * 1.5 + np.abs(np.diff(tj)) * 1.5
    cum = np.concatenate([[0], np.cumsum(lens)])
    n_rib = 360
    tt = np.linspace(0, cum[-1], n_rib)
    fi_r = np.interp(tt, cum, fi)
    tj_r = np.interp(tt, cum, tj)

    def at(poly, x):
        i0 = np.clip(np.floor(x).astype(int), 0, len(poly) - 2)
        f = (x - i0)[:, None]
        return poly[i0] * (1 - f) + poly[i0 + 1] * f
    Fa = at(Fr, fi_r)
    Ta = at(T, tj_r)

    # ---------------- ribs on the last
    ns = 56
    s = np.linspace(0, 1, ns)
    grid = Fa[:, None, :] * (1 - s)[None, :, None] + Ta[:, None, :] * s[None, :, None]
    for it in range(8):
        flat = grid[:, 1:-1].reshape(-1, 3)
        proj, _ = last.nearest(flat)
        grid[:, 1:-1] = proj.reshape(n_rib, ns - 2, 3)
        # even spacing along each rib
        for r in range(n_rib):
            g = grid[r]
            seg = np.linalg.norm(np.diff(g, axis=0), axis=1)
            if seg.sum() < 1e-6:
                continue
            grid[r] = C.resample_polyline(g, n=ns)
        # smooth across ribs (interior only)
        if it < 7:
            g2 = grid.copy()
            g2[1:-1, 1:-1] = 0.5 * grid[1:-1, 1:-1] + 0.25 * (grid[:-2, 1:-1] + grid[2:, 1:-1])
            grid = g2
    flat = grid[:, 1:-1].reshape(-1, 3)
    proj, _ = last.nearest(flat)
    grid[:, 1:-1] = proj.reshape(n_rib, ns - 2, 3)
    # tuck row: 2.2 mm under the feather line (into the sole), prepended as row s<0
    tuck = grid[:, 0].copy()
    tuck[:, 2] -= 2.2
    grid = np.concatenate([tuck[:, None], grid], axis=1)
    ns2 = grid.shape[1]
    # UV: along-rib arc length (v) and mean-rib arc length (u), in mm / 100
    rl = np.concatenate([np.zeros((n_rib, 1)), np.cumsum(np.linalg.norm(np.diff(grid, axis=1), axis=2), axis=1)], 1)
    mid = grid[:, ns2 // 2]
    ul = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(mid, axis=0), axis=1))])
    uv = np.stack([np.repeat(ul[:, None], ns2, 1), rl], -1).reshape(-1, 2) / 400.0
    uverts = grid.reshape(-1, 3)
    ufaces = G.grid_faces(n_rib, ns2)
    log("upper grid", uverts.shape)

    # ---------------- insole top (inside the feather line)
    F2 = C.resample_polyline(Fr[:, :2], step=2.0)
    Fin = C.resample_polyline(F[:, :2], step=2.0, closed=True)
    ug = np.arange(math.floor(Fin[:, 0].min()), math.ceil(Fin[:, 0].max()) + 1, 3.0)
    vg = np.arange(math.floor(Fin[:, 1].min()), math.ceil(Fin[:, 1].max()) + 1, 3.0)
    UU, VV = np.meshgrid(ug, vg, indexing="ij")
    P = np.stack([UU.ravel(), VV.ravel()], 1)
    d = C.poly_sdf2(P, Fin)
    P = P[d < -1.2]
    pts2 = [Vector((float(x), float(y))) for x, y in np.vstack([Fin, P])]
    nb = len(Fin)
    edges = [(k, (k + 1) % nb) for k in range(nb)]
    res = delaunay_2d_cdt(pts2, edges, [], 1, 1e-5, False)
    iv = np.array([[p.x, p.y] for p in res[0]])
    ifaces = [list(f) for f in res[2]]
    ins_v = np.column_stack([iv, zs(iv[:, 0], iv[:, 1])])
    log("insole", ins_v.shape, len(ifaces))

    # ---------------- sole slab
    so = C.resample_polyline(outline, step=1.5, closed=True)
    tg = np.roll(so, -1, 0) - np.roll(so, 1, 0)
    nn = np.stack([tg[:, 1], -tg[:, 0]], 1)
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    if ((so - so.mean(0)) * nn).sum() < 0:
        nn = -nn
    so = so + nn * 0.9
    zt = zs(so[:, 0], so[:, 1]) - 0.6
    zb = zs(so[:, 0], so[:, 1]) - C.D["forefoot_sole"]
    sole_top = np.column_stack([so, zt])
    sole_bot = np.column_stack([so, zb])
    mid1 = np.column_stack([so + nn * 0.35, zt - 1.0])
    mid2 = np.column_stack([so + nn * 0.35, zb + 1.0])
    sections = [sole_top, mid1, mid2, sole_bot]
    sv, sf = G.loft([np.asarray(x) for x in sections])
    # caps via CDT (top is hidden under the insole; bottom visible)
    pts2 = [Vector((float(x), float(y))) for x, y in so]
    res = delaunay_2d_cdt(pts2, [(k, (k + 1) % len(so)) for k in range(len(so))], [], 1, 1e-5, False)
    cv = np.array([[p.x, p.y] for p in res[0]])
    cmap = [int(np.argmin(np.linalg.norm(so - q, axis=1))) for q in cv]
    nsec = len(so)
    for f in res[2]:
        idx = [cmap[k] for k in f]
        sf.append([idx[2], idx[1], idx[0]])                              # top (facing up, winding flipped below)
        sf.append([3 * nsec + idx[0], 3 * nsec + idx[1], 3 * nsec + idx[2]])
    log("sole", sv.shape, len(sf))

    # ---------------- stiletto from the traced profile, on the heel's mid-plane
    vmid = C.D["toplift_uv"][1]
    so_img = np.array(tr["A.stiletto_outline"]["pts"], dtype=float)

    def on_plane(xy, vplane):
        o, d = cam.ray(np.asarray(xy, dtype=float))
        t = (vplane - o[..., 1]) / d[..., 1]
        return o + d * t[..., None]
    back_img = so_img[:9]           # (73,600) .. (84,905)
    front_img = so_img[10:][::-1]   # (139,890) .. (172,600) reversed -> bottom..top? keep sorted by y below
    back3 = on_plane(back_img, vmid)
    front3 = on_plane(np.array(sorted(so_img[10:].tolist(), key=lambda q: -q[1])), vmid)
    log("stiletto back w", back3[:, 2].round(1), "u", back3[:, 0].round(1))
    log("stiletto front w", front3[:, 2].round(1), "u", front3[:, 0].round(1))
    np.savez_compressed(C.CACHE / "body_r.npz", upper_v=uverts, upper_f=np.array(ufaces), upper_uv=uv,
                        upper_grid=grid, insole_v=ins_v, insole_t=np.array([f[:3] for f in ifaces if len(f) == 3]),
                        sole_v=sv, sole_f=np.array([f for f in sf if len(f) == 4]),
                        sole_t=np.array([f for f in sf if len(f) == 3]),
                        F=F, Fr=Fr, T=T, T_lab=T_lab, rib_lab=T_lab[np.clip(np.round(tj_r).astype(int), 0, len(T) - 1)],
                        rib_T=tj_r, stil_back=back3, stil_front=front3, cam=np.array(cam.params()))
    log("saved body_r.npz")


main()
