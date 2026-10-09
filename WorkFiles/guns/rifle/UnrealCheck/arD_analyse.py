"""AR-01 stage 8, analysis (Blender 5.2 headless, numpy + mathutils): everything measured on what Unreal READ BACK.

Inputs: the shipped FBX (Exports/Guns/AR01), arB_verify.json / arB_geometry.json / arB_poses.json (pass B),
arC_render.json / arC_runtime.json (pass C), Unreal's own FBX exports in roundtrip/.
Writes arD_analysis.json:
  fbx_truth       triangles per node of every shipped FBX; UCX nodes; the triangles Unreal's FBX importer drops
                  (|cross| < 1e-4 cm^2, Remove Degenerates)
  triangles       Blender (stage gates) = FBX = Unreal (render data, mesh description, SK export) per LOD
  hulls / C2      Unreal's stored hulls (its FBX export, split into shells): count, vertices, every LOD0 surface sample
                  of the read-back geometry inside their union (300k samples)
  uv1             the GENERATED lightmap UV (Unreal export): inside 0..1, overlap pixels at 1024 / 2048 per LOD
  U1 / U3         skeleton names / parents / heads vs the sidecar; axes; sockets vs the sidecar (0.001 cm / 0.001 deg)
  U5              every LOD0..3 vertex at every runtime clip frame inside the stored bounds
  U9              runtime (compressed) vs RAW per bone as vertex displacement (mm); RAW vs the authored clips
                  (rifle_clips); end pose = start pose; notifies vs the sidecar (+-0.5 frame, no extras)
  U6 / M9         magazine at Mag from the engine attach (rest + every reload frame); seated intersections on the
                  read-back geometry (co-visible LOD pairs); the rock path from the engine sockets (0.5 mm / 0.25 deg)
"""
import bpy, bmesh, json, math, sys, time
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ar_common as C  # noqa: E402
ROOT = C.ROOT
sys.path.insert(0, str(ROOT / "Scripts" / "guns" / "rifle"))
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
t0 = time.time()
B = json.loads((HERE / "arB_verify.json").read_text())
GEO = json.loads((HERE / "arB_geometry.json").read_text())
PB = json.loads((HERE / "arB_poses.json").read_text())
CR = json.loads((HERE / "arC_render.json").read_text())
RTP = json.loads((HERE / "arC_runtime.json").read_text())
RTP["clips"].pop("_bind", None)


def _fix_socket_named_bones():
    """FName lookups are case-insensitive: GetBoneTransform('trigger') returns the socket 'Trigger' (it routes through
    GetSocketTransform). For such bones the runtime value is the socket: bone = socket composed with the inverse of
    the socket's relative transform (pass B)."""
    socks = B["sk_sockets"]
    lower = {k.lower(): k for k in socks}
    fixed = []
    for b in RTP["names"]:
        sname = lower.get(b.lower())
        if sname is None or socks[sname]["bone"] != b:
            continue
        rel = socks[sname]["relative"]
        Rr, tr_ = quat_m(rel[3:7]), np.array(rel[:3])
        for clip in RTP["clips"].values():
            for fr in clip["frames"].values():
                v = fr["bones"][b]
                Rs_, ts_ = quat_m(v[3:7]), np.array(v[:3])
                Rb = Rs_ @ Rr.T
                tb = ts_ - Rb @ tr_
                fr["bones"][b] = list(tb) + list(mat_q(Rb))
        fixed.append(b)
    return fixed
SC = C.sidecar_sk()
GATES = ROOT / "WorkFiles" / "guns" / "rifle" / "gates"
res = {}
F = np.diag([1.0, -1.0, 1.0])


def dump():
    res["seconds"] = round(time.time() - t0, 1)
    (HERE / "arD_analysis.json").write_text(json.dumps(res, indent=1, default=float))


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
    """3x3 -> quaternion (x, y, z, w)."""
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return [x, y, z, w]


