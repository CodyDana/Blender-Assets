"""Heels Unreal check: measure the worn test from Unreal's bone transforms (Blender headless, numpy + mathutils; saves nothing).

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hc_analyze.py -- [capture json]

Unreal gives the component-space transform of every body bone per pose (capture_<RUN>.json, from the offscreen editor with
her BP + the test ABP + CR_HeelPose running). The shipped heels LOD0 and her lower legs (skin_data.npz, exported read-only
from the build blend / fitting body in Unreal cm) are linear-blend skinned with exactly those transforms, which is what the
GPU does (heels <= 3 influences, body <= 8 kept). Per pose:
  * floor: lowest point of the heel tip (top-lift) and of the forefoot sole, per shoe, vs z = 0 (mm)
  * the barefoot baseline (same clip time, HeelAlpha 0): lowest heel / ball skin
  * penetration: shoe vertices inside her skin (nearest-surface normal test, depth > 0.5 mm), body edges crossing the shoe
  * strap: gap between the strap loop and her skin, strap height above the ankle joint
  * stretch: edge-length ratio of every shoe edge vs the standing heel pose (Idle t=0) - p50/p99/max per part
  * foot pitch (foot bone vs barefoot) and pelvis lift
Continuous real-time playback: shoe lowest point per tick while the barefoot clip is grounded (feet floating / sinking).
Writes WorkFiles/SnowFlowerHeels/ue/analysis_<RUN>.json.
"""
import json
import math
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
CAP = argv[0] if argv else "%s/capture_%s.json" % (UE, RUN)
cap = json.load(open(CAP, encoding="utf-8"))
sd = np.load(UE + "/skin_data.npz")
meta = json.load(open(UE + "/skin_data.json", encoding="utf-8"))
BONES = meta["bones"]
crb = json.load(open(UE + "/build_cr.json", encoding="utf-8"))
LOCAL_FWD = {s: np.array(v) for s, v in crb["local_forward_in_foot"].items()}


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat(t):
    m = np.eye(4)
    m[:3, :3] = qmat(t[3:7])
    m[:3, 3] = t[:3]
    return m


REF = {n: mat(t) for n, t in cap["ref_pose_cs"].items()}
REF_INV = {n: np.linalg.inv(m) for n, m in REF.items()}


def skin_mats(bones):
    out = np.tile(np.eye(4), (len(BONES), 1, 1))
    for i, n in enumerate(BONES):
        if n in bones and n in REF_INV:
            out[i] = mat(bones[n]) @ REF_INV[n]
    return out


def skin(co, idx, w, mats):
    h = np.concatenate([co, np.ones((len(co), 1))], 1)
    res = np.zeros((len(co), 3))
    for k in range(idx.shape[1]):
        m = mats[idx[:, k]]
        res += w[:, k:k + 1] * np.einsum("nij,nj->ni", m, h)[:, :3]
    return res


# the Blender -> Unreal conversion mirrors y, which flips the triangle winding: reverse it so face normals point outward
H_CO, H_TRI, H_TMAT, H_IDX, H_W = sd["heel0_co"], sd["heel0_tris"][:, ::-1].copy(), sd["heel0_tmat"], sd["heel0_idx"], sd["heel0_w"]
B_CO, B_TRI, B_IDX, B_W = sd["body_co"], sd["body_tris"][:, ::-1].copy(), sd["body_idx"], sd["body_w"]
side_of = np.where(H_CO[:, 0] > 0, "l", "r")
edges = np.unique(np.sort(np.concatenate([H_TRI[:, [0, 1]], H_TRI[:, [1, 2]], H_TRI[:, [2, 0]]]), 1), axis=0)
b_edges = np.unique(np.sort(np.concatenate([B_TRI[:, [0, 1]], B_TRI[:, [1, 2]], B_TRI[:, [2, 0]]]), 1), axis=0)
vmat = np.zeros(len(H_CO), dtype=np.int64)
for t, m in zip(H_TRI, H_TMAT):
    vmat[t] = m
bi = {n: i for i, n in enumerate(BONES)}
twist = np.isin(H_IDX, [bi[n] for n in BONES if n.startswith("calf_twist")]) & (H_W > 0)
twist_w = (H_W * twist).sum(1)

