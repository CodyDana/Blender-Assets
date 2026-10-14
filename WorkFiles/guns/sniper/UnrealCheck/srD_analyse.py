"""SR01 W5, analysis (Blender 5.2 headless, numpy + mathutils): everything measured on what Unreal READ BACK.
Adapted from WorkFiles/guns/smg/UnrealCheck/smD_analyse.py (SR01: the scope as a third static, the clip truth from
sr_clips composed through the bone parents (bipod -> leg -> extension), the deployed-bipod drop, the bipod pose read-back
and the U4 scope pair).

    blender -b --factory-startup --python srD_analyse.py

Inputs: the shipped FBX (Exports/Guns/SR01), srB_verify.json / srB_geometry.json / srB_poses.json (pass B),
srC_render.json / srC_runtime.json (pass C), srE_game.json / srE_physics_samples.json (pass E), Unreal's own FBX
exports in roundtrip/. Writes srD_analysis.json:
  fbx_truth       triangles per node of every shipped FBX; UCX nodes; the triangles Unreal's static import would drop
  triangles       Blender (stage gates) = FBX = Unreal (render data, mesh description, Unreal's FBX export) per LOD
  hulls / C2      Unreal's stored hulls (its FBX export, split into shells): count, vertices; every LOD0 surface sample
                  of the read-back geometry inside their union (300k samples + every vertex)
  uv1             the AUTHORED lightmap UV (plan Q13) as Unreal exports it vs the shipped FBX: inside 0..1, overlap
                  pixels at 64 / 128 (UD4's resolutions) and 1024
  U1 / U3         skeleton names / parents / heads vs the sidecar; axes; sockets vs the sidecar (0.001 cm / 0.001 deg)
  U5              every LOD0..3 vertex at every runtime clip frame (both stock states, sights folded) inside the stored
                  bounds; the engine sphere radii vs the build's (screen sizes)
  U9              runtime (compressed) vs RAW per bone as vertex displacement (mm); RAW vs the authored clips
                  (smg_clips); end pose = start pose; notifies vs the sidecar (+-0.5 frame, no extras)
  U6 / M9         magazine at Mag from the engine attach (rest + every reload frame); seated intersections on the
                  read-back geometry (co-visible LOD pairs); the straight insert path MagInsertStart -> Mag from the
                  engine sockets (0.5 mm) with the catch at its release angle (M4b: 0) and at rest (R36: only the catch)
  U7              the read-back LOD0 at every physics sample (no tunnelling), and every vertex of the dropped SKs
                  (extended and folded) inside the component's RUNTIME bounds (the W4 review addition)
"""
import bpy, bmesh, json, math, re, sys, time
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_common as C  # noqa: E402
ROOT = C.ROOT
sys.path.insert(0, str(ROOT / "Scripts" / "guns" / "sniper"))
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
t0 = time.time()
B = json.loads((HERE / "srB_verify.json").read_text())
GEO = json.loads((HERE / "srB_geometry.json").read_text())
PB = json.loads((HERE / "srB_poses.json").read_text())
CR = json.loads((HERE / "srC_render.json").read_text())
RTP = json.loads((HERE / "srC_runtime.json").read_text())
BIND_RT = RTP["clips"].pop("_bind", None)
SC = C.sidecar_sk()
GATES = C.GATES
res = {}
F = np.diag([1.0, -1.0, 1.0])


def dump():
    res["seconds"] = round(time.time() - t0, 1)
    (HERE / "srD_analysis.json").write_text(json.dumps(res, indent=1, default=float))


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mesh_np(ob):
    me = ob.data
    me.calc_loop_triangles()
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    V = V @ M[:3, :3].T + M[:3, 3]
    T = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", T)
    return V, T.reshape(-1, 3)


def to_ue_cm(V_m):
    """Blender world (metres, as imported from an Unreal FBX) -> Unreal component frame (cm, y flipped)."""
    return (V_m * 100.0) @ F


