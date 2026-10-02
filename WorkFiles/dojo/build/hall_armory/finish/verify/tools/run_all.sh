#!/usr/bin/env bash
# VERIFIER (finish stage) master run: ONE Unreal process at a time, sequential. Outputs in finish/verify/.
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
V=WorkFiles/dojo/build/hall_armory/finish/verify
A=C:/Users/Cody/Desktop/Blender_Projects/$V
S=C:/Users/Cody/Desktop/Blender_Projects/Scripts
log(){ echo "$(date '+%F %T') $*" | tee -a $V/logs/run_all.txt; }
log "=== sync run 1"
bash Scripts/dojo/unreal/run_armory_sync.sh > $V/logs/sync_run1.out 2>&1; log "sync1 exit $?: $(grep -o 'DJ_STEP_DONE.*' WorkFiles/dojo/build/unreal/armory_sync/logs/sync.log | head -1)"
cp WorkFiles/dojo/build/unreal/armory_sync/sync.json $V/json/sync_run1.json; cp WorkFiles/dojo/build/unreal/armory_sync/files.json $V/json/files_run1.json; cp WorkFiles/dojo/build/unreal/armory_sync/logs/sync.log $V/logs/sync_run1.log
py -3 -B $V/tools/snap.py snap $V/json/snap_dojolab_S1.json
log "=== sync run 2"
bash Scripts/dojo/unreal/run_armory_sync.sh > $V/logs/sync_run2.out 2>&1; log "sync2 exit $?: $(grep -o 'DJ_STEP_DONE.*' WorkFiles/dojo/build/unreal/armory_sync/logs/sync.log | head -1)"
cp WorkFiles/dojo/build/unreal/armory_sync/sync.json $V/json/sync_run2.json; cp WorkFiles/dojo/build/unreal/armory_sync/files.json $V/json/files_run2.json; cp WorkFiles/dojo/build/unreal/armory_sync/logs/sync.log $V/logs/sync_run2.log
py -3 -B $V/tools/snap.py snap $V/json/snap_dojolab_S2.json
py -3 -B $V/tools/snap.py diff $V/json/snap_dojolab_S0.json $V/json/snap_dojolab_S1.json > $V/json/diff_S0_S1.json
py -3 -B $V/tools/snap.py diff $V/json/snap_dojolab_S1.json $V/json/snap_dojolab_S2.json > $V/json/diff_S1_S2.json
log "=== sc_verify"
bash Scripts/dojo/unreal/run_showcase_unreal.sh verify > $V/logs/sc_verify.out 2>&1; log "sc_verify exit $?"
cp WorkFiles/dojo/build/unreal/showcase/verify.json $V/json/sc_verify.json
log "=== ls_verify"
DJ_LS_VOUT="$A/json/ls_verify.json" bash $V/tools/run_ue_v.sh $S/dojo/landscape/dj_ls_verify.py ls_verify.log
log "=== boundary"
DJ_PARTS=height,routes,interior,rearroof,stair,flood1v1,floodbr DJ_OUT=ue_boundary.json bash $V/tools/run_ue_v.sh $A/ue/v_ue_boundary.py ue_boundary.log
log "=== perf"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w $V/perf_tools/run_fp_game_perf.ps1)" -TimeoutMin 40 -VD "$A/perf" > $V/logs/perf.out 2>&1; log "perf: $(tail -1 $V/logs/perf.out)"
(cd $V/perf_tools && py -3 -B fp_perf_csv.py "$A/perf" > $A/logs/perf_csv.out 2>&1); log "perf csv done"
log "=== capture Ref2Match x2"
bash $V/tools/capture_v.sh final CAM_Ref2Match:1920x1440 > $V/logs/cap_final.out 2>&1; log "cap final: $(tail -1 $V/logs/cap_final.out)"
bash $V/tools/capture_v.sh noise CAM_Ref2Match:1920x1440 > $V/logs/cap_noise.out 2>&1; log "cap noise: $(tail -1 $V/logs/cap_noise.out)"
log "=== alley (long)"
DJ_ZB0=0.13 DJ_PARTS=mantle,flood,flood35,floodbr,arcs DJ_OUT=ue_alley.json bash $V/tools/run_ue_v.sh $A/ue/v_ue_alley.py ue_alley.log
py -3 -B $V/tools/snap.py snap $V/json/snap_dojolab_S3.json
py -3 -B $V/tools/snap.py diff $V/json/snap_dojolab_S2.json $V/json/snap_dojolab_S3.json > $V/json/diff_S2_S3.json
log "ALL_DONE"
