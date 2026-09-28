#!/bin/bash
# fp_geo.sh NAME BALLJSON [extra cache args] - mesh cache (2048, no AO) + clay reference view + top crop
cd "C:/Users/Cody/Desktop/Blender_Projects"
BL="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
PY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
T=WorkFiles/smokebomb/rewind/build5/tools
F=WorkFiles/smokebomb/final_pass
export PYTHONUTF8=1
N=$1; J=${2:-"{}"}; shift; shift
"$BL" -b --factory-startup --python $T/b5_cache.py -- $F/$N --no-ao --size 2048 --ball-json "$J" "$@" 2>&1 | grep -E "B4_CACHE|height guard|stretches;|Error|Traceback|line " | cut -c1-300
"$BL" -b --factory-startup --python $T/b5_render.py -- $F/$N $F/$N $F/$N --clay --samples 64 2>&1 | grep -E "Error|Traceback" | grep -v HIPEW
"$PY" $F/tools/fp_crop.py $F/$N/top_pair.png 440 120 520 420 1 References/SmokeBomb/smokebomb.png@2 $F/$N/ref_front_lod0_clay.png
