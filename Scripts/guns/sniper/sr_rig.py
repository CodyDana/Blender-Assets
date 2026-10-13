"""SR01 W3c: rig + export (headless Blender, on the W3b blend; the SMG's smg_rig.py, adapted):

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_rig.py

SR01_BUILD_PLAN 2.2 / 3 / 4, GUN_BUILDING_STUDY 4.6 / 5.2 / 5.3 / 7.2:
- armature object 'root' at the Grip origin (identity), the spec's 13 bones (body + bolt, trigger, selector,
  mag_release, magazine, muzzle_device, cheek_riser, bipod, bipod_leg_l/_r, bipod_leg_l_ext/_r_ext), rest rotation =
  root's for every bone. The legs' 12 deg splay lives in their MOTION (the deployed rotation is about the pin rolled 12
  deg about the leg axis: sr_clips.leg_basis), not in a rest rotation (the standard requires identity rests);
- cheek_riser under 'body': gunlib proposal P1, applied by a sniper-side standard table (sr_common.standard_bones_p1);
  gunlib's own table is untouched and is ALSO run and reported (it rejects only that parent);
- SK_SR01 / _LOD1..3: each LOD's part objects without the magazine (SM_SR01_Mag rides the 'magazine' bone's Mag
  socket: an attach bone with no weighted vertices), every part rigidly on its bone, slots M_SR01_Metal (0) +
  M_SR01_Chassis (1);
- clips (sr_clips: Fire 60 fps, BoltCycle, Reload, ReloadEmpty, Selector, BipodDeploy, BipodStow, CheekRiser 30 fps),
  keys every frame, LINEAR; Fire / BoltCycle / ReloadEmpty hold the safety at FIRE; notifies in the sidecar;
- B11 bounds extension from every vertex of LOD0-3 at every frame of every clip AND at the extreme poses (bipod folded /
  deployed x ext 0 / 76 x cant -15 / 0 / +15, riser low / high, bolt open / back) against LOD0's bind AABB; the SK's
  LOD screen sizes = the LOD-pop switch distances at the SK's engine radius (bind box + extension);
- 20 sockets on their bones (CenterOfMass / Holster = the W3b CoM empty), one physics body on 'body' (folded-pose
  boxes + a barrel capsule, 5.9 kg) + the bounds envelope box (no collision, no mass: the SMG W5 U7 lesson, so the
  physics-route bounds hold every pose: bipod deployed / extended / canted, bolt open / back, riser range);
- qa_skeletal(max_influences=1) + gunlib.rig rigid-skin + skeleton-standard checks, then export_skeletal_set + sidecar;
  SM_SR01 through qa_check and export_fbx(kind="static") with the LOD-pop sizes; sha256 of every file.
Writes scratch/w3/rig/rig_report.json, updates gates/game_lod_sizes.json (SK sizes) and saves Assets/Guns/SR01.blend.
"""
from __future__ import annotations

import hashlib
import json
import os
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, WORK, BLEND, GRIP, GATES, CODE, PARTS_COLL, D, gun_socket_rows, standard_bones_p1  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from pipeline import skeletal_prop as SKP  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from gunlib import rig as RG  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402
import sr_clips as CL  # noqa: E402
from sr_clips import basis_from  # noqa: E402

SK = f"SK_{CODE}"
SM = f"SM_{CODE}"
EXPORTS = ROOT / "Exports" / "Guns" / CODE
SCR = WORK / "scratch" / "w3"
OUT = SCR / "rig"
OUT.mkdir(parents=True, exist_ok=True)
SLOTS = ("M_SR01_Metal", "M_SR01_Chassis")
FPS = 30
MASS_KG = float(D["scale"]["real"]["mass_kg_without_scope_and_mag"])
BUDGET = 55000                       # 50,000 gun ceiling + 5,000 merged magazine (as W2's twin check)
BONE_COMPRESSION = "/Engine/Animation/DefaultRecorderBoneCompression"
REST_FRAME = -100
GAME_REP = json.loads((SCR / "game" / "game_report.json").read_text())
SOCK = {r["socket"]: r for r in gun_socket_rows()}
FIT_SET = {}


