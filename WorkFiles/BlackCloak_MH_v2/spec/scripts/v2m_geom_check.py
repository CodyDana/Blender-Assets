"""3D checks of the SHIPPED BlackCloak_MH_v2 FBX on the male (the parts of TARGET_SPEC.md that are geometry, not pixels).

blender -b --factory-startup --python v2m_geom_check.py -- [--fbx <SK_BlackCloak_MH_v2.fbx>] --out <json>
Re-binds the FBX to the locked fitting body, then measures in the drape/look pose (ARMS_DOWN_V2) and at rest (A-pose):
 * budgets: triangles total / per slot, the *_Sim slot, sliver triangles (min angle < 5 / < 10 deg) per slot;
 * clearance: vertices inside the skin (body + head, every region INCLUDING arms) deeper than 1 mm in ARMS_DOWN_V2;
   at rest with arms ignored (the gate) and with arms counted (info); air distribution to the skin over torso/shoulders;
 * funnel collar: rim (boundary loop above 1.60 m around the head) height at front centre / cheek sides / back, rim
   stand-off from the face, minimum face clearance, outer width at the mouth line and at the funnel base;
 * clasp: centre, diameter, dome height (PCA extents of the clasp slot), distance to the right-shoulder target;
 * hem: lowest z, length of hem lying on the floor (z < 6 mm), hem z profile by azimuth;
 * cloth quality: self-intersecting face pairs (non-adjacent), front fold-over fraction (pilot metric), sim-section
   edge lengths, PinMask coverage, true-scale UV check (UV area / 3D area uniformity) per slot;
 * weights: bones used per slot, max influences.
Thresholds are the TARGET_SPEC ones; every number is reported so a failure says where."""
import sys, os, json, math, argparse
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from v2m_common import *

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument("--fbx", default=DEFAULT_FBX); ap.add_argument("--out", required=True)
ap.add_argument("--skip-selfx", action="store_true")
A = ap.parse_args(argv)
os.chdir(ROOT); A.fbx = os.path.abspath(A.fbx); A.out = os.path.abspath(A.out)
from pipeline import garment_qa as gq
LM = json.load(open(os.path.join(SPEC_OUT, "male_landmarks.json")))
fit = fitbody(); drop_haircards(); arm = fit["armature"]
meshes = import_garment(A.fbx, arm)
R = {"fbx": A.fbx, "meshes": [o.name for o in meshes]}
P = {}


def tri_angles(co, tris):
    a = co[tris[:, 0]]; b = co[tris[:, 1]]; c = co[tris[:, 2]]
    def ang(p, q, r):
        u = q - p; v = r - p
        cs = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12)
        return np.degrees(np.arccos(np.clip(cs, -1, 1)))
    return np.minimum(np.minimum(ang(a, b, c), ang(b, c, a)), ang(c, a, b))


# ---------------------------------------------------------------- per-slot data (rest pose, bind shape)
apply_pose(arm, None)
slots = {}
allco = []; off = 0
for o in meshes:
    co, polys = evaluated_coords(o)
    me = o.data
    me.calc_loop_triangles()
    tris = np.array([t.vertices[:] for t in me.loop_triangles]); tmat = np.array([t.material_index for t in me.loop_triangles])
    names = [m.name if m else "none" for m in me.materials]
    uvl = me.uv_layers[0] if len(me.uv_layers) else None
    for i, n in enumerate(names):
        sel = tmat == i
        t = tris[sel]
        if not len(t): continue
        mins = tri_angles(co, t)
        d = slots.setdefault(n, {"object": o.name, "tris": 0, "sliver_lt5": 0, "sliver_lt10": 0})
        d["tris"] += int(len(t)); d["sliver_lt5"] += int((mins < 5).sum()); d["sliver_lt10"] += int((mins < 10).sum())
        vids = np.unique(t)
        d["z_range"] = [float(co[vids, 2].min()), float(co[vids, 2].max())]
        # true-scale UV: per-triangle sqrt(UV area / 3D area)
        if uvl is not None:
            lt = [lt_ for lt_, s_ in zip(me.loop_triangles, sel) if s_]
            uva = []; a3 = []
            for tri in lt:
                u = [Vector(uvl.data[l].uv) for l in tri.loops]
                uva.append(abs((u[1] - u[0]).cross(u[2] - u[0])) / 2)
                p = [Vector(co[v]) for v in tri.vertices]
                a3.append(((p[1] - p[0]).cross(p[2] - p[0])).length / 2)
            uva = np.array(uva); a3 = np.array(a3); ok = a3 > 1e-8
            r = np.sqrt(uva[ok] / a3[ok])
            d["uv_units_per_m_median"] = float(np.median(r)); d["uv_scale_cv"] = float(r.std() / max(r.mean(), 1e-12))
            d["metres_per_uv_unit"] = float(1.0 / max(np.median(r), 1e-12))
