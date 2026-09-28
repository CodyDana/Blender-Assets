#!/usr/bin/env bash
# Run the pack-material build in the validation project, ONE Unreal commandlet at a time, each its own process.
#   run_build.sh <tag> [steps...]       default steps: maps_check import_meshes import_textures clean build assign verify
# steps: maps_check import_meshes import_textures build assign verify render clean
#   maps_check (no Unreal): the Recolour maps -> recolour_maps.json -> recolour_constants.json sha256 chain is intact
#              and the spec resolves (np_spec.py). If it fails: re-run the map generator that changed, then
#              maps/derive_constants.py (see the README of the materials folder).
# Logs: WorkFiles/materials/build/logs/<step>_<tag>.log ; results: WorkFiles/materials/build/<step>_<tag>.json
# Paths come from this script's location (Scripts/unreal/materials) and UE_CMD (default: the UE 5.8 install).
set -u
export MSYS_NO_PATHCONV=1
TAG="${1:?give a tag, e.g. r1}"; shift
STEPS="${*:-maps_check import_meshes import_textures clean build assign verify}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"
PROJECT_ROOT="$(cd "$HERE/../../.." && { pwd -W 2>/dev/null || pwd; })"
UE="${UE_CMD:-C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe}"
PROJ="$PROJECT_ROOT/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
SCRIPT="$HERE/build_pack_materials.py"
OUT="$PROJECT_ROOT/WorkFiles/materials/build"
mkdir -p "$OUT/logs"

# --- guards (2026-09-27, after two chats collided: see np_preflight.py and np_lock.py) -----------------------------
# 1. ONE owner at a time: take the shared materials lock for the whole run (per-chat owner via NP_OWNER).
OWNER="${NP_OWNER:-run_build:$TAG}"
WINPID="$(cat /proc/$$/winpid 2>/dev/null || echo $$)"
if ! py -3 -B "$HERE/np_lock.py" claim "$OWNER" --pid "$WINPID"; then
  echo "STOP: another chat holds the materials lock (see above). Nothing was run."; exit 2
fi
trap 'py -3 -B "$HERE/np_lock.py" release "$OWNER" >/dev/null 2>&1' EXIT
# 2. PREFLIGHT before anything destructive: every parameter each master asks for must be in the spec, the spec must
#    resolve. If clean/build is requested it ALWAYS runs first, so clean can never delete what build cannot recreate.
FP=""
case " $STEPS " in *" clean "*|*" build "*)
  echo "=== preflight ($TAG) $(date +%T)"
  if ! py -3 -B "$HERE/np_preflight.py" > "$OUT/logs/preflight_${TAG}.log" 2>&1; then
    cat "$OUT/logs/preflight_${TAG}.log"; echo "STOP: preflight failed - nothing was deleted"; exit 3
  fi
  FP="$(py -3 -B "$HERE/np_preflight.py" --fingerprint)"; echo "    ok (fingerprint ${FP:0:16})";;
esac
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
RHI_FLAGS="-unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput -AllowCommandletRendering -RenderOffscreen -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
for step in $STEPS; do
  if [ "$step" = "maps_check" ]; then
    echo "=== maps_check ($TAG) $(date +%T)"
    if ! py -3 -B "$HERE/np_spec.py" > "$OUT/logs/maps_check_${TAG}.log" 2>&1; then
      echo "STOP: maps_check failed (see $OUT/logs/maps_check_${TAG}.log)"; break
    fi
    echo "    ok"
    continue
  fi
  # 3. the code and spec must not change under a run (someone editing mid-run): compare with the preflight fingerprint
  if [ -n "$FP" ]; then
    now="$(py -3 -B "$HERE/np_preflight.py" --fingerprint)"
    if [ "$now" != "$FP" ]; then echo "STOP: Scripts/unreal/materials or material_spec.json changed during this run - re-run from preflight"; break; fi
  fi
  # one commandlet at a time across the machine: wait while anyone's UnrealEditor-Cmd runs (never touch it)
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting: an UnrealEditor-Cmd is running"; sleep 15; done
  flags="$NULL_FLAGS"; case "$step" in render|verify) flags="$RHI_FLAGS";; esac
  log="$OUT/logs/${step}_${TAG}.log"
  echo "=== $step ($TAG) $(date +%T)"
  NP_MODE="$step" NP_TAG="$TAG" timeout 1800 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" $flags > "$log" 2>&1
  code=$?
  echo "    exit $code $(date +%T) | $(grep -o 'NP_BUILD_DONE.*' "$log" | head -1)"
  fails=$(grep -c 'Failed to compile' "$log")
  echo "    compile failures: $fails  errors: $(grep -c 'Error:' "$log")"
  echo "$fails" > "$OUT/compile_failures_${step}_${TAG}.txt"
  if [ $code -ne 0 ] || ! grep -q "NP_BUILD_DONE" "$log"; then echo "STOP: $step failed (see $log)"; break; fi
  if grep -q "NP_BUILD_DONE.*passed=False" "$log"; then echo "STOP: $step reported passed=False (see $OUT/${step}_${TAG}.json)"; break; fi
  if [ "$fails" != "0" ] && { [ "$step" = "verify" ] || [ "$step" = "render" ]; }; then echo "STOP: $step logged $fails material compile failures"; break; fi
done
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "WARNING: an UnrealEditor-Cmd is still running"; fi
