#!/bin/sh
# Kit 8 full pipeline: textures -> build (QA, export) -> renders -> sheets + side-by-sides. Usage: run_all.sh <round dir> [--no-export]
set -e
cd "$(dirname "$0")/../../../.."
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT="WorkFiles/dojo/build/props/stone/renders/${1:-r0}"
py -3 Scripts/dojo/props/stone/make_stone_textures.py > /dev/null
"$B" -b --factory-startup --python Scripts/dojo/props/stone/build_stone_props.py -- $2 2>&1 | grep -E "QA|FAIL|exported|saved|Error|Trace"
"$B" -b --factory-startup --python Scripts/dojo/props/stone/render_stone.py -- --what all --samples 64 --out "$OUT" 2>&1 | grep -E "Error|Trace" || true
py -3 Scripts/dojo/props/stone/compose_stone.py --dir "$OUT" --sbs
echo ALLDONE
