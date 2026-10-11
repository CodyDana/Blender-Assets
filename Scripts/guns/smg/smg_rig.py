"""SMG01 W3c: rig + export (headless Blender, on the W3b blend; the AR-01's rifle_rig.py):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_rig.py

SMG_BUILD_PLAN 2.2 / 8 / 10 / 13, GUN_BUILDING_STUDY 4.6 / 5.2 / 5.3 / 7.2:
- armature object 'root' at the Grip origin (identity), the spec's 11 bones (body + bolt, charging_handle, trigger,
  selector, mag_release, magazine, stock, sight_rear, sight_front, muzzle_device), rest rotation = root's; the eight
  AR-01 bones keep their names, parent and axes (SK_AR01_Skeleton compatible);
- SK_SMG01 / _LOD1..3: each LOD's part objects (the very objects the static twin joins) without the magazine (it is
  SM_SMG01_Mag on the 'magazine' bone's Mag socket: an attach bone with no weighted vertices), every part rigidly on
  its bone (part records), slots M_SMG01_Metal (0) + M_SMG01_Furniture (1), UV0 in 0..1 per slot;
- 8 clips (smg_clips: Fire 60 fps, Charge, Reload, ReloadEmpty, Selector, StockFold, StockUnfold, SightFlip 30 fps),
  keys every frame, LINEAR; the clips moving the bolt hold the selector at AUTO; notifies in the sidecar;
- bounds extension (B11) from every vertex of LOD0-3 at every frame of every clip (incl. the folded stock and the
  folded sights) against LOD0's bind AABB; the SK's LOD screen sizes converted from the LOD-pop switch distances with
  the SK's engine radius (bind box + extension);
- 21 sockets on their bones (spec; CenterOfMass / Holster = the W3b CoM empty; MagInsertStart exactly on the
  magazine's -Z, 68.2 mm below Mag), one physics body on 'body' (boxes + a capsule fitted to the LOD0 part groups,
  2.5 kg), the physics proxy FBX in Physics/;
- qa_skeletal(max_influences=1) + gunlib.rig rigid-skin and skeleton-standard checks, then export_skeletal_set and the
  sidecar; SM_SMG01 through qa_check and export_fbx(kind="static") with the LOD-pop sizes; sha256 of every file;
- reported: the stock latch path in the fold clips (a rigid rig cannot press the button) and the charging-handle lock.
Writes scratch/rig/rig_report.json, updates gates/game_lod_sizes.json (SK sizes) and saves Assets/Guns/SMG01.blend.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, BLEND, GRIP, SPEC, GATES, CODE, PARTS_COLL, D, dims  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from pipeline import skeletal_prop as SKP  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from gunlib import rig as RG  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import fit as F  # noqa: E402
from gunlib import gateutil as GU  # noqa: E402
from gunlib import qa_gun  # noqa: E402
import smg_clips as CL  # noqa: E402
from smg_clips import basis_from  # noqa: E402

SK = f"SK_{CODE}"
SM = f"SM_{CODE}"
EXPORTS = ROOT / "Exports" / "Guns" / CODE
OUT = SCRATCH / "rig"
OUT.mkdir(parents=True, exist_ok=True)
SLOTS = ("M_SMG01_Metal", "M_SMG01_Furniture")
FPS = 30
MASS_KG = float(D["scale"]["mass_kg"])
BUDGET = int(D["budgets_triangles"]["twin_qa_budget"])
BONE_COMPRESSION = "/Engine/Animation/DefaultRecorderBoneCompression"
REST_FRAME = -100
GAME_REP = json.loads((SCRATCH / "game" / "game_report.json").read_text())
SOCK = {r["socket"]: r for r in SPEC.gun_sockets()}
FIT_SET = {}


def log(*a):
    print("[SMG01-rig]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def base_of(name):
    for lv in (1, 2, 3):
        if name.endswith(f"_LOD{lv}"):
            return name[: -len(f"_LOD{lv}")]
    return name


def bone_of(ob):
    return part_rec(ob).get("bone", "body")


def lod_objects(lv):
    cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


def bone_rows():
    return [(b["bone"], tuple(float(v) for v in SPEC.M_to_B(b["head_M"])), b["parent"]) for b in D["bones"]["table"]]


def clean_previous():
    for o in list(bpy.data.objects):
        if o.name == "root" or o.name.startswith((SK, f"{SK}_PhysicsProxy")):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    for a in list(bpy.data.actions):
        if a.name.startswith(f"A_{CODE}_"):
            bpy.data.actions.remove(a)
    c = bpy.data.collections.get(SK)
    if c is not None:
        bpy.data.collections.remove(c)


def obb(V, R):
    L = V @ R
    lo, hi = L.min(0), L.max(0)
    return R @ (0.5 * (lo + hi)), hi - lo


def physics_bodies():
    """One body on 'body' (the held / dropped SMG, stock extended: Q14): boxes for the receiver, the guard, the raked
    grip, the magwell, the stock frame + pad and the two sights, a capsule for the barrel + muzzle device (frame B)."""
    objs = {o.name: o for o in lod_objects(0)}
    Vof = {n: GM.mesh_vt(o)[0] for n, o in objs.items()}
    M = {n: V + GRIP for n, V in Vof.items()}
    lo = M["lower_receiver"]
    x_mw = float(SPEC.box("magwell")["X"][0])
    z_hb = float(SPEC.box("lower_receiver")["Z"][0])
    I = np.eye(3)
    a = math.radians(float(D["sidecar_gun_block"]["grip_axis_deg"]))
    Rg = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    groups = [
        ("receiver (upper, housing, end block, top rail, bolt, handle, selector)",
         np.vstack([M[n] for n in ("upper_receiver", "top_rail", "bolt", "charging_handle", "charging_slide",
                                   "selector", "lower_rail")] + [lo[(lo[:, 2] >= z_hb) & (lo[:, 0] <= x_mw)]]), I),
        ("trigger guard + trigger", np.vstack([lo[(lo[:, 2] < z_hb) & (lo[:, 0] > 335.0) & (lo[:, 0] < x_mw)],
                                               M["trigger"]]), I),
        ("pistol grip + cover (raked)", np.vstack([lo[(lo[:, 2] < z_hb) & (lo[:, 0] <= 345.0)], M["grip_cover"]]), Rg),
        ("magwell", lo[lo[:, 0] >= x_mw], I),
        ("stock frame + buttpad (extended)", np.vstack([M["stock_frame"], M["butt_pad"]]), I),
        ("rear flip sight", np.vstack([M["sight_rear_base"], M["sight_rear_leaf"]]), I),
        ("front flip sight", np.vstack([M["sight_front_base"], M["sight_front_leaf"]]), I),
    ]
    elements = []
    for desc, P, R in groups:
        c, size = obb(P - GRIP, R)
        elements.append({"shape": "box", "covers": desc, "centre_mm": [round(float(v), 3) for v in c],
                         "matrix": np.round(R, 7).tolist(), "size_mm": [round(float(v), 3) for v in size],
                         "collision": True, "contribute_to_mass": True})
    x_ff = float(D["stations_X"]["receiver_front_face"])
    P = np.vstack([M["barrel"], M["muzzle_device"]])
    P = P[P[:, 0] >= x_ff] - GRIP
    x0, x1 = float(P[:, 0].min()), float(P[:, 0].max())
    zc = float(np.mean([P[:, 2].min(), P[:, 2].max()]))
    r = float(np.max(np.hypot(P[:, 1], P[:, 2] - zc)))
    Rc = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
    elements.append({"shape": "capsule", "covers": "barrel + muzzle device ahead of the receiver face",
                     "centre_mm": [round(0.5 * (x0 + x1), 3), 0.0, round(zc, 3)], "matrix": Rc.tolist(),
                     "radius_mm": round(r, 3), "length_mm": round(max(0.1, (x1 - x0) - 2 * r), 3), "axis": "Z -> +X",
                     "collision": True, "contribute_to_mass": True})
    for e in elements:
        e["unreal_component"] = SKP.ue_component_transform(np.array(e["matrix"]), e["centre_mm"])
        if "size_mm" in e:
            e["size_cm"] = [round(v * 0.1, 4) for v in e["size_mm"]]
    return [{"bone": "body", "unreal_bone_any_of": ["body"], "physics_type": "Default", "consider_for_bounds": True,
             "mass_kg": MASS_KG, "elements": elements,
             "role": "ONE rigid body on 'body' (every other bone is its child): Kinematic while held (NoCollision / "
                     "QueryOnly in hand), simulated when dropped; a folded SK keeps the extended stock shapes (Q14, U7 "
                     "reports a folded drop); the seated magazine is its own component with collision off while "
                     "attached"}]


def socket_rows(com_B):
    from mathutils import Euler
    rows = []
    for r in SPEC.gun_sockets():
        n = r["socket"]
        loc = np.array(r["blender_mm"], float)
        if n in ("CenterOfMass", "Holster"):
            loc = com_B.copy()
        if n in FIT_SET:
            loc = FIT_SET[n].copy()
        ro = r["unreal_rotation_deg"]
        Rb = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
        rows.append({"name": n, "bone": r["bone"], "location_mm": [round(float(v), 4) for v in loc],
                     "matrix": np.round(Rb, 9).tolist(), "unreal_rotation_deg": ro,
                     "computed": n in ("CenterOfMass", "Holster"), "fit_set": n in FIT_SET, "use": r.get("use", ""),
                     "unreal_component": SKP.ue_component_transform(Rb, loc)})
    return rows


def posed_envelope(arm, mesh, clips):
    me = mesh.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3) * 1000.0
    gi = {g.index: g.name for g in mesh.vertex_groups}
    vb = np.array([gi[v.groups[0].group] for v in me.vertices])
    lo, hi = V.min(0), V.max(0)
    rest_lo, rest_hi = lo.copy(), hi.copy()
    worst = {}
    for cname, (frames, _n, _fps) in clips.items():
        for f, vals in frames:
            Ms = RG.bone_matrices_mm(arm, basis_from(vals))
            for bn in np.unique(vb):
                M = Ms[bn]
                if np.allclose(M, np.eye(4)):
                    continue
                P = V[vb == bn] @ M[:3, :3].T + M[:3, 3]
                lo, hi = np.minimum(lo, P.min(0)), np.maximum(hi, P.max(0))
                worst[cname] = max(worst.get(cname, 0.0),
                                   float(np.maximum(P.max(0) - rest_hi, rest_lo - P.min(0)).max()))
    return rest_lo, rest_hi, lo, hi, worst


def fold_latch_report(arm, clips):
    """The stock-bone LOD0 parts vs the body parts over the StockFold clip (button at rest: a rigid rig cannot press
    it): intersecting triangle pairs per frame and the deepest penetration (0.5 mm samples)."""
    objs = lod_objects(0)
    G = {o.name: GM.mesh_vt(o) for o in objs if part_rec(o).get("slot") != "M_SMG01_Mag"}
    stock = {n: v for n, v in G.items() if bone_of(bpy.data.objects[n]) == "stock"}
    body = {n: v for n, v in G.items() if bone_of(bpy.data.objects[n]) == "body"}
    btrees = {n: F.tree(V, T) for n, (V, T) in body.items()}
    rows = []
    frames, _n, _fps = clips["A_SMG01_StockFold"]
    head = None
    for f, vals in frames:
        Ms = RG.bone_matrices_mm(arm, basis_from(vals))
        M = Ms["stock"]
        hits = {}
        for sn, (V, T) in stock.items():
            P = V @ M[:3, :3].T + M[:3, 3]
            st = F.tree(P, T)
            for bn, bt in btrees.items():
                k = len(bt.overlap(st))
                if k:
                    Vb, Tb = body[bn]
                    dep = GU.depth_inside(GM.dense_samples(P, T, 0.5), bt, Vb.min(0), Vb.max(0), 10.0)
                    hits[f"{sn}/{bn}"] = {"pairs": k, "depth_mm": round(dep, 3)}
        rows.append({"frame": f, "stock_deg": round(vals.get("stock", 0.0), 3), "hits": hits})
    worst = max((h["depth_mm"] for r in rows for h in r["hits"].values()), default=0.0)
    return {"frames": rows, "worst_depth_mm": worst,
            "parts_hit": sorted({k for r in rows for k in r["hits"]}),
            "note": "the latch button / bolt ride on the 'stock' bone (11 bones, plan 2.2): the clip cannot press the "
                    "button, so the latch bolt's end swings through the end-block lug's bore for the first degrees; "
                    "B3 swept the fold with the button pressed (gates/form.json, b3_lod1.json)"}


def proxy_mesh(arm, mat, coll, com_B):
    import bmesh
    from mathutils import Vector
    me = bpy.data.meshes.new(f"{SK}_PhysicsProxy")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.25)
    for v in bm.verts:
        v.co += Vector(com_B * 0.001)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    uv = me.uv_layers.new(name="UV0")
    for i, l in enumerate(uv.data):
        l.uv = ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9))[i % 3]
    me.materials.append(mat)
    ob = bpy.data.objects.new(f"{SK}_PhysicsProxy", me)
    coll.objects.link(ob)
    vg = ob.vertex_groups.new(name="body")
    vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    return ob


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    clean_previous()
    rep = {"stage": "W3c rig + export", "spec_version": D["meta"].get("version")}
    # ------------------------------------------------------------ fit-set sockets
    mag_B = np.array(SOCK["Mag"]["blender_mm"], float)
    # the magazine axis as every sidecar carries the Mag socket (Unreal pitch 8.27 = Blender -8.27 about Y; the spec's
    # frames.mag rake -8.267 rounds to it): MagInsertStart lies on the exported Mag's -Z
    th = math.radians(-float(SOCK["Mag"]["unreal_rotation_deg"]["pitch"]))
    z_mag = np.array([math.sin(th), 0.0, math.cos(th)])
    CL.MAG_Z = z_mag
    ins = float(np.linalg.norm(np.array(SOCK["MagInsertStart"]["blender_mm"]) - mag_B))
    ins = round(ins, 1)                                    # 68.2 (spec: insert depth 58.2 + 10)
    tI = mag_B - ins * z_mag
    FIT_SET["MagInsertStart"] = tI
    so = bpy.data.objects[f"SOCKET_{SM}_LOD0_MagInsertStart"]
    so.location = tuple(tI * 0.001)
    rep["fit_set_sockets"] = {"MagInsertStart": {"blender_mm": [round(float(v), 5) for v in tI],
                                                 "spec_blender_mm": SOCK["MagInsertStart"]["blender_mm"],
                                                 "delta_mm": round(float(np.abs(tI - np.array(
                                                     SOCK["MagInsertStart"]["blender_mm"])).max()), 5),
                                                 "rule": "Mag - 68.2 x the magazine's +Z (straight path, R_y(-8.267))"}}
    com = np.array(bpy.data.objects[f"SOCKET_{SM}_LOD0_CenterOfMass"].location, float) * 1000.0
    d_rep = float(np.abs(com - np.array(GAME_REP["mass"]["com_B_mm"])).max())
    if d_rep > 0.0051:
        raise SystemExit(f"W3b CoM empty {com} disagrees with game_report by {d_rep:.4f} mm")
    for n in ("CenterOfMass", "Holster"):
        FIT_SET[n] = com.copy()
        rep["fit_set_sockets"][n] = {"blender_mm": [round(float(v), 5) for v in com], "delta_mm": round(d_rep, 5),
                                     "rule": "the W3b CoM empty on SM_SMG01_LOD0 (game_report rounds to 0.01 mm)"}
    CL.configure(float(dims("bolt")["travel"]), float(dims("charging_handle")["travel_minus_X"]), ins)
    rep["motion"] = {"bolt_travel_mm": CL.TRAVEL, "handle_travel_mm": CL.HANDLE, "insert_mm": CL.INSERT,
                     "mag_axis_B": z_mag.round(6).tolist(), "drop_mm": CL.DROP_MM}
    coll = bpy.data.collections.new(SK)
    bpy.context.scene.collection.children.link(coll)
    # ------------------------------------------------------------ skeleton
    rows = bone_rows()
    arm = RG.make_armature("root", rows, coll)
    rep["bones"] = {n: {"head_mm": [round(v, 4) for v in h], "parent": p} for n, h, p in rows}
    # ------------------------------------------------------------ skinned LOD meshes (no magazine)
    mats = [bpy.data.materials[s] for s in SLOTS]

    def slot_of(o):
        return SLOTS.index(part_rec(o)["slot"])
    meshes = []
    rep["lods"] = {}
    for lv in range(4):
        parts = [(o, bone_of(o)) for o in lod_objects(lv) if bone_of(o) != "magazine"
                 and part_rec(o).get("slot") != "M_SMG01_Mag"]
        name = SK if lv == 0 else f"{SK}_LOD{lv}"
        ob = RG.join_rigid(name, parts, arm, mats, slot_of, coll)
        meshes.append(ob)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        uvfix = RG.fix_collapsed_uvs(ob)
        rep["lods"][name] = {"triangles": tris, "parts": len(parts), "uv0_collapsed_fix": uvfix,
                             "bones_weighted": sorted({b for _, b in parts})}
        log(name, tris, "tris,", len(parts), "parts")
    # ------------------------------------------------------------ QA (B1, B2), UD on the SK meshes
    expect = {n: p for n, _, p in rows}
    qa = SKP.qa_skeletal(meshes, arm, max_influences=1, bone_budget=None, max_slots=2)
    std = RG.skeleton_standard_checks(arm, expect=expect)
    rigid = []
    for ob in meshes:
        rigid += RG.rigid_skin_checks(ob, arm)
    rep["qa_skeletal"] = {"passed": qa["passed"], "n": len(qa["checks"]),
                          "failed": [c for c in qa["checks"] if not c["passed"]]}
    rep["skeleton_standard"] = {"passed": all(c["passed"] for c in std), "checks": std}
    rep["rigid_skin"] = {"passed": all(c["passed"] for c in rigid), "checks": rigid}
    from gunlib import ud as UD
    from gunlib import tspace as TS
    rep["sk_ud"] = {}
    for ob in meshes:
        r = UD.check_object(ob)
        rep["sk_ud"][ob.name] = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
                                 "ud3_collapsed_unreal": int(len(TS.collapsed(ob.data, "UV0", unreal=True)))}
    log("qa_skeletal", qa["passed"], [c["name"] + ":" + str(c["object"]) + ":" + c["detail"] for c in qa["checks"]
                                      if not c["passed"]][:12])
    log("standard", rep["skeleton_standard"]["passed"], "rigid", rep["rigid_skin"]["passed"], "UD", rep["sk_ud"])
    # ------------------------------------------------------------ clips
    clips = CL.all_clips()
    mag_parts = [o for o in lod_objects(0) if bone_of(o) == "magazine"]
    Vm = np.vstack([GM.mesh_vt(o)[0] for o in mag_parts])
    well_bottom = float(SPEC.box("magwell")["Z"][0]) - GRIP[2]       # the magwell's lowest point (frame B)
    for cname in ("A_SMG01_Reload", "A_SMG01_ReloadEmpty"):
        frames, notes, fps = clips[cname]
        out_f = None
        for f, v in frames:
            M = basis_from(v).get("magazine")
            if M is None:
                continue
            if (Vm @ M[:3, :3].T + M[:3, 3])[:, 2].max() < well_bottom:
                out_f = f
                break
        clips[cname] = (frames, [(n, out_f if n == "MagOut" else fr) for n, fr in notes], fps)
    actions, notifies = [], []
    rep["clips"] = {}
    for cname, (frames, notes, fps) in clips.items():
        act = RG.key_action(arm, cname, [(f, basis_from(v)) for f, v in frames])
        actions.append(act)
        s_rest, e_rest = CL.ends_rest(cname, frames)
        rep["clips"][cname] = {"fps": fps, "frames": [frames[0][0], frames[-1][0]],
                               "seconds": round((frames[-1][0] - frames[0][0]) / fps, 4),
                               "starts_at_rest": s_rest, "ends_at_rest": e_rest,
                               "rest_as_declared": CL.rest_as_declared(frames, cname),
                               "selector_held_deg": sorted({round(float(v.get("selector", 0.0)), 3)
                                                            for _f, v in frames}),
                               "values": {str(f): {k: round(float(x), 4) for k, x in v.items() if x}
                                          for f, v in frames}}
        for n, fr in notes:
            notifies.append({"clip": cname, "name": n, "frame": int(fr), "time_s": round(fr / fps, 4)})
    rep["notifies"] = notifies
    moves_bolt = {c: any(v.get("bolt") for _f, v in fr) for c, (fr, _n, _p) in clips.items()}
    rep["selector_rule"] = {c: {"moves_bolt": moves_bolt[c], "selector_values": rep["clips"][c]["selector_held_deg"],
                                "ok": (rep["clips"][c]["selector_held_deg"] == [CL.SEL_HELD]) if moves_bolt[c]
                                else True} for c in clips}
    rng = {"bolt": (0.0, CL.TRAVEL), "handle": (0.0, CL.HANDLE), "trigger": (0.0, CL.TRIG),
           "selector": (CL.SEL["SAFE"], CL.SEL["AUTO"]), "release": (CL.REL, 0.0), "stock": (0.0, CL.FOLD),
           "rear": (0.0, CL.REAR_FOLD), "front": (CL.FRONT_FOLD, 0.0)}
    cover = {}
    for cname, (frames, _n, _f) in clips.items():
        for f, v in frames:
            for k, (a, b) in rng.items():
                x = v.get(k, 0.0)
                cover.setdefault(k, [1e9, -1e9])
                cover[k] = [min(cover[k][0], x), max(cover[k][1], x)]
                if x < a - 1e-9 or x > b + 1e-9:
                    rep.setdefault("b3_out_of_range", []).append({"clip": cname, "frame": f, k: x})
    rep["b3_coverage"] = {k: [round(a, 4), round(b, 4)] for k, (a, b) in cover.items()}
    rep["fold_latch_path"] = fold_latch_report(arm, clips)
    log("fold latch path", rep["fold_latch_path"]["worst_depth_mm"], rep["fold_latch_path"]["parts_hit"])
    # ------------------------------------------------------------ bounds over every clip frame (LOD0-3) (B11)
    rlo, rhi, lo, hi, worst = posed_envelope(arm, meshes[0], clips)
    for m_ in meshes[1:]:
        _l, _h, lo2, hi2, w2 = posed_envelope(arm, m_, clips)
        lo, hi = np.minimum(lo, lo2), np.maximum(hi, hi2)
        for k_, v_ in w2.items():
            worst[k_] = max(worst.get(k_, 0.0), v_)
    ext_pos = np.where(hi > rhi + 1e-6, hi - rhi + 1.0, 0.0)
    ext_neg = np.where(lo < rlo - 1e-6, rlo - lo + 1.0, 0.0)
    elo, ehi = rlo - ext_neg, rhi + ext_pos
    bounds_ext = {"positive_cm": [round(float(ext_pos[0]) * 0.1, 3), round(float(ext_neg[1]) * 0.1, 3),
                                  round(float(ext_pos[2]) * 0.1, 3)],
                  "negative_cm": [round(float(ext_neg[0]) * 0.1, 3), round(float(ext_pos[1]) * 0.1, 3),
                                  round(float(ext_neg[2]) * 0.1, 3)],
                  "rest_aabb_mm": [np.round(rlo, 3).tolist(), np.round(rhi, 3).tolist()],
                  "posed_aabb_mm": [np.round(lo, 3).tolist(), np.round(hi, 3).tolist()],
                  "extended_aabb_mm": [np.round(elo, 3).tolist(), np.round(ehi, 3).tolist()],
                  "worst_excursion_mm_per_clip": {k: round(v, 3) for k, v in worst.items()},
                  "why": "LOD0-3 posed at every frame of every clip (the folded stock: StockFold / StockUnfold; the "
                         "folded sights: SightFlip) vs LOD0's bind AABB (Unreal's stored bounds), per axis (+1 mm "
                         "where it grows; Unreal axes: y flipped): the mesh's Positive/Negative Bounds Extension. The "
                         "attached magazine is its own component with its own bounds"}
    rep["bounds_extension"] = bounds_ext
    log("bounds ext", bounds_ext["positive_cm"], bounds_ext["negative_cm"], worst)
    # ------------------------------------------------------------ screen sizes (twin from the LOD-pop gate; SK converted)
    gz = json.loads((GATES / "game_lod_sizes.json").read_text())
    sizes_twin = list(gz[SM])
    r_twin = float(gz["bounds_radius_m"])
    r_sk = float(0.5 * np.linalg.norm(ehi - elo)) / 1000.0
    sizes_sk = [1.0] + [round(s * r_sk / r_twin, 5) for s in sizes_twin[1:]]
    gz[SK] = sizes_sk
    gz["SK_engine_radius_m"] = round(r_sk, 4)
    gz["note"] = ("SM_SMG01 sizes from the LOD-pop gate at the twin's radius (bounds_radius_m); SK_SMG01 sizes = the "
                  "same switch distances at the SK's engine radius (bind box + bounds extension, both stock states)")
    (GATES / "game_lod_sizes.json").write_text(json.dumps(gz, indent=1))
    rep["lod_screen_sizes"] = {"SM": sizes_twin, "SK": sizes_sk, "r_twin_m": r_twin, "r_sk_engine_m": round(r_sk, 4),
                               "switch_distances_m": [round(1.778 * r_twin / s, 3) for s in sizes_twin[1:]]}
    # ------------------------------------------------------------ sockets, physics
    sockets = socket_rows(com)
    bodies = physics_bodies()
    # ------------------------------------------------------------ the static twin: qa_check, then export
    lods = [bpy.data.objects[f"{SM}_LOD{k}"] for k in range(4)]
    q0 = qa_check(lods, budget_tris=BUDGET, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:3], budget_tris=BUDGET, texel_density=agg[f"{SM}_LOD0"], require_uv1=True)
    rep[f"qa_check_{SM}"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                             "texel_target_px_cm": agg[f"{SM}_LOD0"],
                             "failed": [c for c in q0["checks"] + q["checks"] if not c["passed"]],
                             "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa_check", SM, rep[f"qa_check_{SM}"]["passed"])
    sk_ud_ok = all(v["ud1_drops"] == 0 and v["min_area_mm2"] >= 0.01 and v["ud3_collapsed_unreal"] == 0
                   for v in rep["sk_ud"].values())
    if not (rep[f"qa_check_{SM}"]["passed"] and qa["passed"] and rep["rigid_skin"]["passed"]
            and rep["skeleton_standard"]["passed"]):
        (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit("[SMG01-rig] QA failed: nothing exported (see scratch/rig/rig_report.json)")
    rep["sk_ud_ok"] = sk_ud_ok
    EXPORTS.mkdir(parents=True, exist_ok=True)
    grp = bpy.data.objects[f"{SM}_LodGroup"]
    sres = export_fbx(str(EXPORTS / f"{SM}.fbx"), [grp], kind="static", lod_screen_sizes=list(sizes_twin))
    rep["export_static"] = {"fbx": sres["filepath"], "sidecar": sres["sidecar"], "warnings": sres["warnings"],
                            "lod_screen_sizes": sres["lod_screen_sizes"]}
    log(f"{SM} exported", sres["warnings"])
    # ------------------------------------------------------------ the skeletal set
    bpy.context.scene.frame_current = REST_FRAME
    written = SKP.export_skeletal_set(str(EXPORTS), arm, meshes, SK, actions=actions, frame_rate=FPS,
                                      fps_by_action={k: v[2] for k, v in clips.items()})
    bpy.context.scene.frame_current = 0
    proxy = proxy_mesh(arm, mats[0], coll, com)
    pw = SKP.export_skeletal_set(str(EXPORTS / "Physics"), arm, [proxy], f"{SK}_PhysicsProxy", frame_rate=FPS)
    pme = proxy.data
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.meshes.remove(pme)
    rep["export_skeletal"] = {"meshes": [{k: v for k, v in m.items() if k != "objects"} for m in written["meshes"]],
                              "animations": written["animations"], "physics_proxy": pw["meshes"][0]["fbx"]}
    # ------------------------------------------------------------ sidecar
    h1p = SCRATCH / "h1_full.json"
    h1 = json.loads(h1p.read_text()) if h1p.exists() else None
    gun = dict(D["sidecar_gun_block"])
    gun["texel_classes_px_per_cm"] = D["textures"]["texel_classes_px_per_cm"]
    gun["hand_offset"] = (h1 or {}).get("hand_offset", {"weapon_r_to_Grip": "identity (provisional)",
                                                         "note": "H1 full not run"})
    gun["first_person"] = ("FP_Weapon + TP_Weapon (SK_SMG01) and FP_Mag + TP_Mag (SM_SMG01_Mag on Mag); every FP "
                           "component FirstPersonPrimitiveType = FirstPerson and ForcedLodModel = 1")
    gun["center_of_mass_folded_mm"] = GAME_REP["mass"]["com_folded_B_mm"]
    mats_block = {"M_SMG01_Metal": {"slot": 0, "master": "M_Steel_Master", "metal_from_orm": True,
                                    "user_control": "Steel Tint",
                                    "textures": {k: f"T_SMG01_Metal_{k}" for k in ("BC", "ORM", "N", "Masks")}},
                  "M_SMG01_Furniture": {"slot": 1, "master": "M_Fabric_Master", "metal_from_orm": False,
                                        "user_control": "Colour (recolour group SMG01, default the shipped black)",
                                        "textures": {k: f"T_SMG01_Furniture_{k}" for k in ("BC", "ORM", "N", "Masks")},
                                        "detail16": "Recolour/T_SMG01_Furniture_Detail16"},
                  "_source": "smg_spec.json materials.slots (the slot table, not a literal)"}
    clips_side = []
    for a in written["animations"]:
        nm = Path(a["fbx"]).stem
        clips_side.append({"file": Path(a["fbx"]).name, "frames": a["frames"], "fps": a["fps"], "loop": False,
                           "starts_at_rest": rep["clips"][nm]["starts_at_rest"],
                           "ends_at_rest": rep["clips"][nm]["ends_at_rest"],
                           "selector_held_deg": rep["clips"][nm]["selector_held_deg"]})
    payload = {
        "asset": SK, "skeleton": f"{SK}_Skeleton", "physics_asset": f"PHYS_{CODE}",
        "compatible_skeletons": ["SK_AR01_Skeleton"],
        "bones": [b.name for b in arm.data.bones], "root_bone": "root",
        "bones_rest": {b.name: {"head_mm": [round(v * 1000.0, 4) for v in b.head_local],
                                "head_cm": SKP.ue_component_transform(np.eye(3), [v * 1000.0 for v in b.head_local])["location_cm"],
                                "parent": b.parent.name if b.parent else "root",
                                "motion": SPEC.bones[b.name].get("motion")} for b in arm.data.bones},
        "lod_files": [Path(m["fbx"]).name for m in written["meshes"]],
        "lod_screen_sizes": sizes_sk,
        "lod_note": "import LOD1-3 with SkeletalMeshEditorSubsystem.import_lod (same skeleton, same root; no bones "
                    "removed). The sizes are the LOD-pop gate's switch distances at the SK's engine radius (bind box + "
                    "bounds extension). First-person components force LOD0 (ForcedLodModel = 1)",
        "lod_triangles": {k: v["triangles"] for k, v in rep["lods"].items()},
        "animations": clips_side,
        "notifies": notifies,
        "notifies_note": "FBX carries no notifies: the Unreal harness adds them at these frames (U9). ReloadEmpty starts "
                         "with the bolt held open (starts_at_rest false); StockFold ends folded and StockUnfold starts "
                         "folded. Clips that move the bolt hold the selector at AUTO (45 deg); blend the player's fire "
                         "mode from A_SMG01_Selector per bone",
        "import": {"use_t0_as_ref_pose": False, "update_skeleton_reference_pose": False,
                   "import_morph_targets": False, "create_physics_asset": False, "normals": "import normals",
                   "convert_scene": True, "force_front_x_axis": False, "custom_sample_rate": "the file's rate",
                   "bone_compression": BONE_COMPRESSION,
                   "bone_compression_why": "rigid parts: ACL cracked rigid parts by ~1.1 mm on the fan (gun study "
                                           "4.10.9); U9 gates <= 0.1 mm",
                   "bounds_extension_cm": bounds_ext},
        "physics_proxies": {SK: f"Physics/{SK}_PhysicsProxy.fbx",
                            "how": "import the proxy onto SK_SMG01_Skeleton with Create Physics Asset ON (one 250 mm "
                                   "cube on 'body'), rewrite the body from physics_bodies, rename it PHYS_SMG01, assign "
                                   "it to SK_SMG01, delete the proxy mesh"},
        "physics_bodies": bodies, "mass_kg": MASS_KG,
        "center_of_mass_mm": [round(float(v), 3) for v in com],
        "sockets": sockets,
        "magazine": {"asset": "SM_SMG01_Mag", "socket": "Mag", "bone": "magazine",
                     "attach": "zero relative transform (SnapToTarget) on the Mag socket; straight reload path "
                               "MagInsertStart -> (lerp along the magazine's -Z, rotation constant) -> Mag",
                     "insert_mm": CL.INSERT},
        "materials": mats_block,
        "gun": gun,
    }
    sc = SKP.write_skeletal_sidecar(str(EXPORTS / f"{SK}.fbx"), payload)
    # ------------------------------------------------------------ hashes, names
    files = [m["fbx"] for m in written["meshes"]] + [a["fbx"] for a in written["animations"]] + \
        [pw["meshes"][0]["fbx"], sc, sres["filepath"], sres["sidecar"]]
    rep["files"] = {str(Path(f).relative_to(ROOT)).replace("\\", "/"): {"sha256": sha256(f), "bytes": Path(f).stat().st_size}
                    for f in files}
    names = [b.name for b in arm.data.bones] + [s["name"] for s in sockets] + [m.name for m in meshes] + \
        [a.name for a in actions] + list(SLOTS) + [n["name"] for n in notifies] + [Path(f).name for f in files]
    hits = {n: qa_gun.deny_hits(n) for n in names if qa_gun.deny_hits(n)}
    side_txt = Path(sc).read_text()
    import re
    rep["deny_tokens"] = {"checked": len(names), "hits": hits, "sidecar_text_hits":
                          sorted({h for w in re.findall(r"[A-Za-z0-9_\-]+", side_txt) for h in qa_gun.deny_hits(w)}),
                          "pass": not hits}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("RIG_DONE %.1fs" % (time.time() - t0))


main()
