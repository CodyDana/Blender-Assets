#!/usr/bin/env bash
# FINISH stage, final pass after the ISM trial: sync (single actors: the armory masters lack the ISM usage flag), the
# idempotency proof, sc_verify, the walk / interior / stair checks, perf without ProfileGPU, captures (final + noise)
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/hall_armory/finish
DL="/c/Users/Cody/Documents/Unreal Projects/DojoLab/Content"
bash Scripts/dojo/unreal/run_armory_sync.sh 2>&1 | grep exit
cp WorkFiles/dojo/build/unreal/armory_sync/sync.json $F/json/sync_final_run1.json
st(){ (cd "$DL"; for f in Dojo/Maps/L_Dojo.umap ArmoryHall/Materials/*.uasset; do echo "$(md5sum "$f" | cut -c1-32) $(stat -c %Y "$f") $f"; done; find . -type f -newer "$1" -printf "NEWER %P\n") ; }
touch $F/json/idem_marker_final; sleep 2; st $F/json/idem_marker_final > $F/json/idem_final_before.txt
bash Scripts/dojo/unreal/run_armory_sync.sh 2>&1 | grep exit
st $F/json/idem_marker_final > $F/json/idem_final_after.txt
cp WorkFiles/dojo/build/unreal/armory_sync/sync.json $F/json/sync_final_run2_idempotent.json
diff $F/json/idem_final_before.txt $F/json/idem_final_after.txt > /dev/null && echo "IDEMPOTENT identical $(wc -l < $F/json/idem_final_after.txt) newer=$(grep -c NEWER $F/json/idem_final_after.txt)" || echo "IDEMPOTENT DIFFERS"
bash Scripts/dojo/unreal/run_showcase_unreal.sh verify 2>&1 | grep -E "exit|STOP"
cp WorkFiles/dojo/build/unreal/showcase/verify.json $F/checks/sc_verify_final.json
DJ_PARTS=routes,interior,rearroof,stair DJ_OUT=ue_boundary_walk_final.json bash $F/checks/ue/run_ue.sh fin_ue_boundary.py fin_ue_boundary_walk_final.log
DJ_ZB0=0.13 DJ_PARTS=flood,flood35 DJ_OUT=ue_alley_interior_final.json bash $F/checks/ue/run_ue.sh fin_ue_alley.py fin_ue_alley_interior_final.log
rm -f $F/perf/game_perf_guard.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $F/perf_probe/run_fp_game_perf.ps1)" -TimeoutMin 40 -VD "C:/Users/Cody/Desktop/Blender_Projects/$F/perf" | tail -1
(cd $F/perf_probe && py -3 -B fp_perf_csv.py "C:/Users/Cody/Desktop/Blender_Projects/$F/perf" | tail -18)
bash $F/tools/capture.sh final CAM_Ref2Match:1920x1440 CAM_LandscapeRef:1280x1920 CAM_DoorwayIn:1920x1080 CAM_AK_CW_WestAisle:1600x900 CAM_AK_C10_Hero:1600x900 2>&1 | tail -1
bash $F/tools/capture.sh noise CAM_Ref2Match:1920x1440 CAM_AK_CW_WestAisle:1600x900 CAM_AK_C10_Hero:1600x900 2>&1 | tail -1
echo FINAL_DONE
