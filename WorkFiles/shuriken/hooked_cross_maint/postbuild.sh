#!/usr/bin/env bash
# Hooked-cross maintenance (library 3.9.1): every check that runs on the finished build, in order.  READ ONLY on the
# build outputs (Assets / Exports / Renders are only read; the .blend is opened from a scratch copy).
#   bash WorkFiles/shuriken/hooked_cross_maint/postbuild.sh <scratch_dir>
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
BPY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
M="$PROJ/WorkFiles/shuriken/hooked_cross_maint"
S="${1:?scratch dir}"
mkdir -p "$S"
cd "$PROJ"
FORMS6=four_point,eight_point,square_plate,six_point,spike,hooked_cross
echo "== regression: the five frozen forms against post_spike_maint"
"$B" -b --factory-startup --python-exit-code 3 --python WorkFiles/shuriken/regression/compare_frozen.py -- \
  --snapshot post_spike_maint --forms four_point,eight_point,square_plate,six_point,spike \
  --out regression_hooked_cross_maint_frozen.json > "$M/regression_frozen.log" 2>&1
echo "exit $?"; grep -E "PASSED|FAILED|passed|Traceback" "$M/regression_frozen.log" | tail -3
echo "== plan silhouettes (the frozen forms' refs + the hooked cross's own un-ground outline)"
"$B" -b --factory-startup --python WorkFiles/shuriken/hooked_cross/silhouette_ref.py -- "$M/silhouette_ref" > "$M/silhouette_ref.log" 2>&1
cp Assets/Shuriken.blend "$S/shipped_3_9_1.blend"
"$B" -b "$S/shipped_3_9_1.blend" --factory-startup --python WorkFiles/shuriken/restyle_pass2/silhouette_check.py -- \
  "$M/silhouette_ref" "$M/silhouette.json" > "$M/silhouette.log" 2>&1
grep -E "all_unchanged|Traceback" "$M/silhouette.log" | tail -2
echo "== texture-sheet gate on the shipped 3.9.1 blend (and it was run on the 3.9.0 blend before the build)"
"$B" -b "$S/shipped_3_9_1.blend" --factory-startup --python "$M/texture_gate_on_blend.py" -- "$M/texture_gate_on_3_9_1_blend.json" 2>&1 | grep -E "TEXTURE_GATE|Traceback"
echo "== visual + coat metrics"
"$BPY" WorkFiles/shuriken/restyle_pass2/maint/visual_metrics.py Renders/Shuriken WorkFiles/shuriken/diag --out "$M/visual_metrics.json" --forms $FORMS6 > "$M/visual_metrics.txt" 2>&1
"$BPY" WorkFiles/shuriken/spike/coat_interior_metrics.py Renders/Shuriken WorkFiles/shuriken/diag "$M/coat_interior_metrics.json" $FORMS6 > "$M/coat_interior_metrics.txt" 2>&1
tail -2 "$M/visual_metrics.txt"
echo "== sheets"
py -3 Scripts/shuriken/line_sheet.py > "$M/line_sheet.log" 2>&1; tail -1 "$M/line_sheet.log" | cut -c1-200
"$B" -b --factory-startup --python "$M/style_sheet.py" -- --out "$PROJ/Renders/Shuriken/style_comparison.png" \
  --metrics "$M/visual_metrics.json" --silhouette "$M/silhouette.json" --coat "$M/coat_interior_metrics.json" > "$M/style_sheet.log" 2>&1
grep -E "SHEET|Traceback" "$M/style_sheet.log"
echo "== grind extent evidence: A (the shipped build) and B (the rejected photo-length variant), same code"
"$B" -b --factory-startup --python WorkFiles/shuriken/hooked_cross/grind_extent_compare.py -- build-b "$S/variant_b.blend" > "$M/grind_extent_b.log" 2>&1
mkdir -p "$M/grind_extent"
"$B" -b "$S/shipped_3_9_1.blend" --factory-startup --python WorkFiles/shuriken/hooked_cross/grind_extent_compare.py -- closeup "$M/grind_extent/A" > "$M/grind_extent_a_render.log" 2>&1
"$B" -b "$S/variant_b.blend" --factory-startup --python WorkFiles/shuriken/hooked_cross/grind_extent_compare.py -- closeup "$M/grind_extent/B" > "$M/grind_extent_b_render.log" 2>&1
py -3 WorkFiles/shuriken/hooked_cross/grind_extent_compare.py sheet "$M/grind_extent/A" "$M/grind_extent/B" "$PROJ/WorkFiles/shuriken/hooked_cross/grind_extent_compare.png"
echo "== before / after evidence"
py -3 "$M/evidence_sheets.py" "$M/before/renders" "$M/before/textures" | cut -c1-400
echo "== done"
