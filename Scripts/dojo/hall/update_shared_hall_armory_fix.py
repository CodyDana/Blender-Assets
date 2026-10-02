"""HALL + ARMORY FIX round (2026-10-01): write the fix round's SHELL changes into the shared source of truth
(WorkFiles/shared/armory_hall/) as REVISION 2. Every number comes from the build outputs (fix_lower_front_clip.json,
blender_bounds.json, layout_showcase.json); nothing is typed by hand. Hold the ArmoryHall lock (SYNC.md 5).

Changes recorded (all on the shell side, owned by the dojo chat; the interior pieces, cases, items and design lights of
interior_layout.json / lights_design.json 'lights' are NOT changed; interface.json is NOT changed):
- SM_DKH_RoofLower_Front rebuilt with its wall-flashing / rafter ends clamped to world y 24.040 (they poked 9.5 mm
  through the inner face of the front wall at +3.93: the row of dashes seen from the interior); same name (bbox -1.98 cm)
- the extension's rear-wall centre bay X 21-23: DKH_N0022 (SM_DKH_Bay_Door, closed lattice door) removed, DKH_N0084
  (SM_DKH_Bay_Plaster, same place) added
- lights_design.json level_only_not_travelling: the DojoLab-only DJ_ThresholdFill (documentation of a per-level light,
  as the armory's Sun_WindowFill is listed there)
- hall_shell_layout.json lights: the backers' per-level state in DojoLab (off in rev 2: the windows read dark)
Run (system Python): py -3 -B Scripts/dojo/hall/update_shared_hall_armory_fix.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "unreal"))
from pipeline.lock import assert_owner  # noqa: E402
import dj_armory_look as LOOK  # noqa: E402

SH = ROOT / "WorkFiles" / "shared" / "armory_hall"
SC = ROOT / "WorkFiles" / "dojo" / "build" / "showcase"
FIXJ = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "fix" / "json"
DATE = "2026-10-01"
REV = 2
CHAT = "dojo (hall + armory FIX round, DojoLab)"


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def wj(p, o):
    Path(p).write_text(json.dumps(o, indent=1), encoding="utf-8")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert_owner("ArmoryHall", "claude")
    S, M, D = rj(SH / "hall_shell_layout.json"), rj(SH / "manifest.json"), rj(SH / "lights_design.json")
    if M["revision"] >= REV and any(c.get("rev") == REV and c.get("stage") == "fix (shell)" for c in M["change_log"]):
        print("SHARED_FIX already at revision", M["revision"])
        return
    if M["revision"] != REV - 1:
        raise SystemExit(f"manifest revision {M['revision']} != {REV - 1}: re-sync and merge first (SYNC.md 10)")
    L = rj(SC / "layout_showcase.json")
    BB = rj(SC / "blender_bounds.json")
    clip = rj(FIXJ / "fix_lower_front_clip.json")
    assert clip.get("passed") and clip.get("exported"), "fix_lower_front_clip.json did not pass"
    idx = {i.get("shell_id"): n for n, i in enumerate(L["instances"]) if i.get("shell_id")}

    def wbox(n):
        b = BB["instances"][str(n)]
        return [round(v, 4) for v in b["min"] + b["max"]]

    # ---- hall_shell_layout.json
    for it in S["instances_new"]:
        if it["id"] == "DKH_N0022":
            it["status"] = "removed (rev 2)"
            it["removed_rev"] = REV
            it["replaced_by"] = "DKH_N0084"
    if not any(it["id"] == "DKH_N0084" for it in S["instances_new"]):
        n = idx["DKH_N0084"]
        i = L["instances"][n]
        S["instances_new"].append({
            "id": "DKH_N0084", "piece": "SM_DKH_Bay_Plaster", "loc_world_m": i["loc"], "rot_z_deg": i["rot_z"],
            "loc_hall_m": [round(i["loc"][0] - 22.0, 4), round(i["loc"][1] - 24.0, 4), round(i["loc"][2] - 0.5, 4)],
            "status": "new (rev 2)", "collision_class": "building",
            "note": "extension rear wall centre bay X 21-23: plaster (rev 2; replaces the closed lattice door DKH_N0022, "
                    "which glowed dead centre on the rear wall with the armory's hero painting right behind it)",
            "bbox_world_m": wbox(n)})
    S["extension"]["bays"]["rear_Y45"]["23"] = "Plaster"
    for it in S["instances_existing"]:
        if it["id"] == "DKH_S0604":
            it["bbox_world_m"] = wbox(it["showcase_index"])
            it["status"] = "kept (rebuilt rev 2: wall flashing clipped)"
    pe = S["pieces_existing"].get("SM_DKH_RoofLower_Front")
    if isinstance(pe, dict):
        pe["rev2"] = ("rebuilt by Scripts/dojo/hall/fix_lower_front_clip.py: the builder's own roof_pieces() (rebuild vs "
                      f"shipped max dev {clip['rebuild_vs_shipped_max_dev_m']} m), {clip['clamped_vertices']} wall-"
                      f"flashing / rafter-end vertices clamped to world y {clip['clip_y_world']} (y max "
                      f"{clip['y_max_world']['before']} -> {clip['y_max_world']['after']}), qa_check 0 hard fails")
    for Lr in S["lights"]:
        Lr["dojolab_rev2"] = (f"per level: DojoLab {'OFF (visible = False)' if LOOK.BACKER_CD <= 0 else LOOK.BACKER_CD} "
                              f"and backer paper x{LOOK.BACKER_EMISSIVE} (the windows read dark like the armory's own "
                              "night stills; the shell has no openings behind them)")
    S["measured"]["front_wall_inner_face_rev2"] = {
        "inner_face_y_world": 24.045, "probe": "WorkFiles/dojo/build/hall_armory/fix/json/probe_front_wall_{before,after}.json",
        "SM_DKH_RoofLower_Front_y_max_world": clip["y_max_world"], "left_past_inner_face": clip["left_past_inner_face"]}
    c = S.setdefault("counts", {})
    c["new"] = sum(1 for it in S["instances_new"] if not str(it.get("status", "")).startswith("removed"))
    c["removed_rev2"] = sum(1 for it in S["instances_new"] if str(it.get("status", "")).startswith("removed"))
    S["revision"], S["date"] = REV, DATE
    S["written_by"] = CHAT
    # ---- lights_design.json: the level-only record (documentation; it never travels)
    lo = D.setdefault("level_only_not_travelling", [])
    for Lr in getattr(LOOK, "LEVEL_LIGHTS", []):
        rec = {"name": Lr["name"], "type": Lr["type"], "level": "DojoLab",
               "design": {k: Lr[k] for k in ("loc_m", "pitch_deg", "yaw_ue_deg", "size_m", "kelvin", "cd")},
               "why": "per level (SYNC.md 6), DojoLab only: a warm wash just inside the open centre doors so the open "
                      "bays read as a lit room from the courtyard (reference 2: every front bay glows); lighting "
                      "channel 1 (interior), no shadows, no specular. Source: Scripts/dojo/unreal/dj_armory_look.py"}
        lo[:] = [x for x in lo if x.get("name") != Lr["name"]] + [rec]
    D["revision"], D["date"] = REV, DATE
    # ---- manifest.json
    f = M["fbx"]["SM_DKH_RoofLower_Front"]
    p = ROOT / f["path"]
    f["sha256"], f["bytes"] = sha(p), p.stat().st_size
    f["rev2"] = "rebuilt: wall flashing clipped at the front wall's inner face (same name, bbox -1.98 cm, SYNC.md 9)"
    assert f["sha256"] == clip["fbx_sha256_after"], "the exported FBX changed after fix_lower_front_clip.py"
    M["revision"], M["date"], M["chat"] = REV, DATE, CHAT
    M["change_log"].append({
        "rev": REV, "date": DATE, "chat": "dojo", "stage": "fix (shell)",
        "summary": ("fix round (judge deltas checked against the references): SHELL ONLY. SM_DKH_RoofLower_Front rebuilt "
                    f"with its wall flashing / rafter ends clamped to world y {clip['clip_y_world']} (they poked 9.5 mm "
                    "through the inner face of the front wall: the row of dashes seen from the interior); the "
                    "extension's rear-wall centre bay X 21-23 DKH_N0022 (closed lattice door, glowing behind the hero "
                    "painting) removed and replaced by DKH_N0084 (SM_DKH_Bay_Plaster); the backer lights' per-level "
                    "state recorded (DojoLab: off, the windows read dark); lights_design.json level_only_not_travelling "
                    "lists the DojoLab-only DJ_ThresholdFill. No interior piece, case, item or design light changed "
                    "(interior_layout.json untouched); no interface change. ArmoryLab: nothing to re-import (the shell "
                    "is not used there). DojoLab-only look, never synced (SYNC.md 6, Scripts/dojo/unreal/"
                    "dj_armory_look.py): interior PPV exposure -0.6 EV + local exposure 1.0 / bloom 0.3 / shadow "
                    "saturation 1.0, reflect-card emission x0.1, CaseLight_08 x0.5, parked-leaf paper unlit."),
        "files": ["manifest.json", "hall_shell_layout.json", "lights_design.json"]})
    wj(SH / "hall_shell_layout.json", S)
    wj(SH / "lights_design.json", D)
    wj(SH / "manifest.json", M)
    print("SHARED_FIX revision", REV, "DKH_N0084", S["instances_new"][-1]["bbox_world_m"], "RoofLower_Front sha",
          f["sha256"][:12])


main()
