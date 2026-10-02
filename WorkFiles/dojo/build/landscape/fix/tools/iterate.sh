#!/usr/bin/env bash
# fix round: one full iteration. iterate.sh <it> [showcase_steps]   (each step guarded by its own runner)
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/landscape/fix
IT=$1; SC=${2:-}
if [ -n "$SC" ]; then bash Scripts/dojo/unreal/run_showcase_unreal.sh $SC 2>&1 | grep -E "exit|STOP" || exit 4; fi
DJ_LS_STEPS="landscape,foam,fx" DJ_LS_OUT="C:/Users/Cody/Desktop/Blender_Projects/$F/json/ls_materials_fix.json" \
  bash $F/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_ls_materials.py ls_materials_$IT | grep exit
(cd Scripts/dojo/landscape && py -3 -B make_terrain.py | tail -1 && py -3 -B make_world_layout.py | tail -1)
bash $F/tools/run_world.sh ls_world_$IT 2>&1 | grep -E "exit|removed"
DJ_FXL_OUT="C:/Users/Cody/Desktop/Blender_Projects/$F/json/fxl_place.json" \
  bash $F/tools/run_ue.sh C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/dj_fxl_place.py fxl_place_$IT | grep exit
bash $F/tools/capture.sh $IT 2>&1 | tail -1
py -3 -B Scripts/dojo/landscape/measure_landscape.py $F/caps/$IT > /dev/null
py -3 -B Scripts/dojo/landscape/measure_fxlight.py $F/caps/$IT > $F/caps/$IT/fxl_measure.txt 2>&1
py -3 -B $F/tools/measure_fix.py $F/caps/$IT > /dev/null
echo ITERATION_DONE $IT
