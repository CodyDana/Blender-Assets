"""Stage D: assemble the Snow Flower heels in the POSED space: body parts + every ornament as discrete shells, in two
qualities (high = bake source, game = LOD0 shells), both shoes (left = mirror). Writes the source blend
Assets/SnowFlowerHeels/SnowFlowerHeels.blend (locked fitting body appended + GARMENT collections) and caches
r1/cache/parts_{high,game}_r.npz.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_d_assemble.py [-- --no-blend]
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402
import hb_geo as G  # noqa: E402
import hb_orn as O  # noqa: E402

T0 = time.time()
Part = O.Part


def log(*a):
    print(f"[D {time.time() - T0:6.1f}s]", *a, flush=True)


# ------------------------------------------------------------------------------------------------ upper shell

def upper_shell(body, fs, q):
    grid = body["upper_grid"]
    rl = np.linalg.norm(np.diff(grid, axis=1), axis=2).sum(1)
    ok = np.nonzero(rl > 2.0)[0]
    grid = grid[ok[0]:ok[-1] + 1]
    nr, ns, _ = grid.shape
    if q == "game":
        ri = list(range(0, nr, 8))
        if ri[-1] != nr - 1:
            ri.append(nr - 1)
        si = [0, 1] + list(range(5, ns - 1, 6)) + [ns - 1]
        si = sorted(set(si))
        grid = grid[ri][:, si]
        nr, ns = grid.shape[:2]
    du = np.gradient(grid, axis=0)
    dv = np.gradient(grid, axis=1)
    n = np.cross(du, dv)
    ln = np.linalg.norm(n, axis=2, keepdims=True)
    n = n / np.maximum(ln, 1e-9)
    # degenerate ribs: borrow neighbours' normals
    bad = ln[..., 0] < 1e-6
    if bad.any():
        n[bad] = np.array([0, 0, 1.0])
    probe = grid[nr // 2, ns // 2]
    if fs(probe + n[nr // 2, ns // 2] * 1.0) < fs(probe):
        n = -n
    # smooth normals a little
    for _ in range(2):
        n[1:-1, 1:-1] = (n[1:-1, 1:-1] * 2 + n[:-2, 1:-1] + n[2:, 1:-1] + n[1:-1, :-2] + n[1:-1, 2:]) / 6
        n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-9)
    t = C.D["upper_thick"]
    inner = grid
    outer = grid + n * t
    # rounded top rim: a mid row pushed past the topline along the rib direction
    rib_dir = grid[:, -1] - grid[:, -2]
    rib_dir /= np.maximum(np.linalg.norm(rib_dir, axis=1, keepdims=True), 1e-9)
    rim = grid[:, -1] + n[:, -1] * (t * 0.5) + rib_dir * (t * 0.45)
    V = np.vstack([inner.reshape(-1, 3), outer.reshape(-1, 3), rim])
    off_o = nr * ns
    off_r = 2 * nr * ns
    F, M = [], []
    for i in range(nr - 1):
        for j in range(ns - 1):
            a, b, c, d = i * ns + j, (i + 1) * ns + j, (i + 1) * ns + j + 1, i * ns + j + 1
            F.append([a, b, c, d][::-1])
            M.append("lining")
            F.append([off_o + a, off_o + b, off_o + c, off_o + d])
            M.append("leather")
    for i in range(nr - 1):
        top_i, top_i1 = i * ns + ns - 1, (i + 1) * ns + ns - 1
        F.append([off_o + top_i, off_o + top_i1, off_r + i + 1, off_r + i])
        M.append("leather")
        F.append([off_r + i, off_r + i + 1, top_i1, top_i])
        M.append("leather")
        b_i, b_i1 = i * ns, (i + 1) * ns
        F.append([b_i, b_i1, off_o + b_i1, off_o + b_i])
        M.append("leather")
    for i, flip in ((0, False), (nr - 1, True)):
        for j in range(ns - 1):
            f = [i * ns + j, i * ns + j + 1, off_o + i * ns + j + 1, off_o + i * ns + j]
            F.append(f[::-1] if flip else f)
            M.append("leather")
    V, F, M = weld_keep(V, F, M)
    return Part(V, F, M, "upper"), outer, n


def game_body(zl, body, heel):
    """Low versions of the insole, sole, stiletto, top-lift and strap (same shapes, fewer segments)."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    zs = G.zins_sampler(zl)
    out = []
    # insole
    Fin = C.resample_polyline(body["F"][:, :2], step=7.0, closed=True)
    pts, tris = O.cdt(Fin, (), O.interior_grid(Fin, 16.0, 5.0))
    out.append(Part(np.column_stack([pts, zs(pts[:, 0], pts[:, 1])]), [t[::-1] for t in tris], ["insole"] * len(tris), "insole"))
    # sole: top, chamfer, bottom rings + bottom cap
    so = C.resample_polyline(zl["outline"], step=4.5, closed=True)
    tg = np.roll(so, -1, 0) - np.roll(so, 1, 0)
    nn = np.stack([tg[:, 1], -tg[:, 0]], 1)
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    if ((so - so.mean(0)) * nn).sum() < 0:
        nn = -nn
    so = so + nn * 0.9
    zt = zs(so[:, 0], so[:, 1]) - 0.6
    zb = zs(so[:, 0], so[:, 1]) - C.D["forefoot_sole"]
    secs = [np.column_stack([so, zt]), np.column_stack([so + nn * 0.35, zb + 1.0]), np.column_stack([so, zb])]
    v, f = G.loft(secs)
    n = len(so)
    pts, tris = O.cdt(so, (), O.interior_grid(so, 25.0, 6.0))
    base = len(v)
    extra = pts[n:]
    v = np.vstack([v, np.column_stack([extra, zs(extra[:, 0], extra[:, 1]) - C.D["forefoot_sole"]])])
    def bidx(i):
        return 2 * n + i if i < n else base + (i - n)
    for t in tris:
        f.append([bidx(t[0]), bidx(t[1]), bidx(t[2])])
    out.append(Part(v, f, ["sole"] * len(f), "sole"))
    # stiletto: every other section, every 4th point
    S = heel["stil_sections"]
    idx = sorted(set(list(range(0, len(S), 3)) + [len(S) - 1]))
    secs = [S[i][::4] for i in idx]
    v, f = G.loft(secs, cap_start=False, cap_end=True)
    out.append(Part(v, f, ["sole"] * len(f), "stiletto"))
    tl = mesh_part(heel, "toplift", "sole", "toplift")
    tlv = tl.v[:128].reshape(4, 32, 3)[:, ::3] if len(tl.v) >= 128 else None
    if tlv is not None:
        v, f = G.loft([x for x in tlv], cap_start=True, cap_end=True)
        tl = Part(v, f, ["sole"] * len(f), "toplift")
    out.append(tl)
    # strap: every 2nd ring
    sv = heel["strap_v"].reshape(-1, 6, 3)[::3]
    nl = len(sv)
    f = []
    for i in range(nl):
        i1 = (i + 1) % nl
        for j in range(6):
            j1 = (j + 1) % 6
            f.append([i * 6 + j, i * 6 + j1, i1 * 6 + j1, i1 * 6 + j])
    out.append(Part(sv.reshape(-1, 3), f, ["strap"] * len(f), "strap"))
    return out


