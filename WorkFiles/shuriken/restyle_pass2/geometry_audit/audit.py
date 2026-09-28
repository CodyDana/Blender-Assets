"""Independent geometry audit of the shuriken pack (pass 2) from npz dumps of a COPY of the blend.

Run: blender -b --factory-startup --python audit.py -- <scratch dir>
Reads <dir>/p2/*.npz (pass 2) and <dir>/p1/*.npz (pass 1 backup); writes <dir>/audit.json.
"""
import json
import math
import sys
from collections import defaultdict

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

MM = 1e-3
DENSITY = 7.85  # g/cm3
ROOT = sys.argv[sys.argv.index("--") + 1]

FORMS = {
    "FourPoint": dict(kind="star", n=4, r_tip=48.5, t=3.0, hw=5.5, r_hub=11.0, r_hole=4.0, hole_m=16, tip_deg=40.0,
                      grind=35.0, land=0.15, scallop=0.45, hole_ch=0.3, hole_deg=45.0, runout=3.0,
                      mass_target=39.0, study=(34.0, 80.0), bands=((1200, 2500), (500, 900), (120, 250))),
    "EightPoint": dict(kind="star", n=8, r_tip=50.0, t=2.5, hw=5.0, r_hub=22.0, r_hole=4.75, hole_m=24, tip_deg=35.0,
                       grind=35.0, land=0.15, scallop=0.45, hole_ch=0.3, hole_deg=45.0, runout=3.0,
                       mass_target=60.0, study=(53.0, 79.0), bands=((1200, 2500), (500, 900), (120, 250))),
    "SquarePlate": dict(kind="plate", n=4, side=76.2, sagitta=6.0, t=1.9, hole_side=12.7, fillet=1.0,
                        grind=35.0, land=0.15, hole_ch=0.3, hole_deg=45.0,
                        mass_target=66.0, study=(45.0, 82.0), bands=((1200, 2500), (500, 900), (120, 250))),
}


# ----------------------------------------------------------------------------------------- io
def load(tag, name):
    d = dict(np.load(f"{ROOT}/{tag}/{name}.npz"))
    d["polys"] = [d["loop_vert"][s:s + t] for s, t in zip(d["loop_start"], d["loop_total"])]
    d["poly_loops"] = [np.arange(s, s + t) for s, t in zip(d["loop_start"], d["loop_total"])]
    return d


