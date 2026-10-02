"""HALL + ARMORY round (2026-10-01), stage 2 (Blender): compose the level layout and the check blend with the rear
extension, the opened doors, the moved compound back wall / alley closure / 1v1 ring and the armory interior.

Inputs (read-only): WorkFiles/shared/armory_hall/{hall_shell_layout.json, interface.json, interior_layout.json},
  WorkFiles/dojo/build/hall_armory/blender/{layout_hall_rear.json, export_report.json, blockers/...} (build_hall_rear.py),
  Assets/Dojo/DojoHallRear.blend, Assets/Dojo/DojoShowcase.blend (opened, never saved over), Exports/ArmoryKit/*.fbx
  (the armory chat's exports: imported only), the start backup of layout_showcase.json.
Outputs:
  WorkFiles/dojo/build/showcase/layout_showcase.json     IN PLACE (backed up first to hall_armory/blender/start_backup):
      hall instances removed / replaced ('removed': 'hall_armory_rev1', indices kept) and the new shell instances
      appended (each with its hall_shell_layout.json 'shell_id'); the north wall +11 m (moved in place), 24 side-wall
      pieces and 11 alley gravel copies appended; SM_DKX_1v1_HallRear removed, _W / _E / RearRoof appended,
      NorthWallTop moved; markers Wall_N / Wall_W_N / Wall_E_N, climb route O north, CU_R6_AlleyAbove; walk routes:
      CONTROL_into_the_hall renamed (it now passes through the centre door) + the interface's interior routes and
      CONTROLs; 'hall_armory_round' summary
  WorkFiles/dojo/build/hall_armory/blender/layout_checks.json   = the layout + the armory pieces' classes (+ 'glass')
  WorkFiles/dojo/build/hall_armory/blender/world_layout_hall_armory.json + world_layout_delta.json
      the landscape fix round's world layout with the terrace edge moved (B5/B6/B7 lines, WR5 +4+4+2+2 m and its end,
      CherrySlot CS19/CS20 +11 m, the cypress row +12 m); FZ1 forest edge and the LS_Valley spot heights are listed as
      pending (heightmap / ISM edits in the DojoLab stage)
  Assets/Dojo/DojoShowcase_HallArmory.blend   Kit + Assembly for walk / climb / roof-walk checks and renders; the
      removed hall instances sit in collection HallArmory_Removed (the 'before' state for renders)
  WorkFiles/dojo/build/hall_armory/blender/compose_report.json
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/hall/compose_hall_armory.py
"""
import copy
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "hall"))
import hall_armory_common as HC  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build"
OUTD = BUILD / "hall_armory" / "blender"
SHARED = ROOT / "WorkFiles" / "shared" / "armory_hall"
LAYOUT = BUILD / "showcase" / "layout_showcase.json"
BACKUP = OUTD / "start_backup" / "layout_showcase.json"
WORLD_FIX = BUILD / "landscape" / "fix" / "json" / "world_layout.json"
OUT_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase_HallArmory.blend"
REAR_BLEND = ROOT / "Assets" / "Dojo" / "DojoHallRear.blend"
TAG = "hall_armory_rev1"
REP = {"warnings": []}


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def wj(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=1, default=str), encoding="utf-8")


def close(a, b, tol=0.011):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# ------------------------------------------------------------------------------------------------ layout
def piece_entries(LHR, exports):
    out = {}
    for name, info in LHR["pieces"].items():
        if name.startswith("SM_DKH_"):
            kit, ue_dir, fdir = "hall", "/Game/DojoKit/Hall/Meshes", ROOT / "Exports" / "DojoKit" / "Hall"
        elif name.startswith("SM_DKX_"):
            kit, ue_dir, fdir = "outside", "/Game/DojoKit/Outside/Meshes", ROOT / "Exports" / "DojoKit" / "Outside"
        else:
            continue          # the ring keeps its entry (updated below)
        ex = exports.get(name, {})
        lods = ex.get("lods") or 1
        side = fdir / f"{name}.sockets.json"
        out[name] = {"kit": kit, "class": info["class"], "folder": info["folder"], "nanite": bool(info["nanite"]),
                     "note": info["note"][:150], "fbx": str(fdir / f"{name}.fbx"),
                     "sidecar": str(side) if (lods > 1 and side.exists()) else None, "ue_dir": ue_dir,
                     "slots": info["slots"], "tris": info["tris"], "lod_tris": ex.get("lod_tris") or [info["tris"]],
                     "lods": lods, "n_ucx": info["ucx"], "vcol": ["Wear"] if info.get("wear_baked") else [],
                     "hall_armory": TAG}
    return out


