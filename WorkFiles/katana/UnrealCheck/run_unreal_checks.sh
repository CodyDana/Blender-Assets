#!/usr/bin/env bash
# Unreal verification of SM_Katana, ONE commandlet at a time, each its own fresh process
# (adapted copy of WorkFiles/SnowFlower/v4/UnrealCheck/run_unreal_checks.sh):
#   Blender FBX count -> pass1 (import + sidecar, one save) -> texture import -> ORM composite -> texture verify
#   -> pass2 (fresh reload + gates)
# Usage: run_unreal_checks.sh <NEW content path, e.g. /Game/KatanaCheck/Katana_1003a>
set -u
export MSYS_NO_PATHCONV=1
DEST="${1:?give a NEW content path}"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
HERE="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/katana/UnrealCheck"
IMPORTER="C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/ue_import_textures.py"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
export KATANA_DEST="$DEST"
export PROPS_TEXTURE_DIR="C:/Users/Cody/Desktop/Blender_Projects/Exports/Katana/Textures"
export PROPS_TEXTURE_DEST="$DEST/Textures"
FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
rm -f "$HERE"/pass1.json "$HERE"/pass2.json "$HERE"/props_textures_*.json "$HERE"/tex_composite.json "$HERE"/blender_fbx_counts.json
echo "$DEST" > "$HERE/content_path.txt"
"$BLENDER" -b --factory-startup --python "$HERE/kuc_fbx_counts.py" > "$HERE/fbx_counts.log" 2>&1
echo "=== fbx counts $(date +%T): $(grep FBX_COUNTS "$HERE/fbx_counts.log" | cut -c1-300)"
run() {
  while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do sleep 10; done
  echo "=== $1 $(date +%T)"
  "$UE" "$PROJ" -run=pythonscript -script="$2" $FLAGS > "$HERE/$1.log" 2> "$HERE/$1.log.stderr"
  local code=$?
  echo "    exit $code $(date +%T)  warning/error lines: $(grep -c -E 'Warning:|Error:' "$HERE/$1.log")"
}
run pass1 "$HERE/kuc_pass1_import.py"
PROPS_TEXTURE_MODE=import PROPS_TEXTURE_OUT="$HERE/props_textures_import.json" run tex_import "$IMPORTER"
run tex_composite "$HERE/kuc_tex_composite.py"
PROPS_TEXTURE_MODE=verify PROPS_TEXTURE_OUT="$HERE/props_textures_verify.json" run tex_verify "$IMPORTER"
run pass2 "$HERE/kuc_pass2_verify.py"
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "NOTE: an Unreal commandlet is running now (not ours unless listed above)"; fi
echo "=== done $(date +%T)"
