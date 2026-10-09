"""AR-01 stage 5: rig + export (headless Blender, on the stage-4 blend):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_rig.py

RIFLE_BUILD_PLAN 12 stage 5, GUN_BUILDING_STUDY 4.6 / 5.2 / 5.3 / 7.2:
- armature object 'root' at the Grip origin (identity), bones from rifle_spec bones.table (body + bolt, trigger,
  selector, mag_release, magazine, sight_rear, muzzle_device), rest rotation = root's (gunlib.rig.make_armature);
- SK_AR01 / _LOD1..3: each LOD's part objects (the very objects the static twin joins), magazine parts left out (the
  magazine is SM_AR01_Mag on the 'magazine' bone's Mag socket: an attach bone with no weighted vertices), every part
  rigidly on its bone (one influence at 1.0), slots M_AR01_Metal (0) + M_AR01_Furniture (1), UV0 in 0..1 per slot;
- weapon clips (keys every frame, LINEAR): A_AR01_Fire (60 fps), A_AR01_Charge, A_AR01_Reload, A_AR01_ReloadEmpty,
  A_AR01_Selector (30 fps); the reload moves the magazine bone along the spec's rock path (Mag -> MagRockStart ->
  MagInsertStart) and away; notifies with frames go in the skeletal sidecar (FBX carries none);
- 17 sockets on their bones (spec values; CenterOfMass / Holster = the stage-4 computed CoM), physics body on 'body'
  (boxes / capsule fitted to the LOD0 part groups, 3.1 kg), proxy FBX in Physics/ (fan method), bounds extension from
  every vertex of LOD0 at every frame of every clip;
- qa_skeletal(max_influences=1) + gunlib.rig rigid-skin and skeleton-standard checks, then
  skeletal_prop.export_skeletal_set (centimetre copy, per LOD and per clip) and the sidecar;
- SM_AR01 (stage-4 twin, merged magazine) through qa_check and export_fbx(kind="static") with the LOD-pop sizes;
- sha256 of every written file.
Writes WorkFiles/guns/rifle/scratch/rig/rig_report.json and saves Assets/Guns/AR01.blend (rig in collection SK_AR01).
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
from rifle_common import ROOT, SCRATCH, BLEND, GRIP, SPEC, GATES  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline import skeletal_prop as SKP  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from gunlib import rig as RG  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402

CODE = "AR01"
SK = "SK_AR01"
EXPORTS = ROOT / "Exports" / "Guns" / "AR01"
OUT = SCRATCH / "rig"
OUT.mkdir(parents=True, exist_ok=True)
SLOTS = ("M_AR01_Metal", "M_AR01_Furniture")
FPS = 30
FPS_FIRE = 60
MASS_KG = 3.1
INSERT_MM = 8.0
FIT_SET = {}               # sockets the fit sets exactly (spec values are rounded to 0.01 mm)
BONE_COMPRESSION = "/Engine/Animation/DefaultRecorderBoneCompression"


def log(*a):
    print("[AR01-rig]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def B(p_M):
    return np.asarray(p_M, float) - GRIP


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


# ====================================================================== skeleton
SOCK = {r["socket"]: r for r in SPEC.sockets["rifle"]}
GAME_REP = json.loads((SCRATCH / "game" / "game_report.json").read_text())
COM_B = np.array(GAME_REP["mass"]["com_B_mm"], float)


def bone_rows():
    """(name, head mm in frame B, parent): spec heads; 'bolt' (no spec head: it only translates) at the charging
    handle tab (its hand target)."""
    rows = []
    for b in SPEC.d["bones"]["table"]:
        n = b["bone"]
        if n == "bolt":
            head = np.array(SOCK["ChargingHandle"]["blender_mm"], float)
        else:
            head = B(b["head_M"])
        rows.append((n, tuple(float(v) for v in head), b["parent"]))
    return rows


BONE_OF_PART = {}          # LOD0 part name -> bone (from the part records)


def bone_of(ob):
    rec = part_rec(ob)
    if rec.get("bone"):
        return rec["bone"]
    return BONE_OF_PART.get(base_of(ob.name), "body")


def lod_objects(lv):
    cn = "AR01_Parts" if lv == 0 else f"AR01_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


# clips: rifle_clips.py
REST_FRAME = -100          # stage-7: the scene frame while the clips are written (before every clip)
import rifle_clips as CL  # noqa: E402
from rifle_clips import basis_from  # noqa: E402


# ====================================================================== main
def clean_previous():
    for o in list(bpy.data.objects):
        if o.name == "root" or o.name.startswith(("SK_AR01", "SK_AR01_PhysicsProxy")):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.armatures if isinstance(d, bpy.types.Armature) else bpy.data.meshes).remove(d)
    for a in list(bpy.data.actions):
        if a.name.startswith("A_AR01_"):
            bpy.data.actions.remove(a)
    c = bpy.data.collections.get(SK)
    if c is not None:
        bpy.data.collections.remove(c)


def obb(V, R):
    """Box (centre, size) of points V (mm) in the frame whose axes are R's columns."""
    L = V @ R
    lo, hi = L.min(0), L.max(0)
    return R @ (0.5 * (lo + hi)), hi - lo