def quat_m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_q(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return [x, y, z, w]


def tf(arr):
    return quat_m(arr[3:7]), np.array(arr[:3], float)


def bvh(V, T):
    return BVHTree.FromPolygons([tuple(p) for p in V], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def tri_area_drop(V_cm, T):
    a = V_cm.astype(np.float32)
    cr = np.cross(a[T[:, 1]] - a[T[:, 2]], a[T[:, 0]] - a[T[:, 2]]).astype(np.float64)
    return int(((cr ** 2).sum(1) < 1e-8).sum())


def lod_of(name):
    m = re.search(r"LOD(\d+)", name)
    return int(m.group(1)) if m else 0


def uv_overlap(tris, res_px):
    """Strict-interior pixel centres covered by more than one triangle (shared edges are not overlap)."""
    grid = np.zeros((res_px, res_px), np.uint16)
    for a, b, c in tris:
        mn = np.floor(np.minimum(np.minimum(a, b), c) * res_px).astype(int)
        mx = np.ceil(np.maximum(np.maximum(a, b), c) * res_px).astype(int)
        mn = np.clip(mn, 0, res_px - 1)
        mx = np.clip(mx, 0, res_px)
        if mx[0] <= mn[0] or mx[1] <= mn[1]:
            continue
        xs = (np.arange(mn[0], mx[0]) + 0.5) / res_px
        ys = (np.arange(mn[1], mx[1]) + 0.5) / res_px
        X, Y = np.meshgrid(xs, ys)
        w0 = (b[0] - X) * (c[1] - Y) - (c[0] - X) * (b[1] - Y)
        w1 = (c[0] - X) * (a[1] - Y) - (a[0] - X) * (c[1] - Y)
        w2 = (a[0] - X) * (b[1] - Y) - (b[0] - X) * (a[1] - Y)
        ins = ((w0 > 0) & (w1 > 0) & (w2 > 0)) | ((w0 < 0) & (w1 < 0) & (w2 < 0))
        grid[mn[1]:mx[1], mn[0]:mx[0]] += ins.astype(np.uint16)
    return int((grid > 1).sum()), float((grid > 0).mean())


def uv1_overlap_tris(me, res_px=128):
    """the UV1 triangles that share a strictly-interior pixel centre at res_px (diagnosis of U8)."""
    lay = me.uv_layers[1]
    UV = np.empty(len(me.loops) * 2)
    lay.data.foreach_get("uv", UV)
    UV = UV.reshape(-1, 2)
    LT = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", LT)
    tris = UV[LT.reshape(-1, 3)]
    cover = {}
    for ti, (a, b, c) in enumerate(tris):
        mn = np.clip(np.floor(np.minimum(np.minimum(a, b), c) * res_px).astype(int), 0, res_px - 1)
        mx = np.clip(np.ceil(np.maximum(np.maximum(a, b), c) * res_px).astype(int), 0, res_px)
        for ix in range(mn[0], mx[0]):
            for iy in range(mn[1], mx[1]):
                X, Y = (ix + 0.5) / res_px, (iy + 0.5) / res_px
                w0 = (b[0] - X) * (c[1] - Y) - (c[0] - X) * (b[1] - Y)
                w1 = (c[0] - X) * (a[1] - Y) - (a[0] - X) * (c[1] - Y)
                w2 = (a[0] - X) * (b[1] - Y) - (b[0] - X) * (a[1] - Y)
                if (w0 > 0 and w1 > 0 and w2 > 0) or (w0 < 0 and w1 < 0 and w2 < 0):
                    cover.setdefault((ix, iy), []).append(ti)
    V = np.array([v.co[:] for v in me.vertices])
    VT = np.array([t.vertices[:] for t in me.loop_triangles])
    out = []
    for px, ts in cover.items():
        if len(ts) > 1:
            out.append({"px": list(px), "tris": [{"uv": tris[t].round(6).tolist(), "uv_area2": float(abs((tris[t][1][0] - tris[t][0][0]) * (tris[t][2][1] - tris[t][0][1]) - (tris[t][2][0] - tris[t][0][0]) * (tris[t][1][1] - tris[t][0][1]))),
                                                  "centre_ue_cm": to_ue_cm(V[VT[t]].mean(0)[None, :])[0].round(3).tolist()} for t in ts]})
    return out


def uv1_stats(me):
    if len(me.uv_layers) < 2:
        return {"layers": [l.name for l in me.uv_layers], "uv1": None}
    lay = me.uv_layers[1]
    UV = np.empty(len(me.loops) * 2)
    lay.data.foreach_get("uv", UV)
    UV = UV.reshape(-1, 2)
    LT = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", LT)
    tris = UV[LT.reshape(-1, 3)]
    out = {"layers": [l.name for l in me.uv_layers], "layer": lay.name,
           "u_range": [float(UV[:, 0].min()), float(UV[:, 0].max())], "v_range": [float(UV[:, 1].min()), float(UV[:, 1].max())],
           "inside_0_1": bool(UV.min() >= -1e-6 and UV.max() <= 1 + 1e-6)}
    for px in (64, 128, 1024):
        o, cov = uv_overlap(tris, px)
        out[f"overlap_px_{px}"] = o
        out[f"coverage_{px}"] = round(cov, 4)
    return out


# ====================================================================== 1. FBX truth
truth, truth_uv1 = {}, {}
for fn in ("SK_SR01.fbx", "SK_SR01_LOD1.fbx", "SK_SR01_LOD2.fbx", "SK_SR01_LOD3.fbx", "SM_SR01.fbx", "SM_SR01_Mag.fbx",
           f"{C.SCOPE}.fbx"):
    clear()
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    rec = {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        V, T = mesh_np(ob)
        if ob.name.startswith("UCX_"):
            rec.setdefault("_ucx", []).append({"name": ob.name, "verts": len(ob.data.vertices)})
            continue
        rec[ob.name] = {"triangles": int(len(T)), "unreal_import_drops": tri_area_drop(V * 100.0, T)}
        if fn.startswith("SM_"):
            truth_uv1[ob.name] = uv1_stats(ob.data)
    truth[fn] = rec
res["fbx_truth"] = truth
res["fbx_uv1"] = truth_uv1
dump()

# ====================================================================== 2. Unreal round-trip exports (statics)
rt, shells, uv1 = {}, {}, {}


def split_shells(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, vs = [f], set()
        while stack:
            g = stack.pop()
            if g.index in seen:
                continue
            seen.add(g.index)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        stack.append(h)
            for v in g.verts:
                vs.add(v.index)
        out.append(to_ue_cm(np.array([tuple(bm.verts[i].co) for i in vs])))
    bm.free()
    return out


def planes(pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    c = pts.mean(0)
    N, D = [], []
    for f in bm.faces:
        n = np.array(f.normal)
        if np.linalg.norm(n) < 1e-9:
            continue
        d = n @ np.array(f.verts[0].co)
        if n @ c - d > 0:
            n, d = -n, -d
        if (pts @ n - d).max() > 1e-4:      # not a supporting plane (sliver face, wrong normal): skip
            continue
        N.append(n)
        D.append(d)
    bm.free()
    return np.array(N), np.array(D)


for name in ("SM_SR01", "SM_SR01_Mag", C.SCOPE):
    clear()
    bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / f"ue_{name}.fbx"))
    lods = {}
    ucx = []
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        if ob.name.startswith("UCX_"):
            ucx += split_shells(ob)
            continue
        me = ob.data
        me.calc_loop_triangles()
        lods[ob.name] = {"lod": lod_of(ob.name), "triangles": len(me.loop_triangles)}
        uv1[ob.name] = uv1_stats(me)
        if uv1[ob.name].get("overlap_px_128"):
            uv1[ob.name]["overlap_detail_128"] = uv1_overlap_tris(me, 128)
    shells[name] = ucx
    rt[name] = lods
res["roundtrip_static"] = rt
res["uv1"] = uv1
res["hull_shells"] = {k: {"count": len(v), "vertices": [int(len(s)) for s in v]} for k, v in shells.items()}
dump()

# ---- C2: dense LOD0 samples of the read-back geometry inside the stored hulls
rng = np.random.default_rng(7)
c2 = {}
for name in ("SM_SR01", "SM_SR01_Mag", C.SCOPE):
    HP = [planes(s) for s in shells[name]]
    P = np.array(GEO[name][0]["positions"])
    Tr = np.array(GEO[name][0]["triangles"])[:, -3:]
    A, Bq, Cq = P[Tr[:, 0]], P[Tr[:, 1]], P[Tr[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(Bq - A, Cq - A), axis=1)
    n = 300000
    idx = rng.choice(len(Tr), size=n, p=area / area.sum())
    u = rng.random(n); v = rng.random(n); f = u + v > 1; u[f] = 1 - u[f]; v[f] = 1 - v[f]
    S = A[idx] + (Bq[idx] - A[idx]) * u[:, None] + (Cq[idx] - A[idx]) * v[:, None]
    S = np.vstack([S, P])
    out = np.full(len(S), np.inf)
    for N, D in HP:
        out = np.minimum(out, np.maximum((S @ N.T - D).max(1), 0))
    c2[name] = {"samples": int(len(S)), "outside_gt_0.001cm": int((out > 1e-3).sum()), "max_outside_mm": float(out.max() * 10)}
    bad = out > 1e-3
    if bad.any():
        Sb = S[bad]
        c2[name]["outside_bbox_cm"] = [Sb.min(0).round(2).tolist(), Sb.max(0).round(2).tolist()]
        c2[name]["outside_x_hist_cm"] = {f"{int(b)}": int(c) for b, c in zip(*np.unique(np.floor(Sb[:, 0] / 10) * 10, return_counts=True))}
        c2[name]["shell_bboxes_cm"] = [[s_.min(0).round(2).tolist(), s_.max(0).round(2).tolist()] for s_ in shells[name]]
        c2[name]["shell_vertex_counts"] = [int(len(s_)) for s_ in shells[name]]
res["C2"] = c2
dump()

# ====================================================================== 3. skeletal round trip: per-bone vertex sets
clear()
bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / "ue_SK_SR01.fbx"))
sk_lods, bone_verts = {}, {}
for ob in sorted(bpy.data.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    V, T = mesh_np(ob)
    Vu = to_ue_cm(V)
    me = ob.data
    groups = {g.index: g.name for g in ob.vertex_groups}
    owner = np.full(len(me.vertices), -1)
    for v in me.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        if best is not None:
            owner[v.index] = best.group
    names = np.array([groups.get(int(i), "") for i in owner])
    lv = lod_of(ob.name)
    sk_lods[lv] = {"V": Vu, "T": T, "bone": names, "name": ob.name}
    bone_verts[lv] = {b: Vu[names == b] for b in set(names.tolist())}
res["sk_roundtrip"] = {f"LOD{k}": {"object": v["name"], "triangles": int(len(v["T"])), "vertices": int(len(v["V"])),
                                   "bones_weighted": sorted(set(v["bone"].tolist()))} for k, v in sorted(sk_lods.items())}
bb = B["sk_bounds"]["bounds"]
lo = np.array(bb["origin"]) - np.array(bb["extent"])
hi = np.array(bb["origin"]) + np.array(bb["extent"])
res["sk_roundtrip"]["bind_aabb_cm"] = [sk_lods[0]["V"].min(0).round(4).tolist(), sk_lods[0]["V"].max(0).round(4).tolist()]
res["sk_roundtrip"]["stored_bounds_cm"] = [lo.round(4).tolist(), hi.round(4).tolist()]
dump()

# ====================================================================== 4. triangles: Blender = FBX = Unreal
gj = {f: json.loads((GATES / f).read_text()) for f in ("rig_export.json", "mag.json", "game.json", "scope_export.json")}


def gate_val(gfile, prefix):
    for g in gj[gfile]["gates"]:
        if g["name"].startswith(prefix):
            return g["value"]
    return None


bl_sk = gate_val("rig_export.json", "LOD triangles Blender = FBX (SK)")
bl_sm = {f"SM_SR01_LOD{i}": v for i, v in enumerate(gate_val("game.json", "B8 LOD triangles")["with_merged_mag"])}
bl_sc = gate_val("scope_export.json", "re-imported LOD triangles")["build"]
bl_mag = gate_val("mag.json", "mag qa_check")
rt_by_lod = {k: {v["lod"]: v["triangles"] for v in d.values()} for k, d in rt.items()}


def fbx_tris(fn, lod=None):
    rec = {k: v for k, v in truth[fn].items() if not k.startswith("_")}
    if lod is None:
        return sum(v["triangles"] for v in rec.values()), sum(v["unreal_import_drops"] for v in rec.values())
    hit = [v for k, v in rec.items() if lod_of(k) == lod]
    return hit[0]["triangles"], hit[0]["unreal_import_drops"]


tri = {"SK_SR01": [], "SM_SR01": [], "SM_SR01_Mag": [], C.SCOPE: []}
for i, fn in enumerate(["SK_SR01.fbx", "SK_SR01_LOD1.fbx", "SK_SR01_LOD2.fbx", "SK_SR01_LOD3.fbx"]):
    ft, fd = fbx_tris(fn)
    tri["SK_SR01"].append({"lod": i, "blender": bl_sk[fn][0], "fbx": ft, "unreal_export": res["sk_roundtrip"][f"LOD{i}"]["triangles"],
                            "predicted_import_drops": fd})
for i in range(4):
    ft, fd = fbx_tris("SM_SR01.fbx", i)
    tri["SM_SR01"].append({"lod": i, "blender": bl_sm[f"SM_SR01_LOD{i}"], "fbx": ft, "unreal_render": B["SM_SR01"]["lod_triangles"][i],
                            "unreal_mesh_description": len(GEO["SM_SR01"][i]["triangles"]), "unreal_export": rt_by_lod["SM_SR01"][i],
                            "predicted_import_drops": fd})
    ft, fd = fbx_tris("SM_SR01_Mag.fbx", i)
    tri["SM_SR01_Mag"].append({"lod": i, "blender": bl_mag["triangles"][f"SM_SR01_Mag_LOD{i}"], "fbx": ft,
                                "unreal_render": B["SM_SR01_Mag"]["lod_triangles"][i],
                                "unreal_mesh_description": len(GEO["SM_SR01_Mag"][i]["triangles"]),
                                "unreal_export": rt_by_lod["SM_SR01_Mag"][i], "predicted_import_drops": fd})
for i in range(3):
    ft, fd = fbx_tris(f"{C.SCOPE}.fbx", i)
    tri[C.SCOPE].append({"lod": i, "blender": bl_sc[f"{C.SCOPE}_LOD{i}"], "fbx": ft, "unreal_render": B[C.SCOPE]["lod_triangles"][i],
                         "unreal_mesh_description": len(GEO[C.SCOPE][i]["triangles"]), "unreal_export": rt_by_lod[C.SCOPE][i],
                         "predicted_import_drops": fd})
for k, rows in tri.items():
    for r in rows:
        vals = [v for kk, v in r.items() if kk not in ("lod", "predicted_import_drops")]
        r["equal"] = len(set(vals)) == 1
res["triangles"] = tri
dump()

# ====================================================================== 5. U1 / U3
sk = B["skeleton"]
u1 = {"bones": sk["order"], "parents": sk["parents"], "mesh_bones": sk["mesh_bones"]}
exp_par = {n: v["parent"] for n, v in SC["bones_rest"].items()}
u1["names_match"] = sorted(n for n in sk["order"] if n != "root") == sorted(exp_par)
u1["parents_match"] = all(sk["parents"].get(n) == p for n, p in exp_par.items())
head_err = {n: float(np.abs(np.array(sk["ref_comp"][n][:3]) - np.array(v["head_cm"])).max()) for n, v in SC["bones_rest"].items()}
u1["max_head_err_cm"] = max(head_err.values())
root = sk["ref_comp"]["root"]
u1["root"] = root
u1["root_scale_1"] = all(abs(x - 1) < 1e-6 for x in root[7:10])
rots = {n: float(np.degrees(2 * math.acos(min(1.0, abs(sk["ref_comp"][n][6]))))) for n in sk["order"]}
u1["max_bone_rest_rotation_deg"] = max(rots.values())
ss = B["sk_sockets"]
mz, gp, ej, sg = (np.array(ss[k]["component"][:3]) for k in ("Muzzle", "Grip", "ShellEject", "Rail_Top"))
u1["axes"] = {"muzzle_plusX_cm": float(mz[0] - gp[0]), "muzzle_on_bore_y_cm": float(mz[1]),
              "rail_top_above_bore_cm": float(sg[2] - mz[2]), "ejection_port_right_plusY_cm": float(ej[1]),
              "bolt_rest_x_axis_component": quat_m(sk["ref_comp"]["bolt"][3:7])[:, 0].round(6).tolist()}
u1["pass"] = bool(u1["names_match"] and u1["parents_match"] and u1["max_head_err_cm"] <= 1e-3 and u1["root_scale_1"]
                  and u1["max_bone_rest_rotation_deg"] < 1e-3 and mz[0] - gp[0] > 20 and abs(mz[1]) < 1e-3 and sg[2] > mz[2] and ej[1] > 0)
res["U1"] = u1
u3 = {}
for s in SC["sockets"]:
    got = ss.get(s["name"])
    if got is None:
        u3[s["name"]] = "MISSING"
        continue
    Rg, tg = tf(got["component"])
    Re = quat_m(s["unreal_component"]["quaternion_xyzw"])
    dl = float(np.abs(tg - np.array(s["unreal_component"]["location_cm"])).max())
    R = Rg.T @ Re
    ang = math.degrees(math.atan2(0.5 * np.linalg.norm([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]), 0.5 * (np.trace(R) - 1)))
    u3[s["name"]] = {"bone": got["bone"], "bone_ok": got["bone"] == s["bone"], "loc_err_cm": dl, "rot_err_deg": ang,
                     "scale1": all(abs(x - 1) < 1e-9 for x in got["relative"][7:10]),
                     "outer_ok": "SK_SR01" in got["outer"]}
extra = sorted(set(ss) - {s["name"] for s in SC["sockets"]})
res["U3"] = {"sockets": u3, "extra": extra, "worst_loc_cm": max(v["loc_err_cm"] for v in u3.values() if isinstance(v, dict)),
             "worst_rot_deg": max(v["rot_err_deg"] for v in u3.values() if isinstance(v, dict)),
             "pass": bool(not extra and all(isinstance(v, dict) and v["bone_ok"] and v["loc_err_cm"] <= 1e-3 and v["rot_err_deg"] <= 1e-3
                                              and v["scale1"] and v["outer_ok"] for v in u3.values()))}
dump()

# ====================================================================== 6. runtime bone poses (socket-named bones)
# GetSocketTransform(<bone>) answers with a SOCKET of the same name when one exists (FName lookups are case-insensitive):
# 'trigger' -> socket Trigger (on trigger), 'selector' -> Selector (on selector), 'stock' -> Stock (on BODY). Those bones
# are recovered from a socket ON the bone: bone = socket x relative^-1 (pass B's socket relative transforms).
lower = {k.lower(): k for k in ss}
CLASH = {}
for b in RTP["names"]:
    if b.lower() in lower:
        on_bone = sorted(k for k, v in ss.items() if v["bone"] == b)
        CLASH[b] = on_bone[0] if on_bone else None
res["socket_named_bones"] = CLASH


def bone_from_socket(sock_T, sname):
    rel = ss[sname]["relative"]
    Rr, tr_ = quat_m(rel[3:7]), np.array(rel[:3])
    Rs_, ts_ = quat_m(sock_T[3:7]), np.array(sock_T[:3])
    Rb = Rs_ @ Rr.T
    return list(ts_ - Rb @ tr_) + list(mat_q(Rb))


def fix_frame(fr):
    for b, sname in CLASH.items():
        if sname is not None and "sockets" in fr:
            fr["bones"][b] = bone_from_socket(fr["sockets"][sname], sname)


for clip in RTP["clips"].values():
    for fr in clip["frames"].values():
        fix_frame(fr)
if BIND_RT:
    fix_frame(BIND_RT)
    res["bind_runtime_vs_ref_cm"] = max(float(np.abs(np.array(BIND_RT["bones"][b][:3]) - np.array(sk["ref_comp"][b][:3])).max())
                                        for b in RTP["names"])

# ====================================================================== 7. poses: U9 / U5
ref = {n: tf(v) for n, v in sk["ref_comp"].items()}


def deform(Rt, tt, n):
    Rr, tr = ref[n]
    return Rt @ Rr.T, tt - Rt @ Rr.T @ tr          # p' = M p + c


def disp(Ma, ca, Mb, cb, pts):
    if len(pts) == 0:
        return 0.0
    return float(np.linalg.norm(pts @ (Ma - Mb).T + (ca - cb), axis=1).max())


def posed(d, fr):
    P = d["V"].copy()
    for b in set(d["bone"].tolist()):
        if not b:
            continue
        m = d["bone"] == b
        Mc, cc = deform(*tf(fr["bones"][b]), b)
        P[m] = d["V"][m] @ Mc.T + cc
    return P


import sr_clips as CL  # noqa: E402
authored = CL.all_clips()
heads_mm = {n: np.array(v["head_mm"]) for n, v in SC["bones_rest"].items()}
parent_of = {n: v["parent"] for n, v in SC["bones_rest"].items()}


def truth_world(vals):
    """sr_clips values -> each bone's world motion (4x4, Blender mm): the bone's basis about its own head, composed
    through its parents (bipod -> leg -> extension)."""
    bas = CL.basis_from(vals)
    out = {}

    def w(n):
        if n in out:
            return out[n]
        h = heads_mm[n]
        A = np.eye(4)
        if n in bas:
            Th, Ti = np.eye(4), np.eye(4)
            Th[:3, 3], Ti[:3, 3] = h, -h
            A = Th @ bas[n] @ Ti
        par = parent_of.get(n)
        out[n] = (w(par) @ A) if par in heads_mm else A
        return out[n]
    for n in heads_mm:
        w(n)
    return out
u9 = {}
u5 = {"stored_lo_cm": lo.tolist(), "stored_hi_cm": hi.tolist(), "clips": {}}
for cname, rec in RTP["clips"].items():
    fps = rec["fps"]
    frames = rec["frames"]
    raw = PB["clips"][cname]["RAW"]
    comp = PB["clips"][cname]["COMPRESSED"]
    worst_c, worst_raw_truth, worst_ap = 0.0, 0.0, 0.0
    outside, worst_out = 0, 0.0
    afr = dict(authored[cname][0])
    for fs, fr in frames.items():
        f = int(fs)
        key = f"{f / fps:.6f}"
        for b in RTP["names"]:
            if b == "root":
                continue
            pts = bone_verts[0].get(b, np.zeros((0, 3)))
            Mc, cc = deform(*tf(fr["bones"][b]), b)
            if key in raw:
                Mr, cr = deform(*tf(raw[key][b]), b)
                worst_c = max(worst_c, disp(Mc, cc, Mr, cr, pts) * 10)
                Ma, ca = deform(*tf(comp[key][b]), b)
                worst_ap = max(worst_ap, disp(Mc, cc, Ma, ca, pts) * 10)
                vals = afr.get(f)
                if vals is not None and b in heads_mm:
                    Wt = truth_world(vals)[b]
                    Mt = Wt[:3, :3]
                    ct = Wt[:3, 3]
                    Mt_u = F @ Mt @ F
                    ct_u = (F @ ct) / 10.0
                    worst_raw_truth = max(worst_raw_truth, disp(Mr, cr, Mt_u, ct_u, pts) * 10)
        for lv, d in sk_lods.items():
            Pp = posed(d, fr)
            o = np.maximum(lo - Pp, 0).max(1) + np.maximum(Pp - hi, 0).max(1)
            outside += int((o > 1e-4).sum())
            worst_out = max(worst_out, float(o.max()))
    first = frames["0"]["bones"]
    last = frames[str(max(int(k) for k in frames))]["bones"]
    end_vs_start = max(disp(*deform(*tf(last[b]), b), *deform(*tf(first[b]), b), bone_verts[0].get(b, np.zeros((0, 3)))) * 10
                       for b in RTP["names"] if b != "root")
    end_vs_bind = {b: disp(*deform(*tf(last[b]), b), np.eye(3), np.zeros(3), bone_verts[0].get(b, np.zeros((0, 3)))) * 10
                   for b in RTP["names"] if b != "root"}
    start_vs_bind = {b: disp(*deform(*tf(first[b]), b), np.eye(3), np.zeros(3), bone_verts[0].get(b, np.zeros((0, 3)))) * 10
                     for b in RTP["names"] if b != "root"}
    sc_n = [(n["name"], n["frame"]) for n in SC["notifies"] if n["clip"] == cname]
    got_n = [(e["name"], e["time"] * fps) for e in B["clips"][cname]["notifies"]]
    match = []
    for nm, fr_ in sc_n:
        cand = [g for g in got_n if g[0] == nm and abs(g[1] - fr_) <= 0.5]
        match.append({"name": nm, "frame": fr_, "engine_frame": round(cand[0][1], 4) if cand else None})
    u9[cname] = {"frames": len(frames), "engine_num_frames": B["clips"][cname]["num_frames"],
                 "play_length_s": B["clips"][cname]["play_length"], "authored_frames": authored[cname][0][-1][0],
                 "compression": B["clips"][cname]["compression"],
                 "max_runtime_vs_raw_mm": round(worst_c, 5), "max_runtime_vs_animpose_compressed_mm": round(worst_ap, 5),
                 "max_raw_vs_authored_mm": round(worst_raw_truth, 5), "end_vs_start_mm": round(end_vs_start, 5),
                 "end_vs_bind_mm": {k: round(v, 4) for k, v in end_vs_bind.items() if v > 1e-3},
                 "start_vs_bind_mm": {k: round(v, 4) for k, v in start_vs_bind.items() if v > 1e-3},
                 "notifies": match, "notifies_extra": len(got_n) - len(sc_n),
                 "notifies_ok": all(m["engine_frame"] is not None for m in match) and len(got_n) == len(sc_n)}
    u5["clips"][cname] = {"vertices_outside": outside, "worst_outside_cm": worst_out}
res["U9"] = u9
# the engine's sphere radii vs the build's (the screen sizes were derived from them)
gr = gj["game.json"].get("bounds_radius_m") or {}
re_ = gate_val("game.json", "LOD-pop") or {}
u5["radii"] = {"SK_engine_cm": B["sk_bounds"]["bounds"]["radius"], "SK_build_cm": (re_.get("SK_engine_radius_m") or 0) * 100,
               "SM_engine_cm": B["SM_SR01"]["bounds"]["radius"], "SM_build_cm": (re_.get("twin_radius_m") or 0) * 100,
               "Mag_engine_cm": B["SM_SR01_Mag"]["bounds"]["radius"], "Mag_build_cm": None,
               "Scope_engine_cm": B[C.SCOPE]["bounds"]["radius"],
               "Scope_build_cm": (gj["scope_export.json"]["screen_sizes"].get("engine_radius_m") or 0) * 100,
               "game_json_bounds_radius_m": gr}
u5["extension_enters_lod_radius"] = {"imported_radius_cm": B["sk_bounds"]["imported"]["radius"], "extended_radius_cm": B["sk_bounds"]["bounds"]["radius"],
                                     "note": "the SK's engine bounds (LOD selection) include the bounds extension"}
res["U5_bounds"] = u5
dump()

# ====================================================================== 8. U6 / M9: the magazine at Mag
magL = [(np.array(GEO["SM_SR01_Mag"][i]["positions"]), np.array(GEO["SM_SR01_Mag"][i]["triangles"])[:, -3:]) for i in range(4)]


def affine_from_basis(bs):
    o = np.array(bs["o"])
    M = np.stack([np.array(bs[k]) - o for k in "xyz"], axis=1)
    return M, o


def place(Pm, R, t):
    return Pm @ R.T + t


def pairs(A, B_):
    return A.overlap(B_)


gun_bvh = {lv: bvh(d["V"], d["T"]) for lv, d in sk_lods.items()}
att = CR["attach_SK_rest"]
M, o = affine_from_basis(att["mag_to_gun_basis"])
Rs, ts = tf(att["socket_Mag"])
u6 = {"rest": {"affine_orthonormal_err": float(np.abs(M.T @ M - np.eye(3)).max()),
               "attached_vs_socket_cm": float(np.abs(o - ts).max()), "attached_vs_socket_rot": float(np.abs(M - Rs).max()),
               "relative_to_socket": att["relative_to_socket"], "mag_world_scale": att["mag_world_scale"],
               "socket_vs_sidecar_cm": float(np.abs(ts - np.array(next(s for s in SC["sockets"] if s["name"] == "Mag")["unreal_component"]["location_cm"])).max())}}
seat = {}
for lg, lm in ((0, 0), (1, 1), (0, 1), (1, 0), (2, 2), (3, 3), (1, 2), (2, 1), (2, 3), (3, 2)):
    Pm, Tm = magL[lm]
    seat[f"gun LOD{lg} / mag LOD{lm}"] = len(pairs(gun_bvh[lg], bvh(place(Pm, M, o), Tm)))
u6["seated_intersecting_pairs"] = seat
rl = {}
for cname in ("A_SR01_Reload", "A_SR01_ReloadEmpty"):
    frames = RTP["clips"][cname]["frames"]
    worst_attach = 0.0
    hit_frames = []
    for fs, fr in sorted(frames.items(), key=lambda kv: int(kv[0])):
        Rm, tm = tf(fr["Mag_socket"])
        Ma, oa = affine_from_basis(fr["mag_attached"])
        worst_attach = max(worst_attach, float(np.abs(oa - tm).max()), float(np.abs(Ma - Rm).max()))
        P = posed(sk_lods[0], fr)
        pr_ = pairs(bvh(P, sk_lods[0]["T"]), bvh(place(magL[0][0], Rm, tm), magL[0][1]))
        npairs = len(pr_)
        if npairs:
            own = sorted({str(sk_lods[0]["bone"][sk_lods[0]["T"][i][0]]) for i, _ in pr_})
            mb = bvh(place(magL[0][0], Rm, tm), magL[0][1])
            depth = 0.0
            for vi in np.unique(sk_lods[0]["T"][[i for i, _ in pr_]].ravel()):
                loc, nrm, _ix, dist = mb.find_nearest(P[vi])
                if loc is not None and (np.array(P[vi]) - np.array(loc)) @ np.array(nrm) < 0:
                    depth = max(depth, float(dist))
            own = own + [f"depth_mm={depth * 10:.4f}"]
            Pm_ = place(magL[0][0], Rm, tm)
            cen = [P[sk_lods[0]["T"][i]].mean(0).round(3).tolist() for i, _ in pr_[:4]]
            mcen = [Pm_[magL[0][1][j]].mean(0).round(3).tolist() for _, j in pr_[:4]]
            hit_frames.append([int(fs), npairs, own, cen, mcen])
    rl[cname] = {"frames": len(frames), "attached_vs_socket_max": worst_attach, "frames_with_intersections": hit_frames}
u6["reload_frames"] = rl
# the straight insert path from the engine sockets (gun component frame): MagInsertStart -> Mag, rotation constant
Ri, ti = tf(att["socket_MagInsertStart"])
insert_mm = float(np.linalg.norm(ts - ti) * 10)
rot_diff_deg = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rs @ Ri.T) - 1) / 2))))
axis_u = (ts - ti) / max(np.linalg.norm(ts - ti), 1e-12)
n_ins = max(1, int(math.ceil(insert_mm / 0.5)))
steps = [ti + (ts - ti) * k / n_ins for k in range(n_ins + 1)]
# the catch at its release angle: mag_release rotated about its head (Blender -11 deg about Y = Unreal pitch +11)
rel_deg = C.abp_tables()["SR01"]["release_deg"]
a_ = math.radians(rel_deg)
Ry_bl = np.array([[math.cos(a_), 0, math.sin(a_)], [0, 1, 0], [-math.sin(a_), 0, math.cos(a_)]])
R_ue = F @ Ry_bl @ F
head = np.array(sk["ref_comp"]["mag_release"][:3])
path = {"insert_mm": insert_mm, "insert_axis_vs_mag_z": float(axis_u @ Rs[:, 2]), "rotation_constant_deg": rot_diff_deg,
        "steps": len(steps), "catch_release_deg_blender": rel_deg, "lods": {}}
