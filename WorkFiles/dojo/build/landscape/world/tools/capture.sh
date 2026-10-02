#!/usr/bin/env bash
# capture.sh <subdir> : the landscape-round shots into a FRESH folder caps/<subdir> (dj_game_capture detects new PNG names)
set -u
W="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/world"
D="$W/caps/$1"
rm -rf "$D"; mkdir -p "$D"
py -3 -B - "$D" <<'PY'
import json, sys
d = sys.argv[1]
base = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/world/caps/cfg.json"))
base["out_dir"] = d
base["report"] = d + "/game_capture.json"
json.dump(base, open(d + "/cfg.json", "w"), indent=1)
PY
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_game_capture.ps1" -Cfg "$(cygpath -w "$D/cfg.json")" -Log "$(cygpath -w "$D/game.log")" -TimeoutMin 40 | tail -1
grep "DJ_STEP_DONE" "$D/game.log" | cut -c1-160
