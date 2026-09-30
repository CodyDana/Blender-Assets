#!/usr/bin/env bash
# DojoLab Unreal steps, ONE Unreal process at a time machine-wide, each step its own fresh process.
#   run_dojo_unreal.sh [steps...]
# steps:
#   project      (no Unreal) make_dojolab.py: copy GASP -> DojoLab (missing files only), generated Config
#   gasp         commandlet -nullrhi, read-only: GASP traversal facts (dj_gasp_inspect.py -> gasp_inspect.json)
#   gamemode     commandlet: /Game/Dojo/Blueprints/GM_Dojo (child of GM_Sandbox, default pawn SandboxCharacter_CMC)
#   bounds       (Blender -b) the Blender AABBs + slot names + UCX counts the gates compare against
#   import       commandlet -nullrhi: SM_DGB_* into /Game/DojoKit/Greybox/Meshes (legacy FBX, UCX kept)
#   materials    commandlet -nullrhi: one flat master + one MI per grey-box class colour
#   level        commandlet -nullrhi: /Game/Dojo/Maps/L_Dojo from layout.json + traversal blocks + bounds gate
#   verify       commandlet -nullrhi, FRESH process: every gate again on what was saved
#   capture      offscreen editor (D3D12, -RenderOffscreen), tick-driven stills of the layout.json cameras
# Guard (house rule): before every Unreal step, if an UnrealEditor.exe has DojoLab.uproject open, STOP (exit 3).
# Never touches another project, UnrealEditor.exe, or another session's UnrealEditor-Cmd.
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-project gasp gamemode bounds import materials level verify capture}"
HERE="C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal"
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
OUT="$ROOT/WorkFiles/dojo/build/unreal"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
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
    project)
      py -3 "$HERE/make_dojolab.py" > "$OUT/logs/project.log" 2>&1; code=$?
      grep -q '"passed": true' "$OUT/logs/project.log" || code=9 ;;
    bounds)
      "$BLENDER" -b --factory-startup "$ROOT/Assets/Dojo/DojoGreybox.blend" --python "$HERE/blender_bounds.py" > "$OUT/logs/bounds.log" 2>&1; code=$?
      grep -q "BLENDER_BOUNDS" "$OUT/logs/bounds.log" || code=9 ;;
    gasp|gamemode|import|materials|level|verify)
      script="dj_$step.py"; [ "$step" = "gasp" ] && script="dj_gasp_inspect.py"
      editor_guard
      wait_free
      stamp "start $step"
      timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$HERE/$script" $NULL_FLAGS $DPC > "$OUT/logs/$step.log" 2>&1; code=$?
      grep -q "DJ_STEP_DONE $step passed=True" "$OUT/logs/$step.log" || { [ $code -eq 0 ] && code=8; } ;;
    capture)
      editor_guard
      wait_free
      stamp "start capture"
      powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$HERE/run_capture.ps1" 2>/dev/null || echo "$HERE/run_capture.ps1")" > "$OUT/logs/capture_runner.log" 2>&1; code=$?
      grep -q "DJ_STEP_DONE capture passed=True" "$OUT/logs/capture.log" 2>/dev/null || { [ $code -eq 0 ] && code=8; } ;;
    *) echo "unknown step $step"; exit 2 ;;
  esac
  t1=$(date +%s)
  stamp "$step exit $code in $((t1 - t0)) s | $(grep -o 'DJ_STEP_DONE.*' "$OUT/logs/$step.log" 2>/dev/null | head -1)"
  if [ "$step" != "project" ] && [ "$step" != "bounds" ]; then
    echo "    errors: $(grep -c 'Error:' "$OUT/logs/$step.log" 2>/dev/null)  warnings: $(grep -c 'Warning:' "$OUT/logs/$step.log" 2>/dev/null)"
  fi
  if [ $code -ne 0 ]; then echo "STOP: $step failed (exit $code), see $OUT/logs/$step.log"; exit 1; fi
done
echo "=== done $(date +%T)"