def log(*a):
    print("[SR01-rig]", *a, flush=True)


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


def bone_of(ob):
    return part_rec(ob).get("bone", "body")


def lod_objects(lv):
    cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


def base_of(name):
    for lv in (1, 2, 3):
        if name.endswith(f"_LOD{lv}"):
            return name[: -len(f"_LOD{lv}")]
    return name


def bone_rows():
    return [(b["bone"], tuple(float(v) for v in np.array(b["head_M"]) - GRIP), b["parent"]) for b in D["bones"]["table"]]


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


def physics_bodies(envelope=None):
    """One body on 'body' (the held / dropped rifle, bipod FOLDED: plan 3 'deployed legs are kinematic when held, the
    legs fold first when dropped'): boxes per part group (frame B, the raked grip on its axis), a capsule for the barrel
    + device ahead of the chassis; + the bounds envelope (no collision, no mass)."""
    objs = {o.name: o for o in lod_objects(0)}
    M = {n: GM.mesh_vt(o)[0] + GRIP for n, o in objs.items()}
    ch = M["chassis"]
    I = np.eye(3)
    a = math.radians(float(D["frames"]["grip"]["axis_deg_from_vertical"]))
    Rg = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    st = lambda names: np.vstack([M[n] for n in names if n in M])          # noqa: E731
    groups = [
        ("butt + pad + knobs + cheek riser (rest)", st(("butt", "butt_pad", "pad_plate", "butt_knobs", "cheek_riser",
                                                         "riser_posts", "riser_lever")), I),
        ("grip (raked)", st(("grip",)), Rg),
        ("action: chassis centre, receiver, rail, bolt + handle, safety",
         np.vstack([st(("receiver", "rail", "rail_screws", "bolt", "bolt_handle", "safety")),
                    ch[(ch[:, 0] < 414.0) & (ch[:, 2] >= -52.0)]]), I),
        ("trigger guard + trigger + paddle", np.vstack([st(("trigger", "mag_release")),
                                                        ch[(ch[:, 0] < 414.0) & (ch[:, 2] < -52.0) & (ch[:, 0] > 320.0)]]), I),
        ("magazine well", ch[(ch[:, 0] >= 414.0) & (ch[:, 0] < 504.0)], I),
        ("forend + bipod clamp", np.vstack([ch[ch[:, 0] >= 504.0], st(("bipod_clamp",))]), I),
        ("bipod (folded): swivel, knob, legs, extensions, feet", st(("bipod_swivel", "bipod_knob", "bipod_pins",
                                                                     "bipod_leg_l", "bipod_leg_r", "bipod_ext_l",
                                                                     "bipod_ext_r", "bipod_foot_l", "bipod_foot_r")), I),
    ]
    elements = []
    for desc, P, R in groups:
        c, size = obb(P - GRIP, R)
        elements.append({"shape": "box", "covers": desc, "centre_mm": [round(float(v), 3) for v in c],
                         "matrix": np.round(R, 7).tolist(), "size_mm": [round(float(v), 3) for v in size],
                         "collision": True, "contribute_to_mass": True})
    P = np.vstack([M["barrel"], M["muzzle_device"]])
    P = P[P[:, 0] >= 840.0] - GRIP
    x0, x1 = float(P[:, 0].min()), float(P[:, 0].max())
    zc = float(np.mean([P[:, 2].min(), P[:, 2].max()]))
    r = float(np.max(np.hypot(P[:, 1], P[:, 2] - zc)))
    Rc = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
    elements.append({"shape": "capsule", "covers": "barrel + muzzle device ahead of the forend",
                     "centre_mm": [round(0.5 * (x0 + x1), 3), 0.0, round(zc, 3)], "matrix": Rc.tolist(),
                     "radius_mm": round(r, 3), "length_mm": round(max(0.1, (x1 - x0) - 2 * r), 3), "axis": "Z -> +X",
                     "collision": True, "contribute_to_mass": True})
    if envelope is not None:
        elo, ehi = (np.asarray(v, float) for v in envelope)
        elements.append({"shape": "box", "covers": "bounds envelope: the mesh's extended bounds (bind AABB + bounds "
                         "extension: every clip frame + bipod deployed / extended / canted, bolt open / back, riser "
                         "range); no collision, no mass (the component's physics-route bounds, SMG W5 U7)",
                         "centre_mm": [round(float(v), 3) for v in 0.5 * (elo + ehi)], "matrix": np.eye(3).tolist(),
                         "size_mm": [round(float(v), 3) for v in ehi - elo], "collision": False, "contribute_to_mass": False})
    for e in elements:
        e["unreal_component"] = SKP.ue_component_transform(np.array(e["matrix"]), e["centre_mm"])
        if "size_mm" in e:
            e["size_cm"] = [round(v * 0.1, 4) for v in e["size_mm"]]
    return [{"bone": "body", "unreal_bone_any_of": ["body"], "physics_type": "Default", "consider_for_bounds": True,
             "mass_kg": MASS_KG, "elements": elements,
             "role": "ONE rigid body on 'body' (every other bone is its child): Kinematic while held, simulated when "
                     "dropped with the bipod folded (BipodStow or snap the legs to 0 first); the last box is the bounds "
                     "envelope (no collision, no mass) so the component's bounds hold every pose; the seated magazine "
                     "and the scope are their own components with collision off while attached"}]


