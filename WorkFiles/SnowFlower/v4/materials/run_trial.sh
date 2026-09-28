#!/usr/bin/env bash
# Isolated TRIAL build of the Snow Flower materials: the pack's own build script (Scripts/unreal/materials) on a derived
# spec (sf_spec_additions.py trial: the three masters, the functions and ONLY the two Snow Flower items) under its own
# content root /Game/SFMatTrial, so the live /Game/NinjaPack (which the paper bomb session also rebuilds) is untouched.
#   run_trial.sh <tag> [steps...]    default: maps_check import_meshes import_textures clean build assign verify
# One Unreal commandlet at a time (waits while any UnrealEditor-Cmd runs); logs and JSON in this folder.
set -u
export MSYS_NO_PATHCONV=1
TAG="${1:?give a tag}"; shift
STEPS="${*:-maps_check import_meshes import_textures clean build assign verify}"
ROOTDIR="C:/Users/Cody/Desktop/Blender_Projects"
HERE="$ROOTDIR/WorkFiles/SnowFlower/v4/materials"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="$ROOTDIR/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
SCRIPT="$ROOTDIR/Scripts/unreal/materials/build_pack_materials.py"
mkdir -p "$HERE/trial/logs"
export NP_SPEC_PATH="$HERE/trial/trial_spec_${TAG}.json"
export NP_ROOT="/Game/SFMatTrial"
export NP_OUT_DIR="$HERE/trial"
py -3 -B "$HERE/sf_spec_additions.py" trial "$NP_SPEC_PATH" || exit 1
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
RHI_FLAGS="-unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput -AllowCommandletRendering -RenderOffscreen -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
for step in $STEPS; do
  if [ "$step" = "maps_check" ]; then
    echo "=== maps_check ($TAG) $(date +%T)"
    if ! py -3 -B "$ROOTDIR/Scripts/unreal/materials/np_spec.py" > "$HERE/trial/logs/maps_check_${TAG}.log" 2>&1; then
      echo "STOP: maps_check failed"; tail -20 "$HERE/trial/logs/maps_check_${TAG}.log"; break
    fi
    echo "    ok"; continue
  fi
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting: an UnrealEditor-Cmd is running"; sleep 15; done
  flags="$NULL_FLAGS"; case "$step" in render|verify) flags="$RHI_FLAGS";; esac
  log="$HERE/trial/logs/${step}_${TAG}.log"
  echo "=== $step ($TAG) $(date +%T)"
  NP_MODE="$step" NP_TAG="$TAG" timeout 1800 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" $flags > "$log" 2>&1
  code=$?
  fails=$(grep -c 'Failed to compile' "$log")
  echo "    exit $code $(date +%T) | $(grep -o 'NP_BUILD_DONE.*' "$log" | head -1) | compile failures $fails"
  if [ $code -ne 0 ] || ! grep -q "NP_BUILD_DONE" "$log"; then echo "STOP: $step failed (see $log)"; break; fi
  if grep -q "NP_BUILD_DONE.*passed=False" "$log"; then echo "STOP: $step reported passed=False"; break; fi
  if [ "$fails" != "0" ] && { [ "$step" = "verify" ] || [ "$step" = "render" ]; }; then echo "STOP: compile failures"; break; fi
done
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "WARNING: an UnrealEditor-Cmd is still running"; fi