def _fnormal(V, f):
    q = V[f]
    nv = np.zeros(3)
    for k in range(len(f)):
        nv += np.cross(q[k], q[(k + 1) % len(f)])
    return nv


def orient_body(p: Part, fs) -> Part:
    """Upper: its outer leather faces must point up the last SDF (outward); insole: up. Whole-part flips only."""
    if p.name == "upper":
        score = 0.0
        for f, m in zip(p.f, p.m):
            if m != "leather":
                continue
            n = _fnormal(p.v, f)
            c = p.v[f].mean(0)
            score += np.sign(fs(c[None] + n[None] / max(np.linalg.norm(n), 1e-12) * 0.8)[0] - fs(c[None])[0])
        flip = score < 0
    elif p.name == "insole":
        flip = sum(_fnormal(p.v, f)[2] for f in p.f) < 0
    else:
        return Part(p.v, G.recalc_faces(p.v, p.f), p.m, p.name)
    return Part(p.v, [f[::-1] for f in p.f] if flip else p.f, p.m, p.name)


def clearance(p: Part, ff, min_d: float) -> Part:
    """Push vertices closer than ``min_d`` (mm) to her posed skin outward along the skin SDF gradient."""
    V = p.v.copy()
    for _ in range(3):
        d = ff(V)
        bad = d < min_d
        if not bad.any():
            break
        g = np.zeros((bad.sum(), 3))
        for k in range(3):
            e = np.zeros(3)
            e[k] = 0.5
            g[:, k] = ff(V[bad] + e) - ff(V[bad] - e)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        V[bad] += g * (min_d - d[bad])[:, None]
    return Part(V, p.f, p.m, p.name)