def socket_rows(com_B):
    from mathutils import Euler
    rows = []
    for r in gun_socket_rows():
        n = r["socket"]
        loc = np.array(r["blender_mm"], float)
        if n in FIT_SET:
            loc = FIT_SET[n].copy()
        ro = r["unreal_rotation_deg"]
        Rb = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
        rows.append({"name": n, "bone": r["bone"], "location_mm": [round(float(v), 4) for v in loc],
                     "matrix": np.round(Rb, 9).tolist(), "unreal_rotation_deg": ro,
                     "computed": n in ("CenterOfMass", "Holster"), "fit_set": n in FIT_SET, "use": r.get("note", ""),
                     "state": r.get("state", ""), "unreal_component": SKP.ue_component_transform(Rb, loc)})
    return rows


def posed_envelope(arm, mesh, poses):
    """poses: {name: [value dicts]} -> rest AABB, posed AABB, worst excursion per name (mm, frame B)."""
    me = mesh.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3) * 1000.0
    gi = {g.index: g.name for g in mesh.vertex_groups}
    vb = np.array([gi[v.groups[0].group] for v in me.vertices])
    lo, hi = V.min(0), V.max(0)
    rest_lo, rest_hi = lo.copy(), hi.copy()
    worst = {}
    for pname, vals_list in poses.items():
        for vals in vals_list:
            Ms = RG.bone_matrices_mm(arm, basis_from(vals))
            for bn in np.unique(vb):
                M = Ms[bn]
                if np.allclose(M, np.eye(4)):
                    continue
                P = V[vb == bn] @ M[:3, :3].T + M[:3, 3]
                lo, hi = np.minimum(lo, P.min(0)), np.maximum(hi, P.max(0))
                worst[pname] = max(worst.get(pname, 0.0),
                                   float(np.maximum(P.max(0) - rest_hi, rest_lo - P.min(0)).max()))
    return rest_lo, rest_hi, lo, hi, worst


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


