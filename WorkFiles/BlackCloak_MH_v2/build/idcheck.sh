#!/bin/bash
# usage: idcheck.sh <outdir> views...
cd "C:/Users/Cody/Desktop/Blender_Projects"
OUT=$1; shift
S=WorkFiles/BlackCloak_MH_v2/spec/scripts
rm -rf "$OUT"; mkdir -p "$OUT"
for v in "$@"; do "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python $S/v2m_render.py -- --view $v --body 1 --no-beauty --out "$OUT" --tag $v > "$OUT/log_$v.txt" 2>&1; done
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python "C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/342b2b8b-7c00-429a-957a-35d3bfa101ce/scratchpad/bcv2b_idcount.py" -- "$(cd $OUT; pwd -W)" "$@" 2>&1 | grep "^ID"
