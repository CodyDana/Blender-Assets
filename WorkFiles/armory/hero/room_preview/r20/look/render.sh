#!/bin/bash
# r20 look: night + golden C1 (1448x1086), CW, CX, CG (1600x900) of the test copy. Usage: render.sh <outdir-name>
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; P="C:/Users/Cody/Desktop/Blender_Projects"
E="$P/WorkFiles/armory/hero/room_preview/r20/look"; R="$P/Scripts/armory/render_armory.py"; O="$E/${1:-renders}"
mkdir -p "$O/ref_aspect"
for PR in night golden; do
  "$B" -b --factory-startup "$E/ArmoryKit_preview.blend" --python "$R" -- --layout "$E/layout.json" --preset $PR --cams C1_EntryReveal --res 1448x1086 --out "$O/ref_aspect" > "$O/log_${PR}_c1.txt" 2>&1 || echo FAIL $PR c1
  "$B" -b --factory-startup "$E/ArmoryKit_preview.blend" --python "$R" -- --layout "$E/layout.json" --preset $PR --cams CW_WestAisle,CX_FromPlatform,CG_Garden --res 1600x900 --out "$O" > "$O/log_${PR}.txt" 2>&1 || echo FAIL $PR
done
grep -h "^rendered" "$O"/log_*.txt | wc -l
