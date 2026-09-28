"""b2_rig_report.py - PRIVATE / DO NOT SHIP. Step C1: writes WorkFiles/Characters/2B_private/stepC1_report.json
from the stage JSONs in rig_work/ (run with any python 3, e.g. Blender's bundled python)."""
import json, glob

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
W = OUT + "/rig_work"
S = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters"

v = json.load(open(W + "/c1_verify_info.json"))
e = json.load(open(W + "/c1_export_info.json"))
a = json.load(open(W + "/c1_apose_report.json"))
sol = json.load(open(W + "/c1_rig_solve.json"))
st1 = json.load(open(W + "/c1_stage1_info.json"))
heat = json.load(open(W + "/c1_heat_info.json"))
C = OUT + "/checks_c1"
dn = json.load(open(C + "/deform_numbers.json"))      # b2_check_deform.py -- numbers (independent judge)
cc = json.load(open(C + "/check_c1.json"))            # b2_check_c1.py (fresh Blender, raw FBX)
TRIS = "{:,}".format(v["total_tris"])
renders = sorted(r.replace("\\", "/") for r in glob.glob(OUT + "/rig_renders/*.png") if not r.endswith("rig_sheet.png"))
removed = sol["removed_bones"]
twist = [n for n in removed if "twist" in n]
toes = [n for n in removed if "toe_" in n]
helpers = [n for n in removed if n not in twist and n not in toes]
meshes = [{"name": m["name"], "tris": m["tris"], "material_slots": m["material_slots"], "materials": m["materials"],
           "max_influences": m["max_influences"]} for m in v["meshes"]]

NOTES = (
    "PRIVATE / DO NOT SHIP (DAZ G8F body + NieR-ripped parts; never into Fab or the game build). "
    "FILE: export/SK_2B_Private.fbx, written by Scripts/pipeline/export_fbx.py kind='skeletal', units='cm' (the centimetre "
    "path pipeline 1.2.0 uses for garments: -Y forward / Z up, FBX units scale, bone axes Y/X, no leaf bones, deform bones "
    "only, triangulated, no animation, no tangents). Its garment mode was NOT used on purpose: it writes every bone of the "
    "locked MetaHuman skeleton, and hers is a new, re-proportioned 63-bone skeleton. Re-imported in a fresh Blender: "
    "168.0 cm (armature object scale 0.01 = centimetre file), 63 bones, names and parents identical to metahuman_base_skel. "
    "IMPORT (UE 5.8 legacy FBX importer, or Interchange with a duplicated DefaultFBXOBJAssetsPipeline and Recompute Normals "
    "OFF): Skeletal Mesh ON; Skeleton = none -> create a NEW skeleton (e.g. SKEL_2B_Private); do NOT assign "
    "metahuman_base_skel (names match but her reference pose/proportions differ and she has 63 of its 341 bones). Import "
    "Uniform Scale 1.0 (file already in cm, expect 168 cm with root scale 1); Convert Scene ON; Force Front X Axis OFF; "
    "Use T0 As Ref Pose OFF; Morph Targets OFF; Animations OFF; Normals = Import Normals; Create Physics Asset ON; Import "
    "Materials ON, Import Textures ON (every FBX texture reference is the relative path textures/T_2B_*_D.jpg next "
    "to the FBX, all 8 files present; or bring in export/textures/*.jpg yourself). Expect 64 bones in UE (the 'root' node "
    "becomes the root bone, pelvis under it); max 7 influences per vertex; " + TRIS + " tris, 3 meshes, 21 material sections. "
    "ORIENTATION: faces -Y in Blender like the MetaHuman garments, so in UE she faces like the MH body: Character Blueprint "
    "mesh yaw -90, Z offset -capsule half height (capsule ~ radius 30, half height 86 cm). "
    "REST POSE: A-pose whose bone orientations equal the MetaHuman fitting-body rest orientations exactly (0.0 deg, checked "
    "per bone); only the joint positions are hers (arms ~45 deg down with the MH elbow bend, legs straight, feet flat at "
    "z=0, head straight). "
    "IK RIG (same layout as the MetaHuman one; Manny uses the same names so auto-mapping works): Retarget Root = pelvis. "
    "Chains: Spine spine_01->spine_05; Neck neck_01->neck_02; Head head; LeftClavicle clavicle_l; RightClavicle "
    "clavicle_r; LeftArm upperarm_l->hand_l; RightArm upperarm_r->hand_r; LeftLeg thigh_l->ball_l; RightLeg "
    "thigh_r->ball_r (or thigh->foot plus LeftToe/RightToe = ball); per hand Thumb thumb_01->thumb_03, Index "
    "index_metacarpal->index_03, Middle middle_metacarpal->middle_03, Ring ring_metacarpal->ring_03, Pinky "
    "pinky_metacarpal->pinky_03. Optional Full Body IK goals on hand_l/r and foot_l/r if the feet slide. "
    "RETARGETER (hidden Manny -> her, Retarget Pose From Mesh like the MH male): Manny's retarget pose is an A-pose too; "
    "check the arm chain angles in the retarget pose editor. "
    "NO TWIST / CORRECTIVE / TOE BONES: 26 twist, 232 corrective/helper and 20 toe bones deleted (nothing would drive them "
    "without a post-process AnimBP); forearm pronation lands at the wrist; no face bones (face static; eyes, teeth, lashes "
    "and the face skin 100% head, the neck blends below the jaw line). "
    "MATERIALS (base colour only, UV0, opaque JPEGs in export/textures): SK_2B_Body: M_2B_Body + M_2B_Head -> "
    "T_2B_Torso_C_D.jpg (Head = scalp with painted short hair); M_2B_Face, M_2B_Lips, M_2B_Ears, M_2B_EyeSocket -> "
    "T_2B_Face_C_D.jpg; M_2B_Legs, M_2B_Toenails -> T_2B_Leg_C_D.jpg; M_2B_Arms, M_2B_Fingernails -> T_2B_Arm_C_D.jpg; "
    "M_2B_Mouth -> T_2B_G8FBaseMouthMapD_1005_D.jpg (one skin master, roughness ~0.5). SK_2B_HeadParts: M_2B_Sclera, "
    "M_2B_Irises, M_2B_Pupils -> T_2B_Eye_0_D.jpg; M_2B_Teeth -> T_2B_G8FBaseMouthMapD_1005_D.jpg; M_2B_Cornea / "
    "M_2B_EyeMoisture / M_2B_Tear are clear eye covers (opacity 0.12 / 0.05 / 0.05) -> Translucent or hide them, else the "
    "eyes render white; M_2B_Eyelashes -> T_2B_hair_d_D.jpg has no alpha (reads as a dark eyeliner band). SK_2B_Garments: "
    "M_2B_Underwear -> T_2B_body_d_D.jpg, Two Sided; M_2B_BasicTop plain dark grey (0.075,0.075,0.08), roughness 0.85, "
    "Two Sided. "
    "SCALE NOTE: step A scaled the POSED skin to 1.68 m while she stood on tiptoe with a bent knee; flat-footed in the "
    "A-pose she measured 1.63 m, so the A-pose was scaled uniformly by 1.031 to stand 168 cm.")