for n, d in slots.items():
    d["sliver_lt5_frac"] = d["sliver_lt5"] / max(d["tris"], 1); d["sliver_lt10_frac"] = d["sliver_lt10"] / max(d["tris"], 1)
R["slots"] = slots
R["tris_total"] = int(sum(d["tris"] for d in slots.values()))
sim = {n: d for n, d in slots.items() if n.endswith("_Sim")}
R["sim_slot"] = list(sim.keys())
R["sim_tris"] = int(sum(d["tris"] for d in sim.values()))
P["slots_le_4"] = len(slots) <= 4
P["one_sim_slot"] = len(sim) == 1
P["tris_total_le_30000"] = R["tris_total"] <= 30000
P["character_le_160000"] = R["tris_total"] + 121892 <= 160000
P["sim_tris_le_6000"] = R["sim_tris"] <= 6000
P["sim_slivers_lt10deg_le_2pct"] = all(d["sliver_lt10_frac"] <= 0.02 for d in sim.values())
P["all_slivers_lt5deg_le_1pct"] = all(d["sliver_lt5_frac"] <= 0.01 for n, d in slots.items() if "clasp" not in n.lower())
P["wool_uv_true_scale_cv_le_0.12"] = all(d.get("uv_scale_cv", 1) <= 0.12 for n, d in slots.items() if "clasp" not in n.lower() and "fray" not in n.lower())

# ---------------------------------------------------------------- weights
wrec = {}
for o in meshes:
    names = {g.index: g.name for g in o.vertex_groups}
    me = o.data
    vslot = {}
    for p in me.polygons:
        for v in p.vertices: vslot.setdefault(v, set()).add(me.materials[p.material_index].name if me.materials[p.material_index] else "none")
    for v in me.vertices:
        ws = {names[g.group]: g.weight for g in v.groups if g.weight > 1e-6 and g.group in names}
        for sn in vslot.get(v.index, {"none"}):
            d = wrec.setdefault(sn, {"bones": {}, "max_influences": 0})
            d["max_influences"] = max(d["max_influences"], len(ws))
            for b in ws: d["bones"][b] = d["bones"].get(b, 0) + 1
R["weights"] = wrec
P["weights_spine_chain_only"] = all(set(d["bones"]) <= set(gq.SPINE_CHAIN) for d in wrec.values())
P["weights_le_2_influences"] = all(d["max_influences"] <= 2 for d in wrec.values())

# ---------------------------------------------------------------- clearance (skin = body + head; regions)
def clearance(stage_ops, ignore):
    apply_pose(arm, stage_ops)
    skin = [fit["body"], fit["head"]]
    col = gq.Collider(skin, [gq.dominant_regions(o) for o in skin])
    out = {"checked": 0, "inside_gt1mm": 0, "deepest_cm": 0.0, "by_region": {}}
    air = []
    for o in meshes:
        co, _ = evaluated_coords(o)
        dist, found, reg = col.signed(co, 0.25)
        cnt = found & ~np.isin(reg, list(ignore))
        depth = np.where(cnt, -dist, 0.0)
        out["checked"] += len(co); out["inside_gt1mm"] += int((depth > 0.001).sum())
        out["deepest_cm"] = max(out["deepest_cm"], float(depth.max() * 100) if len(depth) else 0)
        for r_ in set(reg[found & (dist < -0.001)]):
            out["by_region"][r_] = out["by_region"].get(r_, 0) + int(((reg == r_) & found & (dist < -0.001)).sum())
        # air over torso / shoulders / neck (vertices whose nearest skin is torso or neck and within 5 cm)
        sel = found & np.isin(reg, ["torso", "neck"]) & (dist > -0.001) & (dist < 0.05)
        air += list(dist[sel])
    if air:
        a_ = np.array(air) * 100
        out["air_cm_torso_neck_within5cm_p5_p50_p95"] = [float(np.percentile(a_, q)) for q in (5, 50, 95)]
    return out
