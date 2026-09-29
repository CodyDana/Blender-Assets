#!/bin/bash
# render.sh <outname> [presets] [c1|corners|both]: C1 at 1448x1086 + the two corner views, into niches/<outname>/<preset>
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/niches"
O="$D/$1"; PRESETS="${2:-golden night}"; WHAT="${3:-both}"
mkdir -p "$O"
py -3 "$D/work/cams.py" "$D"
for P in $PRESETS; do
  if [ "$WHAT" != corners ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$O/$P/ref_aspect" > "$O/render_${P}_c1.log" 2>&1
  fi
  if [ "$WHAT" != c1 ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams CN_WestNiche,CN_EastNiche --res 1200x900 --out "$O/$P" > "$O/render_${P}.log" 2>&1
  fi
done
echo done
