#!/usr/bin/env bash
# DojoLab SHOWCASE Unreal steps, ONE Unreal process at a time machine-wide, each step its own fresh process.
#   run_showcase_unreal.sh [steps...]      default: prep import materials level verify capture
# steps:
#   prep        plain Python: Scripts/dojo/showcase/apply_round2.py on layout_showcase.json (round-2 marker fixes +
#               the 5500 K sun; idempotent, a no-op on a layout composed by the current compose_showcase.py), then
#               apply_look_r3.py (round 3: the look-pass instance values of showcase/look_r3.py; idempotent)
#   import      commandlet -nullrhi: kit 1, ground, props, drum-less pavilion -> /Game/DojoKit/<Kit>/{Meshes,Textures}
#   materials   commandlet -nullrhi: M_DJ_* masters + one MI per slot, assigned by slot name
#   level       commandlet -nullrhi: L_Dojo re-assembled from showcase/layout_showcase.json + bounds gate
#   verify      commandlet -nullrhi, FRESH process: every gate again on what was saved
#   perf        commandlet -nullrhi, read-only: actors, draw-call estimate, triangles, texture memory, cvars (round 5)
#   capture     offscreen editor (D3D12, -RenderOffscreen), tick-driven stills of the showcase cameras
# Guard (house rule): before every Unreal step, if an UnrealEditor.exe has DojoLab.uproject open, STOP (exit 3).
# Never touches another project, UnrealEditor.exe, or another session's UnrealEditor-Cmd (waits while one runs).
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-prep import materials level verify capture}"
HERE="C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/unreal/showcase"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
mkdir -p "$OUT/logs"
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
stamp() { echo "$(date '+%F %T') $*" | tee -a "$OUT/logs/timings.txt"; }
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 4)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours to touch)"
    n=$((n + 1)); sleep 15
  done
}
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then
    echo "STOP: the DojoLab editor is open (UnrealEditor.exe pid $hit). Close it, then re-run. Nothing was written."
    stamp "STOP editor open pid $hit"
    exit 3
  fi
}
for step in $STEPS; do
  t0=$(date +%s)
  case "$step" in
    prep)
      stamp "start sc_prep"
      py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/showcase/apply_round2.py" > "$OUT/logs/prep.log" 2>&1; code=$?
      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/showcase/apply_look_r3.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      # landscape round (2026-09-30): the town removal / hidden grey-box trees / new cameras (idempotent)
      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/apply_landscape.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      # hall + armory round (2026-10-01): the camera moves / new cameras / retired dead BR routes (idempotent; runs last)
      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/hall/apply_hall_armory.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      grep -q "^ROUND2 " "$OUT/logs/prep.log" && grep -q "^LOOK_R3 " "$OUT/logs/prep.log" && grep -q "^LANDSCAPE_PREP " "$OUT/logs/prep.log" && grep -q "^HALL_ARMORY_PREP " "$OUT/logs/prep.log" || { [ $code -eq 0 ] && code=8; } ;;
    import|materials|level|verify|perf)
      editor_guard
      wait_free
      editor_guard
      stamp "start sc_$step"
      timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$HERE/dj_sc_$step.py" $NULL_FLAGS $DPC > "$OUT/logs/$step.log" 2>&1; code=$?
      grep -q "DJ_STEP_DONE sc_$step passed=True" "$OUT/logs/$step.log" || { [ $code -eq 0 ] && code=8; } ;;
    capture)
      editor_guard
      wait_free
      stamp "start sc_capture"
      powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$HERE/run_sc_capture.ps1" 2>/dev/null || echo "$HERE/run_sc_capture.ps1")" > "$OUT/logs/capture_runner.log" 2>&1; code=$?
      grep -q "DJ_STEP_DONE sc_capture passed=True" "$OUT/logs/capture.log" 2>/dev/null || { [ $code -eq 0 ] && code=8; } ;;
    *) echo "unknown step $step"; exit 2 ;;
  esac
  t1=$(date +%s)
  stamp "sc_$step exit $code in $((t1 - t0)) s | $(grep -o 'DJ_STEP_DONE.*' "$OUT/logs/$step.log" 2>/dev/null | head -1)"
  echo "    errors: $(grep -c 'Error:' "$OUT/logs/$step.log" 2>/dev/null)  warnings: $(grep -c 'Warning:' "$OUT/logs/$step.log" 2>/dev/null)"
  if [ $code -ne 0 ]; then echo "STOP: $step failed (exit $code), see $OUT/logs/$step.log"; exit 1; fi
done
echo "=== done $(date +%T)"