R["clearance_arms_down_all_regions"] = clearance(ARMS_DOWN_V2, set())
R["clearance_rest_arms_ignored_gate"] = clearance(None, {"arm"})
R["clearance_rest_all_regions_info"] = clearance(None, set())
P["arms_down_0_inside"] = R["clearance_arms_down_all_regions"]["inside_gt1mm"] == 0
P["rest_0_inside_arms_ignored"] = R["clearance_rest_arms_ignored_gate"]["inside_gt1mm"] == 0
_air = R["clearance_arms_down_all_regions"].get("air_cm_torso_neck_within5cm_p5_p50_p95")
P["air_torso_neck_p5_ge_0.8cm"] = bool(_air) and _air[0] >= 0.8

# ---------------------------------------------------------------- geometry in the look pose
apply_pose(arm, ARMS_DOWN_V2)
G = []; F = []; SL = []; off = 0
for o in meshes:
    co, polys = evaluated_coords(o)
    names = [m.name if m else "none" for m in o.data.materials]
    G.append(co)
    for p, poly in zip(o.data.polygons, polys):
        F.append([v + off for v in poly]); SL.append(names[p.material_index])
    off += len(co)
V = np.concatenate(G); SL = np.array(SL)
_jm = bpy.data.meshes.new("V2M_joined"); _jm.from_pydata(V.tolist(), [], F)   # keeps face order == SL order
bm = bmesh.new(); bm.from_mesh(_jm)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
bm.normal_update()
assert len(bm.faces) == len(SL), (len(bm.faces), len(SL))
# boundary loops (open edges)
bnd = [e for e in bm.edges if len(e.link_faces) == 1]
bpts = np.array([((e.verts[0].co + e.verts[1].co) / 2)[:] for e in bnd]) if bnd else np.zeros((0, 3))
head_c = np.array(LM["neck_02_ring"]["centre_xy"])
# funnel rim: boundary points above 1.60 m within 0.20 m of the neck axis; per azimuth the HIGHEST boundary point
fr = {}
if len(bpts):
    sel = (bpts[:, 2] > 1.60) & (np.hypot(bpts[:, 0] - head_c[0], bpts[:, 1] - head_c[1]) < 0.20)
    rim = bpts[sel]
    def zsel(mask):
        return float(rim[mask][:, 2].max()) if mask.any() else None
    if len(rim):
        fr["rim_points"] = int(len(rim))
        fr["rim_front_centre_z"] = zsel((np.abs(rim[:, 0]) < 0.02) & (rim[:, 1] < 0))
        fr["rim_front_centre_y"] = float(rim[(np.abs(rim[:, 0]) < 0.02) & (rim[:, 1] < 0)][:, 1].min()) if ((np.abs(rim[:, 0]) < 0.02) & (rim[:, 1] < 0)).any() else None
        fr["rim_cheek_r_z"] = zsel((rim[:, 0] > -0.065) & (rim[:, 0] < -0.035) & (rim[:, 1] < -0.04))
        fr["rim_cheek_l_z"] = zsel((rim[:, 0] < 0.065) & (rim[:, 0] > 0.035) & (rim[:, 1] < -0.04))
        fr["rim_back_z"] = zsel((np.abs(rim[:, 0]) < 0.03) & (rim[:, 1] > 0.02))
        fr["rim_side_r_z"] = zsel((rim[:, 0] < -0.07) & (np.abs(rim[:, 1] - head_c[1]) < 0.05))
        fr["rim_side_l_z"] = zsel((rim[:, 0] > 0.07) & (np.abs(rim[:, 1] - head_c[1]) < 0.05))
        fr["rim_top_z"] = float(rim[:, 2].max())
        if fr["rim_front_centre_y"] is not None:
            fr["rim_front_standoff_from_nose_tip_cm"] = (LM["nose_tip"][1] - fr["rim_front_centre_y"]) * 100
# face clearance: funnel vertices (above 1.60, within 0.2 of axis) vs head skin
headbv = BVHTree.FromObject(fit["head"], bpy.context.evaluated_depsgraph_get())
fsel = (V[:, 2] > 1.60) & (np.hypot(V[:, 0] - head_c[0], V[:, 1] - head_c[1]) < 0.20)
dmin = []
for p in V[fsel]:
    hit = headbv.find_nearest(Vector(p), 0.3)
    if hit[0] is not None: dmin.append(hit[3])
