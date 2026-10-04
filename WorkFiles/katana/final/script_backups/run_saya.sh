#!/usr/bin/env bash
# Saya (SM_Katana_Saya): rebuild from the shipped katana -> export -> verify + measure the exported bytes -> renders
# -> design compare. One Blender process per step, absolute paths. Usage: run_saya.sh [build stages...]
set -e
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S="$ROOT/Scripts/Katana"
LOG="$ROOT/WorkFiles/katana/saya_build/logs"
R="$ROOT/Renders/Katana"
mkdir -p "$LOG" "$R"
for st in ${@:-fit geo ao maps game export}; do
  "$B" -b --factory-startup --python "$S/build_saya.py" -- --stage $st > "$LOG/$st.log" 2>&1
  grep -E "\[SAYA" "$LOG/$st.log" | cut -c1-400 | tail -2
  if grep -q "Traceback" "$LOG/$st.log"; then echo "FAILED $st"; grep -A15 Traceback "$LOG/$st.log" | head -30; exit 1; fi
done
"$B" -b --factory-startup --python "$S/saya_verify.py" > "$LOG/verify.log" 2>&1
grep -E "SAYA-VERIFY\] (PASS|FAIL)" "$LOG/verify.log"
"$B" -b --factory-startup --python "$S/saya_render.py" -- --set all > "$LOG/render.log" 2>&1
grep -q SAYA_RENDER_DONE "$LOG/render.log" || { echo "render FAILED"; exit 1; }
"$B" -b --factory-startup --python "$S/saya_compare.py" > "$LOG/compare.log" 2>&1
grep SAYA_COMPARE "$LOG/compare.log" | cut -c1-600
echo ALL_DONE