def tf(arr):
    R = quat_m(arr[3:7])
    return R, np.array(arr[:3], float)


def bvh(V, T):
    return BVHTree.FromPolygons([tuple(p) for p in V], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def tri_area_drop(V_cm, T):
    a = V_cm.astype(np.float32)
    cr = np.cross(a[T[:, 1]] - a[T[:, 2]], a[T[:, 0]] - a[T[:, 2]]).astype(np.float64)
    return int(((cr ** 2).sum(1) < 1e-8).sum())


res["runtime_socket_named_bones_fixed"] = _fix_socket_named_bones()

# ====================================================================== 1. FBX truth
truth = {}
for fn in ("SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx", "SM_AR01.fbx", "SM_AR01_Mag.fbx"):
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
    truth[fn] = rec
res["fbx_truth"] = truth
dump()

# ====================================================================== 2. Unreal round-trip exports
rt = {}
shells = {}
uv1 = {}


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
        N.append(n)
        D.append(d)
    bm.free()
    return np.array(N), np.array(D)


for name in ("SM_AR01", "SM_AR01_Mag"):
    clear()
    bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / f"ue_{name}.fbx"))
    lods = {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        if ob.name.startswith("UCX_"):
            shells[name] = split_shells(ob)
            continue
        me = ob.data
        me.calc_loop_triangles()
        lods[ob.name] = {"triangles": len(me.loop_triangles)}
        lay = me.uv_layers.get("LightMapUV") or (me.uv_layers[1] if len(me.uv_layers) > 1 else None)
        if lay is not None:
            UV = np.empty(len(me.loops) * 2)
            lay.data.foreach_get("uv", UV)
            UV = UV.reshape(-1, 2)
            LT = np.empty(len(me.loop_triangles) * 3, np.int64)
            me.loop_triangles.foreach_get("loops", LT)
            tris = UV[LT.reshape(-1, 3)]
            o1, cov1 = uv_overlap(tris, 1024)
            o2, cov2 = uv_overlap(tris, 2048)
            o64, _ = uv_overlap(tris, 64)
            o256, _ = uv_overlap(tris, 256)
            uv1[ob.name] = {"layer": lay.name, "u_range": [float(UV[:, 0].min()), float(UV[:, 0].max())],
                            "v_range": [float(UV[:, 1].min()), float(UV[:, 1].max())],
                            "inside_0_1": bool(UV.min() >= -1e-6 and UV.max() <= 1 + 1e-6),
                            "overlap_px_64": o64, "overlap_px_256": o256,
                            "overlap_px_1024": o1, "coverage_1024": round(cov1, 4), "overlap_px_2048": o2,
                            "coverage_2048": round(cov2, 4)}
    rt[name] = lods
res["roundtrip_static"] = rt
res["uv1"] = uv1
res["hull_shells"] = {k: {"count": len(v), "vertices": [int(len(s)) for s in v]} for k, v in shells.items()}
dump()

# ---- C2: dense LOD0 samples of the read-back geometry inside the stored hulls
rng = np.random.default_rng(7)
c2 = {}
for name in ("SM_AR01", "SM_AR01_Mag"):
    HP = [planes(s) for s in shells[name]]
    P = np.array(GEO[name][0]["positions"])
    Tr = np.array(GEO[name][0]["triangles"])[:, -3:]   # the id list ends with the three vertex ids (katana note)
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
res["C2"] = c2
dump()

# ====================================================================== 3. skeletal round trip: per-bone vertex sets
clear()
bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / "ue_SK_AR01.fbx"))
sk_lods, bone_verts = {}, {}
for ob in sorted(bpy.data.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    V, T = mesh_np(ob)
    Vu = to_ue_cm(V)
    me = ob.data
    groups = {g.index: g.name for g in ob.vertex_groups}
    owner = np.full(len(me.vertices), -1)
    wsum = np.zeros(len(me.vertices))
    for v in me.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        if best is not None:
            owner[v.index] = best.group
        wsum[v.index] = sum(g.weight for g in v.groups)
    names = np.array([groups.get(int(i), "") for i in owner])
    lv = int(ob.name.rsplit("LOD", 1)[-1]) if "LOD" in ob.name else 0
    sk_lods[lv] = {"V": Vu, "T": T, "bone": names}
    bone_verts[lv] = {b: Vu[names == b] for b in set(names.tolist())}
res["sk_roundtrip"] = {f"LOD{k}": {"triangles": int(len(v["T"])), "vertices": int(len(v["V"])),
                                   "bones_weighted": sorted(set(v["bone"].tolist()))} for k, v in sorted(sk_lods.items())}
# bind geometry vs the stored bounds
bb = B["sk_bounds"]["bounds"]
lo = np.array(bb["origin"]) - np.array(bb["extent"])
hi = np.array(bb["origin"]) + np.array(bb["extent"])
res["sk_roundtrip"]["bind_aabb_cm"] = [sk_lods[0]["V"].min(0).round(4).tolist(), sk_lods[0]["V"].max(0).round(4).tolist()]
res["sk_roundtrip"]["stored_bounds_cm"] = [lo.round(4).tolist(), hi.round(4).tolist()]
dump()

# ====================================================================== 4. triangles: Blender = FBX = Unreal
gj = {f: json.loads((GATES / f).read_text()) for f in ("rig_export.json", "mag.json", "game.json")}


def gate_val(gfile, prefix):
    for g in gj[gfile]["gates"]:
        if g["name"].startswith(prefix):
            return g["value"]
    return None
bl_sk = gate_val("rig_export.json", "LOD triangles Blender = FBX (SK)")
bl_sm = gate_val("game.json", "qa_check (twin LOD0..3)")
bl_mag = gate_val("mag.json", "mag qa_check")
tri = {"SK_AR01": [], "SM_AR01": [], "SM_AR01_Mag": []}
for i, fn in enumerate(["SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"]):
    nm = "SK_AR01" if i == 0 else f"SK_AR01_LOD{i}"
    tri["SK_AR01"].append({"lod": i, "blender": bl_sk[fn][0], "fbx": truth[fn][nm]["triangles"],
                           "unreal_export": res["sk_roundtrip"][f"LOD{i}"]["triangles"]})
for i in range(4):
    tri["SM_AR01"].append({"lod": i, "blender": bl_sm[f"SM_AR01_LOD{i}"], "fbx": truth["SM_AR01.fbx"][f"SM_AR01_LOD{i}"]["triangles"],
                           "unreal_render": B["SM_AR01"]["lod_triangles"][i], "unreal_mesh_description": len(GEO["SM_AR01"][i]["triangles"]),
                           "unreal_export": rt["SM_AR01"][f"SM_AR01_LOD{i}"]["triangles"],
                           "predicted_import_drops": truth["SM_AR01.fbx"][f"SM_AR01_LOD{i}"]["unreal_import_drops"]})
    tri["SM_AR01_Mag"].append({"lod": i, "blender": bl_mag["triangles"][f"SM_AR01_Mag_LOD{i}"],
                               "fbx": truth["SM_AR01_Mag.fbx"][f"SM_AR01_Mag_LOD{i}"]["triangles"],
                               "unreal_render": B["SM_AR01_Mag"]["lod_triangles"][i],
                               "unreal_mesh_description": len(GEO["SM_AR01_Mag"][i]["triangles"]),
                               "unreal_export": rt["SM_AR01_Mag"][f"SM_AR01_Mag_LOD{i}"]["triangles"],
                               "predicted_import_drops": truth["SM_AR01_Mag.fbx"][f"SM_AR01_Mag_LOD{i}"]["unreal_import_drops"]})
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
head_err = {}
for n, v in SC["bones_rest"].items():
    head_err[n] = float(np.abs(np.array(sk["ref_comp"][n][:3]) - np.array(v["head_cm"])).max())
u1["max_head_err_cm"] = max(head_err.values())
root = sk["ref_comp"]["root"]
u1["root"] = root
u1["root_scale_1"] = all(abs(x - 1) < 1e-6 for x in root[7:10])
rots = {n: float(np.degrees(2 * math.acos(min(1.0, abs(sk["ref_comp"][n][6]))))) for n in sk["order"]}
u1["max_bone_rest_rotation_deg"] = max(rots.values())
ss = B["sk_sockets"]
mz, gp, ch, sg = (np.array(ss[k]["component"][:3]) for k in ("Muzzle", "Grip", "ChargingHandle", "Sight"))
u1["axes"] = {"muzzle_plusX_cm": float(mz[0] - gp[0]), "muzzle_on_bore_y_cm": float(mz[1]),
              "sight_above_bore_cm": float(sg[2] - mz[2]), "charging_handle_right_plusY_cm": float(ch[1]),
              "bolt_rest_x_axis_component": quat_m(sk["ref_comp"]["bolt"][3:7])[:, 0].round(6).tolist()}
u1["pass"] = bool(u1["names_match"] and u1["parents_match"] and u1["max_head_err_cm"] <= 1e-3 and u1["root_scale_1"]
                  and mz[0] - gp[0] > 50 and abs(mz[1]) < 1e-3 and sg[2] > mz[2] and ch[1] > 0)
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
                     "outer_ok": got["outer"].split(".")[0].endswith("SK_AR01") or "SK_AR01" in got["outer"]}
