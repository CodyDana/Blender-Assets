#!/usr/bin/env bash
# FINISH stage: boundary re-run with the ISM-aware unwalkable rule, perf, captures (final + a noise run), one Unreal at a time
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/hall_armory/finish
DJ_PARTS=routes,interior,rearroof,stair DJ_OUT=ue_boundary_walk.json bash $F/checks/ue/run_ue.sh fin_ue_boundary.py fin_ue_boundary_walk.log
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $F/perf_probe/run_fp_game_perf.ps1)" -TimeoutMin 40 -VD "C:/Users/Cody/Desktop/Blender_Projects/$F/perf" | tail -1
(cd $F/perf_probe && py -3 -B fp_perf_csv.py "C:/Users/Cody/Desktop/Blender_Projects/$F/perf" | tail -20)
bash $F/tools/capture.sh final CAM_Ref2Match:1920x1440 CAM_LandscapeRef:1280x1920 CAM_DoorwayIn:1920x1080 CAM_AK_CW_WestAisle:1600x900 CAM_AK_C10_Hero:1600x900 2>&1 | tail -2
bash $F/tools/capture.sh noise CAM_Ref2Match:1920x1440 2>&1 | tail -2
echo REST_DONE
