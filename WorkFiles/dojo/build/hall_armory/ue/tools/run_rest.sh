#!/usr/bin/env bash
# HALL + ARMORY round, DojoLab stage: the second pass of checks, perf and the final captures (one Unreal at a time)
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
U=WorkFiles/dojo/build/hall_armory/ue
A=C:/Users/Cody/Desktop/Blender_Projects/$U
bash $U/checks/ue/rerun.sh
DJ_FXL_OUT="$A/json/fxl_place.json" DJ_FXL_VOUT="$A/checks/fxl_verify.json" bash $U/tools/run_fx.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_fxl_verify.py ha_fxl_verify | grep -E "exit|removed"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $A/checks/perf/run_ha_game_perf.ps1)" -TimeoutMin 45 | tail -1
(cd $U/checks/perf && py -3 -B ha_perf_csv.py | tail -1)
bash $U/tools/capture.sh final 2>&1 | tail -2
echo REST_DONE