for lv in (0, 1):
    d = sk_lods[lv]
    Vr = d["V"].copy()
    m = d["bone"] == "mag_release"
    Vr[m] = (d["V"][m] - head) @ R_ue.T + head
    b_rel, b_rest = bvh(Vr, d["T"]), gun_bvh[lv]
    tri_bone = d["bone"][d["T"][:, 0]]
    released, rest_hits, rest_noncatch = [], [], []
    for k, tk in enumerate(steps):
        bm_ = bvh(place(magL[lv][0], Rs, tk), magL[lv][1])
        pr = pairs(b_rel, bm_)
        if pr:
            released.append([k, len(pr)])
        pa = pairs(b_rest, bm_)
        if pa:
            owners = sorted({str(tri_bone[i]) for i, _ in pa})
            rest_hits.append([k, len(pa), owners])
            if any(ow != "mag_release" for ow in owners):
                rest_noncatch.append(k)
    path["lods"][f"LOD{lv}"] = {"released_intersecting_steps": released, "rest_steps_with_contact": len(rest_hits),
                                "rest_contact_parts": sorted({ow for h in rest_hits for ow in h[2]}),
                                "rest_contact_range_mm": [round(rest_hits[0][0] * insert_mm / n_ins, 2), round(rest_hits[-1][0] * insert_mm / n_ins, 2)] if rest_hits else None,
                                "rest_noncatch_steps": rest_noncatch}
