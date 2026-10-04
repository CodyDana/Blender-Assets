"""Independent fit check (Blender 5.2 headless, numpy + mathutils only) on geometry READ BACK FROM UNREAL.

Inputs (written by kvB_verify.py in a fresh Unreal process):
  kvB_geometry.json  per-LOD source positions + triangles of both meshes (cm, Unreal frame)
  kvB_verify.json    attach.katana_to_saya_basis: the katana->saya-local affine map Unreal produced after
                     attach_to_component(Holster, SNAP_TO_TARGET) with the saya at a non-identity world transform;
                     attach.socket_Mouth / socket_DrawPivot (from the in-engine socket transforms)
Gates, all 9 LOD pairs (katana LODj in saya LODk):
  F1 0 triangle-triangle intersections
  F2 every katana vertex and dense surface sample past the mouth plane lies in the empty cavity (even, non-zero ray
     parity in 4 lateral directions and toward the kojiri)
  F3 clearance (blade zone, habaki zone), hilt side outside the saya material, hilt gap
  F4 seat gap: rays from the saya's mouth-face vertices toward the hilt hit the seppa
  F5 draw: rotation about the DrawPivot socket's Y axis until the tip is out, 0 intersections at every step
     (the straight slide along the Mouth socket's -Z is measured as information: the blade is curved)
  F6 tip to cavity end along the tip tangent
Hulls: Unreal's own FBX export (ue_roundtrip_*.fbx) split into its convex shells, compared to the shipped UCX nodes,
convexity, and containment of LOD0 (round-trip LOD0 and the Unreal read-back LOD0).
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final2/iv3_fit.py + iv4_hulls.py.
"""
import bpy, bmesh, json, math, sys, time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final2")
import kv_common as C  # noqa: E402

HERE = C.HERE
t0 = time.time()
geo = json.loads((HERE / "kvB_geometry.json").read_text())
B = json.loads((HERE / "kvB_verify.json").read_text())
att = B["attach"]
bas = att["katana_to_saya_basis"]
o = np.array(bas["o"]); M = np.stack([np.array(bas[k]) - o for k in "xyz"], axis=1)
mouth_p = np.array(att["socket_Mouth"]["t"]); mouth_n = np.array(att["socket_Mouth"]["z_axis"]); mouth_n /= np.linalg.norm(mouth_n)
piv = np.array(att["socket_DrawPivot"]["t"]); piv_axis = np.array(att["socket_DrawPivot"]["y_axis"]); piv_axis /= np.linalg.norm(piv_axis)
res = {"affine_orthonormal_err": float(np.abs(M.T @ M - np.eye(3)).max()), "affine_det": float(np.linalg.det(M)),
       "affine_translation_cm": o.tolist(), "mouth_plane": [mouth_p.tolist(), mouth_n.tolist()],
       "draw_pivot": [piv.tolist(), piv_axis.tolist()]}
HAB_DEPTH = 2.85  # cm past the mouth plane: habaki zone (habaki 28 mm, seated 0.35 mm proud of the mouth)


def to_saya(P):
    return P @ M.T + o


