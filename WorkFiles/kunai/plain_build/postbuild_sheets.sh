#!/usr/bin/env bash
# Plain kunai (library 3.10): the gallery sheets and the lettering proof, regenerated from the FINAL build's renders and
# blend.  READ ONLY on Assets / Exports (the lettering proof opens the shipped blend and never saves it); it writes
# Renders/Shuriken/modern_line_sheet.png, Renders/Shuriken/style_comparison.png and WorkFiles/kunai/**.
#   bash WorkFiles/kunai/plain_build/postbuild_sheets.sh
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
BPY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
M="$PROJ/WorkFiles/kunai/plain_build"
L="$PROJ/WorkFiles/kunai/lettering_test"
cd "$PROJ"
FORMS6=four_point,eight_point,square_plate,six_point,spike,hooked_cross
echo "== visual + coat metrics (the six frozen forms; the kunai's own numbers come from its build report)"
"$BPY" WorkFiles/shuriken/restyle_pass2/maint/visual_metrics.py Renders/Shuriken WorkFiles/shuriken/diag --out "$M/visual_metrics.json" --forms $FORMS6 > "$M/visual_metrics.txt" 2>&1
echo "exit $?"
"$BPY" WorkFiles/shuriken/spike/coat_interior_metrics.py Renders/Shuriken WorkFiles/shuriken/diag "$M/coat_interior_metrics.json" $FORMS6 > "$M/coat_interior_metrics.txt" 2>&1
echo "exit $?"
echo "== line sheet"
py -3 Scripts/shuriken/line_sheet.py > "$M/line_sheet.log" 2>&1; echo "exit $?"; tail -1 "$M/line_sheet.log" | cut -c1-200
echo "== style comparison (plan silhouettes of the frozen forms: hooked_cross_maint/silhouette.json - unchanged forms)"
"$B" -b --factory-startup --python "$M/style_sheet.py" -- --out "$PROJ/Renders/Shuriken/style_comparison.png" \
  --metrics "$M/visual_metrics.json" --silhouette "$PROJ/WorkFiles/shuriken/hooked_cross_maint/silhouette.json" \
  --coat "$M/coat_interior_metrics.json" > "$M/style_sheet.log" 2>&1
echo "exit $?"; grep -E "Saved|Traceback" "$M/style_sheet.log"
echo "== lettering proof (neutral test mask, never shipped)"
"$B" -b "$PROJ/Assets/Shuriken.blend" --factory-startup --python "$L/lettering_test_render.py" > "$L/lettering_test_render.log" 2>&1
echo "exit $?"; grep -cE "Saved" "$L/lettering_test_render.log"
py -3 "$L/compose_sheet.py"
echo "== done"
