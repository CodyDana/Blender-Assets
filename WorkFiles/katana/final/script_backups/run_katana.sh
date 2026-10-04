#!/usr/bin/env bash
# Basic katana: rebuild from nothing -> export -> measure the exported bytes -> renders (game blend + exported FBX)
# -> design compare. One Blender process per step, absolute paths. Usage: run_katana.sh [build stages...]
set -e
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S="$ROOT/Scripts/Katana"
LOG="$ROOT/WorkFiles/katana/build/logs"
R="$ROOT/Renders/Katana"
mkdir -p "$LOG" "$R"
for st in ${@:-geo ao maps game export}; do
  "$B" -b --factory-startup --python "$S/build_katana.py" -- --stage $st > "$LOG/$st.log" 2>&1
  grep -E "\[KAT\]" "$LOG/$st.log" | cut -c1-400 | tail -2
  if grep -q "Traceback" "$LOG/$st.log"; then echo "FAILED $st"; grep -A15 Traceback "$LOG/$st.log" | head -30; exit 1; fi
done
"$B" -b --factory-startup --python "$S/katana_measure.py" > "$LOG/measure.log" 2>&1
grep -q KAT_MEASURE "$LOG/measure.log" || { echo "measure FAILED"; exit 1; }
"$B" -b "$ROOT/Assets/Katana/Katana.blend" --factory-startup --python "$S/katana_render.py" -- --set fbx --out "$R" --samples 96 > "$LOG/render_fbx.log" 2>&1
"$B" -b "$ROOT/Assets/Katana/Katana.blend" --factory-startup --python "$S/katana_render.py" -- --set gallery --out "$R" --samples 128 > "$LOG/render_gallery.log" 2>&1
grep -q KAT_RENDER_DONE "$LOG/render_gallery.log" || { echo "gallery FAILED"; exit 1; }
"$B" -b --factory-startup --python "$S/katana_compare.py" > "$LOG/compare.log" 2>&1
grep KAT_COMPARE "$LOG/compare.log" | cut -c1-600
echo ALL_DONE
