#!/usr/bin/env bash
# FINISH stage: the functional checks in fresh read-only commandlets, one at a time (each runner waits on any
# UnrealEditor-Cmd and stops if a DojoLab editor is open). Outputs in hall_armory/finish/checks/.
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/hall_armory/finish
A=C:/Users/Cody/Desktop/Blender_Projects/$F
bash Scripts/dojo/unreal/run_showcase_unreal.sh verify 2>&1 | grep -E "exit|STOP"
cp WorkFiles/dojo/build/unreal/showcase/verify.json $F/checks/sc_verify.json
DJ_LS_VOUT="$A/checks/ls_verify.json" bash $F/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_verify.py fin_ls_verify | grep exit
DJ_FXL_OUT="$A/json/fxl_place.json" DJ_FXL_VOUT="$A/checks/fxl_verify.json" bash $F/tools/run_fx.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_fxl_verify.py fin_fxl_verify | grep -E "exit|removed"
DJ_PARTS=height,routes,interior,rearroof,stair,flood1v1,floodbr DJ_OUT=ue_boundary.json bash $F/checks/ue/run_ue.sh fin_ue_boundary.py fin_ue_boundary.log
DJ_PARTS=mantle,flood,flood35,floodbr,arcs DJ_OUT=ue_alley.json bash $F/checks/ue/run_ue.sh fin_ue_alley.py fin_ue_alley.log
echo CHECKS_DONE