u6["insert_path"] = path
res["U6_M9"] = u6
dump()

# ====================================================================== 9. mag screen sizes re-derived from the engine radii
# ====================================================================== 8b. bipod poses read back (runtime) vs the build
def leg_check(fr, ext_mm):
    out = {}
    for sd, sgn in (("l", 1.0), ("r", -1.0)):
        leg, ext = f"bipod_leg_{sd}", f"bipod_leg_{sd}_ext"
        Rl, tl = tf(fr["bones"][leg])
        Re, te = tf(fr["bones"][ext])
        Rl0, tl0 = ref[leg]
        Re0, te0 = ref[ext]
        Rd = Rl @ Rl0.T
        exp = F @ CL.leg_basis(sd, CL.DEPLOY)[:3, :3] @ F
        R = Rd.T @ exp
        err = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))
        d = Rd @ np.array([1.0, 0.0, 0.0])                      # the leg's own axis (folded: +X forward)
        swing = math.degrees(math.acos(max(-1.0, min(1.0, float(d[0])))))
        splay = math.degrees(math.atan2(abs(d[1]), -d[2]))
        out_dir = "out" if (d[1] * (tl0[1])) > 0 else "in"
        trav = Rl.T @ (te - tl) - Rl0.T @ (te0 - tl0)
        out[sd] = {"rotation_vs_build_deg": round(err, 5), "swing_from_forward_deg": round(swing, 4), "splay_deg": round(splay, 4),
                   "leans": out_dir, "ext_travel_cm": [round(float(x), 5) for x in trav], "ext_expected_cm": ext_mm / 10.0,
                   "foot_socket_cm": None}
    return out


