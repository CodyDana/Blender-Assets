#!/usr/bin/env bash
# UnrealCheck6, full sequence for the hooked-cross build (library 3.9.0; SM_Shuriken_HookedCross + the five frozen forms), on the shipped bytes in
# Exports/Shuriken, into a FRESH content path.  Every Unreal pass is its own UnrealEditor-Cmd process
# (run_pass.ps1); pass 2 reads the saved asset back in a fresh process (the gate).  Then the texture
# half: Scripts/shuriken/ue_import_textures.py in import mode and, in a second fresh process, verify mode.
#
#   bash WorkFiles/shuriken/UnrealCheck6/run_all_hooked_cross.sh [DEST]   (default /Game/ShurikenCheck6/HookedCross1)
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$PROJ/WorkFiles/shuriken/UnrealCheck6"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
UPROJECT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
# Git Bash (MSYS) rewrites /Game/... in env vars and args into C:/Program Files/Git/Game/...: switch it off.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
export MSYS2_ENV_CONV_EXCL="SHURIKEN_DEST;SHURIKEN_TEXTURE_DEST"
export SHURIKEN_DEST="${1:-/Game/ShurikenCheck6/HookedCross1}"
cd "$PROJ"
echo "== blender_fbx_counts"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/blender_fbx_counts.py" 2>&1 | grep -E "BLENDER_COUNTS_DONE|Error|Traceback"
echo "== hooked_cross_truth (the shipped FBX re-imported: Blender-side handedness truth)"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/hooked_cross_truth.py" 2>&1 | grep -E "HOOKED_CROSS_TRUTH_DONE|Error|Traceback"
for form in four_point eight_point square_plate six_point spike hooked_cross; do
  for pass in 1 2 3; do
    echo "== $form pass $pass (DEST $SHURIKEN_DEST)"
    powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/run_pass.ps1" -Form "$form" -Pass "$pass"
  done
done
echo "== roundtrip_compare"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/roundtrip_compare.py" 2>&1 | grep -E "ROUNDTRIP_DONE|Error|Traceback"
echo "== attach_engine_check"
py "$HERE/attach_engine_check.py"
echo "== textures: import (fresh process)"
export SHURIKEN_TEXTURE_MODE=import
export SHURIKEN_TEXTURE_DEST="$SHURIKEN_DEST/Textures"
export SHURIKEN_TEXTURE_OUT="$HERE/textures_import.json"
"$UE" "$UPROJECT" -run=pythonscript -script="$PROJ/Scripts/shuriken/ue_import_textures.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput > "$HERE/textures_import.log" 2>&1
grep -E "UE_IMPORT_TEXTURES|: *(Warning|Error) *:" "$HERE/textures_import.log" | head -5
echo "== textures: verify (fresh process)"
export SHURIKEN_TEXTURE_MODE=verify
export SHURIKEN_TEXTURE_OUT="$HERE/textures_verify.json"
"$UE" "$UPROJECT" -run=pythonscript -script="$PROJ/Scripts/shuriken/ue_import_textures.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput > "$HERE/textures_verify.log" 2>&1
grep -E "UE_IMPORT_TEXTURES|: *(Warning|Error) *:" "$HERE/textures_verify.log" | head -5
echo "== done"
