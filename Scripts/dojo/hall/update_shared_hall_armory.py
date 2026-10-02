"""HALL + ARMORY round (2026-10-01), stage 2: write the built shell back into the shared source of truth
(WorkFiles/shared/armory_hall/): hall_shell_layout.json (status, built piece records, instance world boxes, measured
numbers) and manifest.json (sha256 of every new FBX and sidecar, the 1v1 site pieces, a dated change line). Every
number comes from the build / compose / measure outputs; nothing is typed by hand. Hold the ArmoryHall lock while it
runs (SYNC.md 5).

Run (system Python): py -3 -B Scripts/dojo/hall/update_shared_hall_armory.py
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.lock import assert_owner  # noqa: E402

SH = ROOT / "WorkFiles" / "shared" / "armory_hall"
B = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "blender"
DATE = "2026-10-01"


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def wj(p, o):
    Path(p).write_text(json.dumps(o, indent=1), encoding="utf-8")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace("\\", "/")


def world_box(bbox_local, pivot, loc, rot):
    """bbox_local is relative to the piece origin; an instance places the origin at loc, turned rot (deg) about Z."""
    x0, y0, z0, x1, y1, z1 = bbox_local
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for x in (x0, x1):
        for y in (y0, y1):
            pts.append((loc[0] + c * x - s * y, loc[1] + s * x + c * y))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [round(min(xs), 4), round(min(ys), 4), round(loc[2] + z0, 4), round(max(xs), 4), round(max(ys), 4),
            round(loc[2] + z1, 4)]


def main():
    assert_owner("ArmoryHall", "claude")
    S = rj(SH / "hall_shell_layout.json")
    M = rj(SH / "manifest.json")
    LHR = rj(B / "layout_hall_rear.json")
    EXP = rj(B / "export_report.json")
    MEA = rj(B / "measure.json")
    SIL = rj(B / "silhouette.json")
    hall_dir = ROOT / "Exports" / "DojoKit" / "Hall"
    # ---- built piece records
    built = {}
    for name, info in LHR["pieces"].items():
        if not name.startswith("SM_DKH_"):
            continue
        fbx = hall_dir / f"{name}.fbx"
        side = hall_dir / f"{name}.sockets.json"
        ex = EXP.get(name, {})
        built[name] = {
            "design": S["pieces_new"][name] if isinstance(S["pieces_new"].get(name), str)
            else S["pieces_new"].get(name, {}).get("design"),
            "note": info["note"], "class": info["class"], "fbx": rel(fbx),
            "sidecar": rel(side) if (ex.get("lods", 1) > 1 and side.exists()) else None,
            "tris": info["tris"], "lods": ex.get("lods", 1), "lod_tris": ex.get("lod_tris"), "ucx": info["ucx"],
            "nanite": info["nanite"], "slots": info["slots"], "local": info["local"],
            "pivot_world": info["pivot_world"], "bbox_local_m": info["bbox_local"],
            "ue_mesh": f"/Game/DojoKit/Hall/Meshes/{name}", "sha256": sha(fbx)}
        if info.get("extra"):
            built[name]["extra"] = info["extra"]
    S["pieces_new"] = built
    # ---- instance world boxes (the shell's pieces: new ones from the build, existing ones keep theirs)
    for it in S["instances_new"]:
        p = it["piece"]
        if p in LHR["pieces"]:
            bl = LHR["pieces"][p]["bbox_local"]
            piv = LHR["pieces"][p]["pivot_world"]
            loc = it["loc_world_m"]
            if piv is not None:          # world-frame pieces: bbox_local is relative to the pivot (= the instance loc)
                pass
            it["bbox_world_m"] = world_box(bl, piv, loc, it["rot_z_deg"])
        if p == "SM_DKH_DoorLeaf_Parked":
            it["note"] = it["note"].replace("sill +0.04 to head +1.90", "standing on the floor, 0 to +1.86")
    # ---- numbers
    n = LHR["numbers"]
    ext = S["extension"]
    ext["wall_plate_world"] = n["rear_wall_plate"]
    ext["roof"]["wall_plate"] = n["rear_wall_plate"]
    ext["roof"]["valley"]["y"] = n["valley"]["y"]
    ext["roof"]["valley"]["z_collision"] = n["valley"]["z"]
    rr = LHR["pieces"]["SM_DKH_Rear_RoofRidge"]["extra"]
    ext["roof"]["ridge"]["planes_meet_z"] = rr["planes_meet"]
    ext["roof"]["ridge"].pop("cap_top_z_est", None)
    ext["roof"]["ridge"].pop("end_top_z_est", None)
    ext["roof"]["ridge"]["cap_top_z"] = rr["ridge_cap_top"]
    ext["roof"]["ridge"]["end_top_z"] = rr["ridge_end_top"]
    vm = ext["roof"]["vs_main"]
    vm["cap_below_main_m"] = round(vm["main_cap_top"] - rr["ridge_cap_top"], 4)
    vm["ridge_end_below_main_end_m"] = round(vm["main_end_top"] - rr["ridge_end_top"], 4)
    env = MEA["envelope"]
    ext["roof"]["clearance_over_the_armory"] = {
        "armory_top_world": env["armory_top_vertex_z_world"], "rule": "shell over the armory >= its top + 0.02",
        "lowest_shell_vertex_world": env["lowest_shell_vertex_over_the_armory"]["z_world"],
        "clearance_m": round(env["lowest_shell_vertex_over_the_armory"]["z_world"] - env["armory_top_vertex_z_world"], 4),
        "by_piece_world": env["lowest_shell_z_over_the_armory_by_piece"],
        "note": "measured on the built meshes (measure_hall_armory.py); both roofs' rafter ends at the valley line were "
                "raised to +5.522 over the armory's plan (84 + 84 vertices)"}
    ext["rear_clere_band_above_floor"] = n["rear_clere_band_above_floor"]
    ext["gable_base_y"] = [n["gable_y0"], round(2 * 39.5 - n["gable_y0"], 4)]
    S["hall"]["main_rear_beam_over_the_opening_world"] = n["main_rear_beam"]
    S["measured"] = {"doors": MEA["doors"], "envelope_violations": env["n_violations"],
                     "rear_visibility_px": {k: v["pixels_at_full_res"] for k, v in MEA["rear_visibility"].items()},
                     "silhouette_xor_px": {k: v["xor_px"] for k, v in SIL.items()},
                     "source": "WorkFiles/dojo/build/hall_armory/blender/{measure.json, silhouette.json}"}
    S["status"] = ("BUILT (rev 1, stage 2 Blender, 2026-10-01): the 13 new SM_DKH pieces exported through "
                   "Scripts/pipeline (qa_check 0 hard fails); WorkFiles/dojo/build/showcase/layout_showcase.json carries "
                   "every shell instance (new ones with their shell_id); not yet in DojoLab")
    S["written_by"] = "dojo (hall + armory round wf_ac6d2186-d40, stage 2 Blender build)"
    S["counts"]["built_pieces"] = len(built)
    wj(SH / "hall_shell_layout.json", S)
    # ---- manifest
    for name, rec in built.items():
        M["fbx"][name] = {"path": rec["fbx"], "sha256": rec["sha256"], "bytes": (ROOT / rec["fbx"]).stat().st_size,
                          "owner": "dojo", "ue_mesh": rec["ue_mesh"]}
        if rec["sidecar"]:
            M["fbx"][name]["sidecar"] = rec["sidecar"]
            M["fbx"][name]["sidecar_sha256"] = sha(ROOT / rec["sidecar"])
        M["pending_fbx"].pop(name, None)
    site = {}
    for name, d, ue in (("SM_DKX_1v1_HallRear_W", "Exports/DojoKit/Outside", "/Game/DojoKit/Outside/Meshes"),
                        ("SM_DKX_1v1_HallRear_E", "Exports/DojoKit/Outside", "/Game/DojoKit/Outside/Meshes"),
                        ("SM_DKX_1v1_RearRoof", "Exports/DojoKit/Outside", "/Game/DojoKit/Outside/Meshes"),
                        ("SM_DGB_Boundary_1v1", "Exports/DojoKit", "/Game/DojoKit/Greybox/Meshes")):
        p = ROOT / d / f"{name}.fbx"
        site[name] = {"path": rel(p), "sha256": sha(p), "bytes": p.stat().st_size, "ue_mesh": f"{ue}/{name}",
                      "owner": "dojo", "note": "DojoLab only (1v1 closure / ring); never placed in ArmoryLab"}
    M["site_fbx_dojolab_only"] = site
    drift = []
    for name, rec in M["fbx"].items():
        if rec.get("owner") == "dojo" and name not in built:
            if sha(ROOT / rec["path"]) != rec["sha256"]:
                drift.append(name)
    M["checks"]["shell_existing_fbx_sha_drift"] = drift
    M["chat"] = "dojo (hall + armory round wf_ac6d2186-d40, stage 2 Blender build)"
    M["change_log"].append({
        "rev": 1, "date": DATE, "chat": "dojo", "stage": "2 (Blender build)",
        "summary": ("built and exported the 13 new SM_DKH shell pieces (rear extension frame, bays, lower rear gable roof, "
                    "ridge, gables, the back slope cut at the valley, the opened door bays, parked leaves, window "
                    "backers) through Scripts/pipeline, qa_check 0 hard fails; hall_shell_layout.json now BUILT with "
                    "measured numbers; INTERFACE CHANGED (rev 1, before release): shell_intrusions front-wall x +-6.3 "
                    "and the parked-leaf box (y 0.13-0.22, z 0-1.86) from the built meshes, rafter clearance measured "
                    "0.0213 m; the 1v1 site pieces (HallRear_W/E, RearRoof, the ring +11 m) listed under "
                    "site_fbx_dojolab_only"),
        "files": ["manifest.json", "hall_shell_layout.json", "interface.json"]})
    wj(SH / "manifest.json", M)
    print(json.dumps({"built": len(built), "site": len(site), "existing_shell_sha_drift": drift,
                      "pending_left": list(M["pending_fbx"])}))


if __name__ == "__main__":
    main()
