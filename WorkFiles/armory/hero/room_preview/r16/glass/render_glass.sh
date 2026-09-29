#!/bin/bash
# glass-bug renders: C1 1448x1086 + the case-6 close view, golden + night (fix), and night with the old budget of 8 (before)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/glass"
for P in night golden; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$D/diag/pre_tb.py" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/renders/$P/ref_aspect" > "$D/render_${P}_c1.log" 2>&1
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$D/diag/pre_tb.py" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams CG6_Case6Glass --out "$D/renders/$P" > "$D/render_${P}_close.log" 2>&1
done
export TB=8
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$D/diag/pre_tb.py" --python "$ROOT/Scripts/armory/render_armory.py" -- \
  --layout "$D/layout_cams.json" --preset night --cams C1_EntryReveal --res 1448x1086 --out "$D/renders/before_tb8/night/ref_aspect" > "$D/render_before_c1.log" 2>&1
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$D/diag/pre_tb.py" --python "$ROOT/Scripts/armory/render_armory.py" -- \
  --layout "$D/layout_cams.json" --preset night --cams CG6_Case6Glass --out "$D/renders/before_tb8/night" > "$D/render_before_close.log" 2>&1
grep -h -E "PRE|rendered" "$D"/render_*.log
