#!/usr/bin/env bash
# After build_pack.py: the reference through the pack rig, the STYLE_TARGET metrics on the reference
# and on every form's baked maps (same script, same kernels), the outline regression against the
# pre-restyle backup, and the comparison sheet.  Headless Blender throughout.
#
#   bash WorkFiles/shuriken/style_reference/run_metrics_and_sheet.sh
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$PROJ/WorkFiles/shuriken/style_reference"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd "$PROJ"
echo "== reference through the pack rig"
"$BLENDER" -b --factory-startup --python "$HERE/ref_on_rig.py" -- --samples 220 2>&1 | grep -E "^REFRIG|Traceback|Error:" | grep -v HIPEW
echo "== metrics: reference"
"$BLENDER" -b --factory-startup --python "$HERE/style_metrics.py" -- --reference "$PROJ/References/Shuriken/style_reference" --out "$HERE/metrics_reference.json" 2>&1 | grep -E "^STYLE_METRICS |Traceback|Error:"
for pair in "four_point:SM_Shuriken_FourPoint" "eight_point:SM_Shuriken_EightPoint" "square_plate:SM_Shuriken_SquarePlate"; do
  form="${pair%%:*}"; mesh="${pair##*:}"
  echo "== metrics: $form"
  "$BLENDER" -b --factory-startup --python "$HERE/style_metrics.py" -- --blend "$PROJ/Assets/Shuriken.blend" --mesh "${mesh}_LOD0" \
      --textures "$PROJ/Exports/Shuriken/Textures" --stem "T_${mesh#SM_}" --out "$HERE/metrics_${form}.json" 2>&1 | grep -E "^STYLE_METRICS |Traceback|Error:"
done
echo "== outline regression vs the pre-restyle backup"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$PROJ/WorkFiles/shuriken/regression/compare_outline_restyle.py" 2>&1 | grep -E "^\[outline\]|OUTLINE_REGRESSION|Traceback|Error:"
echo "== comparison sheet"
"$BLENDER" -b --factory-startup --python "$HERE/style_sheet.py" -- --out "$PROJ/Renders/Shuriken/style_comparison.png" \
    --ref-hero "$HERE/ref_rig_scaled100_persp.png" --ref-top "$HERE/ref_rig_scaled100_top.png" \
    --ref-metrics "$HERE/metrics_reference.json" --ref-stats "$HERE/ref_rig_stats.json" --ref-tag scaled100 \
    --form four_point "$PROJ/Renders/Shuriken/four_point_persp.png" "$PROJ/Renders/Shuriken/four_point_top.png" "$HERE/metrics_four_point.json" "$PROJ/WorkFiles/shuriken/four_point_report.json" \
    --form eight_point "$PROJ/Renders/Shuriken/eight_point_persp.png" "$PROJ/Renders/Shuriken/eight_point_top.png" "$HERE/metrics_eight_point.json" "$PROJ/WorkFiles/shuriken/eight_point_report.json" \
    --form square_plate "$PROJ/Renders/Shuriken/square_plate_persp.png" "$PROJ/Renders/Shuriken/square_plate_top.png" "$HERE/metrics_square_plate.json" "$PROJ/WorkFiles/shuriken/square_plate_report.json" \
    2>&1 | grep -E "^STYLE_SHEET|Traceback|Error:"
echo "== done"
