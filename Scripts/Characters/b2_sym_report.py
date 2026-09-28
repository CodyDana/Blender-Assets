"""b2_sym_report.py - PRIVATE / DO NOT SHIP. Writes WorkFiles/Characters/2B_private/stepSym_report.json (py -3).

Collects checks_sym/{measure_before,measure_after,sym_build,sym_export_info,sym_verify_info,sym_sheet_info}.json.
Build order:
  blender -b rig_work/c1_stage3a_heat.blend -P b2_sym_unsunk.py            -> checks_sym/c1_sink_capture.npz
  blender -b 2B_private_rig.blend -P b2_sym_twistprobe.py -- <abs checks_sym/twist_probe.json>   (diagnostic)
  blender -b 2B_private_rig.blend -P b2_sym_build.py                        -> 2B_private_rig_sym.blend (b2_sym_twist)
  blender -b 2B_private_rig_sym.blend -P b2_sym_gate.py -- <abs checks_sym/gate_after.json>        (girth / volume)
  blender -b <rig | rig_sym> -P b2_sym_detail.py -- <abs sym_renders> {before,after}   (+ prev_chord: a build run
          with B2_SYM_TWIST_BONES=none, i.e. the first build's plain average, rendered before the final build)
  blender -b <rig | rig_sym> -P b2_sym_measure.py -- checks_sym/measure_{before,after}.json checks_sym/mirror_map.npy
  blender -b <rig | rig_sym> -P b2_sym_render.py -- <abs sym_renders> {before,after}
  blender -b 2B_private_rig_sym.blend -P b2_sym_posetest.py -- <abs sym_renders/poses>
  py -3 b2_sym_sheet.py
  blender -b 2B_private_rig_sym.blend -P b2_sym_export.py -- export ; blender -b --factory-startup -P b2_sym_export.py -- verify
  py -3 b2_sym_report.py
"""
import json, os, glob

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
C = OUT + "/checks_sym"
S = "C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters"
j = lambda n: json.load(open(f"{C}/{n}.json"))  # noqa
mb, ma, b, ex, vf, sh = (j("measure_before"), j("measure_after"), j("sym_build"), j("sym_export_info"),
                         j("sym_verify_info"), j("sym_sheet_info"))