extra = sorted(set(ss) - {s["name"] for s in SC["sockets"]})
res["U3"] = {"sockets": u3, "extra": extra, "worst_loc_cm": max(v["loc_err_cm"] for v in u3.values() if isinstance(v, dict)),
             "worst_rot_deg": max(v["rot_err_deg"] for v in u3.values() if isinstance(v, dict)),
             "pass": bool(not extra and all(isinstance(v, dict) and v["bone_ok"] and v["loc_err_cm"] <= 1e-3 and v["rot_err_deg"] <= 1e-3
                                              and v["scale1"] and v["outer_ok"] for v in u3.values()))}
dump()

# ====================================================================== 6. poses: U9 / U5
ref = {n: tf(v) for n, v in sk["ref_comp"].items()}


def deform(Rt, tt, n):
    Rr, tr = ref[n]
    return Rt @ Rr.T, tt - Rt @ Rr.T @ tr          # p' = M p + c


def disp(Ma, ca, Mb, cb, pts):
    if len(pts) == 0:
        return 0.0
    return float(np.linalg.norm(pts @ (Ma - Mb).T + (ca - cb), axis=1).max())


import rifle_clips as CL  # noqa: E402
rep = json.loads((ROOT / "WorkFiles" / "guns" / "rifle" / "scratch" / "rig" / "rig_report.json").read_text())
CL.configure(rep["motion"]["bolt_travel_mm"], rep["motion"]["rock_deg"], rep["motion"]["insert_mm"])
authored = CL.all_clips()
heads_mm = {n: np.array(v["head_mm"]) for n, v in rep["bones"].items()}
u9 = {}
u5 = {"stored_lo_cm": lo.tolist(), "stored_hi_cm": hi.tolist(), "clips": {}}
for cname, rec in RTP["clips"].items():
    fps = rec["fps"]
    frames = rec["frames"]
    raw = PB["clips"][cname]["RAW"]
    comp = PB["clips"][cname]["COMPRESSED"]
    worst_c, worst_raw_truth, worst_ap = 0.0, 0.0, 0.0
    outside = 0
    worst_out = 0.0
    afr = dict(authored[cname][0])
    for fs, fr in frames.items():
        f = int(fs)
        key = f"{f / fps:.6f}"
        for b in RTP["names"]:
            if b == "root":
                continue
            pts = bone_verts[0].get(b, np.zeros((0, 3)))
            Mc, cc = deform(*tf(fr["bones"][b] + [1, 1, 1]), b)
            if key in raw:
                Mr, cr = deform(*tf(raw[key][b] + [1, 1, 1]), b)
                worst_c = max(worst_c, disp(Mc, cc, Mr, cr, pts) * 10)
                Ma, ca = deform(*tf(comp[key][b] + [1, 1, 1]), b)
                worst_ap = max(worst_ap, disp(Mc, cc, Ma, ca, pts) * 10)
                # authored truth (Blender armature mm -> Unreal cm, y flipped)
                vals = afr.get(f)
                if vals is not None and b in heads_mm:
                    bas = CL.basis_from(vals).get(b, np.eye(4))
                    h = heads_mm[b]
                    Mt = bas[:3, :3]
                    ct = h + bas[:3, 3] - Mt @ h            # p' = Mt p + ct (mm, Blender)
                    Mt_u = F @ Mt @ F
                    ct_u = (F @ ct) / 10.0
                    worst_raw_truth = max(worst_raw_truth, disp(Mr, cr, Mt_u, ct_u, pts) * 10)
        # U5: posed LOD0..3 inside the stored bounds
        for lv, d in sk_lods.items():
            P = d["V"]
            Pp = P.copy()
            for b in set(d["bone"].tolist()):
                if not b:
                    continue
                m = d["bone"] == b
                Mc, cc = deform(*tf(fr["bones"][b] + [1, 1, 1]), b)
                Pp[m] = P[m] @ Mc.T + cc
            o = np.maximum(lo - Pp, 0).max(1) + np.maximum(Pp - hi, 0).max(1)
            outside += int((o > 1e-4).sum())
            worst_out = max(worst_out, float(o.max()))
            if (o > 1e-4).any():
                for b in set(d["bone"][o > 1e-4].tolist()):
                    m = (d["bone"] == b) & (o > 1e-4)
                    key2 = f"LOD{lv}:{b}"
                    prev = u5.setdefault("by_bone", {}).get(key2, [0, 0.0, None])
                    side = (np.sign(np.maximum(lo - Pp[m], 0).max(0) * -1 + np.maximum(Pp[m] - hi, 0).max(0))).tolist()
                    u5["by_bone"][key2] = [prev[0] + int(m.sum()), max(prev[1], float(o[m].max())), side]
    first = frames["0"]["bones"]
    last = frames[str(max(int(k) for k in frames))]["bones"]
    end_vs_start = max(disp(*deform(*tf(last[b] + [1, 1, 1]), b), *deform(*tf(first[b] + [1, 1, 1]), b), bone_verts[0].get(b, np.zeros((0, 3)))) * 10
                       for b in RTP["names"] if b != "root")
    end_vs_bind = {b: disp(*deform(*tf(last[b] + [1, 1, 1]), b), np.eye(3), np.zeros(3), bone_verts[0].get(b, np.zeros((0, 3)))) * 10
                   for b in RTP["names"] if b != "root"}
    # notifies
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
                 "max_raw_vs_authored_mm": round(worst_raw_truth, 5),
                 "end_vs_start_mm": round(end_vs_start, 5),
                 "end_vs_bind_mm": {k: round(v, 4) for k, v in end_vs_bind.items() if v > 1e-3},
                 "notifies": match, "notifies_extra": len(got_n) - len(sc_n),
                 "notifies_ok": all(m["engine_frame"] is not None for m in match) and len(got_n) == len(sc_n)}
    u5["clips"][cname] = {"vertices_outside": outside, "worst_outside_cm": worst_out}