def manifold_fix(p: Part) -> Part:
    """Drop duplicate faces, then faces that make an edge carry more than two faces (smallest first)."""
    V = p.v
    seen = set()
    F, M = [], []
    for f, m in zip(p.f, p.m):
        k = tuple(sorted(f))
        if k in seen or len(set(f)) < 3:
            continue
        seen.add(k)
        F.append(list(f))
        M.append(m)

    def area(f):
        q = V[f]
        nv = np.zeros(3)
        for k in range(len(f)):
            nv += np.cross(q[k], q[(k + 1) % len(f)])
        return 0.5 * np.linalg.norm(nv)
    for _ in range(4):
        cnt = {}
        for i, f in enumerate(F):
            for k in range(len(f)):
                cnt.setdefault(tuple(sorted((f[k], f[(k + 1) % len(f)]))), []).append(i)
        drop = set()
        for e, fl in cnt.items():
            if len(fl) > 2:
                fl = sorted(fl, key=lambda i: area(F[i]))
                drop.update(fl[:len(fl) - 2])
        if not drop:
            break
        F = [f for i, f in enumerate(F) if i not in drop]
        M = [m for i, m in enumerate(M) if i not in drop]
    return Part(V, F, M, p.name)


def weld_keep(V, F, M, dist=0.02):
    """Weld coincident vertices, drop degenerate faces; keep per-face materials."""
    V = np.asarray(V, float)
    key = np.round(V / dist).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    newV = V[first]
    F2, M2 = [], []
    for f, m in zip(F, M):
        g = []
        for i in f:
            k = int(inv[i])
            if not g or g[-1] != k:
                g.append(k)
        if len(g) > 1 and g[0] == g[-1]:
            g.pop()
        if len(set(g)) >= 3 and len(set(g)) == len(g):
            F2.append(g)
            M2.append(m)
    return newV, F2, M2


def mesh_part(z, key, mat, name):
    faces = []
    for suf in ("_f", "_q", "_t"):
        k = key + suf
        if k in z.files and len(z[k]):
            faces += z[k].tolist()
    return Part(np.asarray(z[key + "_v"], float), faces, [mat] * len(faces), name)


# ------------------------------------------------------------------------------------------------ ornaments

def rim_points(outer_top, normals_top, ribs_mask):
    idx = np.nonzero(ribs_mask)[0]
    if len(idx) < 2:
        return None, None
    # split into contiguous runs, take the longest
    runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
    r = max(runs, key=len)
    return outer_top[r], normals_top[r]


