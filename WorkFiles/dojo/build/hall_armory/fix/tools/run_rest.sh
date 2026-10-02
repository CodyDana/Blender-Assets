#!/usr/bin/env bash
# HALL + ARMORY FIX round: perf, the final -game captures, the live-noise second run of the courtyard / landscape views,
# and the sheets (one Unreal at a time; every runner waits on any UnrealEditor-Cmd).
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
U=WorkFiles/dojo/build/hall_armory/fix
A=C:/Users/Cody/Desktop/Blender_Projects/$U
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $A/checks/perf/run_ha_game_perf.ps1)" -TimeoutMin 45 | tail -1
(cd $U/checks/perf && py -3 -B ha_perf_csv.py | tail -1)
bash $U/tools/capture.sh final 2>&1 | tail -2
bash $U/tools/capture_noise.sh noise CAM_Ref2Match:1920x1440 CAM_PlayerEyeSand:1920x1080 CAM_HallVeranda:1920x1080 \
  CAM_LandscapeRef:1280x1920 CAM_Overview:1920x1080 CAM_FromGateOut:1920x1080 CAM_EastYard:1920x1080 \
  CU_HallUpperRoof:1920x1080 CAM_Drum:1920x1080 CU_SandEye:1920x1080 CU_Training:1920x1080 CU_Lantern:1920x1080 \
  CAM_RiverRapids:1920x1080 CAM_StairPath:1920x1080 CAM_TerraceWall:1920x1080 CAM_PeaksOverHall:1920x1080 2>&1 | tail -2
py -3 -B Scripts/dojo/hall/ha_sheets.py $A/caps/final $A/caps/noise
py -3 -B Scripts/dojo/landscape/measure_landscape.py $A/caps/final | tail -2
echo REST_DONE