res["U9"] = u9
res["U5_bounds"] = u5
dump()

# ====================================================================== 7. U6 / M9: the magazine at Mag
magL = [(np.array(GEO["SM_AR01_Mag"][i]["positions"]), np.array(GEO["SM_AR01_Mag"][i]["triangles"])[:, -3:]) for i in range(4)]


def affine_from_basis(bs):
    o = np.array(bs["o"])
    M = np.stack([np.array(bs[k]) - o for k in "xyz"], axis=1)
    return M, o


def place(Pm, R, t):
    return Pm @ R.T + t


def n_pairs(A, B_):
    return len(A.overlap(B_))


rifle_bvh = {lv: bvh(d["V"], d["T"]) for lv, d in sk_lods.items()}
att = CR["attach_SK_rest"]
M, o = affine_from_basis(att["mag_to_gun_basis"])
Rs, ts = tf(att["socket_Mag"])
u6 = {"rest": {"affine_orthonormal_err": float(np.abs(M.T @ M - np.eye(3)).max()),
               "attached_vs_socket_cm": float(np.abs(o - ts).max()), "attached_vs_socket_rot": float(np.abs(M - Rs).max()),
               "relative_to_socket": att["relative_to_socket"], "mag_world_scale": att["mag_world_scale"],
               "socket_vs_sidecar_cm": float(np.abs(ts - np.array(next(s for s in SC["sockets"] if s["name"] == "Mag")["unreal_component"]["location_cm"])).max())}}
