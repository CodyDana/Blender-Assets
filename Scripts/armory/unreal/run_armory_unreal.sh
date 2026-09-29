#!/usr/bin/env bash
# ArmoryLab Unreal assembly (lean build), ONE Unreal process at a time machine-wide, each step its own fresh process.
#   run_armory_unreal.sh [steps...]     default: project bounds import materials level verify manny character walk capture stats
# steps:
#   project    (no Unreal) write/refresh the ArmoryLab .uproject + Config from DemoGame_1's render settings (read-only)
#   bounds     (Blender -b) dump the Blender AABBs + slot names the gates compare against
#   import     commandlet -nullrhi: meshes + textures into /Game/ArmoryKit
#   materials  commandlet -nullrhi: masters + one MI per Blender slot name, assigned by slot name
#   level      commandlet -nullrhi: /Game/Armory/Maps/L_Armory from layout.json + the Blender->UE bounds gate, saved
#   verify     commandlet -nullrhi, FRESH process: reload the saved assets + level, every gate again (authoritative)
#   manny      commandlet: our copy of the template BP_ThirdPersonCharacter uses SKM_Manny_Simple
#   character  commandlet, fresh: default game mode -> Manny, no missing references, PlayerStart inside facing in
#   walk       (Blender -b) Manny-sized capsule clearance along the walking routes against the UCX hulls
#   capture    offscreen editor (real D3D12 RHI, -RenderOffscreen), tick-driven: every layout.json camera (+ C1 at the
#              reference's 1448 x 1086), repeated captures; then ak_crop.py (system Python) crops the shift-lens views
#   stats      (system Python, Pillow) ak_image_stats.py: tone / colour vs the Blender renders of the preset and the reference
# Lighting preset (night + genkan, 2026-09-28): env AK_PRESET, default "night" (the moon, night practicals, no fog, night
# exposure; Blender baseline renders/night_live4, fallback night_live2). AK_PRESET=golden rebuilds the golden-hour level (baseline hero_live).
# Run materials, level, verify, capture and stats with the SAME preset (the scenery-card dimming lives in the materials).
# Guard (house rule): before every Unreal step, if an UnrealEditor.exe has ArmoryLab.uproject open, STOP (exit 3)
# without touching the project: the user must close it.
# Logs + results: WorkFiles/armory/build/unreal/{logs/<step>.log, <step>.json}; timings in logs/timings.txt
# Never touches another project, UnrealEditor.exe, or another session's UnrealEditor-Cmd; kills only its own process on timeout.
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-project bounds import materials level verify manny character walk capture stats}"
export AK_PRESET="${AK_PRESET:-night}"
echo "preset: $AK_PRESET"
HERE="C:/Users/Cody/Desktop/Blender_Projects/Scripts/armory/unreal"
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
OUT="$ROOT/WorkFiles/armory/build/unreal"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/ArmoryLab/ArmoryLab.uproject"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
PY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
mkdir -p "$OUT/logs"
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 4)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours to touch)"
    n=$((n + 1)); sleep 15
  done
}
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'ArmoryLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then
    echo "STOP: the ArmoryLab editor is open (UnrealEditor.exe pid $hit). Close it, then re-run. Nothing was written."
    stamp "STOP editor open pid $hit"
    exit 3
  fi
}
stamp() { echo "$(date '+%F %T') $*" | tee -a "$OUT/logs/timings.txt"; }
for step in $STEPS; do
  t0=$(date +%s)
  case "$step" in
    project)
      "$PY" "$HERE/make_project.py" > "$OUT/logs/project.log" 2>&1; code=$? ;;
    bounds)
      "$BLENDER" -b --factory-startup "$ROOT/Assets/Armory/ArmoryKit.blend" --python "$HERE/blender_bounds.py" > "$OUT/logs/bounds.log" 2>&1; code=$?
      grep -q "BLENDER_BOUNDS" "$OUT/logs/bounds.log" || code=9 ;;
    import|materials|level|verify|manny|character)
      editor_guard
      wait_free
      stamp "start $step"
      timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$HERE/ak_$step.py" $NULL_FLAGS $DPC > "$OUT/logs/$step.log" 2>&1; code=$?
      grep -q "AK_STEP_DONE $step passed=True" "$OUT/logs/$step.log" || { [ $code -eq 0 ] && code=8; } ;;
    walk)
      # capsule clearance against the UCX hulls (Unreal traces do not collide in a -nullrhi commandlet)
      "$BLENDER" -b --factory-startup "$ROOT/Assets/Armory/ArmoryKit.blend" --python "$ROOT/Scripts/armory/walk_check.py" > "$OUT/logs/walk.log" 2>&1; code=$?
      grep -q "passed True" "$OUT/logs/walk.log" || code=9 ;;
    capture)
      editor_guard
      wait_free
      stamp "start capture"
      rm -rf "$OUT/captures/diag" "$OUT/captures/sequence" "$OUT"/captures/*.png   # our own outputs only
      powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$HERE/run_capture.ps1" 2>/dev/null || echo "$HERE/run_capture.ps1")" > "$OUT/logs/capture_runner.log" 2>&1; code=$?
      grep -q "AK_STEP_DONE capture passed=True" "$OUT/logs/capture.log" 2>/dev/null || { [ $code -eq 0 ] && code=8; }
      if [ $code -eq 0 ]; then
        py -3 "$HERE/ak_crop.py" > "$OUT/logs/crop.log" 2>&1 || code=7
        grep -q "AK_STEP_DONE crop passed=True" "$OUT/logs/crop.log" || { [ $code -eq 0 ] && code=7; }
      fi ;;
    stats)
      py -3 "$HERE/ak_image_stats.py" > "$OUT/logs/stats.log" 2>&1; code=$? ;;
    *) echo "unknown step $step"; exit 2 ;;
  esac
  t1=$(date +%s)
  stamp "$step [$AK_PRESET] exit $code in $((t1 - t0)) s |$(grep -o 'AK_STEP_DONE.*' "$OUT/logs/$step.log" 2>/dev/null | head -1)"
  if [ "$step" != "project" ] && [ "$step" != "bounds" ] && [ "$step" != "stats" ]; then
    echo "    errors: $(grep -c 'Error:' "$OUT/logs/$step.log" 2>/dev/null)  warnings: $(grep -c 'Warning:' "$OUT/logs/$step.log" 2>/dev/null)"
  fi
  if [ $code -ne 0 ]; then echo "STOP: $step failed (exit $code), see $OUT/logs/$step.log"; exit 1; fi
done
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "note: an UnrealEditor-Cmd is running (someone else's?)"; fi
echo "=== done $(date +%T)"