def rot2(k, n, xy):
    """Rotate XY rows by k/n of a turn (quarter turns trig-free)."""
    xy = np.asarray(xy, dtype=np.float64)
    if n == 4 or (4 * k) % n == 0:
        q = (4 * k // n) % 4
        x, y = xy[..., 0], xy[..., 1]
        return np.stack([[x, y], [-y, x], [-x, -y], [y, -x]][q], axis=-1)
    a = 2.0 * math.pi * k / n
    c, s = math.cos(a), math.sin(a)
    return np.stack([c * xy[..., 0] - s * xy[..., 1], s * xy[..., 0] + c * xy[..., 1]], axis=-1)


# ----------------------------------------------------------------------------------------- hygiene
def newell(co, poly):
    p = co[poly]
    q = np.roll(p, -1, axis=0)
    return 0.5 * np.cross(p, q).sum(axis=0)


def hygiene(d):
    co, polys, edges = d["co"], d["polys"], d["edges"]
    V = len(co)
    out = {}
    sizes = np.array([len(p) for p in polys])
    out["verts"] = V
    out["faces"] = len(polys)
    out["tri_faces"] = int((sizes == 3).sum())
    out["quad_faces"] = int((sizes == 4).sum())
    out["ngons"] = int((sizes > 4).sum())
    out["triangles"] = int((sizes - 2).sum())
    out["loop_triangles"] = int(len(d["tri"]))
    ef = defaultdict(list)
    for fi, p in enumerate(polys):
        n = len(p)
        for k in range(n):
            a, b = int(p[k]), int(p[(k + 1) % n])
            ef[(min(a, b), max(a, b))].append((fi, 1 if a < b else -1))
    counts = {k: len(v) for k, v in ef.items()}
    out["boundary_edges"] = sum(1 for c in counts.values() if c == 1)
    out["non_manifold_edges"] = sum(1 for c in counts.values() if c > 2)
    out["winding_inconsistent_edges"] = sum(1 for v in ef.values() if len(v) == 2 and v[0][1] == v[1][1])
    edge_set = set((int(min(a, b)), int(max(a, b))) for a, b in edges)
    out["wire_edges"] = len(edge_set - set(ef))
    out["face_edges_missing_from_edge_table"] = len(set(ef) - edge_set)
    used = set(int(v) for p in polys for v in p)
    out["loose_verts"] = V - len(used)
    keys = [tuple(sorted(int(v) for v in p)) for p in polys]
    out["duplicate_faces"] = len(keys) - len(set(keys))
    out["faces_with_repeated_vertex"] = sum(1 for p in polys if len(set(p.tolist())) != len(p))

    def ekey(a, b):
        a, b = int(a), int(b)
        return (min(a, b), max(a, b))
    out["interior_faces"] = sum(1 for p in polys
                                if all(counts[ekey(p[k], p[(k + 1) % len(p)])] > 2 for k in range(len(p))))
    el = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
    out["min_edge_mm"] = float(el.min() / MM)
    out["zero_length_edges_1um"] = int((el <= 1e-6).sum())
    areas, planar, normals = [], [], []
    for p in polys:
        N = newell(co, p)
        a = float(np.linalg.norm(N))
        areas.append(a)
        nn = N / a if a > 0 else np.array([0.0, 0.0, 1.0])
        normals.append(nn)
        c = co[p].mean(axis=0)
        planar.append(float(np.abs((co[p] - c) @ nn).max()))
    areas = np.array(areas)
    planar = np.array(planar)
    out["min_face_area_mm2"] = float(areas.min() / MM ** 2)
    out["zero_area_faces_1e-12m2"] = int((areas <= 1e-12).sum())
    out["nonplanar_faces_over_1um"] = int((planar > 1e-6).sum())
    out["nonplanar_faces_over_0.1um"] = int((planar > 1e-7).sum())
    out["max_nonplanarity_mm"] = float(planar.max() / MM)
    # min triangle angle / aspect over the loop triangles
    t = d["tri"]
    A, B, C = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]

    def ang(u, v):
        cu = np.einsum("ij,ij->i", u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-30)
        return np.degrees(np.arccos(np.clip(cu, -1, 1)))
    angs = np.stack([ang(B - A, C - A), ang(A - B, C - B), ang(A - C, B - C)], axis=1)
    mins = angs.min(axis=1)
    out["min_triangle_angle_deg"] = float(mins.min())
    out["triangles_under_1deg"] = int((mins < 1.0).sum())
    out["triangles_under_5deg"] = int((mins < 5.0).sum())
    tri_area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    out["min_loop_triangle_area_mm2"] = float(tri_area.min() / MM ** 2)
    # coincident vertices
    kd = KDTree(V)
    for i, c in enumerate(co):
        kd.insert(Vector(c), i)
    kd.balance()
    pairs = 0
    for i, c in enumerate(co):
        pairs += sum(1 for (_c, j, _d) in kd.find_range(Vector(c), 1e-7) if j > i)
    out["coincident_vertex_pairs_0.1um"] = pairs
    pairs = 0
    for i, c in enumerate(co):
        pairs += sum(1 for (_c, j, _d) in kd.find_range(Vector(c), 1e-6) if j > i)
    out["vertex_pairs_within_1um"] = pairs
    # components
    parent = list(range(V))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    out["components"] = len(set(find(v) for v in used))
    # volume / centroid (divergence theorem on the loop triangles)
    det = np.einsum("ij,ij->i", A, np.cross(B, C))
    vol = det.sum() / 6.0
    cen = ((det[:, None] * (A + B + C)).sum(axis=0) / 24.0) / vol if vol != 0 else np.zeros(3)
    out["signed_volume_mm3"] = float(vol / MM ** 3)
    out["centroid_mm"] = [float(x / MM) for x in cen]
    # folds: dihedral between edge-adjacent faces (normals nearly opposite)
    normals = np.array(normals)
    worst = 0.0
    folds = 0
    for key, v in ef.items():
        if len(v) == 2:
            dotn = float(normals[v[0][0]] @ normals[v[1][0]])
            ang_n = math.degrees(math.acos(max(-1.0, min(1.0, dotn))))
            worst = max(worst, ang_n)
            folds += ang_n > 175.0
    out["max_normal_turn_across_edge_deg"] = worst
    out["folded_edges_over_175deg"] = folds
    # self intersection (triangle pairs that do not share a vertex)
    bvh = BVHTree.FromPolygons([Vector(c) for c in co], [tuple(int(x) for x in tr) for tr in t], all_triangles=True,
                               epsilon=0.0)
    ov = bvh.overlap(bvh)
    bad = []
    for i, j in ov:
        if i >= j:
            continue
        if set(t[i].tolist()) & set(t[j].tolist()):
            continue
        bad.append((int(i), int(j)))
    out["self_intersecting_triangle_pairs"] = len(bad)
    out["self_intersection_examples"] = bad[:5]
    d["_areas"], d["_normals"], d["_planar"] = areas, normals, planar
    return out


# ----------------------------------------------------------------------------------------- symmetry
def kd_of(co):
    kd = KDTree(len(co))
    for i, c in enumerate(co):
        kd.insert(Vector(c), i)
    kd.balance()
    return kd


def sym_check(d, fn):
    co = d["co"]
    kd = kd_of(co)
    moved = fn(co)
    mapping = np.empty(len(co), dtype=np.int64)
    worst = 0.0
    for i, p in enumerate(moved):
        _c, j, dist = kd.find(Vector(p))
        mapping[i] = j
        worst = max(worst, dist)
    keys = set(tuple(sorted(int(v) for v in p)) for p in d["polys"])
    misses = sum(1 for p in d["polys"] if tuple(sorted(int(mapping[v]) for v in p)) not in keys)
    bij = len(set(mapping.tolist())) == len(co)
    return {"max_dev_mm": worst / MM, "face_misses": misses, "vertex_map_bijective": bool(bij)}


