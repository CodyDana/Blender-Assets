#!/bin/bash
# r17 live night renders: C1 at 1448x1086 (ref_aspect), then C1, CX, C10, C3, C5, CW, C4, CG at 1600x900
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; P="C:/Users/Cody/Desktop/Blender_Projects"
D="$P/WorkFiles/armory/build/renders/night_r17"; R="$P/Scripts/armory/render_armory.py"
"$B" -b --factory-startup "$P/Assets/Armory/ArmoryKit.blend" --python "$R" -- --layout "$P/WorkFiles/armory/build/layout.json" --preset night --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/log_ref_aspect.txt" 2>&1 || echo FAIL ref_aspect
"$B" -b --factory-startup "$P/Assets/Armory/ArmoryKit.blend" --python "$R" -- --layout "$P/WorkFiles/armory/build/layout.json" --preset night --cams C1_EntryReveal,CX_FromPlatform,C10_Hero,C3_Case3,C5_CloakCase,CW_WestAisle,C4_ShurikenTray,CG_Garden --res 1600x900 --out "$D" > "$D/log.txt" 2>&1 || echo FAIL main
grep -h "rendered" "$D"/log*.txt | wc -l
