#!/usr/bin/env bash
# probe.sh <name>: one -game HighResShot run with probe/<name>/cfg.json (fresh PNG folder)
set -u
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight/probe/$1"
find "$D" -name "*.png" -delete 2>/dev/null
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_game_capture.ps1" -Cfg "$(cygpath -w "$D/cfg.json")" -Log "$(cygpath -w "$D/game.log")" -TimeoutMin 40 | tail -1
grep "DJ_STEP_DONE" "$D/game.log" | cut -c1-200