def symmetry(d, form):
    f = FORMS[form]
    n = f["n"]
    res = {}
    res[f"C{n}"] = sym_check(d, lambda co: np.column_stack([rot2(1, n, co[:, :2]), co[:, 2]]))
    res["mirror_y"] = sym_check(d, lambda co: co * np.array([1.0, -1.0, 1.0]))
    res["mirror_z_top_bottom"] = sym_check(d, lambda co: co * np.array([1.0, 1.0, -1.0]))
    if f["kind"] == "plate":
        res["mirror_diag_x_eq_y"] = sym_check(d, lambda co: co[:, [1, 0, 2]])
    return res


# ----------------------------------------------------------------------------------------- sections
def section(co, edges, P, t_dir, n_in, s_min, s_max, tol_plane=1e-12):
    """Vertical plane through P (XY) with horizontal normal t_dir; returns (s, z) of mesh-edge crossings,
    s = (p - P) . n_in, kept in [s_min, s_max]."""
    a, b = co[edges[:, 0]], co[edges[:, 1]]
    da = (a[:, :2] - P) @ t_dir
    db = (b[:, :2] - P) @ t_dir
    pts = []
    on_a = np.abs(da) <= tol_plane
    on_b = np.abs(db) <= tol_plane
    pts.append(a[on_a])
    pts.append(b[on_b])
    cross = (da * db < 0) & ~on_a & ~on_b
    tt = da[cross] / (da[cross] - db[cross])
    pts.append(a[cross] + tt[:, None] * (b[cross] - a[cross]))
    pts = np.concatenate(pts, axis=0)
    s = (pts[:, :2] - P) @ n_in
    keep = (s >= s_min) & (s <= s_max)
    return s[keep], pts[keep, 2]


def analyse_section(s, z, half_t, wall_tol=2e-6):
    """Land, per-face facet angle and width, symmetry from one edge section."""
    if len(s) == 0:
        return None
    s = s - s.min()          # the outermost points are the wall (chorded outlines sit off the ideal arc)
    wall = s <= wall_tol
    zt, zb = float(z[wall].max()), float(z[wall].min())
    out = {"land_mm": (zt - zb) / MM, "wall_top_mm": zt / MM, "wall_bot_mm": zb / MM}
    for name, sign, zw in (("top", 1.0, zt), ("bot", -1.0, zb)):
        sel = (sign * z > 0) & (s > wall_tol)
        if not sel.any():
            out[name] = None
            continue
        ss, zz = s[sel], sign * z[sel]
        slopes = (zz - sign * zw) / ss
        k = int(np.argmax(slopes))
        ang = math.degrees(math.atan(float(slopes[k])))
        plate = ss[zz >= half_t - 1e-7]
        width = float(plate.min()) if len(plate) else None
        # points on the facet line (between wall and plate edge): straightness residual
        lim = width if width is not None else float(ss[k])
        mid = (ss > 1e-6) & (ss < lim - 1e-6)
        resid = float(np.abs(zz[mid] - (sign * zw + slopes[k] * ss[mid])).max()) if mid.any() else 0.0
        out[name] = {"angle_deg": ang, "width_mm": None if width is None else width / MM,
                     "drop_mm": (half_t - sign * zw) / MM, "straightness_resid_mm": resid / MM,
                     "roof": width is None}
    return out


def star_geom(f):
    r_tip, hw, r_hub = f["r_tip"] * MM, f["hw"] * MM, f["r_hub"] * MM
    half_tip = math.radians(0.5 * f["tip_deg"])
    x_taper = r_tip - hw / math.tan(half_tip)
    x_root0 = math.sqrt(r_hub ** 2 - hw ** 2)
    alpha = math.radians(f["grind"])
    half_t = 0.5 * f["t"] * MM
    depth = half_t - 0.5 * f["land"] * MM
    w = depth / math.tan(alpha)
    x_apex = r_tip - (w / math.cos(half_tip)) / math.tan(half_tip)
    return dict(r_tip=r_tip, hw=hw, r_hub=r_hub, half_tip=half_tip, x_taper=x_taper, x_root0=x_root0,
                x_run=x_root0 + f["runout"] * MM, half_t=half_t, w=w, depth=depth, x_apex=x_apex,
                half_sector=math.pi / f["n"], arm_half=math.asin(hw / r_hub))


def summarise(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"min": round(min(vals), 5), "max": round(max(vals), 5), "n": len(vals)}