def new_inst(piece, loc, rot, folder, cls, kit, source, note="", **extra):
    d = {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_xyz_deg": [0.0, 0.0, float(rot)], "rot_z": float(rot),
         "scale": [1.0, 1.0, 1.0], "folder": folder, "collision_class": cls, "kit": kit, "source": source, "note": note,
         "hall_armory": TAG}
    d.update(extra)
    return d


def update_layout():
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LAYOUT, BACKUP)
    L = rj(BACKUP)                    # always rebuilt from the start state (re-runs are idempotent)
    S = rj(SHARED / "hall_shell_layout.json")
    I = rj(SHARED / "interface.json")
    LHR = rj(OUTD / "layout_hall_rear.json")
    exports = {}
    for p in (OUTD / "export_report.json", OUTD / "blockers" / "export_report.json",
              OUTD / "blockers" / "ring" / "export_report.json"):
        if p.exists():
            exports.update(rj(p))
    inst = L["instances"]
    n0 = len(inst)
    log = {"removed": [], "moved": [], "added": [], "checks": []}
    # pieces
    L["pieces"].update(piece_entries(LHR, exports))
    ring = LHR["pieces"]["SM_DGB_Boundary_1v1"]
    L["pieces"]["SM_DGB_Boundary_1v1"].update({"tris": ring["tris"], "lod_tris": [ring["tris"]], "n_ucx": ring["ucx"],
                                               "note": ring["note"][:150], "hall_armory": TAG})
    # hall shell: removed / replaced
    for it in S["instances_existing"]:
        if it["status"] == "kept":
            continue
        k = it["showcase_index"]
        cur = inst[k]
        ok = cur["piece"] == it["piece"] and close(cur["loc"], it["loc_world_m"]) and \
            abs(((cur["rot_z"] - it["rot_z_deg"]) + 180) % 360 - 180) < 0.01
        log["checks"].append({"index": k, "piece": it["piece"], "match": ok})
        if not ok:
            raise RuntimeError(f"hall instance {k} does not match the shell layout: {cur} vs {it}")
        cur["removed"] = TAG
        cur["hall_armory_status"] = it["status"]
        if it.get("replaced_by"):
            cur["replaced_by"] = it["replaced_by"]
        log["removed"].append(k)
    for it in S["instances_new"]:
        info = LHR["pieces"].get(it["piece"]) or L["pieces"][it["piece"]]
        inst.append(new_inst(it["piece"], it["loc_world_m"], it["rot_z_deg"], info["folder"], it["collision_class"],
                             "hall", f"hall_shell_layout.json {it['id']}", it.get("note", ""), shell_id=it["id"]))
        log["added"].append(len(inst) - 1)
    # the compound's back wall +11 m (moved in place) and the side walls continued
    nw = I["site"]["north_wall"]
    for m in nw["moved_instances"]:
        k = m["showcase_index"]
        cur = inst[k]
        if cur["piece"] != m["piece"] or not close(cur["loc"], m["from"], 0.002):
            raise RuntimeError(f"north wall instance {k} mismatch: {cur['piece']} {cur['loc']} vs {m}")
        cur["loc"] = [round(v, 4) for v in m["to"]]
        cur["hall_armory"] = TAG + " moved +11 m (north wall)"
        log["moved"].append(k)
    proto = {}
    for i in inst:
        proto.setdefault(i["piece"], i)
    for a in nw["side_wall_additions"]:
        pr = proto[a["piece"]]
        inst.append(new_inst(a["piece"], a["loc"], a["rot_z_deg"], pr["folder"], pr["collision_class"], pr["kit"],
                             "interface.json site.north_wall.side_wall_additions", a.get("covers", "")))
        log["added"].append(len(inst) - 1)
    # the rear alley's gravel copied +11 m (the old strip stays where it is)
    for gcp in I["site"]["rear_alley"]["gravel_copies"]:
        src = inst[gcp["showcase_index"]]
        if src["piece"] != gcp["piece"] or not close(src["loc"], gcp["from"], 0.002):
            raise RuntimeError(f"gravel {gcp} mismatch {src}")
        d = copy.deepcopy(src)
        d.pop("removed", None)
        d["loc"] = [round(v, 4) for v in gcp["copy_to"]]
        d["source"] = f"copy of #{gcp['showcase_index']} (+11 m, the new rear alley)"
        d["hall_armory"] = TAG
        inst.append(d)
        log["added"].append(len(inst) - 1)
    # 1v1 closure
    hr = next(k for k, i in enumerate(inst) if i["piece"] == "SM_DKX_1v1_HallRear")
    inst[hr]["removed"] = TAG
    inst[hr]["replaced_by"] = "SM_DKX_1v1_HallRear_W + _E"
    log["removed"].append(hr)
    for name in ("SM_DKX_1v1_HallRear_W", "SM_DKX_1v1_HallRear_E", "SM_DKX_1v1_RearRoof"):
        info = LHR["pieces"][name]
        inst.append(new_inst(name, info["pivot_world"], 0.0, "Boundary_1v1", "boundary", "outside",
                             "build_hall_rear.py", info["note"][:120]))
        log["added"].append(len(inst) - 1)
    nwt = next(k for k, i in enumerate(inst) if i["piece"] == "SM_DKX_1v1_NorthWallTop")
    inst[nwt]["loc"] = [22.0, 47.5, 0.0]
    inst[nwt]["hall_armory"] = TAG + " moved +11 m"
    log["moved"].append(nwt)
    # traversal markers, climb route O north, the alley camera
    tm = I["site"]["traversal_markers"]
    for m in L["traversal_markers"]:
        if m["name"] in tm and "new" in tm[m["name"]]:
            m["box"] = tm[m["name"]]["new"]
            m["hall_armory"] = TAG
    for c in L["climb_routes"]:
        if c["route"] == "O" and c["marker"] == "Wall_N":
            c["stance"] = tm["climb_route_O_north"]["new_stance"]
            c["hall_armory"] = TAG
    for c in L["cameras"]:
        if c["name"] == "CU_R6_AlleyAbove":
            c["loc"][1] += 11.0
            c["look_at"][1] += 11.0
            c["note"] += " (hall + armory round: +11 m with the alley)"
        if c["name"] == "CU_R6_PocketAboveW":
            c["note"] += " (hall + armory round: now over the new rear yard; re-aim or retire in the DojoLab stage)"
    # walk routes
    W = L["walk_routes"]
    W2 = {}
    for k, v in W.items():
        if k == "CONTROL_into_the_hall":
            W2["hall_front_centre_door_into_the_interior"] = dict(v, note="was CONTROL_into_the_hall: the centre doors "
                                                                          "are open (hall + armory round)")
        else:
            W2[k] = v
    G = I["gameplay"]
    for k, v in G["walk_routes_new_world"].items():
        W2[k] = dict(v, hall_armory=TAG)
    for k, v in G["controls_new_world"].items():
        # walk_check treats a route as a CONTROL only when its name starts with CONTROL (ARM_CONTROL_* -> CONTROL_ARM_*)
        k2 = "CONTROL_ARM_" + k[len("ARM_CONTROL_"):] if k.startswith("ARM_CONTROL_") else k
        W2[k2] = dict(v, hall_armory=TAG, **({"renamed_from": k} if k2 != k else {}))
    # the armory's two wing-deck routes start ON the landing (armory walk_check: start = end floor 0.60 hall-local,
    # no step), i.e. world +1.10, not on the hall floor
    for k in ("ARM_landing_onto_west_wing_deck", "ARM_landing_onto_east_wing_deck"):
        if k in W2:
            W2[k]["floor_z"] = 1.1
            W2[k]["note"] = "starts on the dais landing (+0.60 hall-local = world +1.10; armory walk_check end floor 0.6)"
    # a dead town route (landscape round) ran east along Y 43, north of the old back wall: its north leg follows the
    # wall +11 m (still flagged for the DojoLab stage's dead-route carry-over)
    k = "BR_road_up_the_kerb_into_the_west_lane_north"
    if k in W2:
        W2[k]["points"] = [[-10.5, -5.3], [-10.5, -1.6], [-10.5, 40.0], [-10.5, 54.0], [20.0, 54.0]]
        W2[k]["note"] = ("hall + armory round: the north leg moved Y 43 -> 54 with the compound's back wall; one of the "
                         "landscape round's dead town routes (carry-over: remove or mark in the DojoLab stage)")
    # the rear yards and the new alley (BR only: outside the 1v1); 'leaves': 'open' = walk_check's BR hull set (the
    # gate open, the 1v1 boundary class left out)
    br = {"BR_new_alley_behind_the_extension": {"floor_z": 0.0, "points": [[15.5, 46.15], [28.5, 46.15]]},
          "BR_rear_yard_west_round_the_extension_into_the_alley": {
              "floor_z": 0.0, "points": [[9.0, 38.0], [14.2, 38.0], [14.2, 46.15], [20.0, 46.15]]},
          "BR_rear_yard_east_round_the_extension_into_the_alley": {
              "floor_z": 0.0, "points": [[35.0, 38.0], [29.8, 38.0], [29.8, 46.15], [24.0, 46.15]]},
          "CONTROL_BR_alley_through_the_extension_rear_wall": {"floor_z": 0.0, "points": [[22.0, 46.3], [22.0, 43.5]]},
          "CONTROL_BR_rear_yard_through_the_extension_west_wall": {"floor_z": 0.0,
                                                                   "points": [[13.6, 40.0], [16.5, 40.0]]}}
    for k, v in br.items():
        W2[k] = dict(v, leaves="open", hall_armory=TAG)
    L["walk_routes"] = W2
    L["hall"]["rear_extension"] = LHR["numbers"]
    L["hall_armory_round"] = {
        "date": "2026-10-01", "revision": 1, "tag": TAG,
        "sources": ["WorkFiles/shared/armory_hall/hall_shell_layout.json", "WorkFiles/shared/armory_hall/interface.json",
                    "WorkFiles/dojo/build/hall_armory/blender/layout_hall_rear.json"],
        "instances_before": n0, "instances_after": len(inst), "removed": sorted(log["removed"]),
        "moved": sorted(log["moved"]), "added": [log["added"][0], log["added"][-1]] if log["added"] else [],
        "interior": "placed by Scripts/dojo/unreal/dj_armory_sync.py from WorkFiles/shared/armory_hall/"
                    "interior_layout.json + lights_design.json (NOT in this layout); the shell instances here carry "
                    "their hall_shell_layout.json shell_id so the sync can verify them",
        "shell_lights": "hall_shell_layout.json lights (BackerLight_*): placed by the sync script"}
    L["counts"]["instances"] = len(inst)
    L["counts"]["pieces"] = len(L["pieces"])
    wj(LAYOUT, L)
    REP["layout"] = {"instances_before": n0, "instances_after": len(inst), "removed": len(log["removed"]),
                     "moved": len(log["moved"]), "added": len(log["added"]), "pieces": len(L["pieces"]),
                     "walk_routes": len(W2), "match_checks_ok": all(c["match"] for c in log["checks"])}
    return L, log


