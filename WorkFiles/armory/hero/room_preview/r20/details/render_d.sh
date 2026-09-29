#!/bin/bash
# render_d.sh <build dir (absolute)> [presets] [cams]
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="$1"; PRESETS="${2:-golden night}"; CAMS="${3:-CX_FromPlatform,C10_Hero,CR_RearHigh,CK_WestCorner,CK_EastCorner,CS_StairFootW}"
for P in $PRESETS; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/$P/ref_aspect" > "$D/render_${P}_c1.log" 2>&1
  if [ "$CAMS" != "none" ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams "$CAMS" --out "$D/$P" > "$D/render_${P}.log" 2>&1
  fi
done
echo done