def grind_star(d, form):
    f = FORMS[form]
    g = star_geom(f)
    co, edges = d["co"], d["edges"]
    n = f["n"]
    rows = []
    for k in range(n):
        R = lambda v: rot2(k, n, np.array(v, dtype=np.float64))  # noqa: E731
        for side in (1, -1):
            # parallel run beyond the run-out
            for fr in (0.05, 0.35, 0.65, 0.95):
                x = g["x_run"] + fr * (g["x_taper"] - g["x_run"])
                P, t_dir, n_in = R([x, side * g["hw"]]), R([1.0, 0.0]), R([0.0, -side])
                s, z = section(co, edges, P, t_dir, n_in, -1e-5, g["hw"] - 1e-6)
                rows.append(("parallel", k, side, round(fr, 2), analyse_section(s, z, g["half_t"])))
            # run-out (root -> x_run)
            for fr in (0.1, 0.5, 0.9):
                x = g["x_root0"] + 0.02 * MM + fr * (g["x_run"] - g["x_root0"] - 0.02 * MM)
                P, t_dir, n_in = R([x, side * g["hw"]]), R([1.0, 0.0]), R([0.0, -side])
                s, z = section(co, edges, P, t_dir, n_in, -1e-5, g["hw"] - 1e-6)
                rows.append(("runout", k, side, round(fr, 2), analyse_section(s, z, g["half_t"])))
            # taper edge, shoulder -> tip
            sh = np.array([g["x_taper"], side * g["hw"]])
            tip = np.array([g["r_tip"], 0.0])
            L = float(np.linalg.norm(tip - sh))
            e = (tip - sh) / L
            nrm = np.array([-e[1], e[0]])
            if nrm @ np.array([0.0, -side]) < 0:
                nrm = -nrm
            for fr in (0.05, 0.3, 0.55, 0.8, 0.92, 0.97, 0.99):
                P0 = sh + fr * L * e
                s_axis = -P0[1] / nrm[1]
                P, t_dir, n_in = R(P0), R(e), R(nrm)
                s, z = section(co, edges, P, t_dir, n_in, -1e-5, s_axis + 0.3 * MM)
                rows.append(("taper", k, side, round(fr, 2), analyse_section(s, z, g["half_t"])))
    return rows, g


def grind_plate(d, form):
    f = FORMS[form]
    side = f["side"] * MM
    h = f["sagitta"] * MM
    half = 0.5 * side
    rho = (half * half + h * h) / (2 * h)
    centre = half - h + rho
    cq = centre * math.sqrt(0.5)
    r_tip = side * math.sqrt(0.5)
    half_t = 0.5 * f["t"] * MM
    co, edges = d["co"], d["edges"]
    rows = []
    bA = math.atan2(0.0 - cq, r_tip - cq)
    bB = math.atan2(r_tip - cq, 0.0 - cq)
    # short way: bA ~ -117 deg, bB ~ -153 deg (i.e. 207 deg)
    for j in range(4):
        C = rot2(j, 4, np.array([cq, cq]))
        for fr in (0.01, 0.05, 0.15, 0.3, 0.45, 0.5, 0.55, 0.7, 0.85, 0.95, 0.99):
            beta = bA + fr * (bB - bA)
            P0 = np.array([cq + rho * math.cos(beta), cq + rho * math.sin(beta)])
            P = rot2(j, 4, P0)
            n_in = (P - C) / rho
            t_dir = np.array([-n_in[1], n_in[0]])
            s, z = section(co, edges, P, t_dir, n_in, -1.0 * MM, 4 * MM)
            rows.append(("side", j, 0, fr, analyse_section(s, z, half_t)))
    geo = dict(rho=rho, centre=centre, cq=cq, r_tip=r_tip, half_t=half_t, bA=bA, bB=bB)
    return rows, geo


def notch_and_hole_star(d, form):
    f = FORMS[form]
    g = star_geom(f)
    co, edges = d["co"], d["edges"]
    n = f["n"]
    notch, hole = [], []
    for k in range(n):
        base = 2 * math.pi * k / n
        for side in (1, -1):
            for fr in (0.15, 0.5, 0.85):
                a = base + side * (g["arm_half"] + fr * (g["half_sector"] - g["arm_half"]))
                u = np.array([math.cos(a), math.sin(a)])
                P = g["r_hub"] * u
                s, z = section(co, edges, P, np.array([-u[1], u[0]]), -u, -1.0 * MM, 2.0 * MM)
                notch.append(analyse_section(s, z, g["half_t"]))
    m = f["hole_m"]
    r_poly_min = f["r_hole"] * MM
    for j in range(m):
        a = -math.pi / n + (j + 0.5) * 2 * math.pi / m      # flat midpoints
        u = np.array([math.cos(a), math.sin(a)])
        P = r_poly_min * u
        s, z = section(co, edges, P, np.array([-u[1], u[0]]), u, -0.5 * MM, 2.0 * MM)
        hole.append(analyse_section(s, z, g["half_t"]))
    return notch, hole


def hole_plate(d, form):
    f = FORMS[form]
    co, edges = d["co"], d["edges"]
    half_t = 0.5 * f["t"] * MM
    flat = 0.5 * f["hole_side"] * MM
    out = []
    for j in range(4):
        for off in (-0.3, 0.0, 0.3):   # along the flat, mm-ish fractions of the half side
            a = math.radians(45.0 + 90.0 * j)
            u = np.array([math.cos(a), math.sin(a)])
            tvec = np.array([-u[1], u[0]])
            P = flat * u + off * 0.5 * flat * tvec
            s, z = section(co, edges, P, tvec, u, -0.3 * MM, 2.0 * MM)
            out.append(analyse_section(s, z, half_t))
    return out


