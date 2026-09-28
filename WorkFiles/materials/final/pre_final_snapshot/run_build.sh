#!/usr/bin/env bash
# Run the pack-material build in the validation project, ONE Unreal commandlet at a time, each its own process.
#   run_build.sh <tag> [steps...]       default steps: import_meshes import_textures clean build assign verify
# steps: import_meshes import_textures build assign verify render clean
# Logs: WorkFiles/materials/build/logs/<step>_<tag>.log ; results: WorkFiles/materials/build/<step>_<tag>.json
set -u
export MSYS_NO_PATHCONV=1
TAG="${1:?give a tag, e.g. r1}"; shift
STEPS="${*:-import_meshes import_textures clean build assign verify}"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
SCRIPT="C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/build_pack_materials.py"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build"
mkdir -p "$OUT/logs"
NULL_FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
RHI_FLAGS="-unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput -AllowCommandletRendering -RenderOffscreen -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0"
for step in $STEPS; do
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