if dmin:
    dmin = np.array(dmin) * 100
    fr["funnel_to_head_min_cm"] = float(dmin.min()); fr["funnel_to_head_p5_cm"] = float(np.percentile(dmin, 5))
def xwidth(z, r=0.30, dz=0.006):
    s = V[(np.abs(V[:, 2] - z) < dz) & (np.hypot(V[:, 0] - head_c[0], V[:, 1] - head_c[1]) < r)]
    return [float(s[:, 0].min()), float(s[:, 0].max()), float(s[:, 0].max() - s[:, 0].min())] if len(s) else None
fr["outer_width_at_mouth_line"] = xwidth(LM["stomion_mouth_line"][2], 0.22)
fr["outer_width_at_z1.60"] = xwidth(1.60, 0.25)
fr["outer_width_at_z1.56_base"] = xwidth(1.56, 0.30)
R["funnel"] = fr
def rng(v, lo, hi): return v is not None and lo <= v <= hi
P["rim_front_centre_z_1.680_1.702"] = rng(fr.get("rim_front_centre_z"), 1.680, 1.702)
P["rim_cheeks_1.695_1.725"] = rng(fr.get("rim_cheek_r_z"), 1.695, 1.725) and rng(fr.get("rim_cheek_l_z"), 1.695, 1.725)
P["rim_back_1.725_1.765"] = rng(fr.get("rim_back_z"), 1.725, 1.765)
P["rim_standoff_1.0_3.5cm"] = rng(fr.get("rim_front_standoff_from_nose_tip_cm"), 1.0, 3.5)
P["funnel_face_clear_ge_1.0cm"] = fr.get("funnel_to_head_min_cm", 0) >= 1.0
wm = fr.get("outer_width_at_mouth_line"); P["funnel_width_mouth_0.24_0.29"] = wm is not None and 0.24 <= wm[2] <= 0.29

# clasp
cl = {}
csel = np.array(["clasp" in s_.lower() or "button" in s_.lower() for s_ in SL])
if csel.any():
    vid = np.unique([i for f, c in zip(F, csel) if c for i in f])
    pc = V[vid]; c0 = pc.mean(0)
    u, sv, vt = np.linalg.svd(pc - c0, full_matrices=False)
    ext = [(float(((pc - c0) @ vt[k]).max() - ((pc - c0) @ vt[k]).min())) for k in range(3)]
    cl = {"centre": c0.tolist(), "extents_pca_m": ext, "diameter_m": float((ext[0] + ext[1]) / 2), "dome_height_m": ext[2],
          "axis_normal": vt[2].tolist(), "offset_from_target_m": (c0 - np.array([-0.185, c0[1], 1.48])).tolist()}
R["clasp"] = cl
P["clasp_x_-0.205_-0.165"] = bool(cl) and -0.205 <= cl["centre"][0] <= -0.165
P["clasp_z_1.46_1.50"] = bool(cl) and 1.46 <= cl["centre"][2] <= 1.50
P["clasp_diam_0.050_0.060"] = bool(cl) and 0.050 <= cl["diameter_m"] <= 0.060
P["clasp_dome_0.010_0.018"] = bool(cl) and 0.010 <= cl["dome_height_m"] <= 0.018

# hem
hm = {}
if len(bpts):
    low = bpts[bpts[:, 2] < 0.35]
    if len(low):
        hm["z_min"] = float(low[:, 2].min())
        on = [e for e in bnd if max(e.verts[0].co.z, e.verts[1].co.z) < 0.006]
        hm["hem_length_on_floor_m"] = float(sum(e.calc_length() for e in on))
        hm["hem_length_below_35cm_m"] = float(sum(e.calc_length() for e in bnd if max(e.verts[0].co.z, e.verts[1].co.z) < 0.35))
        az = np.degrees(np.arctan2(low[:, 0], -low[:, 1]))   # 0 = front, +90 = his left, -90 = his right
        hm["lowest_z_by_azimuth_30deg"] = {int(a0): float(low[(az >= a0) & (az < a0 + 30)][:, 2].min()) if ((az >= a0) & (az < a0 + 30)).any() else None for a0 in range(-180, 180, 30)}
R["hem"] = hm
P["hem_zmin_le_0.01"] = hm.get("z_min", 1) <= 0.01
P["hem_pools_ge_0.5m_on_floor"] = hm.get("hem_length_on_floor_m", 0) >= 0.5