def facet_stats(rows):
    """Summaries of land / angle / width / top-bottom symmetry over section rows."""
    lands, at, ab, wt, wb, dsym, straight = [], [], [], [], [], [], []
    for _kind, *_rest, r in rows:
        if not r or "error" in r:
            continue
        lands.append(r["land_mm"])
        dsym.append(abs(r["wall_top_mm"] + r["wall_bot_mm"]))
        if r.get("top"):
            at.append(r["top"]["angle_deg"])
            straight.append(r["top"]["straightness_resid_mm"])
            if r["top"]["width_mm"] is not None:
                wt.append(r["top"]["width_mm"])
        if r.get("bot"):
            ab.append(r["bot"]["angle_deg"])
            straight.append(r["bot"]["straightness_resid_mm"])
            if r["bot"]["width_mm"] is not None:
                wb.append(r["bot"]["width_mm"])
    pair = [abs(a - b) for a, b in zip(at, ab)]
    return {"land_mm": summarise(lands), "angle_top_deg": summarise(at), "angle_bot_deg": summarise(ab),
            "width_top_mm": summarise(wt), "width_bot_mm": summarise(wb),
            "top_bot_angle_diff_deg_max": max(pair) if pair else None,
            "wall_centring_mm_max": max(dsym) if dsym else None,
            "facet_straightness_resid_mm_max": max(straight) if straight else None,
            "sections": len(lands)}


# ----------------------------------------------------------------------------------------- tips
def tips(d, form):
    f = FORMS[form]
    co = d["co"]
    n = f["n"]
    if f["kind"] == "star":
        g = star_geom(f)
        r_tip, half_t = g["r_tip"], g["half_t"]
        half_tip = g["half_tip"]
        x_ridge0 = g["x_apex"]
    else:
        side = f["side"] * MM
        r_tip = side * math.sqrt(0.5)
        half_t = 0.5 * f["t"] * MM
        half_tip = None
        x_ridge0 = None
    res = []
    for k in range(n):
        loc = np.column_stack([rot2(-k, n, co[:, :2]), co[:, 2]])
        near = np.hypot(loc[:, 0] - r_tip, loc[:, 1]) < 1e-6
        zs = loc[near, 2]
        rmax = float(np.hypot(loc[:, 0], loc[:, 1]).max())
        entry = {"tip_vertices": int(near.sum()), "tip_edge_height_mm": float(np.ptp(zs) / MM) if len(zs) else None,
                 "tip_edge_centred_mm": float(abs(zs.max() + zs.min()) / MM) if len(zs) else None,
                 "plan_tip_truncation_mm": float((r_tip - loc[near, 0].max()) / MM) if near.any() else None}
        # ridge on the axis (top), from where the plate ends to the tip
        axis = (np.abs(loc[:, 1]) < 1e-7) & (loc[:, 2] > 0) & (loc[:, 0] > 0.5 * r_tip)
        pts = loc[axis]
        pts = pts[np.argsort(pts[:, 0])]
        # keep the descending ridge: points below the plate face
        ridge = pts[pts[:, 2] < half_t - 1e-7]
        if len(ridge) >= 1:
            # include the last plate-height point on the axis (the ridge start)
            plate_pts = pts[pts[:, 2] >= half_t - 1e-7]
            start = plate_pts[-1] if len(plate_pts) else ridge[0]
            allr = np.vstack([start[None], ridge])
            slope = (allr[-1, 2] - allr[0, 2]) / (allr[-1, 0] - allr[0, 0])
            fit = np.polyfit(allr[:, 0], allr[:, 2], 1) if len(allr) >= 2 else None
            resid = float(np.abs(np.polyval(fit, allr[:, 0]) - allr[:, 2]).max()) if fit is not None else None
            entry.update({"ridge_start_x_mm": float(allr[0, 0] / MM), "ridge_points": int(len(allr)),
                          "ridge_included_deg": float(2 * math.degrees(math.atan(-slope))),
                          "ridge_straightness_mm": resid / MM if resid is not None else None})
        # plan: outline vertices near the tip lie on the two ideal taper lines
        if half_tip is not None:
            sel = (loc[:, 0] > r_tip - 2 * MM)
            p = loc[sel]
            # distance outside the ideal wedge |y| <= (r_tip - x) tan(half_tip)
            excess = np.abs(p[:, 1]) - (r_tip - p[:, 0]) * math.tan(half_tip)
            entry["plan_outside_ideal_wedge_mm"] = float(excess.max() / MM)
        res.append(entry)
    return res