# --- reference frame: standing heel pose (Idle t=0, alpha 1) ----------------------------------------------------------
poses = cap["poses"]
stand = [p for p in poses if p["clip"] == "Idle" and p["alpha"] == 1.0 and p["t"] == 0.0][0]
S = skin(H_CO, H_IDX, H_W, skin_mats(stand["bones"]))
regions = {}
for s in ("l", "r"):
    f = "foot_" + s
    m = mat(stand["bones"][f])
    loc = (np.linalg.inv(m) @ np.concatenate([S, np.ones((len(S), 1))], 1).T).T[:, :3]
    sv = loc @ LOCAL_FWD[s]
    sel = side_of == s
    smin, smax = sv[sel].min(), sv[sel].max()
    frac = (sv - smin) / (smax - smin)
    # rear half holds the stiletto + top-lift (lowest there when standing); the forefoot sole is in the front 40 %
    rear = sel & (frac < 0.50)
    front = sel & (frac > 0.60)
    zr, zf = S[rear, 2].min(), S[front, 2].min()
    regions[s] = {"tip": np.where(rear & (S[:, 2] < zr + 0.3))[0], "sole": np.where(front & (S[:, 2] < zf + 0.3))[0],
                  "length_cm": float(smax - smin)}
# strap: the leather connected component that is a ring around the shin (calf_twist weighted, short along the shin,
# wide across it) - found from mesh connectivity, not from a pose
parent_ = np.arange(len(H_CO))


def find(a):
    while parent_[a] != a:
        parent_[a] = parent_[parent_[a]]
        a = parent_[a]
    return a


for t in H_TRI:
    ra, rb, rc = find(t[0]), find(t[1]), find(t[2])
    parent_[rb] = ra
    parent_[find(rc)] = ra
roots = np.array([find(i) for i in range(len(H_CO))])
strap, strap_info = {}, {}
for s in ("l", "r"):
    calf = mat(stand["bones"]["calf_" + s])
    axis = calf[:3, :3] @ np.array([1.0, 0, 0])
    best = None
    for rt in np.unique(roots[side_of == s]):
        ids = np.where(roots == rt)[0]
        if len(ids) < 20 or twist_w[ids].mean() < 0.4 or (vmat[ids] != 0).mean() > 0.5:
            continue
        along = S[ids] @ axis
        span_along = along.max() - along.min()
        across = np.linalg.norm((S[ids] - S[ids].mean(0)) - np.outer((S[ids] - S[ids].mean(0)) @ axis, axis), axis=1).max()
        score = across - span_along
        if span_along < 3.0 and across > 3.0 and (best is None or score > best[0]):
            best = (score, ids, float(span_along), float(across))
    strap[s] = best[1] if best else np.array([], dtype=np.int64)
    strap_info[s] = {"verts": int(len(strap[s])), "span_along_shin_cm": best[2] if best else None,
                     "radius_cm": best[3] if best else None}


def lowest(P, ids):
    return float(P[ids, 2].min()) * 10.0 if len(ids) else None


def body_contacts(Bp):
    out = {}
    for s in ("l", "r"):
        sel = (B_CO[:, 0] > 0) if s == "l" else (B_CO[:, 0] < 0)
        sel &= B_CO[:, 2] < 12
        out[s] = float(Bp[sel, 2].min()) * 10.0
    return out


