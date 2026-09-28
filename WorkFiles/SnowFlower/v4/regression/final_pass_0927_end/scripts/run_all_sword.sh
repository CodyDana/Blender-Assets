#!/usr/bin/env bash
# Snow Flower v4 sword: build (geo bake maps game export) -> renders from the shipped game blend AND the shipped
# FBX -> comparisons with the reference sheet -> sheath envelope. One Blender process per step, absolute paths.
set -e
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
PY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
V4="$ROOT/Scripts/SnowFlower/v4"
R="$ROOT/WorkFiles/SnowFlower/v4/sword_build/renders"
LOG="$ROOT/WorkFiles/SnowFlower/v4/sword_build/logs"
mkdir -p "$R" "$LOG"
bash "$V4/run_sword_build.sh" ${BUILD_STAGES:-geo bake maps game export}
for st in refviews details gallery; do
  "$B" -b "$ROOT/Assets/SnowFlower/SnowFlower_Game_v4.blend" --factory-startup --python "$V4/sfv4_render.py" -- --set $st --out "$R" > "$LOG/render_$st.log" 2>&1
  grep -q "SF4_RENDER_DONE" "$LOG/render_$st.log" || { echo "render $st FAILED"; exit 1; }
done
"$B" -b --factory-startup --python "$V4/sfv4_render.py" -- --set fbx --out "$R" > "$LOG/render_fbx.log" 2>&1
"$B" -b --factory-startup --python "$V4/sfv4_compare.py" -- --renders "$R" --out "$R" > "$LOG/compare.log" 2>&1
"$B" -b --factory-startup --python "$V4/sfv4_compare.py" -- --renders "$R" --out "$R" --prefix fbx > "$LOG/compare_fbx.log" 2>&1
"$B" -b --factory-startup --python "$V4/sfv4_compare_hilt.py" -- "$R" "$R/compare_hilt_3x.png" > "$LOG/compare_hilt.log" 2>&1
"$B" -b --factory-startup --python "$V4/sfv4_compare_details.py" -- "$R" > "$LOG/compare_details.log" 2>&1
"$B" -b --factory-startup --python "$V4/sfv4_envelope.py" > "$LOG/envelope.log" 2>&1
"$PY" "$ROOT/WorkFiles/SnowFlower/v4/sword_fit/v4_sheath_fit_check.py" 97 > "$LOG/fit97.log" 2>&1
"$PY" "$ROOT/WorkFiles/SnowFlower/v4/sword_fit/v4_sheath_fit_check.py" 115 > "$LOG/fit115.log" 2>&1
grep -h "SF4_COMPARE" "$LOG/compare.log" "$LOG/compare_fbx.log"
grep -h "SF4_ENVELOPE" "$LOG/envelope.log" | cut -c1-300
echo ALL_DONE
