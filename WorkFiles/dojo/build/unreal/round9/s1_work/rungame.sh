#!/usr/bin/env bash
# run_game_capture.ps1 on a cfg (guards inside the ps1). usage: rungame.sh <probe dir>
D="$1"
powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_game_capture.ps1' -Cfg "$(cygpath -w "$D/cfg.json")" -Log "$(cygpath -w "$D/game.log")"
echo "rc $?"; grep -o "DJ_STEP_DONE.*" "$D/game.log" | head -1