def checks_layout(L, interior):
    LC = copy.deepcopy(L)
    G = rj(SHARED / "interface.json")["gameplay"]
    LC["collision_classes"].setdefault("glass", {k: v for k, v in G["collision_classes"]["glass"].items()
                                                 if k != "note"})
    for piece, info in interior["pieces"].items():
        LC["pieces"][piece] = {"kit": "armory", "class": info["collision_class"], "nanite": False,
                               "ucx": info.get("ucx"), "fbx": info["fbx"]}
    LC["stage"] = "hall + armory round stage 2: the showcase layout + the armory interior classes (checks only)"
    wj(OUTD / "layout_checks.json", LC)
    return LC


def world_layout():
    I = rj(SHARED / "interface.json")
    T = I["site"]["terrace_and_terrain"]
    W = rj(WORLD_FIX)
    by = {a["label"]: a for a in W["actors"]}
    delta = {"date": "2026-10-01", "tag": TAG, "base": str(WORLD_FIX.relative_to(ROOT)), "moved": [], "added": [],
             "pending_dojolab": {}}
    for b in I["site"]["closure_1v1"]["terrace_lines"]:
        a = by[b["label"]]
        assert close(a["loc"], b["old"]["loc"], 0.002), (a["loc"], b)
        a["loc"] = b["new"]["loc"]
        a["scale"] = b["new"]["size_m"]
        delta["moved"].append({"label": b["label"], "loc": a["loc"], "scale": a["scale"]})
    wr = T["WR5_east_terrace_wall"]
    end = by[wr["move"][0]["label"]]
    assert close(end["loc"], wr["move"][0]["from"], 0.002)
    end["loc"] = wr["move"][0]["to"]
    delta["moved"].append({"label": end["label"], "loc": end["loc"]})
    proto = by["WR2_WR3_WR4_WR5_28_Wall_4m_H3"]
    for k, add in enumerate(wr["add"]):
        a = copy.deepcopy(proto)
        a["label"] = f"WR5_HA_{k:02d}_{add['piece'].replace('SM_DKT_', '')}"
        a["mesh"] = f"/Game/DojoKit/StoneKit/Meshes/{add['piece']}"
        a["loc"] = add["loc"]
        a["rot_z"] = add["rot_z_deg"]
        W["actors"].append(a)
        delta["added"].append({"label": a["label"], "mesh": a["mesh"], "loc": a["loc"], "rot_z": a["rot_z"]})
    for c in T["cherry_slots"]:
        a = by[c["label"]]
        assert close(a["loc"], c["from"], 0.002)
        a["loc"] = c["to"]
        delta["moved"].append({"label": c["label"], "loc": a["loc"]})
    for c in T["cypress_front_row"]["old"]:
        a = by[c["label"]]
        a["loc"] = [a["loc"][0], round(a["loc"][1] + 12.0, 4), a["loc"][2]]
        a["z_resnap_pending"] = True
        delta["moved"].append({"label": c["label"], "loc": a["loc"], "note": "z to re-snap to LS_Valley"})
    delta["pending_dojolab"] = {
        "LS_Valley_north_hill_spot_heights": T["LS_Valley_north_hill_spot_heights"],
        "north_strip": T["north_strip"], "compound_yards_new": T["compound_yards_new"],
        "forest_FZ1": {"new_south_edge_y": T["forest_FZ1"]["new_south_edge_y"], "drop_or_reseat": T["forest_FZ1"]["list"]},
        "cypress_z": "re-snap Cypress_1..5 to the edited LS_Valley",
        "bank_rocks": "re-check BankB_25 / 30 / 48 against the new WR5 walls (x 49, y 44-56)"}
    W["hall_armory"] = {"tag": TAG, "delta": "world_layout_delta.json"}
    wj(OUTD / "world_layout_hall_armory.json", W)
    wj(OUTD / "world_layout_delta.json", delta)
    REP["world_layout"] = {"moved": len(delta["moved"]), "added": len(delta["added"])}