def physics_bodies():
    """One body on 'body' (the held / dropped rifle): boxes and a capsule fitted to LOD0 part groups (frame B)."""
    objs = {o.name: o for o in lod_objects(0)}

    def pts(names):
        return np.vstack([GM.mesh_vt(objs[n])[0] for n in names if n in objs])
    I = np.eye(3)
    a = math.radians(22.35)
    Rg = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])   # grip axis raked
    s = math.atan2(0.174, 0.985)
    Rs = np.array([[math.cos(s), 0, -math.sin(s)], [0, 1, 0], [math.sin(s), 0, math.cos(s)]])  # comb line
    groups = [
        ("receiver, dust cover, rear sight, carrier, selector", ["receiver", "rear_trunnion", "dust_cover", "rivets",
          "receiver_rails", "bolt_carrier", "rear_sight_block", "rear_sight_leaf", "rear_sight_slider",
          "recoil_spring_button", "selector", "handguard_retainer"], I, "box"),
        ("trigger guard, trigger, catch", ["trigger_guard", "trigger", "mag_catch"], I, "box"),
        ("fore-end (handguards, cap, band)", ["upper_handguard", "lower_handguard", "gas_tube_rear_cap",
                                             "handguard_front_band"], I, "box"),
        ("gas block", ["gas_block"], I, "box"),
        ("front sight block + post", ["front_sight_block", "front_sight_post"], I, "box"),
        ("pistol grip", ["pistol_grip"], Rg, "box"),
        ("stock + butt plate", ["buttstock", "butt_plate", "butt_screws", "stock_hardware", "rear_tang",
                                "sling_swivel_base", "sling_swivel_loop"], Rs, "box"),
    ]
    elements = []
    for desc, names, R, shape in groups:
        c, size = obb(pts(names), R)
        elements.append({"shape": "box", "covers": desc, "centre_mm": [round(float(v), 3) for v in c],
                         "matrix": np.round(R, 7).tolist(), "size_mm": [round(float(v), 3) for v in size],
                         "collision": True, "contribute_to_mass": True})
    # barrel from the front band to the brake end, as one capsule along X (barrel, rod, brake)
    P = pts(["barrel", "muzzle_brake", "cleaning_rod"])
    P = P[P[:, 0] >= B([647.1, 0, 0])[0]]
    x0, x1 = float(P[:, 0].min()), float(P[:, 0].max())
    zc = float(np.mean([P[:, 2].min(), P[:, 2].max()]))
    r = float(np.max(np.hypot(P[:, 1], P[:, 2] - zc)))
    Rc = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)     # capsule axis (local Z) along +X
    elements.append({"shape": "capsule", "covers": "barrel, rod and brake ahead of the front band",
                     "centre_mm": [round(0.5 * (x0 + x1), 3), 0.0, round(zc, 3)], "matrix": Rc.tolist(),
                     "radius_mm": round(r, 3), "length_mm": round(max(0.1, (x1 - x0) - 2 * r), 3), "axis": "Z -> +X",
                     "collision": True, "contribute_to_mass": True})
    for e in elements:
        e["unreal_component"] = SKP.ue_component_transform(np.array(e["matrix"]), e["centre_mm"])
        if "size_mm" in e:
            e["size_cm"] = [round(v * 0.1, 4) for v in e["size_mm"]]
    return [{"bone": "body", "unreal_bone_any_of": ["body"], "physics_type": "Default", "consider_for_bounds": True,
             "mass_kg": MASS_KG, "elements": elements,
             "role": "ONE rigid body on 'body' (every other bone is its child): Kinematic while held (or NoCollision "
                     "/ QueryOnly, plan 7.2), simulated when dropped; the seated magazine is its own component with "
                     "collision off while attached"}]