report = {
    "status": "ok",
    "rig_blend": OUT + "/2B_private_rig.blend",
    "fbx": OUT + "/export/SK_2B_Private.fbx",
    "meshes": meshes,
    "total_tris": v["total_tris"],
    "bones": v["bone_count"],
    "bones_in_unreal_including_root_node": v["bone_count"] + 1,
    "bone_names_all_in_mh": v["bone_names_all_in_mh"],
    "bone_parents_match_mh": v["parents_match_mh"],
    "max_influences": v["max_influences"],
    "height_cm_apose": v["height_cm"],
    "rest_orientation_max_dev_from_MH_deg": a["rest_orientation_max_dev_from_MH_deg"],
    "contact_sheet": OUT + "/rig_renders/rig_sheet.png",
    "pose_renders": renders,
    "textures_dir": OUT + "/export/textures",
    "textures": e["textures"],
    "material_textures": {k: m.get("base_color_texture") for k, m in e["materials"].items()},
    "kept_bones": sol["order"],
    "removed_bones": {"count": len(removed), "twist": twist, "toes": toes, "corrective_helper_count": len(helpers)},
    "scripts": [S + "/" + n for n in (
        "b2_rig_common.py", "b2_rig_geo.py", "b2_rig_mesh.py", "b2_rig_joints.py", "b2_rig_solve.py", "b2_rig_apose.py",
        "b2_rig_posetest.py", "b2_rig_sheet.py", "b2_rig_export.py", "b2_rig_report.py", "b2_rig_look.py",
        "b2_rig_jointviz.py", "b2_check_deform.py", "b2_check_c1.py")],
    "build_order": [
        "blender -b 2B_private_base.blend -P b2_rig_mesh.py  -> rig_work/c1_stage1_mesh.blend",
        "blender -b rig_work/c1_stage1_mesh.blend -P b2_rig_joints.py  -> rig_work/c1_joints_posed.json",
        "blender -b rig_work/c1_stage1_mesh.blend -P b2_rig_solve.py  -> rig_work/c1_rig_solve.json + c1_stage3a_heat.blend",
        "blender -b rig_work/c1_stage3a_heat.blend -P b2_rig_apose.py  -> 2B_private_rig.blend",
        "blender -b 2B_private_rig.blend -P b2_rig_posetest.py -- rig_renders ; py -3 b2_rig_sheet.py rig_renders rig_renders/rig_sheet.png",
        "blender -b 2B_private_rig.blend -P b2_rig_export.py -- export ; blender -b --factory-startup -P b2_rig_export.py -- verify",
        "blender -b 2B_private_rig.blend -P b2_check_deform.py -- both ; blender -b --factory-startup -P b2_check_c1.py",
        "python b2_rig_report.py"],
    "stage_info": {"stage1": {k: st1[k] for k in ("skin", "teeth_tris", "lash_faces_dropped", "top", "underwear_tris",
                                                  "underwear_weld", "crotch_skin_relaxed_verts", "total_tris") if k in st1},
                   "heat": heat, "apose": {k: x for k, x in a.items() if k != "finger_rebuild"},
                   "finger_rebuild": a.get("finger_rebuild")},
    "fixes_done": [
        "Game mesh: exact L1 un-subdivided welded skin shell (58,402 v / 116,800 tris, 100% quads) with the source UVs and 11 surface materials; eyes kept (EyeMoisture/Tear decimated to 30%); teeth decimated 34,560 -> 5,819 tris; lower-lash cards removed by their UV strip (108 faces), upper cards kept; 3 meshes / 21 sections; " + TRIS + " tris (budget 160,000).",
        "CLO_BasicTop: bandeau from the chest Body faces of the skin shell (upper edge 2.5 cm lower at the sides to clear the armpits), cleavage/spine groove bridged, relaxed, +2 mm with a rolled 2 mm inner lip, matte dark grey, exact source-vertex skin weights.",
        "CLO_Underwear: welded (the GLB split every edge), subdivided once, conformed 1.5 mm above the skin and relaxed; skin under the gusset relaxed so the G8F detail no longer peeks out; barycentric skin weights.",
        "Skeleton: metahuman_base_skel appended from the fitting body (object 'root', names untouched); 278 twist/corrective/toe/helper bones deleted; 63 body bones kept.",
        "Joints fitted on her posed body: torso/neck/clavicle/hip joints mapped from MH fitting-body slices; limbs from geodesic level-set medial axes (wrist/ankle calibrated on the MH body, elbow/knee by bend fit or MH ratio); fingers from the finger branches with MH phalanx proportions and palm-frame knuckles; head joint and head frame from her ears and eyeballs; clavicle/thigh heads symmetrised; right leg re-placed with the left leg's lengths.",
        "Bone orientations: swing to the child joint + twist from secondary landmarks or inherited; Kabsch for pelvis/hand/foot/head; the 11 deg head turn spread over neck_01/neck_02/head; half of each wrist twist moved into the forearm.",
        "Weights: heat weights on a 0.3 mm-merged proxy (778 sub-0.1 mm nail-rim edges made the direct solve fail), region rules (no cross-side / arm-on-hip / leg-on-other-leg weights), one finger per vertex, fingers rebuilt from topological finger labels with crisp knuckle blends, nails rigid on the distal phalanx, toenails on the ball, palm/knuckle smoothing, normalised, pruned < 0.01, max 7 influences (mean 2.2).",
        "A-pose: skinned from the bind pose onto the MH rest orientations and applied as rest; symmetric limb lengths reached inside the joint blend zones; left sole flattened; soles at z=0; uniform scale 1.031 to 168 cm.",
        "Left hand (a curled fist in the source) replaced by the mirrored open right hand (topological mirror map, blended along the forearm, weights mirrored); crushed right foot replaced by the mirrored corrected left foot (blended over the ankle).",
        "Poke-through: skin under the garments sunk 3 mm (2 mm near garment edges); bandeau sides and the skin under them share a damped upper-arm weight so the band does not ride up with the arms.",
        "Deformation test (walk, run, squat, arms up, arms forward, T-pose, twist 45, head turn 60, fist) rendered front + side (+ fist close-ups) and inspected; fixed along the way: rubber/claw fingers, detached nails, shared fingertip detection, mirrored-hand wrist seam, head tilted back, feet rotated 90 deg, sawtooth bandeau, crotch poke-through, fragmented briefs, 2.4 cm arm-length asymmetry.",
        "FBX exported through the shared pipeline in centimetres and re-imported in a fresh Blender: 168.0 cm, 63 bones, names/parents identical to metahuman_base_skel, 7 max influences; 8 base-colour JPEGs in export/textures.",
        "FIX ROUND 1 (verifier) face weights: b2_rig_apose.rigid_face makes the Face/Lips/EyeSocket/Mouth skin and all skin within 2.5 cm of the teeth/eyes/lashes 100% head (like the HeadParts), blending into the old neck_01/neck_02 weights over 3 cm of geodesic distance below the jaw/chin line; ears + scalp above head joint + 1 cm blend over 4 cm (a short blend there crushed the side of the neck on a look over the shoulder). Eyelid-region head weight min " + str(dn["_static"]["eyelid_region_head_weight_min"]) + "; eyelid_region_max_dev_from_head_mm head_mild " + str(dn["head_mild"]["eyelid_region_max_dev_from_head_mm"]) + ", head_up " + str(dn["head_up"]["eyelid_region_max_dev_from_head_mm"]) + ", look_shoulder " + str(dn["look_shoulder"]["eyelid_region_max_dev_from_head_mm"]) + " (was 6.56).",
        "FIX ROUND 1 (verifier) bandeau right half: b2_rig_apose.rebuild_top_right re-cuts CLO_BasicTop's right half as the topological mirror of the clean left half (the old right half was cut in the asymmetric source pose). Each left vertex is copied onto the mirrored skin vertex with the same skin offset (her right breast sits ~2 cm higher, so the copy then slides along the skin to the left edge's height), the halves weld on the topological midline, the front is bridged again (cleavage + under-bust, convex-hull envelope) and relaxed, and the copies take the skin weights of the skin vertex under them (same damped upper-arm share at the sides). Upper edge left-minus-right (1 cm bins): front max " + str(max(abs(x) for k, x in dn["_static"]["top_upper_edge_L_minus_R_mm"].items() if k.startswith("front"))) + " mm, back max " + str(max(abs(x) for k, x in dn["_static"]["top_upper_edge_L_minus_R_mm"].items() if k.startswith("back"))) + " mm; A-pose skin through the top: " + str(sum(c for k, (c, m) in dn["apose"]["skin_through_by_region(count,max_mm)"].items() if "BasicTop" in k)) + " verts.",
        "FIX ROUND 1 (verifier) FBX textures: b2_rig_export.py re-points every image node of the export materials at its written export/textures/T_2B_*_D.jpg for the export only (restored afterwards, blend never saved), so the FBX references 'textures/T_2B_*_D.jpg' (was extension-less '../textures/packed/<name>', backslashes in the file); check_c1 fbx_tex_refs_exist_in_textures_dir: " + str(all(cc["fbx_tex_refs_exist_in_textures_dir"].values())) + " for all " + str(len(cc["fbx_tex_refs_exist_in_textures_dir"])) + "."],
    "issues": [
        "PRIVATE / DO NOT SHIP: DAZ Genesis 8 Female body and NieR-ripped parts.",
        "Both hands are mirror images of her right hand and both feet mirror images of her left foot (source left hand was a curled fist, right foot crushed by the boot).",
        "No twist/corrective bones: strong forearm pronation twists at the wrist; deep knee (125 deg) and elbow bends show normal linear-blend volume loss.",
        "No face bones: face static, mouth closed, eyes fixed.",
        "Bandeau: with the arms fully overhead the armpit skin can cut the band's top corners (small ragged edge).",
        "Her body is not symmetric in the A-pose (right breast ~2 cm higher and further forward, the torso's topological midline wanders from x = -14 to +26 mm; a leftover of the source pose, not changed here): the rebuilt right half of the bandeau follows her right breast, so the two cups are not mirror images even though the edges are level.",
        "Bandeau back edge at her right armpit corner (last 1 cm bin, |x| 11-12 cm): " + str(dn["_static"]["top_upper_edge_L_minus_R_mm"].get("back_11cm")) + " mm lower than the left, because her right band ends ~2 cm further in there; every other front/back bin is within ~2 mm.",
        "Rigid face: on the extreme look over the shoulder (head +25 deg yaw on top of 40 deg of neck) the skin just behind her left jaw angle compresses (" + str(dn["look_shoulder"]["tri_collapse_lt0.3"]) + " tris below 30% area there, was 15 spread elsewhere); not visible in the renders, but a neck twist bone or a corrective would be the proper fix.",
        "Pre-existing, not raised: one underwear/pelvis skin vertex reads as 8.2 mm through the briefs in the A-pose numbers (and the underwear leg openings poke in deep hip flexion, as before); the top has 0 at rest.",
        "Upper eyelash cards are opaque (source texture has no alpha): dark eyeliner-like band. Hair not part of this step (scalp keeps painted short hair).",
        "Cornea/EyeMoisture/Tear need translucent materials (or hide those sections) in UE, else the eyes render white.",
        "Her feet are long for 168 cm (ankle-to-ball ~20 cm, source proportion flattened from tiptoe); arch slightly stretched.",
        "Unreal import/retarget not done here by design; the retarget pose may need a small arm-angle tweak."],
    "unreal_import_notes": NOTES,
}
json.dump(report, open(OUT + "/stepC1_report.json", "w"), indent=1)
print("written", OUT + "/stepC1_report.json", len(renders))
