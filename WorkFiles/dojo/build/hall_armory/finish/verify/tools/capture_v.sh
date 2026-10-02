#!/usr/bin/env bash
# VERIFIER copy of finish/tools/capture.sh: -game HighResShot stills into finish/verify/caps/<subdir>
set -u
O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/finish/verify"
D="$O/caps/$1"; shift
rm -rf "$D"; mkdir -p "$D"
py -3 -B - "$D" "$@" <<'PY'
import json, sys
d = sys.argv[1]
shots = [(a.split(":")[0], *map(int, a.split(":")[1].split("x"))) for a in sys.argv[2:]]
cfg = {"out_dir": d, "report": d + "/game_capture.json", "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 14,
       "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"],
       "shots": [{"name": n, "w": w, "h": h} for n, w, h in shots]}
json.dump(cfg, open(d + "/cfg.json", "w"), indent=1)
PY
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_game_capture.ps1" -Cfg "$(cygpath -w "$D/cfg.json")" -Log "$(cygpath -w "$D/game.log")" -TimeoutMin 50 | tail -1
grep "DJ_STEP_DONE" "$D/game.log" | cut -c1-200
