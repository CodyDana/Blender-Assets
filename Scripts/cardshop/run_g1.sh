#!/usr/bin/env bash
# Card Shop Kit G1 standards spike on the PC (Git Bash). ONE Unreal process at a time; every Unreal step is its own
# fresh process, and verify always runs last in a fresh process (house rule).
#
#   bash Scripts/cardshop/run_g1.sh [steps...]
#   default: selftest art build preview project import materials map verify
#
# steps:
#   selftest   (py -3)     Scripts/cardshop/test_csk.py: the kit's self-tests incl. negative cases
#   art        (py -3)     G1 placeholder test-pattern art + atlases via csk_pack_cards -> Exports/CardShopKit/G1/Textures
#   build      (Blender)   build_csk.py: meshes, qa_check, export, .csk.json, kit checks; saves Assets/CardShopKit/CSK_G1.blend
#   preview    (Blender)   preview_g1.py: renders from the EXPORTED files -> Renders/CardShopKit/G1/g1_preview_*.png
#   project    (py -3)     make_project.py: the CardShopKit.uproject (Substrate off, legacy FBX importer)
#   import     (Unreal)    meshes + sidecars (sockets, LOD screen sizes) + textures into /Game/CardShopKit/G1
#   materials  (Unreal)    G1 test masters + instances, default instance per slot
#   map        (Unreal)    L_CSK_G1 (art rows + seated showcase) and L_CSK_G1_Stress (200 attached + 200 filled slabs)
#   verify     (Unreal)    FRESH process: every automatic G1 check -> WorkFiles/cardshop/g1/unreal/verify.json
# Guard: if an UnrealEditor.exe has CardShopKit.uproject open, STOP (exit 3) without touching the project.
# Stops at the first failing step. Logs: WorkFiles/cardshop/g1/unreal/logs/<step>.log; summary in logs/summary.txt.
set -u
export MSYS_NO_PATHCONV=1
STEPS="${*:-selftest art build preview project import materials map verify}"
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$ROOT/Scripts/cardshop"
OUT="$ROOT/WorkFiles/cardshop/g1/unreal"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/CardShopKit/CardShopKit.uproject"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
mkdir -p "$OUT/logs"
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
DPC="-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"

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

stamp "=== run_g1.sh: $STEPS"
for step in $STEPS; do
  t0=$(date +%s)
  log="$OUT/logs/$step.log"
  case "$step" in
    selftest)  py -3 "$HERE/test_csk.py" > "$log" 2>&1; need "$step" "CSK_SELFTEST PASSED"; code=$? ;;
    art)       py -3 "$HERE/art/g1_placeholder_art.py" > "$log" 2>&1; need "$step" "CSK_G1_ART done"; code=$? ;;
    build)     "$BLENDER" -b --factory-startup --python "$HERE/build_csk.py" -- > "$log" 2>&1
               need "$step" "CSK_BUILD PASSED"; code=$? ;;
    preview)   "$BLENDER" -b --factory-startup --python "$HERE/preview_g1.py" -- --samples 64 > "$log" 2>&1
               need "$step" "CSK_G1_PREVIEW"; code=$? ;;
    project)   py -3 "$HERE/unreal/make_project.py" > "$log" 2>&1; need "$step" "CSK_STEP_DONE project passed=True"; code=$? ;;
    import|materials|map|verify)
               editor_guard
               wait_free
               timeout 3600 "$UE" "$PROJ" -run=pythonscript -script="$HERE/unreal/csk_$step.py" $NULL_FLAGS $DPC > "$log" 2>&1
               need "$step" "CSK_STEP_DONE $step passed=True"; code=$? ;;
    *)         stamp "unknown step $step"; exit 2 ;;
  esac
  dt=$(( $(date +%s) - t0 ))
  if [ $code -ne 0 ]; then
    stamp "FAIL $step (${dt}s): see $log"
    exit 1
  fi
  stamp "ok   $step (${dt}s)"
done
stamp "=== all steps passed. Next: the MANUAL checks in WorkFiles/cardshop/G1_HANDOFF.md, then commit the reports."
