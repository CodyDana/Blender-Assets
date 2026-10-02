#!/usr/bin/env bash
# capture.sh <subdir> : the FX + lighting stage's stills into a FRESH folder fxlight/caps/<subdir> (-game HighResShot)
set -u
O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight"
D="$O/caps/$1"
rm -rf "$D"; mkdir -p "$D"
py -3 -B - "$D" <<'PY'
import json, sys
d = sys.argv[1]
shots = [("CAM_LandscapeRef", 1280, 1920), ("CAM_RiverRapids", 1920, 1080), ("CAM_StairPath", 1920, 1080),
         ("CAM_TerraceWall", 1920, 1080), ("CAM_FromGateOut", 1920, 1080), ("CAM_Ref2Match", 1920, 1440),
         ("CAM_Overview", 1920, 1080), ("CAM_PlayerEyeSand", 1920, 1080), ("CAM_PeaksOverHall", 1920, 1080),
         ("CAM_Drum", 1920, 1080), ("CAM_HallVeranda", 1920, 1080), ("CU_HallUpperRoof", 1920, 1080),
         ("CU_Lantern", 1920, 1080), ("CAM_EastYard", 1920, 1080), ("CU_SandEye", 1920, 1080), ("CU_Training", 1920, 1080)]
cfg = {"out_dir": d, "report": d + "/game_capture.json", "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 14,
       "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"],
       "shots": [{"name": n, "w": w, "h": h} for n, w, h in shots]}
json.dump(cfg, open(d + "/cfg.json", "w"), indent=1)
PY
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal\run_game_capture.ps1" -Cfg "$(cygpath -w "$D/cfg.json")" -Log "$(cygpath -w "$D/game.log")" -TimeoutMin 40 | tail -1
grep "DJ_STEP_DONE" "$D/game.log" | cut -c1-160
