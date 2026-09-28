# run_blackcloak_regression.ps1 -- the garment pipeline's regression: BlackCloak through refit + build, compared with the
# 2026-09-26 one-off MetaHuman fit (DemoGame_1 commit 43fd6ce). Needs the BlackCloak lock:
#   py Scripts/pipeline/lock.py claim BlackCloak --agent claude --blend Assets/BlackCloak.blend
# Never touches Assets/BlackCloak.blend (it is copied) or DemoGame_1 (its FBX files are only read).
# Outputs in WorkFiles/garment_pipeline/BlackCloak/: the sculpt copy, the work file, export/, regress_fit.json, regress_fbx.json.
param([string]$Agent = "claude")
$ErrorActionPreference = "Stop"
$Root = "C:/Users/Cody/Desktop/Blender_Projects"
$B = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
$W = "$Root/WorkFiles/garment_pipeline/BlackCloak"
$OneOffFit = "$Root/WorkFiles/BlackCloak_MH/BlackCloak_MH_fit.blend"
$OneOffFbx = "C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Saved/Claude/Blender/SKM_BlackCloak_MH.fbx"
$Waiver = "character_triangle_budget=regression of the in-game one-off; the base alone (121,892) is over 120k - pending Cody's budget decision"
New-Item -ItemType Directory -Force $W | Out-Null
foreach ($generated in @("$W/BlackCloak_MH_garment.blend", "$W/BlackCloak_MH_garment.blend.refit.json", "$W/export")) {
    if (Test-Path $generated) { Remove-Item -Recurse -Force $generated }
}
Copy-Item "$Root/Assets/BlackCloak.blend" "$W/BlackCloak_sculpt_copy.blend" -Force
& $B -b "$W/BlackCloak_sculpt_copy.blend" --factory-startup --python "$Root/Scripts/garments/refit_garment.py" -- --recipe "$Root/Scripts/garments/recipes/BlackCloak.json" --out "$W/BlackCloak_MH_garment.blend" --agent $Agent 2>&1 | Select-String "REFIT_"
& $B -b "$W/BlackCloak_MH_garment.blend" --factory-startup --python "$Root/Scripts/garments/regress_blackcloak.py" -- --stage fit --oneoff $OneOffFit --json "$W/regress_fit.json" 2>&1 | Select-String "REGRESS_"
& $B -b "$W/BlackCloak_MH_garment.blend" --factory-startup --python "$Root/Scripts/garments/build_garment.py" -- --out "$W/export/SK_BlackCloak_MH.fbx" --agent $Agent --waive $Waiver 2>&1 | Select-String "BUILD_GARMENT"
& $B -b --factory-startup --python "$Root/Scripts/garments/regress_blackcloak.py" -- --stage fbx --oneoff $OneOffFbx --pipeline "$W/export/SK_BlackCloak_MH.fbx" --json "$W/regress_fbx.json" 2>&1 | Select-String "REGRESS_"
$fit = Get-Content "$W/regress_fit.json" -Raw | ConvertFrom-Json
$fbx = Get-Content "$W/regress_fbx.json" -Raw | ConvertFrom-Json
"fit: max {0} mm, vertices over 0.01 mm {1}" -f $fit.all.max, $fit.all.'over_0.01mm'
"fbx: vertices {0}, triangles {1}, within 0.01 mm {2}, hausdorff {3} mm, weights max diff {4}, bones same {5}" -f `
    ($fbx.mesh.vertices -join "/"), ($fbx.mesh.triangles -join "/"), $fbx.'matched_vertices_within_0.01mm', $fbx.mesh.hausdorff_mm, `
    $fbx.weights.max_abs_diff_at_matched, $fbx.skeleton.same_names
