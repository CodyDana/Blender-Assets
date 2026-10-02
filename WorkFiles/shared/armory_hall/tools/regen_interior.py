"""Regenerate interior_layout.json + lights_design.json FROM THE ARMORY CHAT'S OWN BUILD DATA (plain Python 3).

    py -3 -B WorkFiles/shared/armory_hall/tools/regen_interior.py                 # dry run: print the diff, write nothing
    py -3 -B WorkFiles/shared/armory_hall/tools/regen_interior.py --write --chat armory   # needs the ArmoryHall lock

Exit codes: 0 = no content change (or written), 1 = an error / an envelope violation (nothing written),
            4 = dry run found content changes (run again with --write, then check_sync.py, then bump_manifest.py).

Inputs (read only):  WorkFiles/armory/build/layout.json (instances, lights, cases, items, cameras, hero pieces),
                     WorkFiles/armory/build/unreal/{import,materials,level}.json (ArmoryLab's import / material / light
                     reports), Exports/ArmoryKit (item FBX sha), and the CURRENT interior_layout.json / lights_design.json /
                     interface.json of this folder (ids, per-level values, the envelope).
Only interior_layout.json and lights_design.json are ever written. The manifest is NOT bumped here: the caller runs
check_sync.py and then bump_manifest.py (SYNC.md section 7).

The conversion (the rules of the hall + armory survey, WorkFiles/dojo/build/hall_armory/survey/make_survey.py, moved here):
  * frame: hall-local = armory + (-6, 0, 0), a pure translation (rotations unchanged);
  * NOT USED in the hall: every SM_AKX_* (the armory's own exterior), the pieces in NOT_USED below (its south wall /
    entrance, threshold, sunken genkan + step beam, the entry plank band, its door leaves, the jamb posts and the wall
    sconces on them) and the south corner posts SM_AK_Corner_5 standing at armory Y < 0;
  * GENKAN SUBSTITUTIONS: the entry floor lanterns and the entry mat that stood on the genkan floor (-0.12) are lifted
    +0.12 onto the floor (lanterns' lights too); the genkan + entry band footprint is filled with eight ordinary
    SM_AK_Floor_Plank_2x2_<A-D> tiles in the armory's own pattern (ids AKI_9001..9008);
  * STABLE IDS: an instance keeps its AKI_* id when its piece, armory location and rotation match a current instance;
    a moved instance (same piece, the nearest unmatched current one within MOVE_MATCH_M) keeps its id; a new instance
    gets the next free number; a vanished instance's id goes to 'retired_ids' and is never reused;
  * the interface envelope (interface.json envelope.with_walls, tolerance 0.012 m) is checked for every instance bbox
    and light; any violation stops the write (an interface change needs the owner: SYNC.md section 4);
  * per-level values in lights_design.json (level_scale, the DojoLab / ArmoryLab-only lights with a 'level' key) and the
    case 'contents' notes are carried over from the current files.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ahcommon as A  # noqa: E402

NOT_USED = {
    "SM_AK_Entrance_12": "the armory's own south wall with its 4.0 x 3.65 m entrance frame, lintel and ranma: the hall's "
                         "front wall and its three centre door bays replace it (the armory's exterior wall is not used)",
    "SM_AK_Threshold_4": "the armory's exterior threshold sill (outside its south wall)",
    "SM_AK_GenkanFloor": "the armory's sunken genkan (-0.12) is not used: the hall's veranda (+0.50) and door sill "
                         "(+0.545) are the entry; the armory floor runs flush to the hall's front wall",
    "SM_AK_StepBeam": "the genkan's agari-kamachi (black step beam) goes with the genkan",
    "SM_AK_Floor_Plank_EntryBand": "the plank band cut round the genkan: replaced by eight ordinary SM_AK_Floor_Plank_2x2 "
                                   "tiles in the armory's own A-D pattern (AKI_9001..9008)",
    "SM_AK_DoorLeaf": "the armory's own entrance leaves (3.9 m) belong to its 4 m entrance; in the hall the hall's door "
                      "leaves are the doors",
    "SM_AK_DoorLeaf_R": "as SM_AK_DoorLeaf",
    "SM_AK_Post_Jamb_480": "entrance jamb posts at hall-local x +-3.83..4.45: rev 1 decision D2 = not placed (they would "
                           "stand in the parked hall door leaves, decision D1)",
    "SM_AK_H_WallSconce": "the wall lanterns hang on the jamb posts (decision D2)",
}
AKX_REASON = "the armory's own exterior (garden, facades, roof, foundations, scenery): the hall supplies the shell"
SOUTH_CORNER = ("south corner post SM_AK_Corner_5 (armory Y -0.3..0): it would stand through the hall's front wall and "
                "show 0.18 m outside its outer face")
GENKAN_Z = -0.12
Z_SHIFT_PIECES = {"SM_AK_Lantern", "SM_AK_EntryMat"}      # stood on the genkan floor (-0.12): lifted onto the floor
ENTRY_TILES = [(2, 0), (4, 0), (6, 0), (8, 0), (2, 2), (4, 2), (6, 2), (8, 2)]   # armory frame, 2 x 2 m tiles
SKIP_CAMERAS = {"CG_Garden"}
MOVE_MATCH_M = 1.0
META_KEYS = {"revision", "date", "written_by", "source"}


def group_of(p):
    if p.startswith("SM_AK_Floor_Plank"):
        return "floor"
    if p.startswith("SM_AK_Case_"):
        return "case"
    if p.startswith(("SM_AK_Ceiling_", "SM_AK_H_Ceiling_")):
        return "ceiling"
    if p.startswith(("SM_AK_WallLower", "SM_AK_WallUpper", "SM_AK_Corner_5", "SM_AK_Window_Lattice", "SM_AK_SillLedge",
                     "SM_AK_Post_480", "SM_AK_Post_260", "SM_AK_WallPanel_LitWide")):
        return "wall"
    if p.startswith(("SM_AK_Platform_", "SM_AK_Steps_", "SM_AK_StairCheek", "SM_AK_EmblemDisc", "SM_AK_Post_Heavy",
                     "SM_AK_H_LanternStand")):
        return "dais_stairs"
    if p.startswith(("SM_AK_PaintingPanel", "SM_AK_H_PaintingBase", "SM_AK_RearScreen", "SM_AK_Post_LED",
                     "SM_AK_H_Canopy", "SM_AK_H_TopBeam", "SM_AK_H_Downlight", "SM_AK_RearAlcove",
                     "SM_AK_H_CornerNiche")):
        return "rear_wall_painting_alcoves_niches"
    if p.startswith("SM_AK_DSP_"):
        return "display_mount"
    return "dressing"


def collision_class(p):
    """interface.json gameplay collision_classes (DojoLab classes + 'glass')."""
    if p.startswith("SM_AK_Case_") and p.endswith("_Glass"):
        return "glass"
    if p.startswith("SM_AK_Case_") and p.endswith("_Plinth"):
        return "propblock"
    if p.startswith(("SM_AK_Floor_Plank", "SM_AK_Platform_", "SM_AK_Steps_", "SM_AK_EntryMat")):
        return "ground"
    if p.startswith(("SM_AK_Lantern", "SM_AK_H_LanternStand", "SM_AK_Vase_Plum_L")):
        return "propblock"
    if p.startswith(("SM_AK_Vase_Plum_S", "SM_AK_SillCaddy", "SM_AK_Banner")):
        return "thin"
    if p.startswith("SM_AK_DSP_"):
        return "nocollision"
    return "building"


def _num(id_):
    try:
        return int(id_.split("_")[1])
    except (IndexError, ValueError):
        return None


def assign_ids(cand, cur_instances, retired_cur):
    """cand: [(piece, armory_loc, rot_z)] in armory layout order -> (ids, retired_new, report)."""
    by_key = {}
    for it in cur_instances:
        src = it.get("src_armory", {})
        if src.get("layout_index") is None:      # the substitution tiles keep their fixed ids
            continue
        k = (it["piece"], tuple(round(float(v), 4) for v in src["loc"]), round(float(it["rot_z_deg"]), 4))
        by_key.setdefault(k, []).append(it["id"])
    used_nums = {_num(i["id"]) for i in cur_instances} | {_num(r["id"]) for r in retired_cur}
    ids = [None] * len(cand)
    taken = set()
    for n, (p, loc, rz) in enumerate(cand):
        k = (p, tuple(round(float(v), 4) for v in loc), round(float(rz), 4))
        lst = by_key.get(k)
        if lst:
            ids[n] = lst.pop(0)
            taken.add(ids[n])
    # moved: same piece, nearest unmatched current instance within MOVE_MATCH_M
    left = [it for it in cur_instances if it["id"] not in taken and it.get("src_armory", {}).get("layout_index") is not None]
    moved = []
    for n, (p, loc, rz) in enumerate(cand):
        if ids[n] is not None:
            continue
        best, bd = None, MOVE_MATCH_M
        for it in left:
            if it["piece"] != p or it["id"] in taken:
                continue
            d = math.dist([float(v) for v in it["src_armory"]["loc"]], [float(v) for v in loc])
            if d <= bd:
                best, bd = it, d
        if best is not None:
            ids[n] = best["id"]
            taken.add(best["id"])
            moved.append({"id": best["id"], "piece": p, "from": best["src_armory"]["loc"], "to": list(loc)})
    nxt = max([x for x in used_nums if x is not None and x < 9000] + [-1]) + 1
    new = []
    for n in range(len(cand)):
        if ids[n] is None:
            ids[n] = f"AKI_{nxt:04d}"
            new.append({"id": ids[n], "piece": cand[n][0]})
            nxt += 1
    vanished = [it for it in cur_instances if it["id"] not in taken and it.get("src_armory", {}).get("layout_index") is not None]
    return ids, vanished, {"moved": moved, "new": new}


def build(cur_I, cur_D, F):
    AL = A.jload(A.ARMORY_BUILD / "layout.json")
    AIMP = A.jload(A.ARMORY_BUILD / "unreal" / "import.json")
    AMAT = A.jload(A.ARMORY_BUILD / "unreal" / "materials.json")
    ALEV = A.jload(A.ARMORY_BUILD / "unreal" / "level.json")
    ww = F["envelope"]["with_walls"]
    ENV = {"x": ww["x"], "y": ww["y"], "z": ww["z"]}
    HERO = AL["hero_pieces"]
    SLOTS = {k: v["slots"] for k, v in AMAT["meshes"].items()}

    # ---- instances
    keep, not_used = [], []
    for idx, ins in enumerate(AL["instances"]):
        p, b = ins["piece"], ins["bbox_min_max"]
        reason = None
        if p.startswith("SM_AKX_"):
            reason = AKX_REASON
        elif p in NOT_USED:
            reason = NOT_USED[p]
        elif p == "SM_AK_Corner_5" and b[1] < -0.01:
            reason = SOUTH_CORNER
        if reason:
            not_used.append({"piece": p, "armory_layout_index": idx, "armory_loc": A.r4(ins["loc"]), "reason": reason})
        else:
            keep.append((idx, ins))
    retired_cur = list(cur_I.get("retired_ids", [])) if cur_I else []
    ids, vanished, idrep = assign_ids([(ins["piece"], A.r4(ins["loc"]), ins["rot_z"]) for _i, ins in keep],
                                      cur_I["instances"] if cur_I else [], retired_cur)
    interior, viol = [], []
    for (idx, ins), iid in zip(keep, ids):
        p, b = ins["piece"], ins["bbox_min_max"]
        dz = (-GENKAN_Z) if (p in Z_SHIFT_PIECES and abs(ins["loc"][2] - GENKAN_Z) < 1e-6) else 0.0
        hb = A.bbox_a2h(b, dz)
        rec = {"id": iid, "piece": p, "loc_m": A.a2h(ins["loc"], dz), "rot_z_deg": ins["rot_z"], "bbox_m": hb,
               "group": group_of(p), "hero_module": HERO.get(p), "collision_class": collision_class(p),
               "src_armory": {"layout_index": idx, "loc": A.r4(ins["loc"])}}
        if dz:
            rec["z_shift_m"] = round(dz, 3)
            rec["note"] = "stood on the armory's sunken genkan (-0.12): lifted +0.12 onto the hall floor"
        if "cast_shadow" in ins:
            rec["cast_shadow"] = ins["cast_shadow"]
        interior.append(rec)
    for k, (x, y) in enumerate(ENTRY_TILES):
        v = "ABCD"[(x // 2) % 2 + 2 * ((y // 2) % 2)]
        interior.append({"id": f"AKI_{9001 + k}", "piece": f"SM_AK_Floor_Plank_2x2_{v}", "loc_m": A.a2h((x, y, 0.0)),
                         "rot_z_deg": 0.0, "bbox_m": A.bbox_a2h((x, y, -0.1, x + 2, y + 2, 0.0)), "group": "floor",
                         "hero_module": None, "collision_class": "ground",
                         "src_armory": {"layout_index": None, "loc": [x, y, 0.0],
                                        "note": "new in the hall variant: fills the EntryBand + genkan footprint"}})
    for rec in interior:
        hb = rec["bbox_m"]
        for k, ax in enumerate("xyz"):
            lo, hi = ENV[ax]
            if hb[k] < lo - A.TOL or hb[k + 3] > hi + A.TOL:
                viol.append({"id": rec["id"], "piece": rec["piece"], "axis": ax, "bbox": hb})
    used_pieces = sorted({r["piece"] for r in interior})
    not_used_pieces = sorted({r["piece"] for r in not_used} - set(used_pieces))

    # ---- cases + items
    contents = {c["label"]: c.get("contents", "") for c in (cur_I or {}).get("cases", [])}
    case_ids = {}
    for r in interior:
        if r["group"] == "case":
            case_ids.setdefault((round(r["src_armory"]["loc"][0], 3), round(r["src_armory"]["loc"][1], 3)), []).append(r["id"])
    cases = []
    for c in AL["cases"]:
        W, D, H, G = c["width_depth_plinth_glass_m"]
        z0 = 0.6 if c["type"] == "Hero" else 0.0
        key = (round(c["loc"][0], 3), round(c["loc"][1], 3))
        cases.append({"label": c["label"], "type": c["type"], "loc_m": A.a2h((c["loc"][0], c["loc"][1], z0)),
                      "rot_z_deg": c["rot_z"], "width_depth_plinth_glass_m": [W, D, H, G],
                      "plinth_piece": f"SM_AK_Case_{c['type']}_Plinth",
                      "glass_piece": (f"SM_AK_Case_{c['type']}_Glass" if G > 0 else None),
                      "instance_ids": case_ids.get(key, []), "glass_top_m": round(z0 + H + G, 3),
                      "contents": c.get("contents") or contents.get(c["label"], "")})
    items = []
    for it in AL["items"]:
        fbx = Path(it["fbx"])
        items.append({"name": it["name"], "case": it["case"], "form": it.get("form"), "loc_m": A.a2h(it["loc"]),
                      "rot_z_deg": it["rot_z"], "mirror": it["mirror"], "ue_asset": it["ue_asset"],
                      "fbx": A.rel(fbx), "fbx_sha256": A.sha256(fbx) if fbx.exists() else None,
                      "textures": A.rel(Path(it["textures"])), "collision_class": "nocollision"})

    # ---- lights
    UEL = {L["name"]: L for L in ALEV["local_lights"]}
    lights, level_only = [], []
    for L in AL["lights"]:
        if L["type"] == "sun":
            level_only.append({"name": L["name"], "type": "directional", "design": L,
                               "why": "sky / sun / moon / time of day stay per level (SYNC.md 6)"
                               + ("; Sun_WindowFill is an interior-only fill through the armory's west windows: in the "
                                  "hall those windows face closed side strips and cavities, the shell's window backers "
                                  "(SM_DKH_Rear_WindowBacker + BackerLight_*) take its role"
                                  if L["name"] == "Sun_WindowFill" else "")})
            continue
        dz = 0.12 if (L["name"].startswith("Lantern_") and L["loc"][1] < 2.4 and L["loc"][2] < 0.5) else 0.0
        rec = {"name": L["name"], "type": L["type"], "role": L.get("role"), "loc_m": A.a2h(L["loc"], dz),
               "design": {k: v for k, v in L.items() if k not in ("loc", "aim")}}
        if "aim" in L:
            rec["aim_m"] = A.a2h(L["aim"], dz)
        if dz:
            rec["z_shift_m"] = dz
        u = UEL.get(L["name"])
        if u:
            rec["ue_armorylab_night"] = {k: u[k] for k in u if k not in ("loc_cm", "name", "type", "role")}
        lights.append(rec)
    for L in lights:
        p = L["loc_m"]
        if not all(ENV[ax][0] - A.TOL <= p[k] <= ENV[ax][1] + A.TOL for k, ax in enumerate("xyz")):
            viol.append({"light": L["name"], "loc": p})
    roles = {}
    for L in lights:
        roles[L["role"]] = roles.get(L["role"], 0) + 1

    # ---- cameras (reference)
    cams = []
    for c in AL["cameras"]:
        if c["name"] in SKIP_CAMERAS:
            continue
        rec = {"name": c["name"], "loc_m": A.a2h(c["loc"]), "look_at_m": A.a2h(c["look_at"]), "lens_mm": c["lens_mm"]}
        if "shift_y" in c:
            rec["shift_y"] = c["shift_y"]
        if c["loc"][1] < 0:
            rec["note"] = ("outside the armory's south wall: in the hall it stands at world (%.2f, %.2f, %.2f) on the "
                           "veranda / step band under the lower roof (eave +3.0 at Y 21.5): the lower roof blocks it; "
                           "the hall needs its own entry camera (proposed CAM_HallArmoryEntry)" % tuple(A.h2w(rec["loc_m"])))
        cams.append(rec)

    # ---- interior_layout.json
    I = copy.deepcopy(cur_I) if cur_I else {}
    I.update({k: v for k, v in {
        "revision": I.get("revision", 0), "date": I.get("date"), "owner": "armory chat (interior)",
        "written_by": I.get("written_by"),
        "source": dict(I.get("source", {}), **{"armory_layout_sha256": A.sha256(A.ARMORY_BUILD / "layout.json"),
                                              "armory_layout_counts": {"instances": len(AL["instances"]),
                                                                       "pieces": len(AL["pieces"])},
                                              "generator": "WorkFiles/shared/armory_hall/tools/regen_interior.py"}),
    }.items()})
    I["pieces"] = {p: {"fbx": f"Exports/ArmoryKit/{p}.fbx", "ue_mesh": f"/Game/ArmoryKit/Meshes/{p}",
                       "slots": SLOTS.get(p, {}), "hero_module": HERO.get(p), "group": group_of(p),
                       "collision_class": collision_class(p), "ucx": AIMP["meshes"].get(p, {}).get("convex"),
                       "tris_lod0": AIMP["meshes"].get(p, {}).get("tris_lod0"),
                       "nanite_armorylab": AIMP["meshes"].get(p, {}).get("nanite")} for p in used_pieces}
    I["instances"] = interior
    I["cases"] = cases
    I["items"] = items
    I["not_used_in_the_hall"] = {"pieces_with_no_instance_used": not_used_pieces, "instances": not_used}
    I["cameras_reference"] = cams
    retired = retired_cur + [{"id": v["id"], "piece": v["piece"], "last_loc_m": v["loc_m"]} for v in vanished]
    if retired:
        I["retired_ids"] = retired
    grp = {}
    for r in interior:
        grp[r["group"]] = grp.get(r["group"], 0) + 1
    I["counts"] = {"instances": len(interior), "pieces": len(used_pieces), "by_group": grp, "cases": len(cases),
                   "items": len(items), "not_used_instances": len(not_used),
                   "not_used_ext_akx": sum(1 for r in not_used if r["piece"].startswith("SM_AKX_")),
                   "envelope_violations": len([v for v in viol if "id" in v])}
    order = ["revision", "date", "owner", "written_by", "source", "units", "frame_conversion", "room", "pieces",
             "instances", "cases", "items", "not_used_in_the_hall", "cameras_reference", "retired_ids", "counts"]
    I = {k: I[k] for k in order if k in I} | {k: v for k, v in I.items() if k not in order}

    # ---- lights_design.json (per-level values carried over)
    D = copy.deepcopy(cur_D) if cur_D else {}
    keep_level = [r for r in D.get("level_only_not_travelling", []) if r.get("level")]
    D["lights"] = lights
    D["level_only_not_travelling"] = level_only + keep_level
    sp = dict(D.get("shadow_policy", {}))
    sp["design_shadowed"] = sum(1 for L in lights if L["design"].get("shadows"))
    sp["armorylab_ue_shadowed"] = sum(1 for L in lights if L.get("ue_armorylab_night", {}).get("shadows"))
    D["shadow_policy"] = sp
    D["counts"] = {"lights": len(lights), "by_role": roles,
                   "missing_ue_values": [L["name"] for L in lights if "ue_armorylab_night" not in L],
                   "outside_the_envelope": [v["light"] for v in viol if "light" in v]}
    return I, D, viol, idrep, vanished


def diff(a, b, path="", out=None, limit=60):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if not path and k in META_KEYS:
                continue
            if k not in a:
                out.append(f"+ {path}/{k}")
            elif k not in b:
                out.append(f"- {path}/{k}")
            else:
                diff(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"~ {path}: {len(a)} -> {len(b)} entries")
        for n, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{n}]", out, limit)
    elif a != b:
        out.append(f"~ {path}: {json.dumps(a)[:80]} -> {json.dumps(b)[:80]}")
    return out


def instance_diff(old, new):
    """by id; 'changed' ignores src_armory.layout_index (a reference into the armory's list, it shifts on inserts)."""
    def norm(i):
        j = copy.deepcopy(i)
        j.get("src_armory", {}).pop("layout_index", None)
        return json.dumps(j, sort_keys=True)
    o = {i["id"]: i for i in old["instances"]}
    n = {i["id"]: i for i in new["instances"]}
    ch = [k for k in o.keys() & n.keys() if norm(o[k]) != norm(n[k])]
    return {"added": sorted(n.keys() - o.keys()), "removed": sorted(o.keys() - n.keys()), "changed": sorted(ch)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the two files (needs the ArmoryHall lock)")
    ap.add_argument("--chat", default="armory", help="who writes (armory | dojo)")
    ap.add_argument("--agent", default="claude")
    a = ap.parse_args()
    S = A.shared()
    cur_I, cur_D, F, M = S.get("interior_layout"), S.get("lights_design"), S["interface"], S["manifest"]
    I, D, viol, idrep, vanished = build(cur_I, cur_D, F)
    rep = {}
    for name, old, new in (("interior_layout.json", cur_I, I), ("lights_design.json", cur_D, D)):
        d = diff(old or {}, new)
        meta = [k for k in META_KEYS if (old or {}).get(k) != new.get(k)]
        rep[name] = {"content_changes": d, "metadata_changes": meta}
        print(f"== {name}: {len(d)} content change(s){' (first 60)' if len(d) >= 60 else ''}; metadata keys differing: "
              f"{meta}")
        for line in d:
            print("   " + line)
    idd = instance_diff(cur_I or {"instances": []}, I)
    print("instances by id:", json.dumps({k: len(v) for k, v in idd.items()}), "| moved (id kept):",
          len(idrep["moved"]), "| new ids:", [x["id"] for x in idrep["new"]][:20], "| retired now:",
          [v["id"] for v in vanished][:20])
    print(f"envelope: {len(viol)} violation(s)", json.dumps(viol[:5]))
    changed = any(rep[n]["content_changes"] for n in rep)
    if viol:
        print("STOP: envelope violations (interface.json envelope.with_walls). Nothing written. An interface change "
              "needs the owner (SYNC.md 4); otherwise fix the armory layout.")
        return 1
    if not a.write:
        print("dry run: nothing written" + ("; content differs -> run with --write" if changed else "; up to date"))
        return 4 if changed else 0
    if not A.lock_held(a.agent):
        print("STOP: take the lock first: py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude")
        return 1
    pending = int(M["revision"]) + 1
    for name, old, new in (("interior_layout.json", cur_I, I), ("lights_design.json", cur_D, D)):
        if not rep[name]["content_changes"] and old is not None and old.get("source") == new.get("source"):
            print(f"{name}: unchanged, not written")
            continue
        new["revision"], new["date"] = pending, A.today()
        new["written_by"] = f"{a.chat} chat via tools/regen_interior.py"
        A.jdump(A.SH / name, new)
        print(f"{name}: WRITTEN as revision {pending} (now run tools/check_sync.py, then tools/bump_manifest.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