seat = {}
for lv in range(4):
    Pm, Tm = magL[lv]
    seat[f"rifle LOD{lv} / mag LOD{lv}"] = n_pairs(rifle_bvh[lv], bvh(place(Pm, M, o), Tm))
u6["seated_intersecting_pairs"] = seat
# reload frames: the posed rifle (its bones) and the magazine on the Mag socket
rl = {}
for cname in ("A_AR01_Reload", "A_AR01_ReloadEmpty"):
    frames = RTP["clips"][cname]["frames"]
    worst_attach = 0.0
    hit_frames = []
    for fs, fr in sorted(frames.items(), key=lambda kv: int(kv[0])):
        Rm, tm = tf(fr["Mag_socket"] + [1, 1, 1])
        Ma, oa = affine_from_basis(fr["mag_attached"])
        worst_attach = max(worst_attach, float(np.abs(oa - tm).max()), float(np.abs(Ma - Rm).max()))
        d = sk_lods[0]
        P = d["V"].copy()
        for b in set(d["bone"].tolist()):
            if not b:
                continue
            m = d["bone"] == b
            Mc, cc = deform(*tf(fr["bones"][b] + [1, 1, 1]), b)
            P[m] = d["V"][m] @ Mc.T + cc
        npairs = n_pairs(bvh(P, d["T"]), bvh(place(magL[0][0], Rm, tm), magL[0][1]))
        if npairs:
            hit_frames.append([int(fs), npairs])
    rl[cname] = {"frames": len(frames), "attached_vs_socket_max": worst_attach, "frames_with_intersections": hit_frames}