def socket_rows():
    rows = []
    for r in SPEC.sockets["rifle"]:
        n = r["socket"]
        loc = np.array(r["blender_mm"], float)
        if n in ("CenterOfMass", "Holster"):
            loc = COM_B.copy()
        if n in FIT_SET:
            loc = FIT_SET[n].copy()
        ro = r["unreal_rotation_deg"]
        e = GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"])
        from mathutils import Euler
        Rb = np.array(Euler(e, "XYZ").to_matrix())
        rows.append({"name": n, "bone": r["bone"], "location_mm": [round(float(v), 4) for v in loc],
                     "matrix": np.round(Rb, 9).tolist(), "unreal_rotation_deg": ro,
                     "computed": n in ("CenterOfMass", "Holster"), "fit_set": n in FIT_SET, "use": r.get("use", ""),
                     "unreal_component": SKP.ue_component_transform(Rb, loc)})
    return rows


def posed_envelope(arm, mesh, clips):
    """AABB (mm, frame B) of every LOD0 vertex at every frame of every clip (rigid: bone matrices x rest verts)."""
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
                worst[cname] = max(worst.get(cname, 0.0), float(np.maximum(P.max(0) - rest_hi, rest_lo - P.min(0)).max()))
    return rest_lo, rest_hi, lo, hi, worst