def analyse_pose(p, stretch_ref=None, full=True):
    M = skin_mats(p["bones"])
    P = skin(H_CO, H_IDX, H_W, M)
    r = {"clip": p["clip"], "t": p["t"], "alpha": p["alpha"]}
    for s in ("l", "r"):
        r["tip_z_mm_" + s] = lowest(P, regions[s]["tip"])
        r["sole_z_mm_" + s] = lowest(P, regions[s]["sole"])
        r["shoe_min_z_mm_" + s] = float(P[side_of == s, 2].min()) * 10
    if not full:
        return r, P
    Bp = skin(B_CO, B_IDX, B_W, skin_mats(p["bones"]))
    r["skin_min_z_mm"] = body_contacts(Bp)
    bvh = BVHTree.FromPolygons([Vector(v) for v in Bp], [tuple(t) for t in B_TRI], all_triangles=True)
    inside, depth = 0, 0.0
    gaps = {"l": [], "r": []}
    for i, v in enumerate(P):
        hit = bvh.find_nearest(Vector(v), 3.0)
        if hit[0] is None:
            continue
        d = Vector(v) - hit[0]
        sd_ = d.dot(hit[1])
        if sd_ < -0.05:
            inside += 1
            depth = max(depth, -sd_)
    for s in ("l", "r"):
        for i in strap[s]:
            hit = bvh.find_nearest(Vector(P[i]), 10.0)
            if hit[0] is not None:
                gaps[s].append((Vector(P[i]) - hit[0]).dot(hit[1]) * 10.0)
    r["shoe_verts_inside_skin"] = inside
    r["max_inside_depth_mm"] = depth * 10.0
    shoe_bvh = BVHTree.FromPolygons([Vector(v) for v in P], [tuple(t) for t in H_TRI], all_triangles=True)
    cross = 0
    detail = []
    for a, b in b_edges:
        if Bp[a, 2] > 25 and Bp[b, 2] > 25:
            continue
        va, vb = Vector(Bp[a]), Vector(Bp[b])
        d = vb - va
        L = d.length
        if L < 1e-6:
            continue
        hit = shoe_bvh.ray_cast(va, d / L, L)
        if hit[0] is not None:
            cross += 1
            fi = hit[2]
            detail.append((round(hit[0].z * 10.0), int(H_TMAT[fi]), bool(twist_w[H_TRI[fi]].max() > 0),
                           "l" if H_CO[H_TRI[fi][0], 0] > 0 else "r"))
    r["body_edges_crossing_shoe"] = cross
    # foot skin behind a shoe surface: signed distance of each foot-region skin vertex to its nearest shoe face
    behind = []
    for i, v in enumerate(Bp):
        if v[2] > 25:
            continue
        hit = shoe_bvh.find_nearest(Vector(v), 3.0)
        if hit[0] is None:
            continue
        sdist = (Vector(v) - hit[0]).dot(hit[1])
        if sdist < -0.1:
            behind.append((-sdist * 10.0, int(H_TMAT[hit[2]]), round(v[2] * 10.0), bool(twist_w[H_TRI[hit[2]]].max() > 0),
                           i))
    r["skin_verts_behind_shoe_surface_1mm"] = int(sum(1 for b in behind if b[0] > 1.0))
    r["skin_verts_behind_shoe_surface_3mm"] = int(sum(1 for b in behind if b[0] > 3.0))
    r["skin_behind_max_mm"] = float(max((b[0] for b in behind), default=0.0))
    r["skin_behind_by_slot_over_1mm"] = {str(k): int(sum(1 for b in behind if b[1] == k and b[0] > 1.0)) for k in (0, 1, 2)}
    r["skin_below_floor_verts"] = int((Bp[:, 2] < -0.1).sum())
    deep = [b for b in behind if b[0] > 1.0]
    if deep:
        zs = np.array([b[2] for b in deep])
        r["skin_behind_detail"] = {"z_mm_p10_p50_p90": [float(np.percentile(zs, q)) for q in (10, 50, 90)],
                                   "on_calf_twist_faces": int(sum(1 for b in deep if b[3])),
                                   "worst": sorted([[round(b[0], 1), b[1], b[2], b[3]] for b in deep], reverse=True)[:6]}
    if detail:
        zs = np.array([d_[0] for d_ in detail])
        r["crossing_detail"] = {"z_mm_p10_p50_p90": [float(np.percentile(zs, q)) for q in (10, 50, 90)],
                                "by_slot": {str(k): int(sum(1 for d_ in detail if d_[1] == k)) for k in (0, 1, 2)},
                                "on_calf_twist_weighted_faces": int(sum(1 for d_ in detail if d_[2])),
                                "by_side": {sd_: int(sum(1 for d_ in detail if d_[3] == sd_)) for sd_ in ("l", "r")}}
    for s in ("l", "r"):
        g = np.array(gaps[s]) if gaps[s] else np.array([np.nan])
        ank = np.array(p["bones"]["foot_" + s][:3])
        r["strap_gap_mm_" + s] = {"min": float(np.nanmin(g)), "p50": float(np.nanmedian(g)), "max": float(np.nanmax(g))}
        cax = mat(p["bones"]["calf_" + s])[:3, :3] @ np.array([1.0, 0, 0])
        # distance of the strap ring centre from the ankle joint, measured along the shin (calf bone axis)
        r["strap_above_ankle_mm_" + s] = float(abs((P[strap[s]].mean(0) - ank) @ cax) * 10.0) if len(strap[s]) else None
    if stretch_ref is not None:
        l0 = np.linalg.norm(stretch_ref[edges[:, 0]] - stretch_ref[edges[:, 1]], axis=1)
        l1 = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)
        ok = l0 > 1e-4
        ratio = l1[ok] / l0[ok]
        dev = np.abs(ratio - 1)
        tw = np.maximum(twist_w[edges[ok, 0]], twist_w[edges[ok, 1]]) > 0
        el = np.abs(l1[ok] - l0[ok]) * 10.0
        r["stretch"] = {"p50": float(np.median(dev)), "p99": float(np.percentile(dev, 99)), "max": float(dev.max()),
                        "max_abs_mm": float(el.max()), "edges_over_1mm": int((el > 1.0).sum()), "edges_over_3mm": int((el > 3.0).sum()),
                        "max_abs_mm_non_twist": float(el[~tw].max()) if (~tw).any() else 0.0,
                        "max_on_calf_twist_edges": float(dev[tw].max()) if tw.any() else 0.0,
                        "p99_on_calf_twist_edges": float(np.percentile(dev[tw], 99)) if tw.any() else 0.0,
                        "edges_over_5pct": int((dev > 0.05).sum()), "edges_over_10pct": int((dev > 0.10).sum())}
    b = p["bones"]
    r["pelvis_z_cm"] = b["pelvis"][2]
    for s in ("l", "r"):
        r["ankle_z_cm_" + s] = b["foot_" + s][2]
    return r, P