# fold-over (pilot metric) on the wool faces in front of the body (y < -0.05 relative to the neck centre), z 0.3..1.3
nrm = []; area = []; cen = []
for f, s_ in zip(bm.faces, SL[:len(bm.faces)]):
    if "clasp" in s_.lower(): continue
    c = f.calc_center_median()
    if 0.3 < c.z < 1.3:
        nrm.append(f.normal[:]); area.append(f.calc_area()); cen.append(c[:])
nrm = np.array(nrm); area = np.array(area); cen = np.array(cen)
fo = {}
if len(cen):
    front = cen[:, 1] < head_c[1] - 0.05
    ny = nrm[front, 1]; fa = area[front]; mj = np.sign((ny * fa).sum())
    fo["front_foldover_area_frac"] = float(fa[np.sign(ny) == -mj].sum() / max(fa.sum(), 1e-9))
    radv = cen[:, :2] - head_c; radv /= np.maximum(np.linalg.norm(radv, axis=1, keepdims=True), 1e-9)
    nrd = (nrm[:, :2] * radv).sum(1); maj = np.sign((nrd * area).sum())
    fo["radial_undercut_area_frac"] = float(area[np.sign(nrd) == -maj].sum() / area.sum())
R["foldover"] = fo
P["front_foldover_ge_0.20"] = fo.get("front_foldover_area_frac", 0) >= 0.20

# self intersections (non-adjacent face pairs), whole garment
if not A.skip_selfx:
    tree = BVHTree.FromBMesh(bm)
    pairs = tree.overlap(tree)
    fv = [set(v.index for v in f.verts) for f in bm.faces]
    bad = [(i, j) for i, j in pairs if i < j and not (fv[i] & fv[j])]
    simf = np.array(["_Sim" in s_ for s_ in SL[:len(bm.faces)]])
    R["self_intersections"] = {"pairs_total": len(bad), "pairs_within_sim": int(sum(1 for i, j in bad if simf[i] and simf[j])),
                               "pairs_sim_vs_skinned": int(sum(1 for i, j in bad if simf[i] != simf[j]))}
    P["self_intersections_0"] = len(bad) == 0

# sim section edge lengths + PinMask coverage (bind shape)
apply_pose(arm, None)
for o in meshes:
    me = o.data
    sidx = [i for i, m in enumerate(me.materials) if m and m.name.endswith("_Sim")]
    if not sidx: continue
    sv = set()
    for p in me.polygons:
        if p.material_index in sidx: sv.update(p.vertices)
    el = [e for e in me.edges if e.vertices[0] in sv and e.vertices[1] in sv]
    co, _ = evaluated_coords(o)
    L_ = np.array([np.linalg.norm(co[e.vertices[0]] - co[e.vertices[1]]) for e in el])
    R["sim_edges_cm_p5_p50_p95"] = [float(np.percentile(L_, q) * 100) for q in (5, 50, 95)]
    ca = me.color_attributes.get("PinMask")
    if ca is not None:
        red = {}
        for p in me.polygons:
            if p.material_index not in sidx: continue
            for li in p.loop_indices:
                red[me.loops[li].vertex_index] = ca.data[li].color[0] if ca.domain == "CORNER" else ca.data[me.loops[li].vertex_index].color[0]
        rv = np.array(list(red.values())); zs = np.array([co[k][2] for k in red.keys()])
        R["pinmask"] = {"sim_verts": int(len(rv)), "frac_pinned_gt0.5": float((rv > 0.5).mean()), "frac_partial": float(((rv > 0.02) & (rv <= 0.5)).mean()),
                        "z_of_pinned_min_max": [float(zs[rv > 0.5].min()), float(zs[rv > 0.5].max())] if (rv > 0.5).any() else None,
                        "active_color": me.color_attributes.active_color.name if me.color_attributes.active_color else None}
R["pass"] = {k: bool(v) for k, v in P.items()}; R["all_pass"] = all(R["pass"].values())
json.dump(R, open(A.out, "w"), indent=1, default=float)
log("GEOM", json.dumps({"tris": R["tris_total"], "sim_tris": R["sim_tris"], "funnel": {k: v for k, v in fr.items() if "width" not in k}, "clasp": cl.get("centre"),
                        "hem": {k: hm.get(k) for k in ("z_min", "hem_length_on_floor_m")}, "fold": fo, "selfx": R.get("self_intersections"),
                        "clear_down": R["clearance_arms_down_all_regions"]["inside_gt1mm"], "pass": R["pass"]}, default=float))