def measured_texel_classes():
    import re
    out = {}
    up = GATES / "uv_bake_paint.json"
    if not up.exists():
        return out
    for g in json.loads(up.read_text()).get("gates", []):
        m = re.match(r"B9 density (\w+) class (\w)", g.get("name", ""))
        if m:
            vals = [float(x) for x in re.findall(r"[\d.]+", str(g.get("value")))[:3]]
            if len(vals) == 3:
                out.setdefault(m.group(1), {})[m.group(2)] = {"p5": vals[0], "median": vals[1], "p95": vals[2]}
    return out


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    clean_previous()
    rep = {"stage": "W3c rig + export", "spec_version": D["meta"].get("version")}
    # ------------------------------------------------------------ fit-set sockets
    mag_B = np.array(SOCK["Mag"]["blender_mm"], float)
    tI = mag_B - np.array([0.0, 0.0, CL.INSERT])
    FIT_SET["MagInsertStart"] = tI
    bpy.data.objects[f"SOCKET_{SM}_LOD0_MagInsertStart"].location = tuple(tI * 0.001)
    rep["fit_set_sockets"] = {"MagInsertStart": {"blender_mm": [round(float(v), 5) for v in tI],
                                                 "spec_blender_mm": SOCK["MagInsertStart"]["blender_mm"],
                                                 "delta_mm": round(float(np.abs(tI - np.array(
                                                     SOCK["MagInsertStart"]["blender_mm"])).max()), 5),
                                                 "rule": "Mag - 67.8 x Z (straight path, the magazine vertical)"}}
    com = np.array(bpy.data.objects[f"SOCKET_{SM}_LOD0_CenterOfMass"].location, float) * 1000.0
    d_rep = float(np.abs(com - np.array(GAME_REP["mass"]["com_B_mm"])).max())
    if d_rep > 0.0051:
        raise SystemExit(f"W3b CoM empty {com} disagrees with game_report by {d_rep:.4f} mm")
    for n in ("CenterOfMass", "Holster"):
        FIT_SET[n] = com.copy()
        rep["fit_set_sockets"][n] = {"blender_mm": [round(float(v), 5) for v in com], "delta_mm": round(d_rep, 5),
                                     "rule": "the W3b CoM empty on SM_SR01_LOD0 (game_report rounds to 0.01 mm)"}
    rep["motion"] = {"bolt_rotate_deg": CL.ROT, "bolt_travel_mm": CL.TRAVEL, "insert_mm": CL.INSERT,
                     "drop_mm": CL.DROP_MM, "splay_deg": CL.SPLAY, "deploy_deg": CL.DEPLOY, "ext_max_mm": CL.EXT_MAX}
    coll = bpy.data.collections.new(SK)
    bpy.context.scene.collection.children.link(coll)
    # ------------------------------------------------------------ skeleton
    rows = bone_rows()
    arm = RG.make_armature("root", rows, coll)
    rep["bones"] = {n: {"head_mm": [round(v, 4) for v in h], "parent": p} for n, h, p in rows}
    mats = [bpy.data.materials[s] for s in SLOTS]

    def slot_of(o):
        return SLOTS.index(part_rec(o)["slot"])
    meshes = []
    rep["lods"] = {}
    for lv in range(4):
        parts = [(o, bone_of(o)) for o in lod_objects(lv) if bone_of(o) != "magazine"
                 and part_rec(o).get("slot") != "M_SR01_Mag"]
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
    std = RG.skeleton_standard_checks(arm, table=standard_bones_p1(), expect=expect)
    std_gunlib = RG.skeleton_standard_checks(arm, expect=expect)
    rigid = []
    for ob in meshes:
        rigid += RG.rigid_skin_checks(ob, arm)
    rep["qa_skeletal"] = {"passed": qa["passed"], "n": len(qa["checks"]),
                          "failed": [c for c in qa["checks"] if not c["passed"]]}
    rep["skeleton_standard"] = {"passed": all(c["passed"] for c in std), "checks": std,
                                "table": "gunlib.rig.STANDARD_BONES + proposal P1 (cheek_riser under body), sniper-side"}
    rep["skeleton_standard_gunlib_unmodified"] = {
        "passed": all(c["passed"] for c in std_gunlib),
        "failed": [c for c in std_gunlib if not c["passed"]],
        "note": "gunlib's own table (no P1): reported, expected to fail only parents_from_standard on cheek_riser<-body"}
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
    log("standard (P1)", rep["skeleton_standard"]["passed"], "gunlib table", rep["skeleton_standard_gunlib_unmodified"],
        "rigid", rep["rigid_skin"]["passed"], "UD", rep["sk_ud"])
    # ------------------------------------------------------------ clips
    clips = CL.all_clips()
    mag_parts = [o for o in lod_objects(0) if bone_of(o) == "magazine"]
    Vm = np.vstack([GM.mesh_vt(o)[0] for o in mag_parts])
    chV = GM.mesh_vt(bpy.data.objects["chassis"])[0]
    xw = (chV[:, 0] + GRIP[0] > 414.0) & (chV[:, 0] + GRIP[0] < 504.0)
    well_bottom = float(chV[xw, 2].min())                                  # the well's lowest point (frame B)
    for cname in (f"A_{CODE}_Reload", f"A_{CODE}_ReloadEmpty"):
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
    rep["safety_rule"] = {c: {"selector_values": rep["clips"][c]["selector_held_deg"],
                              "ok": rep["clips"][c]["selector_held_deg"] == [CL.SEL_HELD]} for c in CL.SAFETY_HELD}
    cover = {}
    seq_bad = []
    for cname, (frames, _n, _f) in clips.items():
        for f, v in frames:
            if v.get("bolt", 0.0) > 1e-9 and abs(v.get("rot", 0.0) - CL.ROT) > 1e-9:
                seq_bad.append({"clip": cname, "frame": f})
            for k, (a, b) in CL.RANGES.items():
                x = v.get(k, 0.0)
                cover.setdefault(k, [1e9, -1e9])
                cover[k] = [min(cover[k][0], x), max(cover[k][1], x)]
                if x < a - 1e-9 or x > b + 1e-9:
                    rep.setdefault("b3_out_of_range", []).append({"clip": cname, "frame": f, k: x})
    rep["b3_coverage"] = {k: [round(a, 4), round(b, 4)] for k, (a, b) in cover.items()}
    rep["bolt_sequence_rule"] = {"slide_only_at_full_rotation": not seq_bad, "violations": seq_bad[:10]}
    # ------------------------------------------------------------ bounds over every clip frame + extreme poses (B11)
    poses = {c: [v for _f, v in fr] for c, (fr, _n, _p) in clips.items()}
    poses.update({f"pose:{k}": [v] for k, v in CL.extreme_poses().items()})
    rlo, rhi, lo, hi, worst = posed_envelope(arm, meshes[0], poses)
    for m_ in meshes[1:]:
        _l, _h, lo2, hi2, w2 = posed_envelope(arm, m_, poses)
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
                  "posed_aabb_M_mm": [np.round(lo + GRIP, 3).tolist(), np.round(hi + GRIP, 3).tolist()],
                  "extended_aabb_mm": [np.round(elo, 3).tolist(), np.round(ehi, 3).tolist()],
                  "worst_excursion_mm_per_clip": {k: round(v, 3) for k, v in worst.items()},
                  "why": "LOD0-3 posed at every frame of every clip and at the extreme poses (bipod folded / deployed x "
                         "ext 0 / 76 x cant -15 / 0 / +15, riser -12.9 / +12, bolt open / back) vs LOD0's bind AABB "
                         "(Unreal's stored bounds), per axis (+1 mm where it grows; Unreal axes: y flipped): the mesh's "
                         "Positive / Negative Bounds Extension. The magazine and the scope are their own components"}
    rep["bounds_extension"] = bounds_ext
    log("bounds ext", bounds_ext["positive_cm"], bounds_ext["negative_cm"], "posed M", bounds_ext["posed_aabb_M_mm"])
    # ------------------------------------------------------------ screen sizes (twin from the LOD-pop gate; SK converted)
    gz = json.loads((GATES / "game_lod_sizes.json").read_text())
    sizes_twin = list(gz[SM])
    r_twin = float(gz["bounds_radius_m"])
    r_sk = float(0.5 * np.linalg.norm(ehi - elo)) / 1000.0
    sizes_sk = [1.0] + [round(s * r_sk / r_twin, 5) for s in sizes_twin[1:]]
    gz[SK] = sizes_sk
    gz["SK_engine_radius_m"] = round(r_sk, 4)
    gz["note"] = ("SM_SR01 sizes from the LOD-pop gate (both bipod poses) at the twin's engine sphere radius "
                  "(bounds_radius_m); SK_SR01 sizes = the same switch distances at the SK's engine radius (bind box + "
                  "bounds extension: every clip frame and the extreme bipod / bolt / riser poses)")
    (GATES / "game_lod_sizes.json").write_text(json.dumps(gz, indent=1))
    rep["lod_screen_sizes"] = {"SM": sizes_twin, "SK": sizes_sk, "r_twin_m": r_twin, "r_sk_engine_m": round(r_sk, 4),
                               "switch_distances_m": [round(1.778 * r_twin / s, 3) for s in sizes_twin[1:]]}
    # ------------------------------------------------------------ sockets, physics
    sockets = socket_rows(com)
    bodies = physics_bodies((elo, ehi))
    # ------------------------------------------------------------ the static twin: qa_check, then export
    lods = [bpy.data.objects[f"{SM}_LOD{k}"] for k in range(4)]
    q0 = qa_check(lods, budget_tris=BUDGET, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:3], budget_tris=BUDGET, texel_density=agg[f"{SM}_LOD0"], require_uv1=True)
    rep[f"qa_check_{SM}"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                             "texel_target_px_cm": agg[f"{SM}_LOD0"],
                             "failed": [c for c in q0["checks"] + q["checks"] if not c["passed"]],
                             "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa_check", SM, rep[f"qa_check_{SM}"]["passed"], json.dumps(rep[f"qa_check_{SM}"]["failed"])[:800])
    sk_ud_ok = all(v["ud1_drops"] == 0 and v["min_area_mm2"] >= 0.01 and v["ud3_collapsed_unreal"] == 0
                   for v in rep["sk_ud"].values())
    rep["sk_ud_ok"] = sk_ud_ok
    if not (rep[f"qa_check_{SM}"]["passed"] and qa["passed"] and rep["rigid_skin"]["passed"]
            and rep["skeleton_standard"]["passed"]):
        (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit("[SR01-rig] QA failed: nothing exported (see scratch/w3/rig/rig_report.json)")
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
    h1p = SCR / "h1_full.json"
    h1 = json.loads(h1p.read_text()) if h1p.exists() else None
    gun = {"grip_axis_deg": float(D["frames"]["grip"]["axis_deg_from_vertical"]),
           "frames": {"M": D["frames"]["M"], "B": "B = M - Grip (mm); Unreal cm = (Bx, -By, Bz) / 10"},
           "action": "bolt action: 3-lug bolt, rotate -60 deg about the bore then slide 88 mm (A_SR01_BoltCycle; the "
                     "game chains Fire -> BoltCycle or skips it)",
           "bipod": {"legs": "independent, 0 (folded forward) .. +90 (deployed), detents 0 / 90; each leg swings about "
                             "its pin rolled 12 deg about the leg axis (outboard down): deployed legs lean 12 deg out",
                     "extension_mm": [0.0, 76.0], "detents_mm": [0.0, 19.0, 38.0, 57.0, 76.0], "cant_deg": [-15.0, 15.0],
                     "ground_Z_below_bore_mm_by_detent": D["bipod"]["ground_Z_deployed"],
                     "prone": "set both legs to 90 and the extension so BipodFoot_L / _R reach the ground (a scalar per "
                              "leg); cant = bipod bone about X; drop the gun with the legs folded",
                     "physics": "PHYS_SR01 uses the folded pose; deployed legs are kinematic while held"},
           "cheek_riser_mm": [-12.9, 12.0],
           "scope": {"asset": "SM_Att_Scope_LongRange", "socket": "Rail_Top", "mount_offset_slots": 2,
                     "slot_pitch_mm": 10.01, "note": "attach the scope's Mount to Rail_Top + 2 slots (X +20.02 mm); the "
                     "gun has no Sight socket (no iron sights): the scope's Sight / EyePoint are the aim sockets"}}
    gun["texel_classes_px_per_cm"] = D["textures"]["texel_classes_px_per_cm"]
    gun["texel_classes_measured_px_per_cm"] = measured_texel_classes()
    gun["hand_offset"] = (h1 or {}).get("hand_offset", {"weapon_r_to_Grip": "identity (provisional)",
                                                        "note": "H1 full not run (see W3_REPORT)"})
    gun["first_person"] = ("FP_Weapon + TP_Weapon (SK_SR01), FP_Mag + TP_Mag (SM_SR01_Mag on Mag), FP_Scope + TP_Scope "
                           "(SM_Att_Scope_LongRange on Rail_Top + 2 slots); every FP component FirstPersonPrimitiveType "
                           "= FirstPerson and ForcedLodModel = 1")
    mats_block = {"M_SR01_Metal": {"slot": 0, "master": "M_Steel_Master", "metal_from_orm": True,
                                   "textures": {k: f"T_SR01_Metal_{k}" for k in ("BC", "ORM", "N", "Masks")}},
                  "M_SR01_Chassis": {"slot": 1, "master": "M_Fabric_Master", "metal_from_orm": True,
                                     "user_control": "Colour on the OD paint only (Masks A = 1 there; rubber, polymer and "
                                                     "anodize at A 0)",
                                     "textures": {k: f"T_SR01_Chassis_{k}" for k in ("BC", "ORM", "N", "Masks")},
                                     "detail16": "Recolour/T_SR01_Chassis_Detail16"},
                  "_source": "SR01_BUILD_PLAN 0 / 7 (slot table)"}
    clips_side = []
    for a in written["animations"]:
        nm = Path(a["fbx"]).stem
        clips_side.append({"file": Path(a["fbx"]).name, "frames": a["frames"], "fps": a["fps"], "loop": False,
                           "starts_at_rest": rep["clips"][nm]["starts_at_rest"],
                           "ends_at_rest": rep["clips"][nm]["ends_at_rest"],
                           "selector_held_deg": rep["clips"][nm]["selector_held_deg"],
                           "optional": nm.endswith("CheekRiser")})
    motion_of = {b["bone"]: b.get("motion") for b in D["bones"]["table"]}
    payload = {
        "asset": SK, "skeleton": f"{SK}_Skeleton", "physics_asset": f"PHYS_{CODE}",
        "compatible_skeletons": ["SK_AR01_Skeleton"],
        "bones": [b.name for b in arm.data.bones], "root_bone": "root",
        "bones_rest": {b.name: {"head_mm": [round(v * 1000.0, 4) for v in b.head_local],
                                "head_cm": SKP.ue_component_transform(np.eye(3), [v * 1000.0 for v in b.head_local])["location_cm"],
                                "parent": b.parent.name if b.parent else "root",
                                "motion": motion_of.get(b.name)} for b in arm.data.bones},
        "bone_notes": {"cheek_riser": "parent body (gunlib proposal P1: the standard lists stock only; SR01 has no stock "
                                      "bone and never a dummy)",
                       "bipod_leg_l": "rotate +0..90 about the pin axis (0, cos 12, +sin 12) through the head (Y rolled "
                                      "+12 deg about X): the deployed leg leans 12 deg out to the left",
                       "bipod_leg_r": "rotate +0..90 about the pin axis (0, cos 12, -sin 12) (Y rolled -12 deg about X): "
                                      "the deployed leg leans 12 deg out to the right",
                       "bipod_leg_l_ext": "translate +X in the leg's rest frame 0..76 (detents every 19)",
                       "bipod_leg_r_ext": "translate +X in the leg's rest frame 0..76 (detents every 19)",
                       "bolt": "rotate about X 0..-60, then translate -X 0..88 (slide only at -60)"},
        "abp_angle_table": {"bolt_rotate_deg": [0.0, CL.ROT], "bolt_mm": [0.0, CL.TRAVEL], "trigger_deg": [0.0, CL.TRIG],
                            "selector_deg": {"FIRE": 0.0, "SAFE": CL.SEL["SAFE"]}, "release_deg": [CL.REL, 0.0],
                            "bipod_legs_deg": [0.0, CL.DEPLOY], "ext_mm": [0.0, CL.EXT_MAX], "cant_deg": [-CL.CANT, CL.CANT],
                            "riser_mm": list(CL.RISER)},
        "lod_files": [Path(m["fbx"]).name for m in written["meshes"]],
        "lod_screen_sizes": sizes_sk,
        "lod_note": "import LOD1-3 with SkeletalMeshEditorSubsystem.import_lod (same skeleton, same root; no bones "
                    "removed). The sizes are the LOD-pop gate's switch distances (both bipod poses) at the SK's engine "
                    "radius (bind box + bounds extension). First-person components force LOD0 (ForcedLodModel = 1)",
        "lod_triangles": {k: v["triangles"] for k, v in rep["lods"].items()},
        "animations": clips_side,
        "notifies": notifies,
        "notifies_note": "FBX carries no notifies: the Unreal harness adds them at these frames (U9). ReloadEmpty starts "
                         "with the bolt open and BipodStow starts deployed at ext 38 (starts_at_rest false); BipodDeploy "
                         "ends deployed (ends_at_rest false). Fire, BoltCycle and ReloadEmpty hold the safety at FIRE",
        "import": {"use_t0_as_ref_pose": False, "update_skeleton_reference_pose": False,
                   "import_morph_targets": False, "create_physics_asset": False, "normals": "import normals",
                   "convert_scene": True, "force_front_x_axis": False, "custom_sample_rate": "the file's rate",
                   "bone_compression": BONE_COMPRESSION,
                   "bone_compression_why": "rigid parts: ACL cracked rigid parts by ~1.1 mm on the fan (gun study "
                                           "4.10.9); U9 gates <= 0.1 mm",
                   "bounds_extension_cm": bounds_ext},
        "physics_proxies": {SK: f"Physics/{SK}_PhysicsProxy.fbx",
                            "how": "import the proxy onto SK_SR01_Skeleton with Create Physics Asset ON (one 250 mm "
                                   "cube on 'body'), rewrite the body from physics_bodies, rename it PHYS_SR01, assign "
                                   "it to SK_SR01, delete the proxy mesh"},
        "physics_bodies": bodies, "mass_kg": MASS_KG,
        "center_of_mass_mm": [round(float(v), 3) for v in com],
        "sockets": sockets,
        "magazine": {"asset": "SM_SR01_Mag", "socket": "Mag", "bone": "magazine",
                     "attach": "zero relative transform (SnapToTarget) on the Mag socket; straight reload path "
                               "MagInsertStart -> (lerp along -Z, rotation constant) -> Mag", "insert_mm": CL.INSERT},
        "materials": mats_block,
        "gun": gun,
    }
    sc = SKP.write_skeletal_sidecar(str(EXPORTS / f"{SK}.fbx"), payload)
    # ------------------------------------------------------------ hashes, names
    files = [m["fbx"] for m in written["meshes"]] + [a["fbx"] for a in written["animations"]] + \
        [pw["meshes"][0]["fbx"], sc, sres["filepath"], sres["sidecar"]]
    rep["files"] = {str(Path(f).resolve().relative_to(ROOT.resolve())).replace("\\", "/"):
                    {"sha256": sha256(f), "bytes": Path(f).stat().st_size} for f in files}
    names = [b.name for b in arm.data.bones] + [s["name"] for s in sockets] + [m.name for m in meshes] + \
        [a.name for a in actions] + list(SLOTS) + [n["name"] for n in notifies] + [Path(f).name for f in files]
    hits = {n: qa_gun.deny_hits(n) for n in names if qa_gun.deny_hits(n)}
    side_txt = Path(sc).read_text()
    import re
    rep["deny_tokens"] = {"checked": len(names), "hits": hits, "sidecar_text_hits":
                          sorted({h for w in re.findall(r"[A-Za-z0-9_\-]+", side_txt) for h in qa_gun.deny_hits(w)}),
                          "pass": not hits}
    # B4 / S2 substitute for the verify step (no iron sights: the scope's A4 on its form bytes, plan 5)
    a4 = [g for g in json.loads((GATES / "scope_form.json").read_text())["gates"] if g["name"].startswith("A4")]
    (OUT / "s2_substitute.json").write_text(json.dumps({"gates": [{
        "name": "S2 sight picture at LOD0 (substitute: the scope attachment's A4, plan 5; no iron sights)",
        "value": {g["name"]: g["value"] for g in a4}, "pass": all(g["pass"] for g in a4)}]}, indent=1))
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "rig_report.json").write_text(json.dumps(rep, indent=1, default=str))
    bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("SR01_BLEND_OUT", str(BLEND)))   # (dry runs save elsewhere)
    log("RIG_DONE %.1fs" % (time.time() - t0))


main()
