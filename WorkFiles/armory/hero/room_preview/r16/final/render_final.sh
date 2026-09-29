#!/bin/bash
# r16 combined renders into r16/final/<preset> (+ ref_aspect C1 1448x1086): render_final.sh [presets]
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/final"
PRESETS="${1:-golden night}"
CAMS="C1_EntryReveal,CX_FromPlatform,C10_Hero,C3_Case3,C5_CloakCase,CW_WestAisle,CE_EntryDown"
for P in $PRESETS; do
  date
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/$P/ref_aspect" > "$D/render_${P}_c1.log" 2>&1
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams "$CAMS" --out "$D/$P" > "$D/render_${P}.log" 2>&1
done
date
grep -h "rendered" "$D"/render_*.log
