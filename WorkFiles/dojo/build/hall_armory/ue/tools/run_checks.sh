#!/usr/bin/env bash
# HALL + ARMORY round, DojoLab stage: every Unreal functional check in fresh read-only commandlets, one at a time
# (each runner waits on any UnrealEditor-Cmd and stops if a DojoLab editor is open). Outputs in hall_armory/ue/checks/.
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
U=WorkFiles/dojo/build/hall_armory/ue
A=C:/Users/Cody/Desktop/Blender_Projects/$U
bash Scripts/dojo/unreal/run_showcase_unreal.sh verify 2>&1 | grep -E "exit|STOP"
cp WorkFiles/dojo/build/unreal/showcase/verify.json $U/checks/sc_verify.json
DJ_LS_VOUT="$A/checks/ls_verify.json" bash $U/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_verify.py ha_ls_verify | grep exit
DJ_FXL_OUT="$A/json/fxl_place.json" DJ_FXL_VOUT="$A/checks/fxl_verify.json" bash $U/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_fxl_verify.py ha_fxl_verify | grep exit
bash $U/checks/ue/run_ue_checks.sh r6_ue_alley_replay.py r6_ue_alley_flood.py r6_ue_pocket_probe.py r6_ue_pocket_probe2.py
DJ_PARTS=height,routes,stair,flood1v1,floodbr DJ_OUT=ue_boundary_a.json bash $U/checks/ue/run_ha_ue.sh ha_ue_boundary.py ue_boundary_a.log
CEIL=$(py -3 -B -c "import json;print(json.load(open('$U/checks/ue/ue_boundary_a.json'))['ceiling_bottom_m'])")
DJ_CEIL=$CEIL DJ_PARTS=arcs1v1 DJ_OUT=ue_boundary_arcs1v1.json bash $U/checks/ue/run_ha_ue.sh ha_ue_boundary.py ue_boundary_arcs1v1.log
echo CHECKS_DONE