out = {"capture": CAP, "follow_mode": cap.get("follow_mode"), "mesh_kind": cap.get("mesh_kind"), "poses": [],
       "regions": {s: {"tip_verts": len(regions[s]["tip"]), "sole_verts": len(regions[s]["sole"]),
                       "shoe_length_cm": regions[s]["length_cm"], "strap": strap_info[s]} for s in regions}}
bare = {(p["clip"], round(p["t"], 4)): p for p in poses if p["alpha"] == 0.0}
seen = set()
for p in poses:
    key = (p["clip"], round(p["t"], 4), p["alpha"])
    if key in seen:
        continue
    seen.add(key)
    r, P = analyse_pose(p, stretch_ref=S, full=True)
    bp = bare.get((p["clip"], round(p["t"], 4)))
    if bp is not None and p["alpha"] == 1.0:
        Bb = skin(B_CO, B_IDX, B_W, skin_mats(bp["bones"]))
        r["barefoot_skin_min_z_mm"] = body_contacts(Bb)
        r["pelvis_lift_cm"] = p["bones"]["pelvis"][2] - bp["bones"]["pelvis"][2]
        for s in ("l", "r"):
            fa, fb = mat(p["bones"]["foot_" + s]), mat(bp["bones"]["foot_" + s])
            ra = fa[:3, :3] @ LOCAL_FWD[s]
            rb = fb[:3, :3] @ LOCAL_FWD[s]
            r["foot_pitch_heel_deg_" + s] = math.degrees(math.asin(max(-1, min(1, -ra[2]))))
            r["foot_pitch_bare_deg_" + s] = math.degrees(math.asin(max(-1, min(1, -rb[2]))))
    out["poses"].append(r)
    print("HC_ANALYZE", p["clip"], p["t"], p["alpha"], {k: v for k, v in r.items() if k.startswith(("tip", "sole", "shoe_verts", "body_edges"))})