def main():
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    t0 = time.time()
    clean_previous()
    rep = {"stage": "5 rig + export", "spec_version": SPEC.d["meta"]["version"]}
    for o in lod_objects(0):
        rec = part_rec(o)
        BONE_OF_PART[o.name] = rec.get("bone", "body")
    TRAVEL = float(part_rec(bpy.data.objects["bolt_carrier"])["joint"]["travel_mm"])
    ROCK = float(SOCK["MagRockStart"]["unreal_rotation_deg"]["pitch"])
    # the fit sets MagInsertStart exactly on the tilted magazine's -Z, INSERT_MM below the hook (plan 2.3: d = 8 mm);
    # the spec's value is that point rounded to 0.01 mm
    INSERT = INSERT_MM
    tR = np.array(SOCK["MagRockStart"]["blender_mm"], float)
    tI = tR + RG.rot_y(-ROCK)[:3, :3] @ np.array([0.0, 0.0, -INSERT])
    FIT_SET["MagInsertStart"] = tI
    so = bpy.data.objects["SOCKET_SM_AR01_LOD0_MagInsertStart"]
    so.location = tuple(tI * 0.001)
    rep["fit_set_sockets"] = {"MagInsertStart": {"blender_mm": [round(float(v), 5) for v in tI],
                                                 "spec_blender_mm": SOCK["MagInsertStart"]["blender_mm"],
                                                 "delta_mm": round(float(np.abs(tI - np.array(SOCK["MagInsertStart"]["blender_mm"])).max()), 5),
                                                 "rule": "MagRockStart + R_y(-rock) (0, 0, -8 mm): on the tilted magazine's -Z"}}
    # CenterOfMass / Holster: the exact stage-4 CoM the static twin's empties carry (game_report rounds it to
    # 0.01 mm), so SK_AR01 and SM_AR01 ship the same point; the report value must agree to its rounding
    global COM_B
    com_exact = np.array(bpy.data.objects["SOCKET_SM_AR01_LOD0_CenterOfMass"].location, float) * 1000.0
    d_rep = float(np.abs(com_exact - COM_B).max())
    if d_rep > 0.0051:
        raise SystemExit(f"stage-4 CoM empty {com_exact} disagrees with game_report {COM_B} by {d_rep:.4f} mm")
    COM_B = com_exact
    for n in ("CenterOfMass", "Holster"):
        FIT_SET[n] = com_exact.copy()
        rep["fit_set_sockets"][n] = {"blender_mm": [round(float(v), 5) for v in com_exact],
                                     "game_report_com_B_mm": GAME_REP["mass"]["com_B_mm"],
                                     "delta_mm": round(d_rep, 5),
                                     "rule": "the stage-4 CoM empty on SM_AR01_LOD0 (game_report rounds to 0.01 mm)"}
    CL.configure(TRAVEL, ROCK, INSERT)
    rep["motion"] = {"bolt_travel_mm": TRAVEL, "rock_deg": ROCK, "insert_mm": round(INSERT, 4), "drop_mm": CL.DROP_MM}
    coll = bpy.data.collections.new(SK)
    bpy.context.scene.collection.children.link(coll)
    # ------------------------------------------------------------ skeleton
    rows = bone_rows()
    arm = RG.make_armature("root", rows, coll)
    rep["bones"] = {n: {"head_mm": [round(v, 4) for v in h], "parent": p} for n, h, p in rows}
    # ------------------------------------------------------------ skinned LOD meshes (no magazine)
    mats = [bpy.data.materials[s] for s in SLOTS]

    def slot_of(o):
        m = o.data.materials[0].name if o.data.materials else ""
        return SLOTS.index(m)
    meshes = []
    rep["lods"] = {}
    for lv in range(4):
        parts = [(o, bone_of(o)) for o in lod_objects(lv) if bone_of(o) != "magazine"
                 and (o.data.materials[0].name if o.data.materials else "") != "M_AR01_Mag"]
        name = SK if lv == 0 else f"{SK}_LOD{lv}"
        ob = RG.join_rigid(name, parts, arm, mats, slot_of, coll)
        meshes.append(ob)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        uvfix = RG.fix_collapsed_uvs(ob)
        rep["lods"][name] = {"triangles": tris, "parts": len(parts), "uv0_collapsed_fix": uvfix,
                             "bones_weighted": sorted({b for _, b in parts})}
        log(name, tris, "tris,", len(parts), "parts")
    # ------------------------------------------------------------ QA (B1, B2)
    expect = {n: p for n, _, p in rows}
    qa = SKP.qa_skeletal(meshes, arm, max_influences=1, bone_budget=None, max_slots=2)
    std = RG.skeleton_standard_checks(arm, expect=expect)
    rigid = []
    for ob in meshes:
        rigid += RG.rigid_skin_checks(ob, arm)
    mag_weighted = sum(c["detail"].count("magazine ") for c in rigid if c["name"] == "rigid_vertices_per_bone")
    rep["qa_skeletal"] = {"passed": qa["passed"], "n": len(qa["checks"]),
                          "failed": [c for c in qa["checks"] if not c["passed"]]}
    rep["skeleton_standard"] = {"passed": all(c["passed"] for c in std), "checks": std}
    rep["rigid_skin"] = {"passed": all(c["passed"] for c in rigid), "checks": rigid,
                         "magazine_bone_vertex_groups": mag_weighted}
    log("qa_skeletal", qa["passed"], [c["name"] + ":" + str(c["object"]) + ":" + c["detail"] for c in qa["checks"]
                                      if not c["passed"]][:12])
    log("standard", rep["skeleton_standard"]["passed"], "rigid", rep["rigid_skin"]["passed"])
    # ------------------------------------------------------------ clips
    clips = CL.all_clips()
    # MagOut: the first frame the magazine (LOD0 parts) is wholly below the receiver's bottom plate
    mag_parts = [o for o in lod_objects(0) if bone_of(o) == "magazine"]
    Vm = np.vstack([GM.mesh_vt(o)[0] for o in mag_parts])
    head = np.array(rep["bones"]["magazine"]["head_mm"])
    rec_bottom = float(GM.mesh_vt(bpy.data.objects["receiver"])[0][:, 2].min())
    for cname in ("A_AR01_Reload", "A_AR01_ReloadEmpty"):
        frames, notes, fps = clips[cname]
        out_f = None
        for f, v in frames:
            M = basis_from(v).get("magazine")
            if M is None:
                continue
            P = (Vm - head) @ M[:3, :3].T + M[:3, 3] + head
            if P[:, 2].max() < rec_bottom:
                out_f = f
                break
        clips[cname] = (frames, [(n, out_f if n == "MagOut" else fr) for n, fr in notes], fps)
    actions = []
    rep["clips"] = {}
    notifies = []
    for cname, (frames, notes, fps) in clips.items():
        act = RG.key_action(arm, cname, [(f, basis_from(v)) for f, v in frames])
        actions.append(act)
        f0, f1 = frames[0][0], frames[-1][0]
        end_rest = CL.loop_rest(frames)          # rest at both ends (a held selector detent allowed)
        rep["clips"][cname] = {"fps": fps, "frames": [f0, f1], "seconds": round((f1 - f0) / fps, 4),
                               "starts_and_ends_at_rest": end_rest,
                               "values": {str(f): {k: round(float(x), 4) for k, x in v.items() if x} for f, v in frames}}
        for n, fr in notes:
            notifies.append({"clip": cname, "name": n, "frame": int(fr), "time_s": round(fr / fps, 4)})
    rep["notifies"] = notifies
    # B3 coverage: every clip value inside the range B3 swept (gates/form.json, game.json)
    rng = {"bolt": (0.0, TRAVEL), "trigger": (0.0, 12.0), "selector": (0.0, 32.0), "catch": (0.0, 10.0),
           "leaf": (0.0, 6.0)}
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
    # ------------------------------------------------------------ bounds over every clip frame (LOD0-3)
    # stage-8 fix round (U5 in Unreal): Unreal stores LOD0's bind box as the asset bounds, and LOD2 is 2.8 mm wider on
    # the left (fix log N4): the extension covers every LOD at every clip frame, not LOD0 only
    rlo, rhi, lo, hi, worst = posed_envelope(arm, meshes[0], clips)
    for m_ in meshes[1:]:
        _l, _h, lo2, hi2, w2 = posed_envelope(arm, m_, clips)
        lo, hi = np.minimum(lo, lo2), np.maximum(hi, hi2)
        for k_, v_ in w2.items():
            worst[k_] = max(worst.get(k_, 0.0), v_)
    ext_pos = np.where(hi > rhi + 1e-6, hi - rhi + 1.0, 0.0)
    ext_neg = np.where(lo < rlo - 1e-6, rlo - lo + 1.0, 0.0)
    bounds_ext = {"positive_cm": [round(float(ext_pos[0]) * 0.1, 3), round(float(ext_neg[1]) * 0.1, 3),
                                  round(float(ext_pos[2]) * 0.1, 3)],
                  "negative_cm": [round(float(ext_neg[0]) * 0.1, 3), round(float(ext_pos[1]) * 0.1, 3),
                                  round(float(ext_neg[2]) * 0.1, 3)],
                  "rest_aabb_mm": [np.round(rlo, 3).tolist(), np.round(rhi, 3).tolist()],
                  "posed_aabb_mm": [np.round(lo, 3).tolist(), np.round(hi, 3).tolist()],
                  "worst_excursion_mm_per_clip": {k: round(v, 3) for k, v in worst.items()},
                  "why": "LOD0-3 posed at every frame of every clip vs LOD0's bind AABB (Unreal's stored bounds), per axis (+1 mm where it grows; "
                         "Unreal axes: y flipped): the mesh's own Positive/Negative Bounds Extension. The attached "
                         "magazine is its own component with its own bounds"}
    rep["bounds_extension"] = bounds_ext
    log("bounds ext", bounds_ext["positive_cm"], bounds_ext["negative_cm"], worst)
    # ------------------------------------------------------------ sockets, physics
    sockets = socket_rows()
    bodies = physics_bodies()
    # ------------------------------------------------------------ the static twin: qa_check, then export
    lods = [bpy.data.objects[f"SM_AR01_LOD{k}"] for k in range(4)]
    q0 = qa_check(lods, budget_tris=57000, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:3], budget_tris=57000, texel_density=agg["SM_AR01_LOD0"], require_uv1=True)
    rep["qa_check_SM_AR01"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                               "texel_target_px_cm": agg["SM_AR01_LOD0"],
                               "failed": [c for c in q0["checks"] + q["checks"] if not c["passed"]],
                               "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa_check SM_AR01", rep["qa_check_SM_AR01"]["passed"])
    if not (rep["qa_check_SM_AR01"]["passed"] and qa["passed"] and rep["rigid_skin"]["passed"]
            and rep["skeleton_standard"]["passed"]):
        (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit("[AR01-rig] QA failed: nothing exported (see scratch/rig/rig_report.json)")
    sizes = json.loads((GATES / "game_lod_sizes.json").read_text())["SM_AR01"]
    EXPORTS.mkdir(parents=True, exist_ok=True)
    grp = bpy.data.objects["SM_AR01_LodGroup"]
    sres = export_fbx(str(EXPORTS / "SM_AR01.fbx"), [grp], kind="static", lod_screen_sizes=list(sizes))
    rep["export_static"] = {"fbx": sres["filepath"], "sidecar": sres["sidecar"], "warnings": sres["warnings"],
                            "lod_screen_sizes": sres["lod_screen_sizes"]}
    log("SM_AR01 exported", sres["warnings"])
    # ------------------------------------------------------------ the skeletal set
    # stage-7 fix round (tech review: every A_*.fbx carried the clip's FRAME-1 pose as its bones' node defaults, the
    # scene sat on frame 1): the scene is parked before every clip, so Blender's exporter takes the clip's START pose
    # (frame 0) instead -- the bind pose for every bone except a selector held at AUTO (measured: Lcl Rotation Y 16 on
    # 'selector', every other bone at rest). Unreal reads the baked curves (absolute) and is unaffected; Blender's
    # importer treats node defaults as rest, so Blender-side readers (gunlib/export_review_job, README) take the
    # clip armature's absolute bone matrices
    bpy.context.scene.frame_current = REST_FRAME
    written = SKP.export_skeletal_set(str(EXPORTS), arm, meshes, SK, actions=actions, frame_rate=FPS,
                                      fps_by_action={k: v[2] for k, v in clips.items()})
    bpy.context.scene.frame_current = 0
    # physics proxy (fan method): one 250 mm cube weighted to 'body'
    proxy = proxy_mesh(arm, mats[0], coll)
    pw = SKP.export_skeletal_set(str(EXPORTS / "Physics"), arm, [proxy], "SK_AR01_PhysicsProxy", frame_rate=FPS)
    pme = proxy.data
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.meshes.remove(pme)
    rep["export_skeletal"] = {"meshes": [{k: v for k, v in m.items() if k != "objects"} for m in written["meshes"]],
                              "animations": written["animations"], "physics_proxy": pw["meshes"][0]["fbx"]}
    # ------------------------------------------------------------ sidecar
    texel = SPEC.d["textures"]["texel_classes_px_per_cm"]
    payload = {
        "asset": SK, "skeleton": f"{SK}_Skeleton", "physics_asset": f"PHYS_{CODE}",
        "bones": [b.name for b in arm.data.bones], "root_bone": "root",
        "bones_rest": {b.name: {"head_mm": [round(v * 1000.0, 4) for v in b.head_local],
                                "head_cm": SKP.ue_component_transform(np.eye(3), [v * 1000.0 for v in b.head_local])["location_cm"],
                                "parent": b.parent.name if b.parent else "root",
                                "motion": SPEC.bones[b.name].get("motion")} for b in arm.data.bones},
        "lod_files": [Path(m["fbx"]).name for m in written["meshes"]],
        "lod_screen_sizes": list(sizes),
        "lod_note": "import LOD1-3 with SkeletalMeshEditorSubsystem.import_lod (same skeleton, same root; no bones "
                    "removed). First-person components force LOD0 (ForcedLodModel = 1)",
        "lod_triangles": {k: v["triangles"] for k, v in rep["lods"].items()},
        "animations": [{"file": Path(a["fbx"]).name, "frames": a["frames"], "fps": a["fps"], "loop": False,
                        "starts_and_ends_at_rest": rep["clips"][Path(a["fbx"]).stem]["starts_and_ends_at_rest"]}
                       for a in written["animations"]],
        "notifies": notifies,
        "notifies_note": "FBX carries no notifies: the Unreal harness adds them at these frames (U9). MagOut / MagIn on "
                         "the character's montage are the buyer's in reload pattern 2 (mag on hand_l); copy these "
                         "weapon-clip frames",
        "import": {"use_t0_as_ref_pose": False, "update_skeleton_reference_pose": False,
                   "import_morph_targets": False, "create_physics_asset": False, "normals": "import normals",
                   "convert_scene": True, "force_front_x_axis": False, "custom_sample_rate": "the file's rate",
                   "bone_compression": BONE_COMPRESSION,
                   "bone_compression_why": "rigid parts: the fan measured ACL cracking rigid parts by ~1.1 mm (gun "
                                           "study 4.10.9); U9 gates <= 0.1 mm",
                   "bounds_extension_cm": bounds_ext},
        "physics_proxies": {SK: "Physics/SK_AR01_PhysicsProxy.fbx",
                            "how": "import the proxy onto SK_AR01_Skeleton with Create Physics Asset ON (one 250 mm "
                                   "cube on 'body' -> exactly one body), rewrite the body from physics_bodies, rename "
                                   "it PHYS_AR01, assign it to SK_AR01, delete the proxy mesh (np_skeletal method)"},
        "physics_bodies": bodies, "mass_kg": MASS_KG,
        "center_of_mass_mm": [round(float(v), 3) for v in COM_B],
        "sockets": sockets,
        "magazine": {"asset": "SM_AR01_Mag", "socket": "Mag", "bone": "magazine",
                     "attach": "zero relative transform (SnapToTarget) on the Mag socket; reload path MagInsertStart "
                               "-> (lerp) MagRockStart -> (slerp about the front-lug hook) Mag",
                     "rock_deg": ROCK, "insert_mm": round(INSERT, 4)},
        "materials": {"M_AR01_Metal": {"slot": 0, "master": "M_Fabric_Master", "metal_from_orm": True,
                                       "textures": {k: f"T_AR01_Metal_{k}" for k in ("BC", "ORM", "N", "Masks")}},
                      "M_AR01_Furniture": {"slot": 1, "master": "M_Fabric_Master", "metal_from_orm": False,
                                           "textures": {k: f"T_AR01_Furniture_{k}" for k in ("BC", "ORM", "N", "Masks")},
                                           "detail16": "Recolour/T_AR01_Furniture_Detail16"}},
        "gun": {"class": "long_gun", "grip_axis_deg": 22.35, "rail_slots": {}, "muzzle_class": "rifle_14mm_lh",
                "mag_family": "AR01 curved 30", "texel_classes_px_per_cm": texel,
                "first_person": "FP_Weapon + TP_Weapon (SK_AR01) and FP_Mag + TP_Mag (SM_AR01_Mag on Mag); every FP "
                                "component FirstPersonPrimitiveType = FirstPerson and ForcedLodModel = 1",
                "hand_offset": {"weapon_r_to_Grip": "identity (provisional)",
                                "note": "H1 early set Grip on the fit body's palm centre (46 mm, gates/form.json); the "
                                        "posed H1 (hand_r frame on MH_PlayerDefault) is not run in this stage"}},
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
    rep["deny_tokens"] = {"checked": len(names), "hits": hits, "sidecar_text_hits":
                          sorted({h for w in __import__("re").findall(r"[A-Za-z0-9_\-]+", side_txt)
                                  for h in qa_gun.deny_hits(w)}), "pass": not hits}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("RIG_DONE %.1fs" % (time.time() - t0))


def proxy_mesh(arm, mat, coll):
    import bmesh
    me = bpy.data.meshes.new("SK_AR01_PhysicsProxy")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.25)
    c = COM_B * 0.001
    for v in bm.verts:
        v.co += __import__("mathutils").Vector(c)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    uv = me.uv_layers.new(name="UV0")
    for i, l in enumerate(uv.data):
        l.uv = ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9))[i % 3]
    me.materials.append(mat)
    ob = bpy.data.objects.new("SK_AR01_PhysicsProxy", me)
    coll.objects.link(ob)
    vg = ob.vertex_groups.new(name="body")
    vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    return ob


main()
