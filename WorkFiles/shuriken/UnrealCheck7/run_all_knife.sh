#!/usr/bin/env bash
# UnrealCheck7 (independent verifier), full sequence for style pass 2 / knife grind (library 3.6), on the
# shipped bytes in Exports/Shuriken and Assets/Shuriken.blend, into a FRESH content path.  Every Unreal
# pass is its own UnrealEditor-Cmd process (run_pass.ps1); passes 2 and 5 read back in a fresh process.
#   bash WorkFiles/shuriken/UnrealCheck7/run_all_knife.sh
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$PROJ/WorkFiles/shuriken/UnrealCheck7"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
# Git Bash (MSYS) rewrites /Game/... in env vars and args into C:/Program Files/Git/Game/...: switch it off.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
export MSYS2_ENV_CONV_EXCL="SHURIKEN_DEST"
export SHURIKEN_DEST="/Game/ShurikenCheck7/Knife"
cd "$PROJ"
echo "== blender_fbx_counts"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/blender_fbx_counts.py" 2>&1 | grep -E "DONE|Error|Traceback"
echo "== blend_lod_counts"
"$BLENDER" -b "$PROJ/Assets/Shuriken.blend" --factory-startup --python-exit-code 3 --python "$HERE/blend_lod_counts.py" 2>&1 | grep -E "DONE|Error|Traceback"
for form in four_point eight_point square_plate; do
  for pass in 1 2 3; do
    echo "== $form pass $pass (DEST $SHURIKEN_DEST)"
    powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/run_pass.ps1" -Form "$form" -Pass "$pass"
  done
done
for pass in 4 5; do
  echo "== textures pass $pass (DEST $SHURIKEN_DEST)"
  powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/run_pass.ps1" -Form textures -Pass "$pass"
done
echo "== roundtrip_compare"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/roundtrip_compare.py" 2>&1 | grep -E "DONE|Error|Traceback"
echo "== summarize"
py "$HERE/summarize.py"
echo "== done"