def ornaments(pj, tr, body, up_outer, up_n, q, pjs=None):
    parts = []
    s = pj.cam.s
    P = lambda k: np.array(tr[k]["pts"], float)  # noqa: E731
    hq = q == "high"

    def add(p):
        if p is None:
            return
        f = G.recalc_faces(p.v, p.f)
        cen = p.v.mean(0)
        best = None
        for sf in pj.surfs:
            loc, n_, _i, d_ = sf.tree.find_nearest(Vector(cen))
            if loc is not None and (best is None or d_ < best[1]):
                best = (np.array(n_), d_)
        up = best[0]
        acc = 0.0
        area = 0.0
        for fc in f:
            q = p.v[fc]
            nv = np.zeros(3)
            for k in range(len(fc)):
                nv += np.cross(q[k], q[(k + 1) % len(fc)])
            acc += 0.5 * np.dot(nv, up)
            area += 0.5 * np.linalg.norm(nv)
        if acc < -0.05 * area:
            f = [fc[::-1] for fc in f]
        parts.append(Part(p.v, f, p.m, p.name))

    # --- counter
    add(O.plate(pj, P("A.medallion_leather"), thick=2.6, bevel_px=6, dome=0.55, edge_frac=0.25, q=q, mat="crackle",
                name="medallion"))
    add(O.plate(pj, P("A.crest_spike"), thick=2.8, bevel_px=4.5, dome=0.6, q=q, lens_px=O.inset(O.resample_keep_corners(P("A.crest_spike_inset"), 2.0), 3.0),
                lens_depth=0.8, name="crest_spike"))
    fb = P("A.front_branch_band")
    fbw = np.array(tr["A.front_branch_band"]["width_px"], float)
    add(O.band(pj, fb, fbw * 2.0, height=2.6, profile="flat", q=q, name="front_band"))
    add(O.band(pj, P("A.rear_c_band"), 16.0, height=2.2, q=q, taper=(0.12, 0.12), name="c_band"))
    add(O.band(pj, P("A.sickle_plate_1"), 22.0, height=2.4, profile="flat", taper=(0.0, 0.45), q=q, name="sickle1"))
    add(O.band(pj, P("A.sickle_plate_2"), 19.0, height=2.3, profile="flat", taper=(0.15, 0.5), q=q, name="sickle2"))
    k1 = P("A.sickle_plate_1")[0]
    add(O.plate(pj, O.leaf_outline(k1 + [2, -8], k1 + [-3, 10], 14, 0.0, 10), thick=1.8, bevel_px=2.5, q=q,
                name="sickle_knob"))
    add(O.plate(pj, P("A.rear_leaf_spur"), thick=1.5, bevel_px=2.5, q=q, name="leaf_spur"))
    add(O.plate(pj, P("A.medallion_leaf"), thick=1.1, bevel_px=2.0, q=q, name="med_leaf"))
    for base, tip, w, cv in (((70, 560), (44, 486), 17, 0.08), ((66, 572), (36, 545), 12, -0.05),
                             ((82, 584), (110, 600), 12, 0.05), ((86, 566), (104, 528), 11, -0.08),
                             ((66, 588), (50, 610), 10, 0.0)):
        add(O.plate(pj, O.leaf_outline(base, tip, w, cv), thick=1.4, bevel_px=2.2, q=q, name="low_leaf"))
    add(O.plate(pj, P("A.heel_thorn_1"), thick=1.4, bevel_px=1.5, q=q, name="heel_thorn"))
    add(O.plate(pj, P("A.heel_diamond"), thick=1.9, bevel_px=2.0, dome=0.5, q=q, name="heel_diamond"))
    # --- strap and buckle
    add(O.frame_loop(pjs, P("A.buckle_hex_frame"), bar_px=7.0, height=1.7, q=q, name="hex_frame"))
    add(O.frame_loop(pjs, P("A.buckle_left_diamond"), bar_px=6.0, height=1.5, q=q, name="dia_left"))
    add(O.frame_loop(pjs, P("A.buckle_right_diamond"), bar_px=6.0, height=1.5, q=q, name="dia_right"))
    add(O.band(pjs, np.array([[243, 229], [256, 230]], float), 3.0, height=1.0, q=q, name="tongue"))
    add(O.pyramid(pjs, P("A.strap_stud"), height=2.0, q=q, name="stud"))
    # --- vamp: piping on the open-side topline rim, vine frame and runs
    labs = body["rib_lab"]
    rl_ = np.linalg.norm(np.diff(body["upper_grid"], axis=1), axis=2).sum(1)
    ok_ = np.nonzero(rl_ > 2.0)[0]
    labs = labs[ok_[0]:ok_[-1] + 1]
    top = up_outer[:, -1]
    ntop = up_n[:, -1]
    rp, rn = rim_points(top, ntop, (labs == 5) | (labs == 4))
    if rp is not None:
        rp = C.resample_polyline(rp, step=1.2 if hq else 6.0)
        rn2, _ = rp, None
        nn = np.array([ntop[np.argmin(np.linalg.norm(top - p, axis=1))] for p in rp])
        add(O.band(pj, None, 3.3 * s, height=1.5, q=q, profile="round", points3d=rp - nn * 0.35, normals3d=nn,
                   name="piping"))
    rb, _ = rim_points(top, ntop, (labs == 1) | (labs == 2) | (labs == 3))
    if rb is not None:
        rb = C.resample_polyline(rb, step=1.2 if hq else 9.0)
        nn = np.array([ntop[np.argmin(np.linalg.norm(top - p, axis=1))] for p in rb])
        add(O.band(pj, None, 2.2 * s, height=0.8, q=q, profile="round", mat="binding", points3d=rb - nn * 0.3,
                   normals3d=nn, name="binding"))
    for k, w in (("A.vine_frame_upper", 5.5), ("A.vine_frame_back", 5.5), ("A.vine_frame_lower", 5.5),
                 ("A.vine_lower_run", 5.0)):
        add(O.band(pj, P(k), w * 1.7, height=1.7, q=q, taper=(0.04, 0.06), name=k.split(".")[1]))
    add(O.thorn(pj, (272, 1005), (-1, 0.05), length_px=17, width_px=10, height=1.4, q=q, name="vine_corner"))
    for at, d in (((372, 910), (-0.8, -0.6)), ((477, 910), (0.25, -1)), ((652, 1070), (1, 0.35))):
        add(O.thorn(pj, at, d, length_px=13, width_px=7, height=1.2, q=q, name="vine_thorn"))
    # --- toe
    spike = P("A.toe_apex_spike")
    add(O.plate(pj, spike, thick=2.0, bevel_px=3.0, dome=0.6, q=q, lens_px=O.inset(O.resample_keep_corners(spike, 2.0), 9.0),
                lens_depth=0.7, name="toe_spike"))
    add(O.plate(pj, P("A.toe_rear_arm"), thick=1.6, bevel_px=2.5, dome=0.6, q=q, name="toe_arm"))
    add(O.plate(pj, P("A.toe_keystone"), thick=1.9, bevel_px=2.5, dome=0.5, q=q, name="keystone"))
    add(O.plate(pj, P("A.toe_cap"), thick=0.8, bevel_px=2.0, dome=0.35, edge_frac=0.6, sink=0.3, q=q, mat="patent",
                smooth=0, name="toe_cap"))
    fr = P("A.toe_frame_far_rail")
    add(O.band(pj, fr, np.linspace(22, 13, len(fr)), height=2.3, profile="flat", taper=(0.0, 0.08), q=q, name="far_rail"))
    nr_ = P("A.toe_frame_near_rail")
    add(O.band(pj, nr_, np.linspace(15, 10, len(nr_)), height=2.0, profile="flat", taper=(0.0, 0.08), q=q, name="near_rail"))
    for at, d in (((773, 1027), (-1, 0.55)), ((805, 1090), (-1, 0.5))):
        add(O.thorn(pj, at, d, length_px=13, width_px=7, height=1.2, q=q, name="rail_thorn"))
    add(O.plate(pj, [(836, 1137), (857, 1149), (872, 1170), (864, 1177), (833, 1153)], thick=1.5, bevel_px=2.0, q=q,
                name="tip_cap"))
    # --- blossoms and buds
    rots = {"A.counter_blossom": 0.4, "A.buckle_blossom": 1.2, "A.vamp_blossom": 0.9, "A.toe_blossom": 0.2}
    for k, rot in rots.items():
        c = tr[k]["pts"][0]
        b, _R = O.blossom(pjs if k == "A.buckle_blossom" else pj, c, tr[k]["d_px"], q=q, rot=rot, lift=0.35, scale_fix=1.22)
        b.name = k.split(".")[1]
        add(b)
    vines = np.vstack([P("A.vine_frame_upper"), P("A.vine_frame_lower"), P("A.vine_lower_run"), P("A.vine_frame_back")])
    for c in tr["A.vamp_buds"]["pts"]:
        c = np.array(c, float)
        near = vines[np.argmin(np.linalg.norm(vines - c, axis=1))]
        add(O.bud(pj, c, 17.0, near, q=q))
    add(O.bud(pj, (85, 447), 16.0, (95, 470), q=q))
    return parts


