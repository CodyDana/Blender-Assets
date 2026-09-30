#!/usr/bin/env bash
# Card Shop Kit showcase room on the PC (Git Bash): builds L_CSK_Shop from the imported kit and renders its cameras.
# Needs the G1 run's import + materials steps done first (bash Scripts/cardshop/run_g1.sh). ONE Unreal process at a
# time; each step is its own fresh process.
#
#   bash Scripts/cardshop/run_shop.sh [steps...]      default: project shop capture
#
# steps:
#   project   (py -3)                   make_project.py (Lumen on distance fields, L_CSK_Shop as the start-up map)
#   shop      (Unreal commandlet)       csk_shop.py: builds and saves /Game/CardShopKit/Maps/L_CSK_Shop
#   capture   (offscreen Unreal editor) csk_shop_capture.py: every CAM_ -> WorkFiles/cardshop/shop/captures/<cam>.png
#             env CSK_CAMS / CSK_FRAMES / CSK_WARM pass through
# Guard: if an UnrealEditor.exe has CardShopKit.uproject open, STOP (exit 3) without touching the project.
# Logs: WorkFiles/cardshop/shop/logs/<step>.log; summary in logs/summary.txt.
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-project shop capture}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd -W)"
HERE="$ROOT/Scripts/cardshop"
OUT="$ROOT/WorkFiles/cardshop/shop"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/CardShopKit/CardShopKit.uproject"
mkdir -p "$OUT/logs"
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
# r.AOAsyncBuildQueue=0: build mesh distance fields synchronously (async tasks were abandoned at quit, so Lumen had none)
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0,r.AOAsyncBuildQueue=0"

stamp() { echo "$(date '+%F %T') $*" | tee -a "$OUT/logs/summary.txt"; }
wait_free() {
  local n=0
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do
    [ $((n % 4)) -eq 0 ] && echo "    waiting: an UnrealEditor-Cmd is running (not ours to touch)"
    n=$((n + 1)); sleep 15
  done
}
editor_guard() {
  local hit
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'CardShopKit' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
  if [ -n "${hit// /}" ]; then
    stamp "STOP: the CardShopKit editor is open (UnrealEditor.exe pid $hit). Close it, then re-run. Nothing was written."
    exit 3
  fi
}
need() { grep -q "$2" "$OUT/logs/$1.log"; }

stamp "=== run_shop.sh: $STEPS"
for step in $STEPS; do
  t0=$(date +%s)
  log="$OUT/logs/$step.log"
  case "$step" in
    project)  py -3 "$HERE/unreal/make_project.py" > "$log" 2>&1; need "$step" "CSK_STEP_DONE project passed=True"; code=$? ;;
    shop)     editor_guard; wait_free
              timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$HERE/unreal/csk_shop.py" $NULL_FLAGS $DPC > "$log" 2>&1
              need "$step" "CSK_STEP_DONE shop passed=True"; code=$? ;;
    capture)  editor_guard; wait_free
              timeout 2400 "$UE" "$PROJ" -unattended -nosplash -nop4 -RenderOffscreen -dx12 -NoSound -NoLiveCoding \
                "$DPC" \
                "-ExecutePythonScript=$HERE/unreal/csk_shop_capture.py" "-abslog=$log" > "$OUT/logs/capture_stdout.txt" 2>&1
              need "$step" "CSK_STEP_DONE capture passed=True"; code=$? ;;
    *)        stamp "unknown step $step"; exit 2 ;;
  esac
  dt=$(( $(date +%s) - t0 ))
  if [ $code -ne 0 ]; then
    stamp "FAIL $step (${dt}s): see $log"
    exit 1
  fi
  stamp "ok   $step (${dt}s)"
done
stamp "=== all steps passed. Captures: WorkFiles/cardshop/shop/captures/"
