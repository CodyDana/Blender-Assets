"""Independent fit check (Blender headless, numpy + mathutils only) on geometry READ BACK FROM UNREAL.

Inputs (both written by ivb_verify.py in a fresh Unreal process):
  ivB_geometry.json  per-LOD source positions + triangles of both meshes (cm, Unreal frame)
  ivB_verify.json    attach.sword_to_sheath_basis: the sword->sheath-local affine map Unreal produced after
                     attach_to_component(Holster, SNAP_TO_TARGET) with the sheath at a non-identity world transform;
                     attach.mouth_socket (the draw axis)
For all 9 LOD pairings: triangle-triangle intersections; every sword vertex past the mouth plane (plus dense random
surface samples) must be in the empty cavity (even ray parity in 4 lateral directions, enclosed laterally and toward
the chape); clearance = distance to the sheath surface; the hilt side must be outside the sheath material; and a straight
draw along the Mouth socket's -Z must stay intersection-free.
Also compares Unreal's own FBX export (collision) with the shipped FBX's UCX hulls.
"""
import bpy, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep")
EXP = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\SnowFlower\v4")
geo = json.loads((HERE / "ivB_geometry.json").read_text())
B = json.loads((HERE / "ivB_verify.json").read_text())
att = B["attach"]
bas = att["sword_to_sheath_basis"]
o = np.array(bas["o"]); X = np.array(bas["x"]) - o; Y = np.array(bas["y"]) - o; Z = np.array(bas["z"]) - o
M = np.stack([X, Y, Z], axis=1)  # columns
mouth_p = np.array(att["mouth_socket"]["t"]); mouth_n = np.array(att["mouth_socket"]["z_axis"])
mouth_n = mouth_n / np.linalg.norm(mouth_n)
res = {"affine_orthonormal_err": float(np.abs(M.T @ M - np.eye(3)).max()), "det": float(np.linalg.det(M)),
       "tilt_deg_from_sheath_z": math.degrees(math.acos(min(1.0, float(Z @ np.array([0, 0, 1]))))),}


def to_sheath(P):
    return P @ M.T + o


def bvh(P, T):
    return BVHTree.FromPolygons([tuple(p) for p in P], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def hits_along(tree, p, d, maxd=500.0):
    n = 0
    origin = Vector(p); dirv = Vector(d)
    travelled = 0.0
    while travelled < maxd and n < 64:
        loc, nor, idx, dist = tree.ray_cast(origin, dirv, maxd - travelled)
        if loc is None:
            break
        n += 1
        step = dist + 1e-4
        origin = origin + dirv * step
        travelled += step
    return n


DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0)}


def classify(tree, pts):
    """per point: lateral hit counts; in_cavity = all 4 lateral directions hit >=2 and even and chape direction hits."""
    out = []
    for p in pts:
        c = {k: hits_along(tree, p, d) for k, d in DIRS.items()}
        c["+n"] = hits_along(tree, p, tuple(mouth_n))
        out.append(c)
    return out


def sample_surface(P, T, n, rng):
    A = P[T[:, 0]]; Bq = P[T[:, 1]]; C = P[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(Bq - A, C - A), axis=1)
    idx = rng.choice(len(T), size=n, p=area / area.sum())
    u = rng.random(n); v = rng.random(n)
    f = u + v > 1
    u[f] = 1 - u[f]; v[f] = 1 - v[f]
    return A[idx] + (Bq[idx] - A[idx]) * u[:, None] + (C[idx] - A[idx]) * v[:, None]


rng = np.random.default_rng(12345)
def lod_arrays(l):
    P = np.array(l["positions"]); T = np.array(l["triangles"])[:, -3:]  # UE returns (?, ?, ?, v0, v1, v2); keep the vertex ids
    assert T.max() < len(P) and T.min() >= 0
    e = max(np.linalg.norm(P[T[:, a]] - P[T[:, b]], axis=1).max() for a, b in ((0, 1), (1, 2), (2, 0)))
    return P, T, float(e)
sheath_lods, sword_lods = [], []
res["max_edge_cm"] = {}
for tag, dst in (("sheath", sheath_lods), ("sword", sword_lods)):
    for i, l in enumerate(geo[tag]):
        P, T, e = lod_arrays(l)
        dst.append((P, T))
        res["max_edge_cm"][f"{tag}_LOD{i}"] = e