# ----------------------------------------------------------------------------------------- silhouette
def radial_profile(co, edges, angles):
    """Outer max / inner min radius of the XY projection of all edges along rays from the origin."""
    a = co[edges[:, 0], :2]
    b = co[edges[:, 1], :2]
    e = b - a
    keep = np.hypot(e[:, 0], e[:, 1]) > 1e-12
    a, e = a[keep], e[keep]
    outer = np.full(len(angles), -np.inf)
    inner = np.full(len(angles), np.inf)
    for start in range(0, len(angles), 512):
        th = angles[start:start + 512]
        dx, dy = np.cos(th)[:, None], np.sin(th)[:, None]
        # a + t e = r d  ->  cross(d, a) + t cross(d, e) = 0
        cda = dx * a[None, :, 1] - dy * a[None, :, 0]
        cde = dx * e[None, :, 1] - dy * e[None, :, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = -cda / cde
        valid = (np.abs(cde) > 1e-18) & (t >= -1e-9) & (t <= 1 + 1e-9)
        px = a[None, :, 0] + t * e[None, :, 0]
        py = a[None, :, 1] + t * e[None, :, 1]
        r = px * dx + py * dy
        valid &= r > 0
        # also ray through an endpoint exactly (parallel edges): use endpoints
        r_o = np.where(valid, r, -np.inf).max(axis=1)
        r_i = np.where(valid, r, np.inf).min(axis=1)
        outer[start:start + 512] = r_o
        inner[start:start + 512] = r_i
    # vertices exactly on rays (covers edges collinear with the ray)
    return outer, inner


def silhouette(d1, d2):
    co1, co2 = d1["co"], d2["co"]
    ang_v = np.concatenate([np.arctan2(co1[:, 1], co1[:, 0]), np.arctan2(co2[:, 1], co2[:, 0])])
    angles = np.unique(np.concatenate([ang_v, np.linspace(-math.pi, math.pi, 36000, endpoint=False)]))
    # also tiny offsets either side of each vertex angle
    angles = np.unique(np.concatenate([angles, ang_v + 1e-7, ang_v - 1e-7]))
    o1, i1 = radial_profile(co1, d1["edges"], angles)
    o2, i2 = radial_profile(co2, d2["edges"], angles)
    return {"rays": int(len(angles)), "outer_max_diff_mm": float(np.abs(o1 - o2).max() / MM),
            "inner_max_diff_mm": float(np.abs(i1 - i2).max() / MM),
            "outer_max_mm": float(o2.max() / MM), "inner_min_mm": float(i2.min() / MM)}


def plan_area(d):
    """Projected area of the up-facing faces = the plan area of the solid (walls vertical)."""
    co, t = d["co"], d["tri"]
    A, B, C = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]
    cz = 0.5 * ((B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0]))
    up = cz[cz > 0].sum()
    down = -cz[cz < 0].sum()
    return up, down


# ----------------------------------------------------------------------------------------- UVs
def uv_checks(d, res=4096):
    uv, tl = d["uv"], d["tri_loops"]
    out = {"uv_min": [float(x) for x in uv.min(axis=0)], "uv_max": [float(x) for x in uv.max(axis=0)]}
    out["outside_unit_square"] = int(((uv < 0) | (uv > 1)).any(axis=1).sum())
    owner = np.full((res, res), -1, dtype=np.int32)
    count = np.zeros((res, res), dtype=np.int16)
    pairs = set()
    tri_poly = d["tri_poly"]
    for ti, (la, lb, lc) in enumerate(tl):
        pa, pb, pc = uv[la] * res - 0.5, uv[lb] * res - 0.5, uv[lc] * res - 0.5
        area = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if abs(area) < 1e-12:
            continue
        x0 = max(int(math.ceil(min(pa[0], pb[0], pc[0]))), 0)
        x1 = min(int(math.floor(max(pa[0], pb[0], pc[0]))), res - 1)
        y0 = max(int(math.ceil(min(pa[1], pb[1], pc[1]))), 0)
        y1 = min(int(math.floor(max(pa[1], pb[1], pc[1]))), res - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float64), np.arange(y0, y1 + 1, dtype=np.float64))
        sgn = 1.0 if area > 0 else -1.0
        eps = 1e-6   # strictly inside: shared edges do not count twice
        w0 = sgn * ((pb[0] - pa[0]) * (gy - pa[1]) - (pb[1] - pa[1]) * (gx - pa[0]))
        w1 = sgn * ((pc[0] - pb[0]) * (gy - pb[1]) - (pc[1] - pb[1]) * (gx - pb[0]))
        w2 = sgn * ((pa[0] - pc[0]) * (gy - pc[1]) - (pa[1] - pc[1]) * (gx - pc[0]))
        inside = (w0 > eps) & (w1 > eps) & (w2 > eps)
        if not inside.any():
            continue
        sub_o = owner[y0:y1 + 1, x0:x1 + 1]
        sub_c = count[y0:y1 + 1, x0:x1 + 1]
        clash = inside & (sub_o >= 0) & (sub_o != -1)
        if clash.any():
            for other in np.unique(sub_o[clash]):
                if tri_poly[other] != tri_poly[ti]:
                    pairs.add((int(min(tri_poly[other], tri_poly[ti])), int(max(tri_poly[other], tri_poly[ti]))))
        sub_c[inside] += 1
        sub_o[inside] = ti
    out["overlap_pixels_4096"] = int((count > 1).sum())
    out["overlapping_face_pairs"] = len(pairs)
    out["coverage"] = float((count > 0).mean())
    # UV winding per face (vs. 3D winding seen along its own normal: all faces are laid out planar-ish,
    # so a negative UV area means a mirrored island)
    neg = 0
    ratios = []
    for p, loops, area3 in zip(d["polys"], d["poly_loops"], d["_areas"]):
        q = uv[loops]
        a2 = 0.5 * np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])
        neg += a2 < 0
        if area3 > 0:
            ratios.append(math.sqrt(abs(a2) / area3))
    ratios = np.array(ratios)
    out["mirrored_uv_faces"] = int(neg)
    out["texel_uv_per_m"] = {"min": float(ratios.min()), "median": float(np.median(ratios)), "max": float(ratios.max())}
    return out


