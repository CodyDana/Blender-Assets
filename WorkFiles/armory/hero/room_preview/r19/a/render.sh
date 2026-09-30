#!/bin/bash
# r19 a (reference order): night + golden; C1 at 1448x1086 (ref_aspect) and 1600x900 with CX, CW, C4, C5
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r19/a"; R=/c/Users/Cody/Desktop/Blender_Projects/Scripts/armory/render_armory.py
for P in night golden; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/render_${P}_c1ref.log" 2>&1 || echo FAIL $P c1ref
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams C1_EntryReveal,CX_FromPlatform,CW_WestAisle,C4_ShurikenTray,C5_CloakCase --res 1600x900 --out "$D" > "$D/render_${P}.log" 2>&1 || echo FAIL $P
done
grep -h "rendered" "$D"/render_*.log | wc -l