# ------------------------------------------------------------------------------------------------ blend output

MATS = {  # high-poly shading (bake source) : (base colour linear, metallic, roughness, final slot)
    "leather": ((0.010, 0.0095, 0.009), 0.0, 0.58, "Leather"),
    "lining": ((0.010, 0.009, 0.009), 0.0, 0.75, "Leather"),
    "binding": ((0.014, 0.013, 0.013), 0.0, 0.45, "Leather"),
    "crackle": ((0.030, 0.028, 0.027), 0.0, 0.48, "Leather"),
    "strap": ((0.013, 0.012, 0.012), 0.0, 0.40, "Leather"),
    "sole": ((0.012, 0.011, 0.011), 0.0, 0.38, "Leather"),
    "insole": ((0.030, 0.029, 0.028), 0.0, 0.62, "Insole"),
    "silver": ((0.50, 0.46, 0.43), 1.0, 0.27, "Metal"),
    "silver_recess": ((0.16, 0.145, 0.135), 1.0, 0.42, "Metal"),
    "pearl": ((0.60, 0.56, 0.53), 0.0, 0.30, "Metal"),
    "patent": ((0.006, 0.006, 0.006), 0.0, 0.06, "Metal"),
}


def material(name):
    m = bpy.data.materials.get("HP_" + name)
    if m is None:
        m = bpy.data.materials.new("HP_" + name)
        col, met, rough, _slot = MATS[name]
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*col, 1.0)
        bsdf.inputs["Metallic"].default_value = met
        bsdf.inputs["Roughness"].default_value = rough
        if name in ("patent", "pearl"):
            bsdf.inputs["Coat Weight"].default_value = 1.0 if name == "patent" else 0.4
            bsdf.inputs["Coat Roughness"].default_value = 0.03 if name == "patent" else 0.2
        m["final_slot"] = _slot
    return m