u6["reload_frames"] = rl
# rock path from the engine sockets (gun component frame)
Rr, tr = tf(CR["attach_SK_rest"]["socket_MagRockStart"])
Ri, ti = tf(CR["attach_SK_rest"]["socket_MagInsertStart"])
Rd = Rs @ Rr.T
td = ts - Rd @ tr
ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rd) - 1) / 2))))
ax = np.array([Rd[2, 1] - Rd[1, 2], Rd[0, 2] - Rd[2, 0], Rd[1, 0] - Rd[0, 1]])
ax = ax / max(np.linalg.norm(ax), 1e-12)
p0 = np.linalg.lstsq(np.eye(3) - Rd, td, rcond=None)[0]


def rot(axis, deg):
    a = math.radians(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
insert_mm = float(np.linalg.norm(tr - ti) * 10)
poses = []
n_ins = max(1, int(math.ceil(insert_mm / 0.5)))
for k in range(n_ins + 1):
    u = k / n_ins
    poses.append(("insert", Rr, ti + (tr - ti) * u))
n_rock = max(1, int(math.ceil(ang / 0.25)))
for k in range(n_rock + 1):
    Rk = rot(ax, ang * k / n_rock)
    poses.append(("rock", Rk @ Rr, p0 + Rk @ (tr - p0)))
path = {"insert_mm": insert_mm, "rock_deg": ang, "hook_point_cm": p0.round(4).tolist(), "axis": ax.round(6).tolist(),
        "rock_end_vs_Mag_cm": float(np.abs(poses[-1][2] - ts).max()), "pairs": {}}
for lv in (0, 1):
    hits = []
    for i, (kind, Rk, tk) in enumerate(poses):
        npairs = n_pairs(rifle_bvh[lv], bvh(place(magL[lv][0], Rk, tk), magL[lv][1]))
        if npairs:
            hits.append([i, kind, npairs])
    path["pairs"][f"rifle LOD{lv} / mag LOD{lv}"] = {"steps": len(poses), "intersecting_steps": hits}
u6["rock_path"] = path
res["U6_M9"] = u6
dump()

# ====================================================================== 8. mag screen sizes re-derived from engine bounds
mb = B["SM_AR01_Mag"]["bounds"]["extent"]
rb = B["sk_bounds"]["bounds"]["extent"]
r_mag = float(np.linalg.norm(mb))
r_rifle = float(np.linalg.norm(rb))
rs = SC["lod_screen_sizes"]
der = [1.0] + [round(s * r_mag / r_rifle, 4) for s in rs[1:]]
res["mag_screen_sizes"] = {"r_mag_cm": r_mag, "r_rifle_cm": r_rifle, "derived": der,
                           "sidecar": B["SM_AR01_Mag"]["lod_screen_sizes"],
                           "max_diff": max(abs(a - b) for a, b in zip(der, B["SM_AR01_Mag"]["lod_screen_sizes"]))}
dump()
print("AR_ANALYSIS_DONE", round(time.time() - t0, 1))

# ====================================================================== 9. U7: the read-back LOD0 at every physics sample
ps_path = HERE / "arE_physics_samples.json"
if ps_path.exists():
    PS = json.loads(ps_path.read_text())
    geom = {"AR_PHYS_SM_AR01": np.array(GEO["SM_AR01"][0]["positions"]),
            "AR_PHYS_SM_AR01_rolled": np.array(GEO["SM_AR01"][0]["positions"]),
            "AR_PHYS_SM_AR01_Mag": np.array(GEO["SM_AR01_Mag"][0]["positions"]),
            "AR_PHYS_SK_AR01": sk_lods[0]["V"]}
    Rb, tb = tf(sk["ref_comp"]["body"])           # the SK sample is the 'body' bone: mesh = body-local x bone
    u7 = {}
    for k, P in geom.items():
        if k not in PS[0]:
            continue
        Pl = (P - tb) @ Rb if k == "AR_PHYS_SK_AR01" else P
        lows = []
        for s in PS:
            R, t = tf(s[k]["xform"])
            lows.append(float((Pl @ R.T + t)[:, 2].min()))
        last = [s for s in PS if s["t"] >= PS[-1]["t"] - 1.0]
        sp = [s[k]["speed"] for s in last if s[k]["speed"] is not None]
        u7[k] = {"samples": len(PS), "sim_seconds": PS[-1]["t"], "start_lowest_vertex_cm": round(lows[0], 4),
                 "min_lowest_vertex_cm": round(min(lows), 4), "final_lowest_vertex_cm": round(lows[-1], 4),
                 "max_speed_last_1s_cm_s": max(sp) if sp else None,
                 "rests": bool(sp and max(sp) < 1.0), "no_tunnelling": bool(min(lows) > -2.0 and lows[-1] > -0.5)}
    res["U7_vertices"] = u7
    dump()
print("AR_ANALYSIS_DONE2", round(time.time() - t0, 1))
