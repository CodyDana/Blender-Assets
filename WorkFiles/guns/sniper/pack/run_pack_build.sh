#!/usr/bin/env bash
# SR-01 pack colours: the ONE script the main chat runs to build SR01 into the shared pack and gate it.
# Written by the sr01-pack session (2026-10-16), which did every check that needs no Unreal and did NOT run this.
#
#   bash WorkFiles/guns/sniper/pack/run_pack_build.sh [tag]          (default tag sr01_1016; run from anywhere)
#   env: REF_DUMP   the last pack build's dump (default WorkFiles/guns/smg/materials/build/dump_smg01_1013b.json)
#        LOCK_PID   pid to hold the materials lock with (default: this shell's Windows pid, which is "dead" once the
#                   script ends; pass the main chat's claude.exe pid to keep the lock live afterwards)
#        DRY_RUN=1  run steps 0-3 only (no Unreal) and stop
#
# Steps (stops at the FIRST failure with a clear message; nothing after it runs):
#   0  lock      the PackMaterials lock is free, dead, or already sr01-pack's (never forces a live holder)
#   1  spec      add_sr01_to_spec.py re-run leaves material_spec.json byte-identical (additions only, projection check)
#   2  newer     no pack build newer than the reference dump in the main checkout (else the dump comparison is stale)
#   3  mirror    make_mirror.py: short-path mirror at C:/Users/Cody/AppData/Local/Temp/claude/sr01pk (M1-M4)
#   4  build     NP_OWNER=sr01-pack run_build.sh <tag> maps_check import_meshes import_textures clean build assign
#                verify render, from the mirror (preflight runs first inside it; waits behind other UnrealEditor-Cmd)
#   5  capture   sr01_ue_capture.py in a fresh UnrealEditor-Cmd (real RHI), the lock re-claimed as sr01-pack
#   6  analyse   sr01_pack_analyse.py in headless Blender (P1-P4 on the captures)
#   7  gates     sr01_pack_gates.py -> WorkFiles/guns/sniper/gates/pack_materials.json (P1-P4 + S1-S7 + dump compare)
#   7b frames    lit render frames (SR01 + scope) and render_<tag>.json copied to pack/build/frames/
#   8  cleanup   the mirror is removed (junctions unlinked, never recursed into); the lock stays HELD by sr01-pack
# Build records are copied to WorkFiles/guns/sniper/pack/build/; logs of 5-7 go there too.
set -u
export MSYS_NO_PATHCONV=1
TAG="${1:-sr01_1016}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"
WT="$(cd "$HERE/../../../.." && { pwd -W 2>/dev/null || pwd; })"
MAIN="C:/Users/Cody/Desktop/Blender_Projects"
MIRROR="C:/Users/Cody/AppData/Local/Temp/claude/sr01pk"
MPACK="$MIRROR/Scripts/unreal/materials"
REF_DUMP="${REF_DUMP:-$WT/WorkFiles/guns/smg/materials/build/dump_smg01_1013b.json}"
UE="${UE_CMD:-C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe}"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT="$HERE/build"
OWNER="sr01-pack"
LOCK="py -3 -B $WT/Scripts/unreal/materials/np_lock.py"
mkdir -p "$OUT"
RHI_FLAGS="-unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput -AllowCommandletRendering -RenderOffscreen -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"

