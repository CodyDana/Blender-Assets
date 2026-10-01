#!/bin/bash
# r20 final2 (combined, judge fixes: cases + floor/moon look + Unreal-side changes): night + golden; C1 at 1448x1086 (ref_aspect) and
# 1600x900 with CX, CW, C10, C3, C4, C5; then the neutral-light floor swatch of the built M_AK_Plank (as built, no overrides)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r20/final2"; R=/c/Users/Cody/Desktop/Blender_Projects/Scripts/armory/render_armory.py
CAMS=C1_EntryReveal,CX_FromPlatform,CW_WestAisle,C10_Hero,C3_Case3,C4_ShurikenTray,C5_CloakCase
for P in night golden; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/render_${P}_c1ref.log" 2>&1 || echo FAIL $P c1ref
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams $CAMS --res 1600x900 --out "$D" > "$D/render_${P}.log" 2>&1 || echo FAIL $P
done
mkdir -p "$D/swatch"
"$B" -b --factory-startup --python "$D/work/floor_swatch.py" -- --src "$D/ArmoryKit_preview.blend" --out "$D/swatch" --tag r20final2 > "$D/swatch/swatch.log" 2>&1 || echo FAIL swatch
grep -h "^rendered" "$D"/render_*.log | wc -l
