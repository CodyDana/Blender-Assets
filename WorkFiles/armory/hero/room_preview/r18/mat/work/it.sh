#!/bin/bash
# r18 mat iteration: it.sh TAG "SWAPSPEC" [presets] [cams] [res] -> work/it/TAG/<preset>/ (on the r18/mat test blend)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
W="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r18/mat"
CAMS="${4:-C1_EntryReveal}"; RES="${5:-1448x1086}"
mkdir -p "$W/work/it/$1"
for P in ${3:-golden night}; do
  AK_TEXDIR="${AK_TEXDIR:-$W/Textures}" AK_SWAP="$2" "$B" -b --factory-startup "$W/ArmoryKit_preview.blend" --python "$W/work/swap_mat.py" \
    --python "$ROOT/Scripts/armory/render_armory.py" -- --layout "$W/layout_cams.json" --preset $P --cams "$CAMS" --res $RES \
    --out "$W/work/it/$1/$P" > "$W/work/it/$1/log_$P.txt" 2>&1
  grep -h "swapped\|rendered\|Error" "$W/work/it/$1/log_$P.txt"
done
