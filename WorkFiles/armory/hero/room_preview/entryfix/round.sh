#!/usr/bin/env bash
# entryfix r2: one test-copy round. Usage: bash round.sh <tag> [build|render|walk|all]   (writes only inside entryfix/)
set -e
TAG=$1; WHAT=${2:-all}
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/Cody/Desktop/Blender_Projects"
E="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/entryfix"
R="$E/renders/$TAG"
cd "$ROOT"
if [ "$WHAT" = build ] || [ "$WHAT" = all ]; then
  "$BL" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$E" > "$E/build_log_$TAG.txt" 2>&1
  grep -E "QA|hard|Traceback|Error" "$E/build_log_$TAG.txt" | tail -5
  py -3 -B "$E/add_review_cams.py"
fi
if [ "$WHAT" = walk ] || [ "$WHAT" = all ]; then
  "$BL" -b --factory-startup "$E/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$E/walk_log_$TAG.txt" 2>&1
  grep -o "entry_steps_ok.*" "$E/walk_log_$TAG.txt" | tail -1
fi
if [ "$WHAT" = render ] || [ "$WHAT" = all ]; then
  mkdir -p "$R/ref_aspect"
  "$BL" -b --factory-startup "$E/ArmoryKit_preview.blend" --python Scripts/armory/render_armory.py -- --layout "$E/layout.json" \
      --cams C1_EntryReveal --res 1448x1086 --out "$R/ref_aspect" > "$E/renders_${TAG}_a.log" 2>&1
  "$BL" -b --factory-startup "$E/ArmoryKit_preview.blend" --python Scripts/armory/render_armory.py -- --layout "$E/layout.json" \
      --cams C1_EntryReveal,CX_FromPlatform,CE_EntryDown,CE_BarFromMat --res 1600x900 --out "$R" > "$E/renders_${TAG}_b.log" 2>&1
  grep -c "^rendered" "$E/renders_${TAG}_a.log" "$E/renders_${TAG}_b.log"
fi
