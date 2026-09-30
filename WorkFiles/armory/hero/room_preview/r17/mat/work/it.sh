#!/bin/bash
# r17 mat iteration: it.sh TAG "SWAPSPEC" [presets] [blend] -> work/it/TAG_<preset>.png (C1 1448x1086)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
W="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r17/mat"
BLEND="${4:-C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/final/ArmoryKit_preview.blend}"
LAYOUT="${5:-C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/final/layout_cams.json}"
CAMS="${6:-C1_EntryReveal}"
RES="${7:-1448x1086}"
mkdir -p "$W/work/it/$1"
for P in ${3:-night golden}; do
  AK_TEXDIR="$W/Textures" AK_SWAP="$2" "$B" -b --factory-startup "$BLEND" --python "$W/work/swap_mat.py" \
    --python "$ROOT/Scripts/armory/render_armory.py" -- --layout "$LAYOUT" --preset $P --cams "$CAMS" --res $RES \
    --out "$W/work/it/$1/$P" > "$W/work/it/$1/log_$P.txt" 2>&1
  grep -h "swapped\|rendered\|Error" "$W/work/it/$1/log_$P.txt"
done