def part_object(part: Part, name, side, collection, fix=True):
    v = C.local_to_world(part.v, side)
    faces = part.f if side == "r" else [f[::-1] for f in part.f]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in v], [], [tuple(f) for f in faces])
    mats = sorted(set(part.m))
    for mn in mats:
        me.materials.append(material(mn))
    idx = {mn: i for i, mn in enumerate(mats)}
    me.polygons.foreach_set("material_index", [idx[m] for m in part.m])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if fix:
        fix_normals(ob)
    return ob


def fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    make_blend = "--no-blend" not in argv
    zl = np.load(C.CACHE / "last_r.npz")
    body = np.load(C.CACHE / "body_r.npz")
    heel = np.load(C.CACHE / "heel_r.npz")
    fs = G.grid_sampler(zl)
    ff = G.grid_sampler({"lo": zl["lo"], "f_last": zl["f_foot"]})
    camd = json.loads((C.CACHE / "camera.json").read_text())
    cam = HC.Cam(camd["az"], camd["el"], camd["s"], camd["tx"], camd["ty"], camd.get("roll", 0.0))
    tr = C.load_json(C.SPEC)["traces"]
    results = {}
    for q in ("high", "game"):
        up, up_outer, up_n = upper_shell(body, fs, q)
        # projection surfaces use the HIGH upper's outer grid (smooth), whatever the output quality
        if q == "high":
            hi_outer, hi_n = up_outer, up_n
            nr, ns = up_outer.shape[:2]
            gf = G.orient_by_sdf(up_outer.reshape(-1, 3), G.grid_faces(nr, ns), fs)
            surf_upper = G.Surf(up_outer.reshape(-1, 3), gf)
            surfs = [surf_upper]
            for key in ("stil", "strap", "toplift"):
                pp = mesh_part(heel, key, "x", key)
                surfs.append(G.Surf(pp.v, G.recalc_faces(pp.v, pp.f)))
            pp = mesh_part(body, "sole", "x", "sole")
            surfs.append(G.Surf(pp.v, G.recalc_faces(pp.v, pp.f)))
            pj = O.Projector(cam, surfs)
            pjs = O.Projector(cam, [surfs[2]])
        if q == "high":
            body_parts = [up,
                          mesh_part(body, "insole", "insole", "insole"),
                          mesh_part(body, "sole", "sole", "sole"),
                          mesh_part(heel, "stil", "sole", "stiletto"),
                          mesh_part(heel, "toplift", "sole", "toplift"),
                          mesh_part(heel, "strap", "strap", "strap")]
        else:
            body_parts = [up] + game_body(zl, body, heel)
        orn = ornaments(pj, tr, body, hi_outer, hi_n, q, pjs)
        if q == "game":
            for p_ in sorted(orn, key=lambda p: -sum(len(f) - 2 for f in p.f))[:14]:
                log("   ", p_.name, sum(len(f) - 2 for f in p_.f))
            for p_ in body_parts:
                log("   body", p_.name, sum(len(f) - 2 for f in p_.f))
        log(q, "ornaments", len(orn), "tris", sum(sum(len(f) - 2 for f in p.f) for p in orn),
            "body tris", sum(sum(len(f) - 2 for f in p.f) for p in body_parts))
        body_parts = [orient_body(manifold_fix(p_), fs) for p_ in body_parts]
        orn = [clearance(p_, ff, 1.3) for p_ in orn]
        body_parts = [clearance(p_, ff, 1.0) if p_.name in ("strap", "upper") else p_ for p_ in body_parts]
        orn = [manifold_fix(p_) for p_ in orn]
        results[q] = (body_parts, orn)
        if q == "game":
            for p_ in body_parts + orn:
                cnt = {}
                for f in p_.f:
                    for k in range(len(f)):
                        e = tuple(sorted((f[k], f[(k + 1) % len(f)])))
                        cnt[e] = cnt.get(e, 0) + 1
                bad = [e for e, c in cnt.items() if c > 2]
                dup = len(p_.f) - len({tuple(sorted(f)) for f in p_.f})
                ng = sum(1 for f in p_.f if len(f) > 4)
                if bad or dup or ng:
                    log("  TOPO", p_.name, "nonmanifold", len(bad), "dupfaces", dup, "ngons", ng,
                        p_.v[list(bad[0])].mean(0).round(1) if bad else "")
        allp = Part.join(body_parts + orn)
        save = {}
        for mn in sorted(set(allp.m)):
            sel = [i for i, m in enumerate(allp.m) if m == mn]
            fs_ = [allp.f[i] for i in sel]
            used = sorted({i for f in fs_ for i in f})
            remap = {o: n for n, o in enumerate(used)}
            save[f"{mn}_v"] = allp.v[used]
            tri = [[remap[i] for i in f] for f in fs_ if len(f) == 3]
            quad = [[remap[i] for i in f] for f in fs_ if len(f) == 4]
            other = [f for f in fs_ if len(f) > 4]
            if other:
                log("ngons in", mn, len(other))
            save[f"{mn}_t"] = np.array(tri, dtype=np.int64).reshape(-1, 3)
            save[f"{mn}_q"] = np.array(quad, dtype=np.int64).reshape(-1, 4)
        np.savez_compressed(C.CACHE / f"parts_{q}_r.npz", **save)
    if not make_blend:
        return
    # ---- the source blend
    from pipeline import garment_helpers as gh
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system, sc.unit_settings.scale_length, sc.unit_settings.length_unit = "METRIC", 1.0, "METERS"
    gh.append_fitbody("MH_PlayerFemale")
    cols = gh.ensure_collections()
    bpy.data.collections.remove(cols.pop(gh.SIM_COLLECTION))
    sc["garment_name"] = "SnowFlowerHeels"
    sc["garment_asset"] = "SnowFlowerHeels"
    sc["garment_type"] = "fitted"
    sc["garment_base"] = "MH_PlayerFemale"
    sc["garment_socket_bone"] = ""
    sc["garment_sim_target_tris"] = 0
    sc["garment_skin_target_tris"] = 0
    sc["garment_export_name"] = "SK_SnowFlowerHeels"
    sc["garment_unique_uvs"] = True
    for cname in ("HEELS_HIGH_POSED", "HEELS_GAME_POSED"):
        c = bpy.data.collections.new(cname)
        sc.collection.children.link(c)
    for q, cname in (("high", "HEELS_HIGH_POSED"), ("game", "HEELS_GAME_POSED")):
        body_parts, orn = results[q]
        col = bpy.data.collections[cname]
        for side in ("r", "l"):
            for p in body_parts:
                ob = part_object(p, f"{q.upper()}_{side.upper()}_{p.name}", side, col, fix=False)
            op = Part.join(orn, "ornaments")
            part_object(op, f"{q.upper()}_{side.upper()}_ornaments", side, col, fix=False)
    # posed feet reference into the helpers
    with bpy.data.libraries.load(str(C.FOOT_POSED_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("HEEL_")]
    for ob in dst.objects:
        if ob is not None:
            cols[gh.HELPER_COLLECTION].objects.link(ob)
            ob.hide_render = True
    C.ASSET_BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(C.ASSET_BLEND))
    log("saved", C.ASSET_BLEND)


main()
