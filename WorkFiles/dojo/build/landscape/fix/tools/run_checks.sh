#!/usr/bin/env bash
# fix round: every functional check in fresh processes on the final level (one Unreal process at a time)
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/landscape/fix
A=C:/Users/Cody/Desktop/Blender_Projects/$F
bash Scripts/dojo/unreal/run_showcase_unreal.sh verify 2>&1 | grep -E "exit|STOP"
cp WorkFiles/dojo/build/unreal/showcase/verify.json $F/checks/sc_verify.json 2>/dev/null
DJ_LS_VOUT="$A/checks/ls_verify.json" bash $F/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_verify.py ls_verify_final | grep exit
DJ_FXL_OUT="$A/json/fxl_place.json" DJ_FXL_VOUT="$A/checks/fxl_verify.json" bash $F/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_fxl_verify.py fxl_verify_final | grep exit
bash $F/checks/ue/run_ue_checks.sh r6_ue_alley_replay.py r6_ue_alley_flood.py r6_ue_pocket_probe.py r6_ue_pocket_probe2.py
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fix\checks\perf\run_v9_game_perf.ps1" | tail -2
py -3 -B $F/checks/perf/v9_perf_csv.py | tail -3
echo CHECKS_DONE