dep = RTP["clips"]["A_SR01_BipodDeploy"]["frames"]
stw = RTP["clips"]["A_SR01_BipodStow"]["frames"]
dl = dep[str(max(int(k) for k in dep))]
bp = {"deploy_last": leg_check(dl, CL.EXT_DEPLOY), "stow_first": leg_check(stw["0"], CL.EXT_DEPLOY),
      "stow_last": {b: float(np.abs(np.array(stw[str(max(int(k) for k in stw))]["bones"][b][:3]) - np.array(sk["ref_comp"][b][:3])).max())
                    for b in ("bipod_leg_l", "bipod_leg_r", "bipod_leg_l_ext", "bipod_leg_r_ext")}}
for sd, sn in (("l", "BipodFoot_L"), ("r", "BipodFoot_R")):
    bp["deploy_last"][sd]["foot_socket_cm"] = [round(float(x), 4) for x in dl["sockets"][sn][:3]]
    bp["deploy_last"][sd]["foot_below_bore_cm"] = round(float(np.array(ss["Muzzle"]["component"])[2] - dl["sockets"][sn][2]), 4)
# the build's deployed foot (Blender truth composed through the parents) in Unreal cm
tw = truth_world(dict(CL.deploy_values(36)))
for sd, sn in (("l", "BipodFoot_L"), ("r", "BipodFoot_R")):
    srec = next(x for x in SC["sockets"] if x["name"] == sn)
    p_mm = np.array(srec["location_mm"])
    Wt = tw[f"bipod_leg_{sd}_ext"]
    q = Wt[:3, :3] @ p_mm + Wt[:3, 3]
    bp["deploy_last"][sd]["foot_build_cm"] = [round(float(x), 4) for x in (F @ q) / 10.0]
    bp["deploy_last"][sd]["foot_vs_build_cm"] = round(float(np.abs(np.array(dl["sockets"][sn][:3]) - (F @ q) / 10.0).max()), 5)
