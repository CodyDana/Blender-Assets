#!/usr/bin/env bash
# UnrealCheck6, full sequence for the KUNAI BLADE-SECTION build (library 3.11, option C: SM_Kunai_Plain + the six frozen
# forms), on the shipped bytes in Exports/Shuriken, into a FRESH content path.  Adapted from run_all_kunai_plain.sh (kept
# unchanged); the differences:
#   * the run's evidence goes to its own folder (UC6_OUT, default blade_section_c1/) - the six frozen forms' reports cite
#     the earlier run's pass files in this folder, which must not be overwritten;
#   * every Unreal launch goes through run_ue_guarded.ps1: the ONE-UNREAL-AT-A-TIME guard (wait_unreal_free.ps1: no
#     UnrealEditor-Cmd.exe, no UnrealEditor.exe with -run= / -ExecutePythonScript / -unattended / -nullrhi; else wait
#     60 s, up to 90 min) runs right before EVERY launch, logged in guard.log;
#   * the SHA-256 of every imported file (FBX, sidecar, texture) is taken before and after the passes (hash_inputs.py);
#   * attach_engine_check.py WRITES only the kunai's report (UC6_ATTACH_WRITE=kunai_plain); the six are verified
#     check-only and compared with the engine_check already attached to their byte-frozen reports.
# Every Unreal pass is its own UnrealEditor-Cmd process; pass 2 reads the saved asset back in a fresh process (the
# gate).  Then the texture half: Scripts/shuriken/ue_import_textures.py in import mode and, in a second fresh process,
# verify mode.  Blender runs headless (-b --factory-startup) only.
#
#   bash WorkFiles/shuriken/UnrealCheck6/run_all_kunai_blade_section.sh [DEST] [OUTDIR]
#        (defaults /Game/ShurikenCheck9/KunaiBladeC1, WorkFiles/shuriken/UnrealCheck6/blade_section_c1)
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$PROJ/WorkFiles/shuriken/UnrealCheck6"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
# Git Bash (MSYS) rewrites /Game/... in env vars and args into C:/Program Files/Git/Game/...: switch it off.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
export MSYS2_ENV_CONV_EXCL="SHURIKEN_DEST;SHURIKEN_TEXTURE_DEST;UC6_OUT"
export PYTHONDONTWRITEBYTECODE=1
export SHURIKEN_DEST="${1:-/Game/ShurikenCheck9/KunaiBladeC1}"
export UC6_OUT="${2:-$HERE/blade_section_c1}"
GUARD="$UC6_OUT/guard.log"
mkdir -p "$UC6_OUT"
cd "$PROJ"
guarded() {   # guarded <script.py> <log> <label>
  powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/run_ue_guarded.ps1" -Script "$1" -Log "$2" -GuardLog "$GUARD" -Label "$3"
  local rc=$?
  if [ $rc -eq 2 ]; then echo "ABORTED (Unreal busy 90 min) at $3"; exit 2; fi
}
echo "== start $(date -Iseconds)  DEST=$SHURIKEN_DEST  OUT=$UC6_OUT"
echo "== hash inputs (before)"
py "$HERE/hash_inputs.py" "$UC6_OUT/input_sha256_before.json"
echo "== blender_fbx_counts"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/blender_fbx_counts.py" 2>&1 | grep -E "BLENDER_COUNTS_DONE|Error|Traceback"
echo "== hooked_cross_truth (the shipped FBX re-imported: Blender-side handedness truth)"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/hooked_cross_truth.py" 2>&1 | grep -E "HOOKED_CROSS_TRUTH_DONE|Error|Traceback"
declare -A SCRIPT=([1]="$HERE/pass1_import.py" [2]="$HERE/pass2_reload.py" [3]="$HERE/pass3_export_diag.py")
for form in kunai_plain four_point eight_point square_plate six_point spike hooked_cross; do
  for pass in 1 2 3; do
    echo "== $form pass $pass (DEST $SHURIKEN_DEST)"
    export SHURIKEN_FORM="$form"
    guarded "${SCRIPT[$pass]}" "$UC6_OUT/${form}_pass$pass.log" "$form pass $pass"
  done
done
unset SHURIKEN_FORM
echo "== roundtrip_compare"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/roundtrip_compare.py" 2>&1 | grep -E "ROUNDTRIP_DONE|Error|Traceback"
echo "== textures: import (fresh process)"
export SHURIKEN_TEXTURE_MODE=import
export SHURIKEN_TEXTURE_DEST="$SHURIKEN_DEST/Textures"
export SHURIKEN_TEXTURE_OUT="$UC6_OUT/textures_import.json"
guarded "$PROJ/Scripts/shuriken/ue_import_textures.py" "$UC6_OUT/textures_import.log" "textures import"
grep -E "UE_IMPORT_TEXTURES" "$UC6_OUT/textures_import.log" | head -3
echo "== textures: verify (fresh process)"
export SHURIKEN_TEXTURE_MODE=verify
export SHURIKEN_TEXTURE_OUT="$UC6_OUT/textures_verify.json"
guarded "$PROJ/Scripts/shuriken/ue_import_textures.py" "$UC6_OUT/textures_verify.log" "textures verify"
grep -E "UE_IMPORT_TEXTURES" "$UC6_OUT/textures_verify.log" | head -3
echo "== hash inputs (after)"
py "$HERE/hash_inputs.py" "$UC6_OUT/input_sha256_after.json"
if [ "${UC6_SKIP_ATTACH:-0}" = "1" ]; then
  echo "== attach_engine_check SKIPPED (UC6_SKIP_ATTACH=1)"
else
  echo "== attach_engine_check (writes kunai_plain only; the six check-only)"
  UC6_ATTACH_WRITE=kunai_plain py "$HERE/attach_engine_check.py" four_point eight_point square_plate six_point spike hooked_cross kunai_plain
fi
echo "== done $(date -Iseconds)"
