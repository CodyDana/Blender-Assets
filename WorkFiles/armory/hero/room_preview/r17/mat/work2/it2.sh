#!/bin/bash
# it2.sh TAG 'JSON' [presets] [cams] [res] -> work2/it/TAG/<preset>/...
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r17/mat"
W="$D/work2"
mkdir -p "$W/it/$1"
for P in ${3:-night golden}; do
  AK_TEXDIR="$D/Textures" AK_SWAP2="$2" "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$W/swap2.py" \
    --python "$ROOT/Scripts/armory/render_armory.py" -- --layout "$D/layout_cams.json" --preset $P --cams "${4:-C1_EntryReveal}" --res ${5:-1448x1086} \
    --out "$W/it/$1/$P" > "$W/it/$1/log_$P.txt" 2>&1
  grep -h "swapped\|rendered\|Error\|WARNING" "$W/it/$1/log_$P.txt"
done
