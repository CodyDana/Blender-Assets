#!/usr/bin/env bash
# Snow Flower sheath: build (fit geo bake maps game export) -> fit verification on the EXPORTED bytes of both assets
# -> renders from the shipped maps -> comparison with the reference -> deliverables in Renders/SnowFlower/v4/.
# One Blender process per step, absolute paths only.   Usage: run_sheath_all.sh   (STAGES="..." to limit the build)
set -e
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
V4="$ROOT/Scripts/SnowFlower/v4"
W="$ROOT/WorkFiles/SnowFlower/v4/sheath_build"
LOG="$W/logs"
RR="$W/renders"
OUT="$ROOT/Renders/SnowFlower/v4"
mkdir -p "$LOG" "$RR" "$OUT"
for st in ${STAGES:-fit geo bake maps game export}; do
  "$B" -b --factory-startup --python "$V4/build_sheath.py" -- --stage $st > "$LOG/$st.log" 2>&1 || true
  grep -E "\[SH4" "$LOG/$st.log" | tail -3 | cut -c1-400
  if grep -q "Traceback" "$LOG/$st.log" || ! grep -q "stage $st finished" "$LOG/$st.log"; then
    echo "FAILED $st"; grep -A20 Traceback "$LOG/$st.log" | head -30; exit 1; fi
done
if [ -z "${SKIP_POST:-}" ]; then
  "$B" -b --factory-startup --python "$V4/shv4_verify.py" -- --mode shipped --out "$W/fit_verify.json" > "$LOG/verify.log" 2>&1
  grep -E "SH4-VERIFY\] (PASS|FAIL)" "$LOG/verify.log" || { echo "verify FAILED to run"; tail -20 "$LOG/verify.log"; exit 1; }
  for s in refview details fit sections gallery; do
    "$B" -b --factory-startup --python "$V4/shv4_render.py" -- --set $s --out "$RR" > "$LOG/render_$s.log" 2>&1
    grep -q "SH4_RENDER_DONE" "$LOG/render_$s.log" || { echo "render $s FAILED"; grep -A15 Traceback "$LOG/render_$s.log" | head -20; exit 1; }
  done
  "$B" -b --factory-startup --python "$V4/shv4_compare.py" -- --renders "$RR" --out "$OUT" > "$LOG/compare.log" 2>&1
  grep -q "SH4_COMPARE" "$LOG/compare.log" || { echo "compare FAILED"; grep -A15 Traceback "$LOG/compare.log" | head -20; exit 1; }
  cp "$W/fit_verify.json" "$OUT/SnowFlower_Sheath_fit_verify.json"
  for f in ref_front ref_back ref_side persp_throat persp_band persp_chape fit_front fit_side fit_hero fit_cutaway_full \
           fit_cutaway_mouth fit_cutaway_tip fit_cutaway_mouth_persp fit_sections hero back_hero wire lod_strip; do
    cp "$RR/$f.png" "$OUT/SnowFlower_Sheath_$f.png"
  done
  cp "$RR/fit_sections.json" "$OUT/SnowFlower_Sheath_fit_sections.json"
fi
echo ALL_DONE