def uv_transfer(d0, dl, px=2048):
    """LOD UVs against LOD0: at each LOD triangle centroid, LOD0's UV at the nearest same-facing point."""
    co0, t0, tl0, uv0 = d0["co"], d0["tri"], d0["tri_loops"], d0["uv"]
    bvh = BVHTree.FromPolygons([Vector(c) for c in co0], [tuple(int(x) for x in tr) for tr in t0], all_triangles=True)
    co, t, tl, uv = dl["co"], dl["tri"], dl["tri_loops"], dl["uv"]
    plate_d, all_d, unmatched = [], [], 0
    for tri, loops in zip(t, tl):
        P = co[tri]
        c = P.mean(axis=0)
        nrm = np.cross(P[1] - P[0], P[2] - P[0])
        nl = np.linalg.norm(nrm)
        if nl == 0:
            continue
        nrm /= nl
        uvc = uv[loops].mean(axis=0)
        best = None
        for (hit, hn, idx, dist) in bvh.find_nearest_range(Vector(c), 0.5 * MM):
            dotn = float(np.dot(np.array(hn), nrm))
            if dotn > 0.99 and (best is None or dist < best[3]):
                best = (np.array(hit), dotn, idx, dist)
        if best is None:
            unmatched += 1
            continue
        hit, _dn, idx, _dist = best
        A, B, C = co0[t0[idx]]
        v0, v1, v2 = B - A, C - A, hit - A
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        bv = (d11 * d20 - d01 * d21) / den
        bw = (d00 * d21 - d01 * d20) / den
        bu = 1 - bv - bw
        L = tl0[idx]
        uvh = bu * uv0[L[0]] + bv * uv0[L[1]] + bw * uv0[L[2]]
        dpx = float(np.linalg.norm(uvh - uvc) * px)
        all_d.append(dpx)
        if abs(nrm[2]) > 0.9999:
            plate_d.append(dpx)
    return {"plate_max_px": max(plate_d) if plate_d else None, "plate_median_px": float(np.median(plate_d)) if plate_d else None,
            "all_matched_max_px": max(all_d) if all_d else None, "all_matched_p95_px": float(np.percentile(all_d, 95)) if all_d else None,
            "matched": len(all_d), "unmatched_triangles": unmatched}


# ----------------------------------------------------------------------------------------- shading
def shading(d, form):
    """Angle between each corner normal and its face normal, grouped by a geometric face class."""
    if "corner_normals" not in d:
        return None
    cn, normals = d["corner_normals"], d["_normals"]
    co = d["co"]
    f = FORMS[form]
    cls_max = defaultdict(float)
    cls_count = defaultdict(int)
    worst_faces = []
    for fi, (p, loops) in enumerate(zip(d["polys"], d["poly_loops"])):
        nz = abs(normals[fi][2])
        ang = math.degrees(math.acos(min(1.0, nz)))
        if nz > 0.9999:
            c = "plate"
        elif nz < 1e-4:
            c = "wall"
        elif abs(ang - 45.0) < 0.5:
            c = "hole_chamfer_45"
        elif abs(ang - f["grind"]) < 0.6:
            c = "facet_35"
        else:
            c = f"other_{round(ang)}deg"
        dev = 0.0
        for L in loops:
            dev = max(dev, math.degrees(math.acos(max(-1.0, min(1.0, float(cn[L] @ normals[fi]))))))
        cls_max[c] = max(cls_max[c], dev)
        cls_count[c] += 1
        worst_faces.append((dev, c, [round(float(x) / MM, 3) for x in co[p].mean(axis=0)]))
    worst_faces.sort(reverse=True)
    sharp = int(d["sharp_edge"].sum()) if "sharp_edge" in d else None
    return {"max_corner_normal_dev_deg_by_class": {k: round(v, 3) for k, v in cls_max.items()},
            "faces_by_class": dict(cls_count), "sharp_edges": sharp,
            "worst": [(round(a, 2), c, xyz) for a, c, xyz in worst_faces[:6]]}


