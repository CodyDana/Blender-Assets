"""b2_report.py - PRIVATE / DO NOT SHIP. Writes WorkFiles/Characters/2B_private/stepA_report.json (py -3)."""
import json

W = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/"
d = json.load(open(W + "stepA_build_analysis.json"))
bi = d["body_integrity"]; u = d["unsubdiv"]; ex = u["exact_topological"]
R = W + "renders/"
renders = [R + n + ".png" for n in [
    "full_front", "full_tq", "full_side", "full_back", "body_front", "body_tq", "body_side", "body_back",
    "clothing_front", "clothing_tq", "clothing_side", "hair_front", "hair_tq", "hair_side",
    "face_front_close", "face_front_close_nohair", "face_tq_close", "face_side_close", "unsubdiv_wire",
    "diag_feet_close", "stepA_sheet"]]
f = d["feet"]
lines = []
for k, v in u.items():
    if k == "exact_topological":
        continue
    lines.append(f"{k[:14]}: {v['orig_verts']}v -> x1 {v['unsub1']['verts']} ({v['unsub1']['quad_fraction']*100:.0f}% quads), "
                 f"x2 {v['unsub2']['verts']} ({v['unsub2']['quad_fraction']*100:.0f}% quads, {v['unsub2']['poly_sizes'].get('3', 0)} tris), "
                 f"x4 {v['unsub4']['verts']} ({v['unsub4']['quad_fraction']*100:.0f}% quads)")
e0 = ex["exact2_resubdiv_limit0"]
unsub = ("The source is 100% triangles, but each quad is stored as 2 consecutive tris (100% pairing on every body surface), so the exact quads were recovered. "
         "Blender Decimate UNSUBDIV counts HALF levels. x1 is the diamond half-step (~0.50 vert ratio, 94-97% quads, fine). x2 undoes one Catmull-Clark level "
         "(ratio 0.26-0.28 vs 0.25 expected) but gives only 71-84% quads, with triangle fans and seams, so it is NOT clean. x4 is worse (30-44% quads). "
         + " | ".join(lines)
         + f" | BEST = my exact topological un-subdivide (b2_import_split.topo_unsub_level) of the welded skin shell: {ex['exact1']['verts']}v at L1 and "
         f"{ex['exact2']['verts']}v/{ex['exact2']['faces']} faces at L0. 100% quads, 0 non-manifold, all 1156 poles classed as original verts. "
         f"Subsurf L2 (limit surface off) on L0 reproduces the GLB skin within mean {e0['mean_mm']} mm, p95 {e0['p95_mm']} mm, max {e0['max_mm']} mm, "
         "so the GLB body is DAZ G8F at SubD level 2 and the base cage can be recovered. Test objects are in the hidden collection Test_Unsubdiv: "
         "TEST_<part>_quads/_unsub1/_unsub2/_unsub4, TEST_SkinShell_quads/_unsub*, TEST_SkinShell_exact1/_exact2.")
openb = ("Per object (after the exact weld): " + ", ".join(f"{k} {v['open_loops']}" for k, v in bi["per_object"].items() if k.startswith("BODY"))
         + ". These are all DAZ surface seams (e.g. Body 5 = neck + 2 arm + 2 leg borders; Face 4 = head border, lips, 2 eye sockets), "
         "separate teeth pieces (32) and lash cards (19). Welded skin shell (" + "+".join(bi["shell_surfaces"]) + f"): {bi['shell_open_loops']} open loops, "
         f"{bi['shell_nonmanifold_edges']} non-manifold edges. It is CLOSED: no holes or deleted regions under the clothes.")