def bvh(P, T):
    return BVHTree.FromPolygons([tuple(p) for p in P], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def hits_along(tree, p, d, maxd=500.0):
    n, origin, dirv, travelled = 0, Vector(p), Vector(d), 0.0
    while travelled < maxd and n < 64:
        loc, nor, idx, dist = tree.ray_cast(origin, dirv, maxd - travelled)
        if loc is None:
            break
        n += 1
        step = dist + 1e-5
        origin = origin + dirv * step
        travelled += step
    return n


DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+n": tuple(mouth_n)}


def enclosed(tree, p):
    c = {k: hits_along(tree, p, d) for k, d in DIRS.items()}
    return all(v >= 1 and v % 2 == 0 for v in c.values()), c


def sample_surface(P, T, n, rng):
    A = P[T[:, 0]]; Bq = P[T[:, 1]]; Cq = P[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(Bq - A, Cq - A), axis=1)
    idx = rng.choice(len(T), size=n, p=area / area.sum())
    u = rng.random(n); v = rng.random(n); f = u + v > 1; u[f] = 1 - u[f]; v[f] = 1 - v[f]
    return A[idx] + (Bq[idx] - A[idx]) * u[:, None] + (Cq[idx] - A[idx]) * v[:, None]


def lod_arrays(l):
    P = np.array(l["positions"], dtype=np.float64); T = np.array(l["triangles"])[:, -3:]
    assert T.max() < len(P) and T.min() >= 0
    return P, T


rng = np.random.default_rng(1003)
saya_lods = [lod_arrays(l) for l in geo["SM_Katana_Saya"]]
kat_lods = [lod_arrays(l) for l in geo["SM_Katana"]]
kat_saya = [(to_saya(P), T) for P, T in kat_lods]
saya_trees = [bvh(P, T) for P, T in saya_lods]


def closed_part(P, T):
    """Triangles of the connected components that have NO open edge (for ray parity). Open shells (e.g. a knob whose
    open rim is buried in the wall) cannot change whether a point is inside the cavity, but break parity counting."""
    from collections import Counter
    E = Counter()
    for t in T:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            E[(min(a, b), max(a, b))] += 1
    parent = list(range(len(P)))
    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for t in T:
        for v in t[1:]:
            a, b = f(t[0]), f(v)
            if a != b:
                parent[a] = b
    bad_roots = {f(a) for (a, b), c in E.items() if c != 2}
    keep = np.array([f(t[0]) not in bad_roots for t in T])
    dropped = T[~keep]
    info = {"open_or_nonmanifold_edges": int(sum(1 for c in E.values() if c != 2)),
            "edge_share_histogram": {str(k): v for k, v in sorted(Counter(E.values()).items())},
            "parity_excluded_triangles": int((~keep).sum()),
            "parity_excluded_bbox_cm": ([P[dropped.ravel()].min(0).round(4).tolist(), P[dropped.ravel()].max(0).round(4).tolist()]
                                        if len(dropped) else None)}
    return T[keep], info


parity = [closed_part(P, T) for P, T in saya_lods]
parity_trees = [bvh(P, Tk) for (P, _), (Tk, _) in zip(saya_lods, parity)]
res["saya_topology"] = {f"LOD{i}": inf for i, (_, inf) in enumerate(parity)}
print("TOPO", json.dumps(res["saya_topology"]), flush=True)
res["counts"] = {"katana": [[len(P), len(T)] for P, T in kat_lods], "saya": [[len(P), len(T)] for P, T in saya_lods]}

pairs = {}
for j, (Ps, Tw) in enumerate(kat_saya):
    sw_tree = bvh(Ps, Tw)
    depth = (Ps - mouth_p) @ mouth_n
    S = sample_surface(Ps, Tw, 40000 if j == 0 else 15000, rng)
    S = S[((S - mouth_p) @ mouth_n) > 0]
    Sd = (S - mouth_p) @ mouth_n
    for k, tree in enumerate(saya_trees):
        ptree = parity_trees[k]
        r = {"tri_tri_intersections": len(tree.overlap(sw_tree))}
        inside = np.where(depth > 0)[0]
        ok = [enclosed(ptree, Ps[i]) for i in inside]
        r["vertices_past_mouth"] = int(len(inside))
        r["vertices_enclosed"] = int(sum(g for g, _ in ok))
        r["bad_vertex_examples"] = [{"p": Ps[i].round(4).tolist(), "hits": c} for i, (g, c) in zip(inside, ok) if not g][:5]
        dist = np.array([tree.find_nearest(Vector(p))[3] for p in Ps[inside]])
        dz = depth[inside]
        r["min_clearance_habaki_zone_mm"] = float(dist[dz <= HAB_DEPTH].min() * 10)
        r["max_clearance_habaki_zone_vertices_le_0.2mm"] = float(dist[(dz <= HAB_DEPTH) & (dist < 0.02)].max() * 10) if ((dz <= HAB_DEPTH) & (dist < 0.02)).any() else None
        r["min_clearance_blade_zone_mm"] = float(dist[dz > HAB_DEPTH].min() * 10)
        Ssub = S if k == 0 else S[: len(S) // 3]
        oks_full = [enclosed(ptree, p) for p in Ssub]
        oks = [g for g, _ in oks_full]
        r["bad_sample_examples"] = []
        for p_, (g, c) in zip(Ssub, oks_full):
            if not g and len(r["bad_sample_examples"]) < 5:
                alt = [hits_along(ptree, p_, tuple(np.array(dd) / np.linalg.norm(dd))) for dd in ((1, 0.13, 0.07), (-1, 0.11, -0.05), (0.09, 1, 0.12), (0.06, -1, -0.1))]
                r["bad_sample_examples"].append({"p": p_.round(4).tolist(), "depth_cm": float((p_ - mouth_p) @ mouth_n), "hits": c,
                                                 "perturbed_dir_hits": alt,
                                                 "clearance_mm": float(tree.find_nearest(Vector(p_))[3] * 10)})
        ds = np.array([tree.find_nearest(Vector(p))[3] for p in Ssub])
        Sdz = Sd if k == 0 else Sd[: len(S) // 3]
        r["surface_samples_past_mouth"] = int(len(Ssub))
        r["surface_samples_enclosed"] = int(sum(oks))
        deepok = Sdz > 0.005  # samples within 50 um of the mouth plane graze the mouth face: parity is undefined there
        r["surface_samples_past_mouth_gt_50um"] = int(deepok.sum())
        r["surface_samples_enclosed_gt_50um"] = int(sum(g for g, dk in zip(oks, deepok) if dk))
        r["min_clearance_samples_blade_zone_mm"] = float(ds[Sdz > HAB_DEPTH].min() * 10)
        r["min_clearance_samples_habaki_zone_mm"] = float(ds[Sdz <= HAB_DEPTH].min() * 10)
        hilt = np.where(depth <= 0)[0]
        in_mat = 0
        for i in hilt:
            cx, cmx = hits_along(ptree, Ps[i], (1, 0, 0)), hits_along(ptree, Ps[i], (-1, 0, 0))
            in_mat += int(cx % 2 == 1 and cmx % 2 == 1)
        r["hilt_vertices"] = int(len(hilt))
        r["hilt_vertices_inside_saya_material"] = in_mat
        r["hilt_min_gap_mm"] = float(min(tree.find_nearest(Vector(p))[3] for p in Ps[hilt]) * 10)
        above = np.where(depth <= -0.025)[0]  # seppa face (0.3 mm proud of the mouth) and everything above it
        r["seppa_tsuba_tsuka_min_gap_mm"] = float(min(tree.find_nearest(Vector(p))[3] for p in Ps[above]) * 10)
        r["deepest_katana_point_depth_cm"] = float(depth.max())
        r["pass"] = (r["tri_tri_intersections"] == 0 and r["vertices_enclosed"] == r["vertices_past_mouth"]
                     and r["surface_samples_enclosed_gt_50um"] == r["surface_samples_past_mouth_gt_50um"] and in_mat == 0)
        pairs[f"katana_LOD{j}_in_saya_LOD{k}"] = r
        print("PAIR", j, k, r["tri_tri_intersections"], r["vertices_enclosed"], "/", r["vertices_past_mouth"],
              r["surface_samples_enclosed"], "/", r["surface_samples_past_mouth"],
              round(r["min_clearance_blade_zone_mm"], 4), round(r["min_clearance_habaki_zone_mm"], 4), round(r["hilt_min_gap_mm"], 4), flush=True)
res["pairs"] = pairs

# F4 seat gap: rays from the mouth-face vertices of each saya LOD toward the hilt (-mouth_n) onto katana LOD0
seat = {}
for k, (Pk, Tk) in enumerate(saya_lods):
    d = (Pk - mouth_p) @ mouth_n
    face = Pk[d <= d.min() + 1e-3]
    for j, (Ps, Tw) in enumerate(kat_saya):
        tree = bvh(Ps, Tw)
        g = []
        for p in face:
            loc, nor, idx, dist = tree.ray_cast(Vector(p - mouth_n * 1e-5), Vector(-mouth_n), 5.0)
            if loc is not None:
                g.append(dist * 10 + 1e-4)
        seat[f"saya_LOD{k}_katana_LOD{j}"] = {"mouth_face_vertices": int(len(face)), "rays_hit": len(g),
                                              "gap_min_mm": float(min(g)) if g else None, "gap_max_mm": float(max(g)) if g else None,
                                              "mouth_face_depth_cm": float(d.min())}
res["seat_gap"] = seat
print("SEAT", json.dumps(seat), flush=True)


def rot_about(P, c, axis, ang):
    a = axis / np.linalg.norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
    return (P - c) @ R.T + c


# draw direction: the sign that moves the Grip (katana origin) toward -mouth_n
grip = o
sgn = 1.0 if ((rot_about(grip[None], piv, piv_axis, math.radians(1.0))[0] - grip) @ mouth_n) < 0 else -1.0
tip = kat_saya[0][0][np.argmax((kat_saya[0][0] - mouth_p) @ mouth_n)]
ang_out = None
a = 0.0
while a < math.radians(20):
    a += math.radians(0.01)
    if ((rot_about(tip[None], piv, piv_axis, sgn * a)[0] - mouth_p) @ mouth_n) < -0.5:
        ang_out = a
        break
res["draw_sign"] = sgn
res["draw_angle_tip_0.5cm_out_deg"] = math.degrees(ang_out)
STEP = math.radians(0.05)
draw = {}
for j, (Ps0, Tw) in enumerate(kat_saya):
    for k, tree in enumerate(saya_trees):
        worst, first, n_steps, a = 0, None, 0, 0.0
        minclr = []
        while a <= ang_out + 1e-12:
            Pr = rot_about(Ps0, piv, piv_axis, sgn * a)
            n = len(tree.overlap(bvh(Pr, Tw)))
            if n and first is None:
                first = math.degrees(a)
            worst = max(worst, n)
            if j == 0 and k == 0 and n_steps % 20 == 0:
                dd = (Pr - mouth_p) @ mouth_n
                sel = Pr[dd > 0]
                if len(sel):
                    minclr.append([round(math.degrees(a), 3), float(min(tree.find_nearest(Vector(p))[3] for p in sel) * 10)])
            n_steps += 1
            a += STEP
        draw[f"katana_LOD{j}_saya_LOD{k}"] = {"steps": n_steps, "step_deg": 0.05, "max_intersections": worst, "first_hit_deg": first}
        if minclr:
            draw[f"katana_LOD{j}_saya_LOD{k}"]["min_clearance_mm_every_1deg"] = minclr
        print("DRAW", j, k, n_steps, worst, first, flush=True)
res["arc_draw"] = draw

slide = {}
for j, k in ((0, 0), (1, 1), (2, 2)):
    Ps0, Tw = kat_saya[j]
    first, s = None, 0.0
    while s <= 3.0:
        if len(saya_trees[k].overlap(bvh(Ps0 - mouth_n * s, Tw))):
            first = s
            break
        s += 0.02
    slide[f"katana_LOD{j}_saya_LOD{k}"] = {"first_collision_cm": first, "step_cm": 0.02}
res["straight_slide_info"] = slide

# F6 tip to cavity end along the tip tangent (BladeTip socket, pitch -11.044 -> direction in katana frame)
ksc = json.loads((C.EXP / "SM_Katana.sockets.json").read_text())
bt = next(s for s in ksc["sockets"] if s["socket"] == "BladeTip")
pitch = math.radians(bt["rotation_deg"]["pitch"])
tipdir_k = np.array([math.sin(-pitch), 0.0, math.cos(-pitch)])  # +Z tilted toward +X by 11.044 deg
tipdir = M @ tipdir_k; tipdir /= np.linalg.norm(tipdir)
tipF6 = {}
for j, (Ps, Tw) in enumerate(kat_saya):
    tp = Ps[np.argmax((Ps - mouth_p) @ mouth_n)]
    for k, tree in enumerate(saya_trees):
        loc, nor, idx, dist = tree.ray_cast(Vector(tp), Vector(tipdir), 10.0)
        tipF6[f"katana_LOD{j}_saya_LOD{k}"] = float(dist * 10) if loc is not None else None
res["tip_to_cavity_end_mm"] = tipF6
print("TIP", tipF6, flush=True)


# ---- hulls: Unreal's own FBX export vs the shipped UCX
def import_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        mw = np.array(ob.matrix_world)
        co = np.array([tuple(v.co) for v in ob.data.vertices]).reshape(-1, 3)
        W = (co @ mw[:3, :3].T + mw[:3, 3]) * 100.0
        polys = [list(p.vertices) for p in ob.data.polygons]
        out[ob.name] = (W, polys)
    return out


def shells(W, polys):
    parent = list(range(len(W)))
    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for p in polys:
        for v in p[1:]:
            a, b = f(p[0]), f(v)
            if a != b:
                parent[a] = b
    groups = {}
    for i in range(len(W)):
        groups.setdefault(f(i), []).append(i)
    return [W[g] for g in groups.values()]


def planes_of(pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    c = pts.mean(axis=0)
    N, D = [], []
    for fc in bm.faces:
        n = np.array(fc.normal)
        if np.linalg.norm(n) < 1e-9:
            continue
        d = n @ np.array(fc.verts[0].co)
        if n @ c - d > 0:
            n, d = -n, -d
        N.append(n); D.append(d)
    nf = len(bm.faces); nv = len(bm.verts)
    bm.free()
    return np.array(N), np.array(D), nv, nf


hull = {}
for name, rt in (("SM_Katana", HERE / "ue_roundtrip_katana.fbx"), ("SM_Katana_Saya", HERE / "ue_roundtrip_saya.fbx")):
    shipped = import_fbx(C.EXP / f"{name}.fbx")
    rtrip = import_fbx(rt)
    ship_ucx = {n: W for n, (W, _) in shipped.items() if n.startswith("UCX_")}
    rt_ucx_nodes = [n for n in rtrip if n.startswith("UCX_")]
    rt_shells = []
    for n in rt_ucx_nodes:
        rt_shells += shells(*rtrip[n])
    h = {"shipped_ucx": len(ship_ucx), "roundtrip_ucx_nodes": rt_ucx_nodes, "roundtrip_shells": len(rt_shells),
         "roundtrip_mesh_nodes": {n: len(p) for n, (W, p) in rtrip.items() if not n.startswith("UCX_")}}
    match = {}
    for sn, P in ship_ucx.items():
        best = None
        for i, Q in enumerate(rt_shells):
            dmat = np.sqrt(((P[:, None, :] - Q[None, :, :]) ** 2).sum(-1))
            hd = max(dmat.min(1).max(), dmat.min(0).max())
            if best is None or hd < best[0]:
                best = (hd, i)
        Q = rt_shells[best[1]]
        N, D, nv, nf = planes_of(Q)
        Nq, Dq, nvs, nfs = planes_of(P)
        match[sn] = {"roundtrip_shell": best[1], "hausdorff_cm": float(best[0]), "verts_shipped_hull": nvs,
                     "verts_roundtrip_hull": nv, "faces_shipped_hull": nfs, "faces_roundtrip_hull": nf,
                     "roundtrip_points_off_own_hull_cm": float(max(0.0, (Q @ N.T - D).max()))}
    h["match"] = match
    # containment of LOD0: round-trip LOD0 and the Unreal read-back LOD0 (Unreal frame: y flipped vs Blender)
    HP = [planes_of(Q)[:2] for Q in rt_shells]
    h["roundtrip_shell_sizes"] = [int(len(Q)) for Q in rt_shells]
    HP = [(N, D) for N, D in HP if len(N)]          # finaliser copy: skip degenerate fragments (no planes)
    def contain(V):
        out = np.full(len(V), np.inf)
        for N, D in HP:
            out = np.minimum(out, np.maximum((V @ N.T - D).max(1), 0))
        return {"vertices": int(len(V)), "outside_count_gt_0.001cm": int((out > 1e-3).sum()), "max_outside_cm": float(out.max())}
    lod0_rt = next((W for n, (W, _) in rtrip.items() if not n.startswith("UCX_") and ("LOD0" in n or n == name)), None)
    h["lod_nodes_in_roundtrip"] = [n for n in rtrip if not n.startswith("UCX_")]
    if lod0_rt is not None:
        h["roundtrip_lod0_containment"] = contain(lod0_rt)
    ue0 = np.array(geo[name][0]["positions"]) * np.array([1, -1, 1])
    h["unreal_readback_lod0_containment"] = contain(ue0)
    for li in (1, 2):
        V = np.array(geo[name][li]["positions"]) * np.array([1, -1, 1])
        h[f"unreal_readback_lod{li}_containment_info"] = contain(V)
        out = np.full(len(V), np.inf)
        for N, D in HP:
            out = np.minimum(out, np.maximum((V @ N.T - D).max(1), 0))
        worst = np.argsort(-out)[:6]
        h[f"unreal_readback_lod{li}_worst_outside_unreal_frame_cm"] = [[*(V[i] * np.array([1, -1, 1])).round(3).tolist(), round(float(out[i]), 4)] for i in worst if out[i] > 1e-3]
    hull[name] = h
    print("HULL", name, json.dumps({k: v for k, v in h.items() if k != "match"}), flush=True)
res["hulls"] = hull
res["seconds"] = round(time.time() - t0, 1)
res["all_pairs_pass"] = all(p["pass"] for p in pairs.values())
res["arc_draw_clean"] = all(d["max_intersections"] == 0 for d in draw.values())
(HERE / "kv3_fit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("KV3_DONE", res["all_pairs_pass"], res["arc_draw_clean"], res["seconds"])
