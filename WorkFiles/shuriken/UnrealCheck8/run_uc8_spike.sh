#!/usr/bin/env bash
# UnrealCheck8 (independent import verifier), spike build (library 3.8.0): all five forms on the exact bytes in
# Exports/Shuriken, a FRESH content path, every Unreal step its own UnrealEditor-Cmd process (run_uc8.ps1).
#   bash WorkFiles/shuriken/UnrealCheck8/run_uc8_spike.sh [DEST]   (default /Game/ShurikenCheck8/Spike1)
set -u
PROJ="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$PROJ/WorkFiles/shuriken/UnrealCheck8"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
export MSYS2_ENV_CONV_EXCL="SHURIKEN_UC8_DEST;SHURIKEN_TEXTURE_DEST"
export SHURIKEN_UC8_DEST="${1:-/Game/ShurikenCheck8/Spike1}"
cd "$PROJ"
echo "== b1 blend truth"
"$BLENDER" -b "$PROJ/Assets/Shuriken.blend" --factory-startup --python-exit-code 3 --python "$HERE/b1_blend_truth.py" > "$HERE/b1_blend_truth.log" 2>&1; echo "b1 exit=$?"
echo "== p1..p4 (DEST $SHURIKEN_UC8_DEST)"
powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/run_uc8.ps1"
echo "== b2 roundtrip"
"$BLENDER" -b --factory-startup --python-exit-code 3 --python "$HERE/b2_roundtrip.py" > "$HERE/b2_roundtrip.log" 2>&1; echo "b2 exit=$?"
echo "== summarize"
py "$HERE/summarize.py"
echo "== done"
