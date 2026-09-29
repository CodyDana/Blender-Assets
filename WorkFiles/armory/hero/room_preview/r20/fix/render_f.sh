#!/bin/bash
# r20 fix round renders into r20/<outdir> (default final): render_f.sh [outdir] [presets] [cams]
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r20"
O="$D/${1:-final}"; PRESETS="${2:-golden night}"; CAMS="${3:-C3_Case3,C10_Hero,CW_WestAisle,CX_FromPlatform,CG_Garden,CE_EntryDown}"
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