sheath_trees = [bvh(P, T) for P, T in sheath_lods]
pairs = {}
for j, (Pw, Tw) in enumerate(sword_lods):
    Ps = to_sheath(Pw)
    sw_tree = bvh(Ps, Tw)
    depth = (Ps - mouth_p) @ mouth_n
    inside_idx = np.where(depth > 0)[0]
    hilt_idx = np.where(depth <= 0)[0]
    # dense samples on the part of the sword surface past the mouth plane
    S = sample_surface(Ps, Tw, 60000 if j == 0 else 20000, rng)
    S = S[((S - mouth_p) @ mouth_n) > 0]
    for k, tree in enumerate(sheath_trees):
        r = {}
        ov = tree.overlap(sw_tree)
        r["tri_tri_intersections"] = len(ov)
        pts_in = Ps[inside_idx]
        cls = classify(tree, pts_in)
        ok = [all(c[d] >= 1 and c[d] % 2 == 0 for d in DIRS) and c["+n"] >= 1 and c["+n"] % 2 == 0 for c in cls]
        r["vertices_past_mouth"] = int(len(inside_idx))
        r["vertices_past_mouth_in_cavity"] = int(sum(ok))
        bad = [i for i, g in enumerate(ok) if not g][:5]
        r["bad_examples"] = [{"p": pts_in[i].round(4).tolist(), "hits": cls[i]} for i in bad]
        dist = np.array([tree.find_nearest(Vector(p))[3] for p in pts_in])
        r["min_clearance_vertices_mm"] = float(dist.min() * 10)
        r["p1_clearance_vertices_mm"] = float(np.percentile(dist, 1) * 10)
        # samples
        Ssub = S if k == 0 else S[: len(S) // 3]
        cls_s = classify(tree, Ssub)
        ok_s = [all(c[d] >= 1 and c[d] % 2 == 0 for d in DIRS) and c["+n"] >= 1 and c["+n"] % 2 == 0 for c in cls_s]
        dist_s = np.array([tree.find_nearest(Vector(p))[3] for p in Ssub])
        r["surface_samples_past_mouth"] = int(len(Ssub))
        r["surface_samples_in_cavity"] = int(sum(ok_s))
        r["min_clearance_samples_mm"] = float(dist_s.min() * 10)
        # hilt side: must not be inside the sheath material (odd parity along +x AND -x)
        cls_h = classify(tree, Ps[hilt_idx])
        in_mat = [(c["+x"] % 2 == 1 and c["-x"] % 2 == 1) for c in cls_h]
        r["hilt_vertices"] = int(len(hilt_idx))
        r["hilt_vertices_inside_sheath_material"] = int(sum(in_mat))
        dh = np.array([tree.find_nearest(Vector(p))[3] for p in Ps[hilt_idx]])
        r["hilt_min_gap_mm"] = float(dh.min() * 10)
        # deepest point: tip vs sheath end
        tip = Ps[np.argmax(depth)]
        r["deepest_sword_point"] = tip.round(4).tolist()
        r["deepest_depth_past_mouth_cm"] = float(depth.max())
        pairs[f"sword_LOD{j}_in_sheath_LOD{k}"] = r
        print("PAIR", j, k, r["tri_tri_intersections"], r["vertices_past_mouth_in_cavity"], "/", r["vertices_past_mouth"],
              r["surface_samples_in_cavity"], "/", r["surface_samples_past_mouth"], round(r["min_clearance_samples_mm"], 3), flush=True)
res["pairs"] = pairs

# straight draw along -mouth_n
draw = {}
for j, k, step in ((0, 0, 0.25), (1, 1, 1.0), (2, 2, 1.0), (0, 2, 1.0), (2, 0, 1.0)):
    Pw, Tw = sword_lods[j]
    Ps0 = to_sheath(Pw)
    worst = 0
    first_hit = None
    s = 0.0
    while s <= 100.0:
        Ps = Ps0 - mouth_n * s
        n = len(sheath_trees[k].overlap(bvh(Ps, Tw)))
        if n and first_hit is None:
            first_hit = s
        worst = max(worst, n)
        s += step
    draw[f"sword_LOD{j}_sheath_LOD{k}"] = {"step_cm": step, "max_intersections": worst, "first_hit_cm": first_hit}
    print("DRAW", j, k, worst, first_hit, flush=True)
res["draw"] = draw

# Unreal's own FBX export: hull comparison vs the shipped FBX
def ucx_sets(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    lods = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        mw = np.array(ob.matrix_world)
        co = np.array([tuple(v.co) for v in ob.data.vertices])
        W = co @ mw[:3, :3].T + mw[:3, 3]
        if ob.name.startswith("UCX_"):
            out[ob.name] = W
        else:
            lods[ob.name] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return out, lods


hulls = {}
for tag, shipped, rt in (("sword", EXP / "SM_SnowFlower.fbx", HERE / "ue_roundtrip_sword.fbx"),
                         ("sheath", EXP / "SM_SnowFlower_Sheath.fbx", HERE / "ue_roundtrip_sheath.fbx")):
    a, la = ucx_sets(shipped)
    b, lb = ucx_sets(rt)
    A = list(a.values()); Bv = list(b.values())
    # match each shipped hull to the nearest roundtrip hull by symmetric Hausdorff
    def haus(P, Q):
        d1 = np.sqrt(((P[:, None, :] - Q[None, :, :]) ** 2).sum(-1))
        return max(d1.min(1).max(), d1.min(0).max())
    match = {}
    for name, P in a.items():
        best = min(((haus(P, Q), n) for n, Q in b.items()), default=(None, None))
        match[name] = {"roundtrip_hull": best[1], "hausdorff_m": float(best[0]) if best[0] is not None else None,
                       "verts_shipped": len(P), "verts_roundtrip": len(b[best[1]]) if best[1] else None}
    hulls[tag] = {"shipped_ucx": len(a), "roundtrip_ucx": len(b), "match": match, "roundtrip_mesh_nodes": lb, "shipped_mesh_nodes": la}
res["hull_roundtrip"] = hulls
(HERE / "iv3_fit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("IV3_DONE")