res["bipod_poses"] = bp
dump()

# ====================================================================== 8c. U4 scope pair (static twin in pass B, SK in pass C)
ssc = json.loads((C.EXP / f"{C.SCOPE}.sockets.json").read_text())
sloc = {x["socket"]: np.array(x["location_cm"]) for x in ssc["sockets"]}
OFF = C.scope_offset_cm()


def scope_pair(rec):
    if not isinstance(rec, dict) or "scope_sockets_in_gun" not in rec:
        return {"error": str(rec)[:300]}
    S = rec["scope_sockets_in_gun"]
    rail = np.array(rec["gun_socket_Rail_Top"][:3])
    muz, Rm = np.array(rec["gun_socket_Muzzle"][:3]), quat_m(rec["gun_socket_Muzzle"][3:7])
    seat = np.array(rec["gun_socket_MuzzleSeat"][:3])
    mount = np.array(S["Mount"][:3])
    exp_mount = rail + np.array([OFF, 0, 0])
    o = {"mount_cm": mount.round(5).tolist(), "mount_minus_rail_top_cm": (mount - rail).round(5).tolist(),
         "mount_err_cm": float(np.abs(mount - exp_mount).max())}
    bore_dir = Rm[:, 0]
    bore_dir2 = (muz - seat) / np.linalg.norm(muz - seat)
    for sn in ("Sight", "EyePoint", "Lens_Front"):
        P = np.array(S[sn][:3])
        Rs_ = quat_m(S[sn][3:7])
        o[sn] = {"cm": P.round(5).tolist(), "vs_blender_cm": float(np.abs(P - (exp_mount + sloc[sn])).max()),
                 "above_bore_mm": round(float((P[2] - muz[2]) * 10), 4), "lateral_mm": round(float(P[1] * 10), 5),
                 "axis_vs_bore_deg": round(math.degrees(math.acos(max(-1.0, min(1.0, float(Rs_[:, 0] @ bore_dir))))), 6)}
    o["bore_dir_sockets_vs_muzzle_axis_deg"] = round(math.degrees(math.acos(max(-1.0, min(1.0, float(bore_dir @ bore_dir2))))), 6)
    o["scale"] = rec.get("scope_world_scale")
    o["attach_socket"] = rec.get("attach_socket")
    return o