def summ(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return {"min": min(vals), "max": max(vals), "mean": float(np.mean(vals))} if vals else None


heel_rows = [r for r in out["poses"] if r["alpha"] == 1.0]
summary = {}
for clip in ("Idle", "Walk", "Run"):
    rows = [r for r in heel_rows if r["clip"] == clip]
    if not rows:
        continue
    c = {"frames": len(rows)}
    for k in ("shoe_verts_inside_skin", "max_inside_depth_mm", "body_edges_crossing_shoe", "pelvis_lift_cm",
              "skin_verts_behind_shoe_surface_1mm", "skin_verts_behind_shoe_surface_3mm", "skin_behind_max_mm", "skin_below_floor_verts"):
        c[k] = summ(rows, k)
    # grounded frames: the barefoot clip has that foot's heel or ball skin within 10 mm of its own lowest contact
    for s in ("l", "r"):
        g = [r for r in rows if r.get("barefoot_skin_min_z_mm") and r["barefoot_skin_min_z_mm"][s] < 10.0]
        low = [min(r["tip_z_mm_" + s], r["sole_z_mm_" + s]) for r in g]
        c["grounded_frames_" + s] = len(g)
        c["grounded_lowest_shoe_point_mm_" + s] = {"min": min(low), "max": max(low), "mean": float(np.mean(low))} if low else None
        c["grounded_barefoot_lowest_skin_mm_" + s] = summ([{"v": r["barefoot_skin_min_z_mm"][s]} for r in g], "v") if g else None
        c["strap_gap_p50_mm_" + s] = summ([{"v": r["strap_gap_mm_" + s]["p50"]} for r in rows], "v")
        c["strap_gap_min_mm_" + s] = summ([{"v": r["strap_gap_mm_" + s]["min"]} for r in rows], "v")
        c["strap_gap_max_mm_" + s] = summ([{"v": r["strap_gap_mm_" + s]["max"]} for r in rows], "v")
        c["strap_above_ankle_mm_" + s] = summ([{"v": r["strap_above_ankle_mm_" + s]} for r in rows], "v")
        c["foot_pitch_heel_deg_" + s] = summ(rows, "foot_pitch_heel_deg_" + s)
    c["stretch_p99_max"] = max(r["stretch"]["p99"] for r in rows)
    c["stretch_max"] = max(r["stretch"]["max"] for r in rows)
    c["stretch_max_calf_twist_edges"] = max(r["stretch"]["max_on_calf_twist_edges"] for r in rows)
    c["edges_over_10pct_max"] = max(r["stretch"]["edges_over_10pct"] for r in rows)
    c["stretch_max_abs_mm"] = max(r["stretch"]["max_abs_mm"] for r in rows)
    c["stretch_max_abs_mm_non_twist"] = max(r["stretch"]["max_abs_mm_non_twist"] for r in rows)
    c["edges_over_3mm_max"] = max(r["stretch"]["edges_over_3mm"] for r in rows)
    c["stance_tip_minus_sole_mm"] = None
    summary[clip] = c
out["summary"] = summary

# continuous real-time playback: lowest shoe point per tick (heels skin only needs foot/ball/calf_twist)
cont = {}
for clip, rows in cap.get("continuous", {}).items():
    bare_rows = sorted([p for p in poses if p["clip"] == clip and p["alpha"] == 0.0], key=lambda p: p["t"])
    L = {"Walk": 4.0, "Run": 2.5}[clip]
    bt = np.array([p["t"] for p in bare_rows])
    bare_min = []
    for p in bare_rows:
        Bb = skin(B_CO, B_IDX, B_W, skin_mats(p["bones"]))
        bare_min.append(body_contacts(Bb))
    ticks = []
    for row in rows:
        M = skin_mats(row["bones"])
        P = skin(H_CO, H_IDX, H_W, M)
        tt = row["t"] % L
        j = int(np.argmin(np.abs(bt - tt))) if len(bt) else None
        e = {"t": row["t"], "pelvis_z": row["bones"]["pelvis"][2]}
        for s in ("l", "r"):
            e["low_" + s] = min(lowest(P, regions[s]["tip"]), lowest(P, regions[s]["sole"]))
            e["bare_" + s] = bare_min[j][s] if j is not None else None
        ticks.append(e)
    c = {"ticks": len(ticks), "duration_s": rows[-1]["t"] if rows else 0,
         "pelvis_z_range_cm": [min(t["pelvis_z"] for t in ticks), max(t["pelvis_z"] for t in ticks)] if ticks else None}
    for s in ("l", "r"):
        g = [t for t in ticks if t["bare_" + s] is not None and t["bare_" + s] < 10.0]
        lows = np.array([t["low_" + s] for t in g]) if g else np.array([np.nan])
        c["grounded_ticks_" + s] = len(g)
        c["grounded_low_mm_" + s] = {"min": float(np.nanmin(lows)), "p50": float(np.nanmedian(lows)), "max": float(np.nanmax(lows))}
        c["grounded_ticks_floating_over_10mm_" + s] = int((lows > 10).sum())
        c["grounded_ticks_sinking_below_minus3mm_" + s] = int((lows < -3).sum())
    cont[clip] = c
out["continuous"] = cont
with open("%s/analysis_%s%s.json" % (UE, RUN, "" if cap.get("mesh_kind", "fix") == "fix" else "_shipped"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("HC_ANALYZE summary", json.dumps(summary, default=str)[:4000])
print("HC_ANALYZE continuous", json.dumps(cont, default=str))