# ----------------------------------------------------------------------------------------- hull
def hull_check(dh, dm):
    co, t = dh["co"], dh["tri"]
    cen = co.mean(axis=0)
    worst = -np.inf
    convex_bad = 0
    for tri in t:
        a, b, c = co[tri]
        nrm = np.cross(b - a, c - a)
        nrm /= np.linalg.norm(nrm)
        if (a - cen) @ nrm < 0:
            nrm = -nrm
        worst = max(worst, float(((dm["co"] - a) @ nrm).max()))
        convex_bad += int((((co - a) @ nrm) > 1e-9).sum())
    return {"max_outside_mm": worst / MM, "hull_convexity_violations": convex_bad,
            "hull_verts": int(len(co)), "hull_tris": int(len(t))}


# ----------------------------------------------------------------------------------------- main
def main():
    report = {}
    for form, f in FORMS.items():
        fr = {}
        lods = {}
        for lvl in range(3):
            name = f"SM_Shuriken_{form}_LOD{lvl}"
            d2 = load("p2", name)
            d1 = load("p1", name)
            lods[lvl] = d2
            e = {}
            e["matrix_world_identity"] = bool(np.allclose(d2["matrix_world"], np.eye(4), atol=0, rtol=0))
            e["hygiene"] = hygiene(d2)
            hygiene(d1)
            lo, hi = f["bands"][lvl]
            e["triangles_in_band"] = {"triangles": e["hygiene"]["triangles"], "band": [lo, hi],
                                      "ok": lo <= e["hygiene"]["triangles"] <= hi}
            e["symmetry"] = symmetry(d2, form)
            e["silhouette_vs_pass1"] = silhouette(d1, d2)
            up, down = plan_area(d2)
            up1, _ = plan_area(d1)
            e["plan_area_mm2"] = {"pass2_up": up / MM ** 2, "pass2_down": down / MM ** 2, "pass1_up": up1 / MM ** 2}
            vol = e["hygiene"]["signed_volume_mm3"]
            e["mass_g"] = {"ground": vol * 1e-3 * DENSITY,
                           "outline_unground": up / MM ** 2 * f["t"] * 1e-3 * DENSITY,
                           "pass1_mesh": hygiene(d1)["signed_volume_mm3"] * 1e-3 * DENSITY}
            if "uv" in d2:
                e["uv"] = uv_checks(d2)
            e["shading"] = shading(d2, form)
            if f["kind"] == "star":
                rows, g = grind_star(d2, form)
                e["grind_parallel"] = facet_stats([r for r in rows if r[0] == "parallel"])
                e["grind_taper_plate_region"] = facet_stats([r for r in rows if r[0] == "taper" and r[4] and r[4].get("top") and not r[4]["top"]["roof"]])
                e["grind_taper_roof_region"] = facet_stats([r for r in rows if r[0] == "taper" and r[4] and r[4].get("top") and r[4]["top"]["roof"]])
                e["grind_runout"] = [(r[3], k_, s_, round(r[4]["land_mm"], 4) if r[4] and "land_mm" in r[4] else None,
                                      round(r[4]["top"]["angle_deg"], 3) if r[4] and r[4].get("top") else None,
                                      round(r[4]["top"]["width_mm"], 4) if r[4] and r[4].get("top") and r[4]["top"]["width_mm"] else None)
                                     for r in rows if r[0] == "runout" for k_, s_ in [(r[1], r[2])] if k_ == 0]
                e["grind_rows_arm0_plus"] = [(r[0], r[3], r[4]) for r in rows if r[1] == 0 and r[2] == 1]
                e["expected"] = {"grind_width_mm": g["w"] / MM, "x_apex_mm": g["x_apex"] / MM, "x_taper_mm": g["x_taper"] / MM,
                                 "x_run_mm": g["x_run"] / MM, "x_root0_mm": g["x_root0"] / MM}
                notch, hole = notch_and_hole_star(d2, form)
                e["notch_scallop"] = facet_stats([("n", 0, 0, 0, r) for r in notch])
                e["hole"] = facet_stats([("h", 0, 0, 0, r) for r in hole])
            else:
                rows, geo = grind_plate(d2, form)
                e["grind_sides"] = facet_stats(rows)
                e["grind_rows_side0"] = [(r[3], r[4]) for r in rows if r[1] == 0]
                e["hole"] = facet_stats([("h", 0, 0, 0, r) for r in hole_plate(d2, form)])
            e["tips"] = tips(d2, form)
            fr[f"LOD{lvl}"] = e
        # UV transfer LOD1/LOD2 from LOD0
        for lvl in (1, 2):
            fr[f"LOD{lvl}"]["uv_transfer_vs_lod0"] = uv_transfer(lods[0], lods[lvl])
        # hull
        dh = load("p2", f"UCX_SM_Shuriken_{form}_LOD0_00")
        fr["ucx"] = {f"LOD{l}": hull_check(dh, lods[l]) for l in range(3)}
        fr["ucx"]["matrix_world_identity"] = bool(np.allclose(dh["matrix_world"], np.eye(4), atol=0, rtol=0))
        fr["ucx"]["hygiene"] = {k: v for k, v in hygiene(dh).items() if k in ("boundary_edges", "non_manifold_edges", "signed_volume_mm3", "winding_inconsistent_edges")}
        report[form] = fr
    with open(f"{ROOT}/audit.json", "w") as fh:
        json.dump(report, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print("AUDIT DONE")


main()
