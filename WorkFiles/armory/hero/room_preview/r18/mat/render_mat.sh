#!/bin/bash
# r18 mat renders into r18/mat/<outdir>/<preset>: C1 1448x1086 (ref_aspect) + CE_MatDown / CE_EntryDown 1600x900
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r18/mat"
O="$D/${1:-final}"; PRESETS="${2:-night golden}"; CAMS="${3:-CE_MatDown,CE_EntryDown}"
mkdir -p "$O"
for P in $PRESETS; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$O/$P/ref_aspect" > "$O/render_${P}_c1.log" 2>&1
  if [ "$CAMS" != "none" ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams "$CAMS" --out "$O/$P" > "$O/render_${P}.log" 2>&1
  fi
done
grep -h "rendered" "$O"/render_*.log
