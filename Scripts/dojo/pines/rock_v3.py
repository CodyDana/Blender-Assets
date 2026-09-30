"""Pine D planting rock v3 (the stone study's method: STONE_BUILDING_STUDY.md 4.9, 8.3). bpy + numpy.

Owner (2026-09-30): 2-3 fused, rounded-but-fractured granite lobes at ~0.65 x the v2 rock's size relative to the
tree, lichen speckle, moss only in the crevices and on top, the shared library granite where it fits; the tree set
lower so its root plate spreads over the rock top; 8-12 roots hugging the faces and diving into the cracks.

Pipeline (study 4.9.2 / 4.9.5 a):
  lobes (joint families, per variant below)  ->  Scripts/vegetation/rock_sdf.sdf_rock (GN SDF: per-lobe opening,
  union, closing, fresh-fracture cutters, crack wedges, lip opening, Grid to Mesh threshold 0)  ->  dense source
  (~0.5 M tris) with masked meso noise and masks (moss / lichen / dirt in a colour attribute)  ->  decimated mid
  (the shipped Nanite mesh) + a moss-cushion shell on the mossy top  ->  unique UV0 (smart project, texel 5.12
  px/cm), UV1 = the full-tile packing  ->  bakes dense -> mid: normal (DirectX), mask (EMIT); AO on the mid  ->
  T_DKN_<V>_Rock_N / _ORM / _M.
Lobe sizes are in metres, read off the sheet's D panels (P4F/P4S for D1, P4Q/P4S for D2) at 0.65 x (owner) and
checked by silhouette IoU against the traced outlines scaled by the same 0.65 (SG15).
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

import rock_sdf as rs

ROCK_SCALE = 0.65          # owner: the rock at 60-70 % of the v2 rock's size relative to the tree

# ---------------------------------------------------------------------------------------------------- the plans
# Frame: x right, y back (the front camera looks +Y), z up, ground z = 0, 12 cm buried (study 3.10: set stones sink).
# Joint families: u (yaw) and v vertical, the sheeting plane on top (slope = dz/du, dz/dv); r = the lobe's opening.
PLANS = {
    # v2f (judge deltas 1-2, checked on the P4F / P4Q / P4S crops): ONE broad, rounded-angular boulder, wider
    # than tall, domed on the top shoulder, with the lobes FUSED (a crease and a crack where they meet, not a V
    # cleft between separate stones). v2 rock stage: near-vertical joint faces and flat sheeting tops read as
    # upright blocks, D2's back-right lobe as a separate standing slab. Changes: sheeting cut shallower (the
    # ellipsoid dome survives), joint faces less deep and battered more (sides lean in toward the top), the
    # lobes overlap more, the SDF closing radius 1.2 -> 5.5 cm (a fillet fuses the joins).
    # P4F / P4S: a big front-left block with a broad front face, a lower right block fused to it, a rounded crown
    # block behind them that the tree sits on
    "PineD1": dict(
        yaw=8.0, seed=4101, close_r=0.055,
        lobes=[dict(name="front_left", c=(-0.15, -0.05), a=0.55, b=0.38, top=1.00, slope=(0.14, 0.10), r=0.13,
                    facets=11, s_top=(0.94, 0.975), s_family=(0.82, 0.90), batter=16.0),
               dict(name="right", c=(0.34, 0.04), a=0.36, b=0.36, top=0.84, slope=(-0.30, 0.05), r=0.10,
                    facets=10, s_top=(0.93, 0.97), s_family=(0.82, 0.90), batter=16.0),
               dict(name="crown", c=(0.04, 0.12), a=0.42, b=0.31, top=1.06, bot=0.28, slope=(0.0, 0.0), r=0.12,
                    facets=9, s_top=(0.95, 0.98), s_family=(0.84, 0.92), batter=18.0)],
        # fresh fractures (crisper, after the lobes' opening): lobe, outward normal, share of the lobe span removed
        cutters=[(0, (-0.60, -0.62, 0.48), 0.07), (1, (0.72, -0.50, 0.25), 0.08), (2, (0.30, 0.55, 0.75), 0.05)],
        # cracks along the joint planes (the fused lobe joins read as creases)
        cracks=[dict(name="face", face="front", xz=[(-0.04, 0.80), (-0.17, 0.56), (-0.30, 0.32)], depth=0.10,
                     w=0.022),
                dict(name="back", face="back", xz=[(-0.10, 0.84), (-0.08, 0.56), (-0.12, 0.26)], depth=0.12,
                     w=0.026)],
    ),
    # P4Q / P4S: a broad front-left mass with a rounded face and a back-right block rising a little higher behind
    # it, fused into one rock; the tree stands on the top centre, over the mossy join
    "PineD2": dict(
        yaw=-12.0, seed=4202, close_r=0.055,
        lobes=[dict(name="front_left", c=(-0.22, -0.06), a=0.56, b=0.40, top=1.08, slope=(0.20, 0.08), r=0.12,
                    facets=11, s_top=(0.94, 0.975), s_family=(0.82, 0.90), batter=16.0),
               dict(name="back_right", c=(0.30, 0.14), a=0.44, b=0.40, top=1.16, slope=(-0.10, 0.0), r=0.10,
                    facets=11, s_top=(0.93, 0.97), s_family=(0.82, 0.90), batter=16.0)],
        cutters=[(0, (-0.55, -0.65, 0.50), 0.07), (1, (0.60, -0.40, 0.70), 0.06), (1, (0.70, -0.70, -0.05), 0.06)],
        cracks=[dict(name="face", face="front", xz=[(-0.30, 0.92), (-0.38, 0.66), (-0.46, 0.38)], depth=0.10,
                     w=0.022),
                dict(name="back", face="back", xz=[(0.34, 1.06), (0.38, 0.76), (0.34, 0.40)], depth=0.12,
                     w=0.026)],
    ),
}

VOXEL = 0.005
NOISE = [(0.004, 3.5), (0.0025, 9.0), (0.0012, 24.0)]      # meso octaves (amplitude m, frequency /m)
MID_TRIS = 90000
MID_VOXEL = 0.0115           # the shipped mid: ~1 cm quads (study 4.14: 1-2 cm on faces), ~100k tris


# ---------------------------------------------------------------------------------------------------- dense source

def _crack_paths(plan, lobe_pl, rng):
    """Crack polylines on the lobe surfaces: the planned key points, densified to about 4 cm steps with a small
    lateral wander (a joint crack is straight at the metre scale, ragged at the centimetre scale), widths tapering
    shut at both ends and depth tapering with them (l4: uniform saw-cut slots)."""
    paths = []
    for ck in plan["cracks"]:
        key = np.asarray(ck.get("xz", ck.get("xy")), float)
        seg = np.linalg.norm(np.diff(key, axis=0), axis=1)
        s_ = np.concatenate([[0], np.cumsum(seg)])
        n = max(4, int(s_[-1] / 0.04) + 1)
        ss = np.linspace(0, s_[-1], n)
        pts2 = np.stack([np.interp(ss, s_, key[:, 0]), np.interp(ss, s_, key[:, 1])], 1)
        tang = np.gradient(pts2, axis=0)
        nrm2 = np.stack([-tang[:, 1], tang[:, 0]], 1)
        nrm2 /= np.maximum(np.linalg.norm(nrm2, axis=1, keepdims=True), 1e-9)
        wander = np.cumsum(rng.normal(0, 0.004, n))
        wander -= np.linspace(wander[0], wander[-1], n)
        pts2 = pts2 + nrm2 * wander[:, None]
        pts = []
        if ck["face"] in ("front", "back"):
            sgn = -1.0 if ck["face"] == "front" else 1.0
            for x, z in pts2:
                p = rs.surface_point(lobe_pl, (x, sgn * 2.0, z), (0.0, -sgn, 0.0))
                if p is not None:
                    pts.append(p)
            m = np.array([0.0, sgn, 0.0])
        else:
            for x, y in pts2:
                p = rs.surface_point(lobe_pl, (x, y, 3.0), (0.0, 0.0, -1.0))
                if p is not None:
                    pts.append(p)
            m = np.array([0.0, 0.0, 1.0])
        if len(pts) >= 2:
            tt = np.linspace(0, 1, len(pts))
            prof = np.clip(np.sin(np.pi * tt) ** 0.6, 0.12, 1.0) * rng.uniform(0.8, 1.15, len(pts))
            paths.append(dict(name=ck["name"], pts=np.array(pts), m=m, depth=ck["depth"] * np.clip(prof, 0.3, 1),
                              w=ck["w"] * prof))
    return paths


def build_dense(vname: str, log=print) -> Dict:
    plan = PLANS[vname]
    rng = np.random.default_rng(plan["seed"])
    t0 = time.time()
    lobe_pl, lobes, lobe_V = [], [], []
    for L in plan["lobes"]:
        pl = rs.lobe_planes_rounded(L, plan["yaw"], rng)
        V = rs.corestone_points(L, plan["yaw"], pl)
        lobe_pl.append(pl)
        lobe_V.append(V)
        Vh, Fh = rs.hull_mesh(V)
        lobes.append((Vh, Fh, float(L["r"])))
    cutters = []
    for li, n, share in plan["cutters"]:
        pl, d = rs.cutter_planes(lobe_V[li], np.asarray(n, float), share)
        cutters.append(rs.hull_mesh(rs.polytope_vertices(pl)))
    paths = _crack_paths(plan, lobe_pl, rng)
    cracks = []
    for c in paths:
        for P in rs.crack_wedge(c["pts"], c["m"], c["depth"], c["w"]):
            cracks.append(rs.hull_mesh(P))
    V, F, sinfo = rs.sdf_rock(lobes, cutters, cracks, voxel=VOXEL, close_r=float(plan.get("close_r", 0.012)),
                              lip_r=0.012)
    log(f"[{vname}] rock SDF: {sinfo}")
    # masks and meso noise on the dense surface (study 4.9.2 step 6: mask the noise down on the arrises)
    E = rs.edges_of(F)
    N = rs.vertex_normals(V, F)
    H = rs.mean_curvature(V, F, E, N, n_smooth=4)
    arris = rs.smoothstep(H, 6.0, 22.0)                  # rounded arrises r 3.5-7 cm: H 14-28 /m
    cleft = rs.smoothstep(-H, 5.0, 25.0)
    disp = rs.fbm(V, NOISE, seed=plan["seed"]) * (1.0 - 0.75 * arris)
    # fracture relief: small stepped planar facets on the flat faces (granite grain breaks along planes)
    ridge = 1.0 - 2.0 * np.abs(rs.vnoise3(V * 11.0 + 3.1, plan["seed"] + 7))
    disp += 0.0016 * np.clip(ridge, -1, 1) * (1.0 - arris)
    V = V + N * disp[:, None]
    N = rs.vertex_normals(V, F)
    # secondary fracture facets (t7 vs the sheet: our faces were smooth where the sheet's granite is scaled into
    # 8-20 cm flakes with crisp little edges): Voronoi cells on the surface, each cut flat by the seed's tangent plane
    # set 0.3-1.6 cm inside; strongest on the rounded arrises (flaking), light on the broad joint faces
    frng = np.random.default_rng(plan["seed"] + 51)
    Ns = rs.smooth_field(N, E, 6)
    Ns /= np.maximum(np.linalg.norm(Ns, axis=1, keepdims=True), 1e-9)
    area = float(0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum())
    n_cells = int(area / (0.13 ** 2))
    seeds = frng.choice(len(V), n_cells, replace=False)
    kd = KDTree(n_cells)
    for k, i in enumerate(seeds):
        kd.insert(Vector(V[i]), k)
    kd.balance()
    cell = np.empty(len(V), np.int64)
    for j, p in enumerate(V):
        cell[j] = kd.find(p)[1]
    depth = frng.uniform(0.003, 0.016, n_cells)
    tilt = np.array([rs.jitter(Ns[i], 9.0, frng) for i in seeds])
    sp = V[seeds]
    dist = ((V - sp[cell]) * tilt[cell]).sum(1) + depth[cell]
    w = 0.30 + 0.70 * arris
    cut = np.clip(dist, 0.0, 0.03) * w
    # t9: cutting along each cell's own plane normal folded triangles at the cell borders (the mid's charts then
    # flipped in the unwrap): move along the vertex normal instead, lightly smoothed across the borders
    cut = rs.smooth_field(cut, E, 1)
    V = V - N * cut[:, None]
    N = rs.vertex_normals(V, F)
    # crack proximity (the wedges' polylines), lobe joins (two lobe polytopes both close)
    crack_d = np.full(len(V), 9.0)
    for c in paths:
        for A, B in zip(c["pts"][:-1], c["pts"][1:]):
            d, _ = rs.point_segment_dist(V, A, B)
            crack_d = np.minimum(crack_d, d)
    sd = np.stack([rs.plane_sdf(V, pl) for pl in lobe_pl], 1)
    sd.sort(1)
    join = rs.smoothstep(0.05 - sd[:, 1], 0.0, 0.04) if sd.shape[1] > 1 else np.zeros(len(V))
    top = float(V[:, 2].max())
    info = {"sdf": sinfo, "lobes": len(lobes), "cutters": len(cutters), "cracks": [c["name"] for c in paths],
            "arris_r_m": [float(L["r"]) for L in plan["lobes"]], "seconds": round(time.time() - t0, 1)}
    return dict(V=V, F=F, N=N, H=H, arris=arris, cleft=cleft, crack_d=crack_d, join=join, top=top,
                lobe_pl=lobe_pl, lobe_V=lobe_V, paths=paths, info=info, plan=plan)


def masks(D, seed):
    """Per-vertex masks on the dense surface (study 4.11): R moss (top + crevices, never overhangs), G lichen
    (round patches and specks on exposed faces), B dirt (the foot). Returns (n, 3) floats and the top-moss field
    that the cushion shell follows."""
    V, N = D["V"], D["N"]
    nz = N[:, 2]
    z = V[:, 2]
    top = D["top"]
    brk = 0.5 + 0.5 * rs.fbm(V, [(0.65, 5.0), (0.35, 13.0)], seed + 11)
    brk2 = 0.5 + 0.5 * rs.fbm(V, [(0.6, 9.0), (0.4, 23.0)], seed + 12)
    # v2f (judge delta 1, P4F/P4Q: a thick moss cap on the top shoulder running down the clefts): wider top zone,
    # lower normal threshold, less breakup (v2 rock stage: 17 % moss, mostly hidden under the trunk base)
    # (l15 close-up: the lower zone made flat olive stains down the faces; the cap stays on the top shoulder)
    top_zone = rs.smoothstep(z, 0.50 * top, 0.70 * top)
    moss_top = rs.smoothstep(nz, 0.30, 0.60) * top_zone * rs.smoothstep(brk, 0.18, 0.32)
    crev = np.maximum(rs.smoothstep(0.045 - D["crack_d"], 0.0, 0.03), 0.8 * D["cleft"] * D["join"])
    crev = np.maximum(crev, 0.7 * rs.smoothstep(D["cleft"], 0.4, 0.9))
    moss_crev = crev * rs.smoothstep(nz, -0.15, 0.15) * rs.smoothstep(brk2, 0.30, 0.45) * rs.smoothstep(z, 0.04, 0.2)
    moss = np.clip(np.maximum(moss_top, moss_crev), 0, 1)
    # lichen: round patches 2-12 cm (Voronoi seeds) + fine specks, on exposed faces only
    rng = np.random.default_rng(seed + 21)
    area = 7.0
    ns = int(area * 420)
    idx = rng.choice(len(V), ns, replace=False)
    kd = KDTree(ns)
    for k, i in enumerate(idx):
        kd.insert(Vector(V[i]), k)
    kd.balance()
    rad = rng.uniform(0.004, 0.015, ns) * np.where(rng.uniform(size=ns) < 0.08, 2.0, 1.0)   # 0.8-3 cm specks
    d = np.empty(len(V))
    who = np.empty(len(V), np.int64)
    for j, p in enumerate(V):
        _, k, dd = kd.find(p)
        d[j] = dd
        who[j] = k
    edge_n = 0.5 + 0.5 * rs.vnoise3(V * 60.0, seed + 23)
    patch = rs.smoothstep(rad[who] * (0.75 + 0.5 * edge_n) - d, 0.0, 0.003)
    speck = rs.smoothstep(rs.vnoise3(V * 85.0, seed + 24), 0.55, 0.75)
    exposed = rs.smoothstep(nz, -0.45, -0.1) * (1.0 - D["cleft"]) * rs.smoothstep(z, 0.08, 0.3)
    # clustered (t2: an even polka-dot 'terrazzo', study S10): the sheet's specks gather in patches on the faces
    cluster = rs.smoothstep(0.5 + 0.5 * rs.fbm(V, [(0.7, 2.2), (0.3, 6.0)], seed + 25), 0.34, 0.50)
    lichen = np.clip(np.maximum(patch, 0.8 * speck) * cluster * exposed * (1.0 - moss), 0, 1)
    dirt = rs.smoothstep(0.22 - z, 0.0, 0.22) * (0.6 + 0.4 * brk)
    return np.stack([moss, lichen, dirt], 1), moss_top


# ---------------------------------------------------------------------------------------------------- blender side

def make_obj(name, V, F, coll, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(map(int, f)) for f in F])
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def mesh_arrays(ob):
    """(V, F) of a mesh object, triangulated on a bmesh copy (the object is not changed)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts], float)
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def remesh(ob, voxel):
    md = ob.modifiers.new("remesh", "REMESH")
    md.mode = "VOXEL"
    md.voxel_size = voxel
    md.adaptivity = 0.0
    md.use_smooth_shade = True
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def decimate(ob, target_tris):
    n = len(ob.data.polygons)
    md = ob.modifiers.new("dec", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = min(1.0, target_tris / max(n, 1))
    md.use_collapse_triangulate = True
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def cushion_shell(Vm, Fm, moss_top_m, seed, h=(0.008, 0.040)):
    """Moss cushions on the mossy top (the sheet's thick green cushions): the mid's faces where the top-moss field
    is high, lifted along the normal by a lumpy height that fades to 2 mm under the rock at the shell's rim."""
    sel = (moss_top_m[Fm] > 0.35).all(1)
    if sel.sum() < 20:
        return None
    Fs = Fm[sel]
    used = np.unique(Fs)
    remap = -np.ones(len(Vm), np.int64)
    remap[used] = np.arange(len(used))
    F2 = remap[Fs]
    V2 = Vm[used].copy()
    N2 = rs.vertex_normals(Vm, Fm)[used]
    E2 = rs.edges_of(F2)
    # rim = vertices on a boundary edge of the selection
    Eall = np.vstack([F2[:, [0, 1]], F2[:, [1, 2]], F2[:, [2, 0]]])
    Eall.sort(1)
    u, cnt = np.unique(Eall, axis=0, return_counts=True)
    rim = np.zeros(len(V2), bool)
    rim[u[cnt == 1].ravel()] = True
    # distance to the rim in rings (0 at the rim) -> a soft rise over the first ~4 cm
    ring = np.where(rim, 0.0, 9.0)
    for _ in range(12):
        nb = np.full(len(V2), 9.0)
        np.minimum.at(nb, E2[:, 0], ring[E2[:, 1]])
        np.minimum.at(nb, E2[:, 1], ring[E2[:, 0]])
        ring = np.minimum(ring, nb + 1.0)
    el = float(np.median(np.linalg.norm(V2[E2[:, 0]] - V2[E2[:, 1]], axis=1)))
    rise = rs.smoothstep(ring * el, 0.0, 0.045)
    rng = np.random.default_rng(seed)
    # lumps: gaussian cushions 4-9 cm across
    lump = np.zeros(len(V2))
    cs = V2[rng.choice(len(V2), max(8, len(V2) // 60), replace=False)]
    for c in cs:
        s = rng.uniform(0.02, 0.045)
        lump += np.exp(-((V2 - c) ** 2).sum(1) / (2 * s * s)) * rng.uniform(0.5, 1.0)
    lump = np.clip(lump, 0, 1.4) / 1.4
    fine = 0.5 + 0.5 * rs.vnoise3(V2 * 70.0, seed + 3)
    hh = (h[0] + (h[1] - h[0]) * (0.6 * lump + 0.25 * fine + 0.15 * moss_top_m[used])) * rise - 0.002 * (1 - rise)
    hh = np.where(hh >= 0, np.maximum(hh, 0.0015), np.minimum(hh, -0.0015))   # never on the rock (qa coincident)
    V2 = V2 + N2 * hh[:, None]
    return V2, F2, float(hh.max())


def smart_uv(ob, margin=0.004, angle=66.0):
    """Smart project (it packs the islands itself; the concave pack_islands is too slow on a 100k mid)."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, shape_method="AABB", margin_method="FRACTION", margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def overlap_faces(tris, eps=1e-6):
    """Face indices in overlapping UV triangle pairs (the qa_check SAT test, returning the pairs)."""
    from itertools import combinations
    from collections import defaultdict
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    keep = np.nonzero(np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 1e-12)[0]
    T = tris[keep]
    mins, maxs = T.min(1), T.max(1)
    cell = max(float(np.median(maxs - mins)) * 2.0, 1e-4)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    buckets = defaultdict(list)
    for i in range(len(T)):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                buckets[(cx, cy)].append(i)
    pairs = set()
    for m in buckets.values():
        if len(m) > 1:
            pairs.update(combinations(m, 2))
    if not pairs:
        return []
    P = np.array(sorted(pairs))
    A, B = T[P[:, 0]], T[P[:, 1]]
    sep = np.any(maxs[P[:, 0]] <= mins[P[:, 1]] + eps, 1) | np.any(maxs[P[:, 1]] <= mins[P[:, 0]] + eps, 1)
    for tri in (A, B):
        for k in range(3):
            ed = tri[:, (k + 1) % 3] - tri[:, k]
            ax = np.stack([-ed[:, 1], ed[:, 0]], -1)
            ax = ax / np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-12)
            pa = np.einsum("pij,pj->pi", A, ax)
            pb = np.einsum("pij,pj->pi", B, ax)
            sep |= (pa.max(1) <= pb.min(1) + eps) | (pb.max(1) <= pa.min(1) + eps)
    bad = P[~sep]
    return sorted(set(keep[bad.ravel()].tolist()))


def unwrap_with_seams(ob, bad_faces, margin=0.004):
    me = ob.data
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.seams_from_islands()
    bpy.ops.object.mode_set(mode="OBJECT")
    bad = set(bad_faces)
    ek_bad = {ek for p in me.polygons if p.index in bad for ek in p.edge_keys}
    for e in me.edges:
        if e.key in ek_bad:
            e.use_seam = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()          # ABF sizes each island on its own: restore one texel density
    bpy.ops.uv.pack_islands(rotate=True, shape_method="AABB", margin_method="FRACTION", margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def repack(ob, margin):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, shape_method="AABB", margin_method="ADD", margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


BOX6 = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
DIR26 = np.array([[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)],
                 float)
DIR26 /= np.linalg.norm(DIR26, axis=1, keepdims=True)


def _face_adjacency(me):
    E = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            E.setdefault(ek, []).append(p.index)
    return E


def _components(n, E, labels):
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for fs in E.values():
        if len(fs) == 2 and labels[fs[0]] == labels[fs[1]]:
            a, b = find(fs[0]), find(fs[1])
            if a != b:
                parent[a] = b
    return np.array([find(i) for i in range(n)])


def chart_labels(me, k=6, smooth_iter=40, min_faces=60):
    """Face labels = the box direction nearest to the face's SMOOTHED normal (vertex normals averaged over
    ``smooth_iter`` rings), with small connected pieces merged into their neighbours."""
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    F = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", F)
    F = F.reshape(-1, 3)
    N = rs.vertex_normals(V, F)
    E = rs.edges_of(F)
    N = rs.smooth_field(N, E, smooth_iter)
    fn = N[F].mean(1)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    labels = np.argmax(fn @ BOX6.T, 1)
    return merge_small(me, labels, min_faces)


def merge_small(me, labels, min_faces):
    labels = labels.copy()
    E = _face_adjacency(me)
    nb = {}
    for fs in E.values():
        if len(fs) == 2:
            nb.setdefault(fs[0], []).append(fs[1])
            nb.setdefault(fs[1], []).append(fs[0])
    for _ in range(6):
        comp = _components(len(labels), E, labels)
        ids, cnt = np.unique(comp, return_counts=True)
        small = set(ids[cnt < min_faces].tolist())
        if not small:
            break
        changed = False
        for f in range(len(labels)):
            if comp[f] in small:
                votes = [labels[g] for g in nb.get(f, []) if comp[g] != comp[f]]
                if votes:
                    labels[f] = max(set(votes), key=votes.count)
                    changed = True
        if not changed:
            break
    return labels


def split_charts(me, labels, bad, rnd):
    """Charts holding overlapping faces get re-labelled by the 26 directions (finer, still smooth-normal based)."""
    E = _face_adjacency(me)
    comp = _components(len(labels), E, labels)
    bad_comps = {comp[f] for f in bad}
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    F = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", F)
    F = F.reshape(-1, 3)
    N = rs.smooth_field(rs.vertex_normals(V, F), rs.edges_of(F), max(8, 30 - 10 * rnd))
    fn = N[F].mean(1)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    fine = 100 * (rnd + 1) + np.argmax(fn @ DIR26.T, 1)
    m = np.isin(comp, list(bad_comps))
    out = labels.copy()
    out[m] = fine[m] + 1000 * comp[m] % 7919
    return merge_small(me, out, 30)


def unwrap_charts(ob, labels, margin=0.0015):
    me = ob.data
    E = _face_adjacency(me)
    ek_seam = {ek for ek, fs in E.items() if len(fs) == 2 and labels[fs[0]] != labels[fs[1]]}
    for e in me.edges:
        e.use_seam = e.key in ek_seam
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, shape_method="CONCAVE", margin_method="ADD", margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    return int(len(np.unique(_components(len(labels), E, labels))))


def uv_arrays(me, name):
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[name].data.foreach_get("uv", uv)
    return uv.reshape(-1, 2)


def poly_area_uv(me, uv):
    tot = 0.0
    for p in me.polygons:
        li = list(p.loop_indices)
        q = uv[li]
        x, y = q[:, 0], q[:, 1]
        tot += 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    return tot


def bake(target, sources, img, kind, samples=4, extrusion=0.012, ray=0.03, margin=16):
    """Selected-to-active bake (NORMAL or EMIT) from ``sources`` onto ``target``'s active UV into ``img``."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.device = "CPU"
    mats = [s.material for s in target.material_slots if s.material]
    nodes = []
    for m in mats:
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        for o in m.node_tree.nodes:
            o.select = False
        n.select = True
        m.node_tree.nodes.active = n
        nodes.append((m, n))
    b = sc.render.bake
    b.margin = margin
    b.margin_type = "EXTEND"
    b.use_selected_to_active = True
    b.use_cage = False
    b.cage_extrusion = extrusion
    b.max_ray_distance = ray
    b.normal_space = "TANGENT"
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for s in sources:
        s.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    with bpy.context.temp_override(object=target, active_object=target,
                                   selected_objects=list(sources) + [target], selected_editable_objects=list(sources) + [target]):
        res = bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=extrusion,
                                  max_ray_distance=ray, margin=margin, margin_type="EXTEND", use_clear=False)
    for m, n in nodes:
        m.node_tree.nodes.remove(n)
    if "FINISHED" not in res:
        raise RuntimeError(f"{kind} bake failed: {res}")


def new_image(name, size, fill, alpha=False, data=True):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    im = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=False, is_data=data)
    im.colorspace_settings.name = "Non-Color" if data else "sRGB"
    im.pixels.foreach_set(np.tile(np.array(fill, np.float32), size * size))
    return im


def emit_material(name, attr):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = attr
    at.attribute_type = "GEOMETRY"
    nt.links.new(at.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def set_point_colour(ob, name, cols):
    me = ob.data
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    ca = me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    c4 = np.concatenate([np.clip(cols, 0, 1), np.ones((len(cols), 1))], 1).astype(np.float32)
    ca.data.foreach_set("color", c4.ravel())


def sample_nearest(src_V, dst_V, values):
    kd = KDTree(len(src_V))
    for i, p in enumerate(src_V):
        kd.insert(Vector(p), i)
    kd.balance()
    out = np.empty((len(dst_V),) + values.shape[1:])
    for j, p in enumerate(dst_V):
        _, i, _ = kd.find(p)
        out[j] = values[i]
    return out


# ---------------------------------------------------------------------------------------------------- measures

def plane_fraction(V, F, lobe_pl, ang=15.0, dist=0.02):
    """SG14: share of the surface area within ``ang`` of, and within ``dist`` of, a lobe plane (the joint faces)."""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    a = 0.5 * np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(2 * a[:, None], 1e-12)
    fc = V[F].mean(1)
    hit = np.zeros(len(F), bool)
    ca = math.cos(math.radians(ang))
    for pl in lobe_pl:
        for n, d in pl:
            if n[2] < -0.9:
                continue
            hit |= ((fn @ n) > ca) & (np.abs(fc @ n - d) < dist)
    above = fc[:, 2] > 0.02
    return float(a[hit & above].sum() / max(a[above].sum(), 1e-9))


def sharp_crease_share(V, F, deg=30.0):
    """SG14: share of edges whose dihedral deviation is over ``deg`` (sharper than 180 - deg)."""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    fid = np.tile(np.arange(len(F)), 3)
    key = np.sort(E, 1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    ks = key[order]
    same = (ks[1:] == ks[:-1]).all(1)
    f1 = fid[order][:-1][same]
    f2 = fid[order][1:][same]
    cosd = (fn[f1] * fn[f2]).sum(1)
    return float((cosd < math.cos(math.radians(deg))).mean())


# ---------------------------------------------------------------------------------------------------- the asset

def build_rock_v3(vname, coll, tex_dir: Path, work_dir: Path, make_materials, size=2048, ao_samples=64, texel=5.4,
                  log=print):
    """Build SM_DKN_<V>_Rock (v3). ``make_materials(vname, S_m_per_uv, paths)`` returns (rock_mat, moss_mat).
    Returns (obj, info, extra) with extra = lobe hull points (UCX), crease / crack attractors for the roots, BVH
    geometry of the bare rock (no cushions) for the root walk."""
    t0 = time.time()
    plan = PLANS[vname]
    D = build_dense(vname, log)
    M, moss_top = masks(D, plan["seed"])
    dense = make_obj(f"__{vname}_RockDense", D["V"], D["F"], coll)
    set_point_colour(dense, "Mask", M)
    # ---- mid (the shipped Nanite mesh): decimated from the dense source
    mid0 = make_obj(f"__{vname}_RockMid", D["V"], D["F"], coll)
    remesh(mid0, MID_VOXEL)   # t9: collapse decimation left slivers and folds the unwrap flipped; voxel remesh is clean
    Vm, Fm = mesh_arrays(mid0)
    Ns_m = rs.smooth_field(rs.vertex_normals(Vm, Fm), rs.edges_of(Fm), 20)
    fn_m = np.cross(Vm[Fm[:, 1]] - Vm[Fm[:, 0]], Vm[Fm[:, 2]] - Vm[Fm[:, 0]])
    folded = int(((fn_m * Ns_m[Fm].mean(1)).sum(1) < 0).sum())
    log(f"[{vname}] rock mid: {len(Fm)} tris, {folded} faces against the smoothed normal")
    d0 = mid0.data
    bpy.data.objects.remove(mid0)
    bpy.data.meshes.remove(d0)
    fields = np.column_stack([M, moss_top, D["arris"], D["cleft"], D["join"], np.minimum(D["crack_d"], 1.0)])
    Fm_fields = sample_nearest(D["V"], Vm, fields)
    Mm, moss_top_m, arris_m, cleft_m, join_m, crack_m = (Fm_fields[:, :3], Fm_fields[:, 3], Fm_fields[:, 4],
                                                         Fm_fields[:, 5], Fm_fields[:, 6], Fm_fields[:, 7])
    shell = cushion_shell(Vm, Fm, moss_top_m, plan["seed"] + 5)
    V_all, F_all, mat_idx = Vm, Fm, np.zeros(len(Fm), np.int32)
    shell_tris = 0
    if shell is not None:
        V2, F2, hmax = shell
        V_all = np.vstack([Vm, V2])
        F_all = np.vstack([Fm, F2 + len(Vm)])
        mat_idx = np.concatenate([mat_idx, np.ones(len(F2), np.int32)])
        shell_tris = int(len(F2))
    ob = make_obj(f"SM_DKN_{vname}_Rock", V_all, F_all, coll)
    me = ob.data
    me.polygons.foreach_set("material_index", mat_idx)
    # 'Wear' corner colours read by the library granite (R grime, G edge wear, B ground dirt; POINT colours)
    n_sh = len(V_all) - len(Vm)
    # grime: the clefts and cracks, plus a weathering mottle (the sheet's faces carry darker grey-brown patches at a
    # 10-30 cm scale; t3 read flat and uniform)
    mott = rs.smoothstep(0.5 + 0.5 * rs.fbm(Vm, [(0.6, 3.5), (0.3, 9.0), (0.1, 25.0)], plan["seed"] + 31), 0.45, 0.75)
    grime = np.clip(0.55 * cleft_m + 0.45 * join_m + 0.6 * rs.smoothstep(0.03 - crack_m, 0, 0.03) + 0.75 * mott,
                    0, 1)
    light = rs.smoothstep(0.5 + 0.5 * rs.fbm(Vm, [(0.6, 3.0), (0.3, 8.0), (0.1, 22.0)], plan["seed"] + 37), 0.55, 0.80)
    wear = np.column_stack([grime, np.maximum(0.8 * arris_m, 0.7 * light), Mm[:, 2]])
    wear = np.vstack([wear, np.tile([[0.5, 0.0, 0.0]], (n_sh, 1))])
    set_point_colour(ob, "Wear", wear)
    # ---- UVs: unique UV0 (smart project + pack), UV1 = that full-tile packing, UV0 scaled to the house texel
    me.uv_layers.new(name="UVMap")
    # smart project folds concave clefts onto themselves at a wide angle limit (build 1: 53-163 overlapping pairs):
    # retry with tighter limits until the qa_check overlap test is clean
    from pipeline.qa_check import uv_overlap_sat
    # few, big charts (study 4.9.5 / 4.14: rounded rocks want one or few charts; t9's smart project on the faceted
    # mid made 12.5k islands): faces are grouped by their SMOOTHED normal into box directions, connected charts
    # are unwrapped angle-based with seams at the chart borders, and any chart that still folds is split finer
    uv_tries = []
    labels = chart_labels(me, 6)
    for rnd in range(4):
        n_charts = unwrap_charts(ob, labels)
        uvt = uv_arrays(me, "UVMap")
        bad = overlap_faces(uvt.reshape(-1, 3, 2))
        uv_tries.append((f"charts{rnd}", n_charts, len(bad)))
        if not bad:
            break
        if len(bad) <= 60:
            # a handful of pinched faces: each becomes its own tiny chart (a lone triangle never folds)
            labels = labels.copy()
            labels[np.asarray(bad)] = 10 ** 6 + np.asarray(bad)
        else:
            labels = split_charts(me, labels, set(bad), rnd)
    ov = int(uv_overlap_sat(uvt.reshape(-1, 3, 2)))
    uv_tries.append(("final_sat", ov))
    log(f"[{vname}] rock UV (round, charts, overlapping faces): {uv_tries}")
    if ov:
        raise RuntimeError(f"{vname} rock UV0 overlaps: {ov}")
    me.uv_layers.new(name="UV1", do_init=True)
    uv = uv_arrays(me, "UVMap")
    area_uv = poly_area_uv(me, uv)
    area_m = float(sum(p.area for p in me.polygons))
    target_uv = (texel * 100.0 / size) ** 2 * area_m
    k = math.sqrt(target_uv / max(area_uv, 1e-9))
    k = min(k, 1.0)                                    # never above the full packing (the texel then falls short)
    me.uv_layers["UVMap"].data.foreach_set("uv", (uv * k).ravel())
    me.uv_layers.active = me.uv_layers["UVMap"]
    S = math.sqrt(area_m / (area_uv * k * k))                      # metres per UV0 unit (all charts one scale)
    # ---- bakes (only the dense and the mid render; every other object is hidden)
    hidden = [o for o in bpy.data.objects if o not in (ob, dense) and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    tmp = bpy.data.materials.new("__rock_bake")
    tmp.use_nodes = True
    me.materials.append(tmp)
    me.materials.append(tmp)
    dense.data.materials.append(emit_material("__rock_mask_emit", "Mask"))
    tb = time.time()
    img_n = new_image(f"T_DKN_{vname}_Rock_N_gl", size, (0.5, 0.5, 1.0, 1.0))
    bake(ob, [dense], img_n, "NORMAL")
    img_m = new_image(f"T_DKN_{vname}_Rock_M", size, (0.0, 0.0, 0.0, 1.0))
    bake(ob, [dense], img_m, "EMIT")
    dense.hide_render = True
    from pipeline import textures
    ao = textures.bake_ao(ob, f"__{vname}_rock_ao", size=size, samples=ao_samples, margin=16)
    t_bake = round(time.time() - tb, 1)
    for o in hidden:
        o.hide_render = False
    # ---- write the maps
    tex_dir.mkdir(parents=True, exist_ok=True)
    gl_path = Path(work_dir) / f"{vname}_rock_N_gl.png"
    gl_path.parent.mkdir(parents=True, exist_ok=True)
    npx = textures.image_pixels(img_n)
    textures.write_png(npx, gl_path)
    n_path = tex_dir / f"T_DKN_{vname}_Rock_N.png"
    textures.flip_normal_green(gl_path, n_path)
    mpx = textures.image_pixels(img_m)
    m_path = tex_dir / f"T_DKN_{vname}_Rock_M.png"
    textures.write_png(mpx, m_path)
    rough = bpy.data.images.new(f"__{vname}_rock_rough", size, size, alpha=False, float_buffer=False, is_data=True)
    rp = np.ones((size, size, 4), np.float32)
    rp[..., 0] = rp[..., 1] = rp[..., 2] = np.clip(0.80 + 0.14 * mpx[..., 0], 0, 1)
    rough.pixels.foreach_set(rp.ravel())
    orm_path = tex_dir / f"T_DKN_{vname}_Rock_ORM.png"
    textures.pack_orm(ao, rough, None, orm_path)
    aopx = textures.image_pixels(ao)[..., 0]
    for im in (img_n, img_m, ao, rough):
        bpy.data.images.remove(im)
    me.materials.clear()
    bpy.data.materials.remove(tmp)
    rock_mat, moss_mat = make_materials(vname, S, {"N": n_path, "ORM": orm_path, "M": m_path})
    me.materials.append(rock_mat)
    me.materials.append(moss_mat)
    # ---- root attractors: lobe joins (the V clefts) and the cracks, on the bare dense surface
    V, N = D["V"], D["N"]
    att = (D["join"] > 0.55) | (D["crack_d"] < 0.012)
    idx = np.nonzero(att)[0][::6]
    extra = {"lobe_V": D["lobe_V"], "attract": V[idx], "attract_n": N[idx], "bare_V": Vm, "bare_F": Fm,
             "paths": [p["pts"] for p in D["paths"]]}
    # ---- measures (SG14 on the dense source; the mid follows it within the decimation error)
    info = dict(D["info"])
    covered = aopx > 0.02                                   # the UV-covered texels
    info.update({"tris": int(len(F_all)), "rock_tris": int(len(Fm)), "cushion_tris": shell_tris,
                 "dense_tris": int(len(D["F"])), "verts_per_tri": round(len(V_all) / max(len(F_all), 1), 3),
                 "uv_tries": uv_tries, "uv0_scale_k": round(k, 4), "uv0_fill_packed": round(area_uv, 4),
                 "texel_px_cm": round(math.sqrt(area_uv * k * k / area_m) * size / 100.0, 3), "m_per_uv0": round(S, 4), "texel_target_px_cm": texel,
                 "map_px": size, "bake_s": t_bake,
                 "plane_fraction": round(plane_fraction(D["V"], D["F"], D["lobe_pl"]), 3),
                 "sharp_crease_share": round(sharp_crease_share(D["V"], D["F"]), 4),
                 "arris_r_share_of_short_axis": [round(float(L["r"]) / (2 * min(L["a"], L["b"])), 3)
                                                 for L in plan["lobes"]],
                 "moss_share_area": round(float(np.mean(Mm[:, 0] > 0.5)), 3),
                 "lichen_share": round(float(np.mean(Mm[:, 1] > 0.5)), 3),
                 "ao_p50": round(float(np.median(aopx[covered])), 3) if covered.any() else None,
                 "bbox": [np.round(V_all.min(0), 3).tolist(), np.round(V_all.max(0), 3).tolist()]})
    bpy.data.objects.remove(dense)
    for m in [m for m in bpy.data.materials if m.name.startswith("__rock_mask_emit")]:
        bpy.data.materials.remove(m)
    info["seconds"] = round(time.time() - t0, 1)
    log(f"[{vname}] rock v3: {info}")
    return ob, info, extra