stop() { echo; echo "STOP at step $1: $2"; echo "(nothing after this step ran; the mirror is left at $MIRROR for inspection;"; echo " remove it with: py -3 -B $HERE/make_mirror.py --remove)"; exit 1; }
wait_ue() { while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting: an UnrealEditor-Cmd is running"; sleep 15; done; }
claim() {
  local pid="${LOCK_PID:-$(cat /proc/$$/winpid 2>/dev/null || echo $$)}"
  $LOCK claim "$OWNER" --pid "$pid" || stop "$1" "another chat holds the materials lock (see above); never force a live holder"
}

echo "=== SR01 pack build, tag $TAG, worktree $WT  $(date +%T)"
# 0 lock
echo "=== 0 lock"
claim 0
# 1 spec additions only
echo "=== 1 spec additions only"
before="$(sha256sum < "$WT/Scripts/unreal/materials/material_spec.json")"
py -3 -B "$WT/WorkFiles/guns/sniper/materials/add_sr01_to_spec.py" || stop 1 "add_sr01_to_spec.py refused (spec changed by someone else?)"
after="$(sha256sum < "$WT/Scripts/unreal/materials/material_spec.json")"
[ "$before" = "$after" ] || stop 1 "re-running add_sr01_to_spec.py changed material_spec.json: the spec on disk was not the reviewed one (check git diff)"
# 2 no newer pack build than the reference dump
echo "=== 2 reference dump $REF_DUMP"
[ -f "$REF_DUMP" ] || stop 2 "reference dump missing: $REF_DUMP"
newer="$(find "$MAIN/WorkFiles/materials/build" -maxdepth 1 -name 'dump_*.json' -newermt 2026-10-13 2>/dev/null)"
[ -z "$newer" ] || stop 2 "a pack build newer than smg01_1013b exists in the main checkout ($newer): set REF_DUMP to it and re-run"
# 3 mirror
echo "=== 3 mirror"
py -3 -B "$HERE/make_mirror.py" --mirror "$MIRROR" || stop 3 "make_mirror.py failed (see $HERE/mirror_check.json)"
py -3 -B "$MPACK/np_spec.py" > "$OUT/maps_check_mirror_${TAG}.log" 2>&1 || stop 3 "maps_check failed in the mirror (see $OUT/maps_check_mirror_${TAG}.log)"
py -3 -B "$MPACK/np_preflight.py" > "$OUT/preflight_mirror_${TAG}.log" 2>&1 || stop 3 "preflight failed in the mirror (see $OUT/preflight_mirror_${TAG}.log)"
echo "    mirror ok, maps_check ok, preflight ok"
if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY_RUN=1: stopping before any Unreal step (mirror left at $MIRROR)"; exit 0; fi
# 4 build (run_build.sh takes the lock itself as NP_OWNER and releases it on exit)
echo "=== 4 run_build.sh $TAG"
STEPS="maps_check import_meshes import_textures clean build assign verify render"
NP_OWNER="$OWNER" bash "$MPACK/run_build.sh" "$TAG" $STEPS 2>&1 | tee "$OUT/run_build_${TAG}.log"
for f in "$MIRROR"/WorkFiles/materials/build/*_"${TAG}".* "$MIRROR"/WorkFiles/materials/build/logs/*_"${TAG}".log; do
  [ -f "$f" ] && cp -f "$f" "$OUT/"
done
grep -q "^STOP" "$OUT/run_build_${TAG}.log" && stop 4 "run_build.sh stopped (see $OUT/run_build_${TAG}.log and $OUT/<step>_${TAG}.log)"
n_ok="$(grep -c 'passed=True' "$OUT/run_build_${TAG}.log")"
n_cf="$(grep -c 'compile failures: 0 ' "$OUT/run_build_${TAG}.log")"
[ "$n_ok" = "7" ] && [ "$n_cf" = "7" ] || stop 4 "expected 7 Unreal steps passed=True with 0 compile failures, got $n_ok passed / $n_cf clean"
[ -f "$OUT/dump_${TAG}.json" ] || stop 4 "verify wrote no dump_${TAG}.json"
echo "    build ok (7 steps)"
# 5 capture (fresh process on the built pack; re-claim the lock: run_build.sh released it)
echo "=== 5 capture"
claim 5
wait_ue
CAPS="$WT/WorkFiles/guns/sniper/scratch/pack_captures"
mkdir -p "$CAPS"
SR01_PACK_DIR="$MPACK" SR01_CAPTURE_OUT="$CAPS" timeout 3600 "$UE" "$MIRROR/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject" \
  -run=pythonscript -script="$HERE/sr01_ue_capture.py" $RHI_FLAGS > "$OUT/capture_${TAG}.log" 2>&1
code=$?
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "WARNING: an UnrealEditor-Cmd is still running"; fi
grep -q "SR01_CAPTURE_DONE passed=True" "$OUT/capture_${TAG}.log" || stop 5 "capture failed (exit $code; see $OUT/capture_${TAG}.log and $CAPS/capture_jobs.json)"
echo "    $(grep -o 'SR01_CAPTURE_DONE.*' "$OUT/capture_${TAG}.log" | head -1)"
# 6 analyse
echo "=== 6 analyse"
SR01_PACK_DIR="$MPACK" SR01_CAPTURE_OUT="$CAPS" "$BLENDER" -b --factory-startup --python "$HERE/sr01_pack_analyse.py" > "$OUT/analyse_${TAG}.log" 2>&1 \
  || stop 6 "analysis failed (see $OUT/analyse_${TAG}.log)"
grep -q "SR01_ANALYSE_DONE" "$OUT/analyse_${TAG}.log" || stop 6 "analysis did not finish (see $OUT/analyse_${TAG}.log)"
echo "    $(grep -o 'SR01_ANALYSE_DONE.*' "$OUT/analyse_${TAG}.log" | head -c 600)"
# 7 gates
echo "=== 7 gates"
py -3 -B "$HERE/sr01_pack_gates.py" "$TAG" "$REF_DUMP" --pack-dir "$MPACK" 2>&1 | tee "$OUT/gates_${TAG}.log"
st="${PIPESTATUS[0]}"
[ "$st" = "0" ] || stop 7 "a blocking gate failed: see WorkFiles/guns/sniper/gates/pack_materials.json (blocking_failed). If only P1 failed on a BC1 kind, re-run add_sr01_to_spec.py with BC_BC7 and this script again"
# 7b keep the lit render frames (R3): they live only in the mirror, which step 8 removes
echo "=== 7b frames"
FRAMES="$OUT/frames"
mkdir -p "$FRAMES"
n_fr=0
for f in "$MIRROR"/WorkFiles/materials/ue_renders/frames_raw/*SR01*.png \
         "$MIRROR"/WorkFiles/materials/ue_renders/frames_raw/*Scope_LongRange*.png \
         "$MIRROR"/WorkFiles/materials/build/render_"${TAG}".json; do
  [ -f "$f" ] && cp -f "$f" "$FRAMES/" && n_fr=$((n_fr + 1))
done
[ "$n_fr" -gt 1 ] || echo "WARNING: no SR01/scope frames found in $MIRROR/WorkFiles/materials/ue_renders/frames_raw/"
echo "    $n_fr files (lit frames + render_${TAG}.json) copied to $FRAMES"
# 8 cleanup
echo "=== 8 cleanup"
py -3 -B "$HERE/make_mirror.py" --mirror "$MIRROR" --remove
$LOCK status
echo
echo "DONE: every blocking gate passed (WorkFiles/guns/sniper/gates/pack_materials.json)."
echo "Lit frames (R3): $FRAMES"
echo "Next (main chat): look at the lit frames in the render step (R3), review git diff, commit, then release the lock:"
echo "    py -3 -B Scripts/unreal/materials/np_lock.py release $OWNER"
