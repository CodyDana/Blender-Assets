#!/usr/bin/env bash
# Snow Flower v4 sword: full build, one Blender process per stage.  Usage: run_sword_build.sh [stages...]
set -e
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S="C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4/build_sword_game.py"
LOG="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_build/logs"
mkdir -p "$LOG"
STAGES=${@:-geo bake maps game export}
for st in $STAGES; do
  "$B" -b --factory-startup --python "$S" -- --stage $st > "$LOG/$st.log" 2>&1
  grep -E "\[SF4\]" "$LOG/$st.log" | tail -4
  if grep -q "Traceback" "$LOG/$st.log"; then echo "FAILED $st"; grep -A15 Traceback "$LOG/$st.log" | head -30; exit 1; fi
done