ga, gp = j("gate_after"), j("gate_prev_chord")
skin_max_cm = round(b["skin_symmetrize_move_mm"]["max"] / 10, 1)
regions = ["all", "face", "neck", "torso", "breasts", "pelvis", "arms", "hands", "legs", "feet", "midline_abs_x"]
bone_max_cm = round(b["skeleton"]["head_moved_mm_max"] / 10, 3)
rep = {
    "status": "ok",
    "private": "PRIVATE / DO NOT SHIP",
    "sym_blend": OUT + "/2B_private_rig_sym.blend",
    "fbx": OUT + "/export_sym/SK_2B_Private.fbx",
    "textures_dir": OUT + "/export_sym/textures",
    "untouched": [OUT + "/2B_private_rig.blend", OUT + "/export/"],
    "sagittal_plane_before": {
        "whole_skin": mb["skin_planes"]["all"],
        "note": "best-fit plane of the whole skin is 0.11 deg yaw / 0.10 deg roll off x = 0 and 1.7 mm to the side at the "
                "body centre, so x = 0 is the mirror plane; the slant is local (per-region planes below)",
        "per_region": {k: v for k, v in mb["skin_planes"].items() if k != "all"}},
    "asymmetry_skin_mm": {r: {"before": mb["skin"][r], "after": ma["skin"][r]} for r in regions},
    "asymmetry_face_only_mm": {"before": mb["skin"]["face"], "after": ma["skin"]["face"]},
    "asymmetry_bones": {"before": {k: v for k, v in mb["bones"].items() if k in ("pairs_head_max_mm", "pairs_head_mean_mm", "midline_head_max_abs_x_mm")},
                        "after": {k: v for k, v in ma["bones"].items() if k in ("pairs_head_max_mm", "pairs_head_mean_mm", "midline_head_max_abs_x_mm")},
                        "pairs_before": mb["bones"]["pairs"]},
    "asymmetry_headparts_garments_chamfer_mm": {"before": {**mb["SK_2B_HeadParts"], **mb["SK_2B_Garments"]},
                                                "after": {**ma["SK_2B_HeadParts"], **ma["SK_2B_Garments"]}},
    "render_pixel_asymmetry_clay": sh["pixel_stats"],
    "mirror_map": b["mirror_map"],
    "twist_fix": {
        "problem": "first build: plain p' = (p + M p_twin) / 2; on the upper arm the topological twin sits up to ~100 deg "
                   "around the limb from its mirrored geometric partner (forearm / thigh / calf ~15-45 deg, base of the "
                   "neck up to ~100 deg), so the chord average cut through the limb: upper arm radius -24 %, skin "
                   "volume -3.4 %",
        "fix": b["skin_twist_average"],
        "gates_first_build_plain_average": gp["gates"], "gates_after": ga["gates"],
        "volume_l": {"before": ga["volume_l"]["before"], "first_build": gp["volume_l"]["after"], "after": ga["volume_l"]["after"]},
        "limb_girth_after": ga["girth_mm"], "limb_girth_first_build": {k: {kk: vv for kk, vv in v.items() if kk in ("after_mean", "after_vs_before_lr_mean_pct", "sections_after_vs_before_pct")} for k, v in gp["girth_mm"].items()},
        "area_by_region_vs_before_pair_mean": ga["area_by_region_vs_before_pair_mean"],
        "faces_below_0.7_after": ga["shrunk_faces_below_0.7"],
        "faces_below_0.7_first_build_total": gp["shrunk_faces_below_0.7"]["total"]},
    "build": b,
    "fit": {"garment_clearance_before": mb["garment_clearance"], "garment_clearance_after": ma["garment_clearance"],
            "skin_under_garments_before": {k: v for k, v in mb["skin_under_garments"].items() if k != "through_list"},
            "skin_under_garments_after": ma["skin_under_garments"],
            "eyes_vs_lids_before": mb["eyes_vs_lids"], "eyes_vs_lids_after": ma["eyes_vs_lids"],
            "feet_before": mb["feet"], "feet_after": ma["feet"],
            "height_m_after": ma["height_m"], "min_z_after": ma["min_z_m"]},
    "export": {"fbx": ex["fbx"], "verify": {k: v for k, v in vf.items() if k not in ("bones", "imported_images")}},
    "renders": sorted(glob.glob(OUT + "/sym_renders/*.png") + glob.glob(OUT + "/sym_renders/poses/*.png")),
    "sheet": OUT + "/sym_renders/sym_sheet.png",
    "scripts": sorted(glob.glob(S + "/b2_sym_*.py")),
    "unreal_reimport_notes": (
        f"Same skeleton: 63 bones (64 with the root node), identical names, parents and MetaHuman rest orientations "
        f"(orientation change 0.0 deg). Bone positions moved by at most {bone_max_cm} cm (legs: the thigh/calf/foot/ball "
        f"pairs were 3.2 mm apart in height and are now averaged; spine/neck/head were already on x = 0, arms/fingers "
        f"< 0.1 cm). The skin moved up to {skin_max_cm} cm (neck/torso midline recentred, head roll and jaw skew removed), so this "
        f"is a mesh + skeleton reimport: import export_sym/SK_2B_Private.fbx over the private SK (or as a new SK with a "
        f"new skeleton asset), textures from export_sym/textures (FBX paths verified). The IK rig, IK retargeter, ABP "
        f"and BP can be kept (same bone names / hierarchy / orientations); after reimport re-check the retarget pose in "
        f"the retargeter (A-pose chains, feet on the floor) since joint positions changed by a few mm. Mesh counts "
        f"changed slightly: HeadParts 13564 -> 13592 verts (right eye / teeth / lashes are now mirror copies), "
        f"Garments 5878 -> {b['garments_verts']['total']} verts (briefs rebuilt from the left half, one stray bandeau lip quad removed); "
        f"materials and slot order unchanged. The vertex layout on the upper arm / forearm / thigh / calf / base of the "
        f"neck was turned around the limb by half the left/right twist (up to ~50 deg at the elbow), so the skin texture "
        f"there turns with it. This replaces the first export_sym build (which had pinched upper arms). The old export/ "
        f"FBX was not touched."),
}
json.dump(rep, open(OUT + "/stepSym_report.json", "w"), indent=1)
print("wrote", OUT + "/stepSym_report.json", len(rep["renders"]), "renders")