res["U4_scope_pair"] = {"SM_SR01 (pass B)": scope_pair(B.get("scope_on_SM")), "SK_SR01 (pass C)": scope_pair(CR.get("U4_scope_on_SK")),
                        "blender_A1_A4": {"mount_minus_rail_top_mm": 20.02, "sight_Z_over_bore_mm": 57.6}}
dump()

r_mag = float(B["SM_SR01_Mag"]["bounds"]["radius"])
r_sk = float(B["sk_bounds"]["bounds"]["radius"])
r_tw = float(B["SM_SR01"]["bounds"]["radius"])
rs = SC["lod_screen_sizes"]
der = [1.0] + [round(s * r_mag / r_sk, 5) for s in rs[1:]]
der_tw = [1.0] + [round(s * r_mag / r_tw, 5) for s in B["SM_SR01"]["lod_screen_sizes"][1:]]
res["mag_screen_sizes"] = {"r_mag_cm": r_mag, "r_sk_cm": r_sk, "r_twin_cm": r_tw, "derived_from_SK": der, "derived_from_twin": der_tw,
                           "sidecar": B["SM_SR01_Mag"]["lod_screen_sizes"],
                           "max_diff": min(max(abs(a - b) for a, b in zip(d_, B["SM_SR01_Mag"]["lod_screen_sizes"])) for d_ in (der, der_tw))}