# ------------------------------------------------------------------------------------------------ blend
def compose_blend(L, log, interior):
    asm = bpy.data.collections["Assembly"]
    kit = bpy.data.collections["Kit"]
    rem = bpy.data.collections.new("HallArmory_Removed")
    bpy.context.scene.collection.children.link(rem)
    by_name = {o.name: o for o in asm.objects}
    # the landscape round removed 338 instances from the level (the town etc.): they leave the check Assembly too, so
    # the checks see what Unreal places (collection Landscape_Removed keeps them for reference)
    lrem = bpy.data.collections.new("Landscape_Removed")
    bpy.context.scene.collection.children.link(lrem)
    n_lrem = 0
    for k, it in enumerate(L["instances"]):
        if it.get("removed") and it["removed"] != TAG:
            o = by_name.get(f"{it['piece']}__{k:04d}")
            if o is not None:
                asm.objects.unlink(o)
                lrem.objects.link(o)
                n_lrem += 1
    lrem.hide_render = True
    REP["landscape_removed_out_of_assembly"] = n_lrem
    for k in log["removed"]:
        nm = f"{L['instances'][k]['piece']}__{k:04d}"
        o = by_name.get(nm)
        if o is None:
            REP["warnings"].append(f"removed instance not in blend: {nm}")
            continue
        asm.objects.unlink(o)
        rem.objects.link(o)
    before = {}
    for k in log["moved"]:
        it = L["instances"][k]
        o = by_name.get(f"{it['piece']}__{k:04d}")
        if o is None:
            REP["warnings"].append(f"moved instance not in blend: {k}")
            continue
        before[k] = list(o.matrix_world.translation)
        o.matrix_world.translation = Vector(it["loc"])
    # replace the ring in the Kit, append the new pieces
    old = bpy.data.objects.get("SM_DGB_Boundary_1v1")
    if old is not None:
        HC.remove_object_tree(old)
    new = HC.append_kit(REAR_BLEND, ("Kit", "Blockers"), kit)
    ring_inst = by_name.get("SM_DGB_Boundary_1v1__0002")
    ring_inst.data = new["SM_DGB_Boundary_1v1"].data
    kobj = {o.name: o for o in kit.objects if o.type == "MESH" and not o.name.startswith("UCX_")}
    n_new = 0
    for k in log["added"]:
        it = L["instances"][k]
        src = kobj.get(it["piece"])
        if src is None:
            REP["warnings"].append(f"no kit mesh for {it['piece']}")
            continue
        HC.place(asm, src, f"{it['piece']}__{k:04d}", it["loc"], it["rot_z"])
        n_new += 1
    # the armory interior (imported read-only from Exports/ArmoryKit)
    akit = bpy.data.collections.new("ArmoryKit")
    bpy.context.scene.collection.children.link(akit)
    got, rep = HC.import_armory(kit, interior)
    n_ak, bad_bbox = 0, []
    for it in interior["instances"]:
        src = got.get(it["piece"])
        if src is None:
            REP["warnings"].append(f"armory piece missing: {it['piece']}")
            continue
        o = HC.place(asm, src, f"{it['piece']}__{it['id']}", HC.hall_local_to_world(it["loc_m"]), it["rot_z_deg"])
        n_ak += 1
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bb = [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]
        want = list(HC.hall_local_to_world(it["bbox_m"][:3])) + list(HC.hall_local_to_world(it["bbox_m"][3:]))
        err = max(abs(a - b) for a, b in zip(bb, want))
        if err > 0.02:
            bad_bbox.append({"id": it["id"], "piece": it["piece"], "err_m": round(err, 4)})
    bpy.data.collections.remove(akit)
    REP["blend"] = {"moved_from": {str(k): [round(v, 3) for v in t] for k, t in before.items()},
                    "new_instances": n_new, "armory_instances": n_ak, "armory_pieces": len(got),
                    "armory_bbox_mismatch_over_2cm": bad_bbox[:20], "n_armory_bbox_mismatch": len(bad_bbox),
                    "armory_import": rep, "assembly": len(asm.objects), "kit": len(kit.objects)}
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))


def main():
    interior = rj(SHARED / "interior_layout.json")
    L, log = update_layout()
    checks_layout(L, interior)
    world_layout()
    compose_blend(L, log, interior)
    wj(OUTD / "compose_report.json", REP)
    print("COMPOSE", json.dumps({k: v for k, v in REP.items() if k != "blend"}), json.dumps(
        {k: v for k, v in REP["blend"].items() if k != "armory_import"}), flush=True)


if __name__ == "__main__":
    main()