issues = [
    "Classification checked in renders: 7_-mask.face_eyeslashes = NieR eyelash cards (upper black lash + lower lash plane), kept as BODY_Eyelashes; "
    "24_+mask.outfit_b = blindfold (CLO_Blindfold); 24_outfit_a_1.2_0_0 (head piece) = black hairband with bow (CLO_Headband); boots and underwear were as guessed. "
    "None of the guesses was wrong.",
    "The import splits vertices along nearly every edge (glTF merge_vertices only merged 575584->567878). BODY objects were welded on EXACT duplicates only "
    "(find_doubles 1e-9 m, never collapsing an edge). Tris are unchanged; verts drop, e.g. BODY_Body 62467->39753. A 1e-5 m weld would have deleted 303 real faces "
    "(3-micron nail/toe edges), so I didn't use one. Hair and clothing are left as imported.",
    "Material fix: Cornea/EyeMoisture/Tear import at alpha 0.995 (BLEND), which renders the eyes solid white. I set them to alpha 0.12/0.05/0.05 with low roughness. "
    "The originals are stored in the material custom props b2_src_alpha/b2_src_roughness, with the change in b2_fix. No other material edits. "
    "All 9 images are packed into the .blend, and every render came from reopening the saved file (no pink textures).",
    "All textures are opaque JPEGs (no alpha). So the hair renders as solid cards with jagged ends, and the lower eyelash card shows as a grey slab under each eye. "
    "Fixing that needs alpha masks the source pack doesn't include.",
    "BODY renders: 2B_Underware is bottoms only, so the chest would be bare. The body_* and face renders add a render-only dark bandeau "
    "(RIG_ModestyBand, made at render time from BODY_Body faces z 1.21-1.36 offset 4 mm). It is NOT saved in the .blend. "
    "The wire torso panel is shot from behind with CLO_Underwear visible.",
    f"Skin self-intersections: {bi['self_intersection_faces']} faces. The biggest by far is the RIGHT foot: heel and toes crushed inside the boot (~1760 faces). "
    "Then the lips (closed mouth, normal), the right armpit/back of shoulder (~170, arm pressed into the torso), the crotch (~140) and the left fingers (~130).",
    "Crush check (3D area / UV area vs its UV-island median, <0.30 flagged): the right foot is strongly compressed (Legs ~1650 faces at 0.16-0.25, "
    "2-11 mm from the boot), so that is boot crush. The fingers of both hands are compressed by the relaxed curl (a joint, not clothing). "
    "Mild compression at the crotch/hip crease and the right armpit. Nothing crushed under the belt, kimono or underwear. "
    "The Face/Ears 'stretched' flags are texel-density differences in the eye/ear UV islands, not geometry.",
    "Blender Decimate UNSUBDIV doesn't give clean quads at one full level (x2 = 71-84% quads), so I wrote an exact topological un-subdivide "
    "(see unsubdivide). That is the recommended route to a clean G8F-like base cage.",
    f"The head is turned about 11 deg relative to the torso (eye axis {d['orient']['eye_axis_deg']} deg vs torso {d['orient']['torso_axis_deg']} deg). "
    f"Facing comes from the torso axis (yaw {d['orient']['applied_yaw_deg']} deg), centred on the torso bbox X/Y. "
    "The pose is asymmetric: left foot on tiptoe, arms relaxed and flared.",
    "The kimono sleeves are wind-blown and wide (clothing X -0.77..0.85 m, trailing to y +0.65 m), so the character looks small in the full-body frames. "
    "Hair renders get their own framing; full/body/clothing share one camera per view so they overlay.",
    "The .blend is 102 MB (packed 4k JPEGs plus the Test_Unsubdiv meshes). Blender's automatic .blend1 backup, made by my own re-save in this run, was removed.",
    "PRIVATE / DO NOT SHIP: DAZ G8F body, NieR-ripped hair/outfit, Square Enix character. All outputs stay inside WorkFiles/Characters/2B_private.",
]
objs = [{"name": r["name"], "layer": r["layer"], "materials": r["materials"], "tris": r["tris"]} for r in d["objects"]]
rep = {
    "status": "ok", "blend_path": d["blend"], "objects": objs, "total_tris": d["total_tris"], "source_tris": 636666,
    "scale_factor": d["scale"]["scale_factor"],
    "body_height_cm": round(100 * (d["scale"]["skin_zmax"] - d["scale"]["skin_zmin"]), 3),
    "facing_note": f"The importer already gives Z-up (node quaternion converted). Rotated {d['orient']['applied_yaw_deg']} deg about Z using the torso PCA axis. "
                   "The face points -Y (checked: Face centroid y < Head centroid y, no 180 flip). Centred on the torso bbox X/Y. "
                   "Confirmed in the full_front/body_front renders. All transforms applied (every object at identity).",
    "outfit_floor_note": f"Boots' lowest point is at z=0. The bare body's lowest skin point is z={d['scale']['skin_zmin']:.4f} m (right toes). "
                         f"The feet are posed for heels: L(+X) toe {f['L(+X)']['toe_region_lowest_z']} m, heel {f['L(+X)']['heel_region_lowest_z']} m (on tiptoe); "
                         f"R(-X) toe {f['R(-X)']['toe_region_lowest_z']} m, heel {f['R(-X)']['heel_region_lowest_z']} m (heel partly crushed into the boot). "
                         f"Top of scalp z={d['scale']['skin_zmax']:.4f} m, so skin height is exactly 1.68 m. Hair top 1.7035 m, headband top 1.6912 m.",
    "body_open_boundaries": openb, "unsubdivide": unsub,
    "renders": renders, "contact_sheet": R + "stepA_sheet.png",
    "scripts": ["C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters/b2_import_split.py",
                "C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters/b2_sheets.py",
                "C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters/b2_report.py",
                "C:/Users/Cody/Desktop/Blender_Projects/Scripts/Characters/b2_inspect.py"],
    "issues": issues,
    "details": d,
}
json.dump(rep, open(W + "stepA_report.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "details"}))
