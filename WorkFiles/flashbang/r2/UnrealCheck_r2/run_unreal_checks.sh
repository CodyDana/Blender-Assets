#!/usr/bin/env bash
# SM_Flashbang Unreal verification, ONE commandlet at a time, each a fresh process:
#   pass1 (import 4 FBX + sidecars) -> texture import -> texture verify -> pass2 (fresh reload + gates)
# Usage: run_unreal_checks.sh <NEW content path, e.g. /Game/PropsCheck/Flashbang_FIN_0927a>  (FINALISE copy of ../UnrealCheck)
set -u
export MSYS_NO_PATHCONV=1
DEST="${1:?give a NEW content path}"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
HERE="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/UnrealCheck_r2"
IMPORTER="C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/ue_import_textures.py"
export FLASHBANG_DEST="$DEST"
export PROPS_TEXTURE_DIR="C:/Users/Cody/Desktop/Blender_Projects/Exports/Flashbang/Textures"
export PROPS_TEXTURE_DEST="$DEST/Textures"
FLAGS="-unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput"
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "an Unreal commandlet is already running: refusing"; exit 3; fi
rm -f "$HERE"/pass1.json "$HERE"/pass2.json "$HERE"/props_textures_*.json
echo "$DEST" > "$HERE/content_path.txt"
run() {
  if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "commandlet running before $1: refusing"; exit 3; fi
  echo "=== $1 $(date +%T)"
  "$UE" "$PROJ" -run=pythonscript -script="$2" $FLAGS > "$HERE/$1.log" 2> "$HERE/$1.log.stderr"
  echo "    exit $? $(date +%T)"
}
run pass1 "$HERE/fbu_pass1_import.py"
PROPS_TEXTURE_MODE=import PROPS_TEXTURE_OUT="$HERE/props_textures_import.json" run tex_import "$IMPORTER"
PROPS_TEXTURE_MODE=verify PROPS_TEXTURE_OUT="$HERE/props_textures_verify.json" run tex_verify "$IMPORTER"
run pass2 "$HERE/fbu_pass2_verify.py"
if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then echo "WARNING: an Unreal commandlet is still running"; fi
echo "=== done $(date +%T)"