dump()
print("SM_ANALYSIS_DONE", round(time.time() - t0, 1))

# ====================================================================== 10. U7: the read-back LOD0 at every physics sample
ps_path = HERE / "srE_physics_samples.json"
if ps_path.exists():
    PS = json.loads(ps_path.read_text())
    fold_fr = RTP["clips"]["A_SR01_BipodDeploy"]["frames"]
    folded_V = posed(sk_lods[0], fold_fr[str(max(int(k) for k in fold_fr))])
    geom = {"SM_PHYS_SM_SR01": np.array(GEO["SM_SR01"][0]["positions"]),
            "SM_PHYS_SM_SR01_rolled": np.array(GEO["SM_SR01"][0]["positions"]),
            "SM_PHYS_SM_SR01_Mag": np.array(GEO["SM_SR01_Mag"][0]["positions"]),
            "SM_PHYS_SK_SR01": sk_lods[0]["V"], "SM_PHYS_SK_SR01_deployed": folded_V}
    Rb, tb = tf(sk["ref_comp"]["body"])           # the SK sample is the 'body' bone: mesh = body-local x bone
    u7 = {}
    for k, P in geom.items():
        if k not in PS[0]:
            continue
        sk_ = k.startswith("SM_PHYS_SK_")
        Pl = (P - tb) @ Rb if sk_ else P
        lows, outb = [], []
        for s in PS:
            R, t = tf(s[k]["xform"])
            W = Pl @ R.T + t
            lows.append(float(W[:, 2].min()))
            bo = s[k].get("bounds")
            if bo:
                c_, e_ = np.array(bo[:3]), np.array(bo[3:6])
                outb.append(float(np.maximum(np.abs(W - c_) - e_, 0).max()))
        last = [s for s in PS if s["t"] >= PS[-1]["t"] - 1.0]
        sp = [s[k]["speed"] for s in last if s[k]["speed"] is not None]
        u7[k] = {"samples": len(PS), "sim_seconds": PS[-1]["t"], "start_lowest_vertex_cm": round(lows[0], 4),
                 "min_lowest_vertex_cm": round(min(lows), 4), "final_lowest_vertex_cm": round(lows[-1], 4),
                 "max_speed_last_1s_cm_s": max(sp) if sp else None,
                 "rests": bool(sp and max(sp) < 1.0), "no_tunnelling": bool(min(lows) > -2.0 and lows[-1] > -0.5),
                 "runtime_bounds_max_outside_cm": round(max(outb), 4) if outb else None,
                 "runtime_bounds_samples_outside": int(sum(1 for x in outb if x > 1e-3))}
        if sk_:
            # the Shoulder socket (on body) as Unreal placed it vs this analysis's placement
            sname = "Shoulder"
            rel = ss[sname]["relative"]
            sb = ss[sname]["bone"]
            fr_last = fold_fr[str(max(int(kk) for kk in fold_fr))] if k.endswith("_deployed") else {"bones": {sb: sk["ref_comp"][sb]}}
            Rst, tst = tf(fr_last["bones"][sb])
            sock_comp = tst + Rst @ np.array(rel[:3])
            R, t = tf(PS[-1][k]["xform"])
            pred = ((sock_comp - tb) @ Rb) @ R.T + t
            u7[k]["shoulder_engine_vs_analysis_cm"] = round(float(np.abs(pred - np.array(PS[-1][k]["shoulder"][:3])).max()), 5)
    res["U7_vertices"] = u7
    dump()
print("SM_ANALYSIS_DONE2", round(time.time() - t0, 1))
