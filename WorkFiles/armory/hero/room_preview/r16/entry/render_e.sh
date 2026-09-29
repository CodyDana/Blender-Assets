#!/bin/bash
# r16 entry renders into r16/entry/<outdir> (default final): render_e.sh [outdir] [presets] [cams|none]
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/entry"
O="$D/${1:-final}"; PRESETS="${2:-golden night}"; CAMS="${3:-CE_EntryDown,CE_EntryFront}"
mkdir -p "$O"
for P in $PRESETS; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$O/$P/ref_aspect" > "$O/render_${P}_c1.log" 2>&1
  if [ "$CAMS" != "none" ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams "$CAMS" --out "$O/$P" > "$O/render_${P}.log" 2>&1
  fi
done
echo done
