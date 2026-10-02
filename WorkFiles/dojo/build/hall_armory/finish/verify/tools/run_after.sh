#!/usr/bin/env bash
# VERIFIER: after run_all.sh, two captures with the landscape round's exact 16-shot list and order (CAM_Ref2Match shot
# at the same elapsed game time, so the UDS cloud layer is comparable), one Unreal at a time.
set -u
cd /c/Users/Cody/Desktop/Blender_Projects
V=WorkFiles/dojo/build/hall_armory/finish/verify
until grep -q ALL_DONE $V/logs/run_all.txt; do sleep 20; done
echo "$(date '+%F %T') === timed capture A" >> $V/logs/run_all.txt
bash $V/tools/capture_v.sh timedA CAM_LandscapeRef:1280x1920 CAM_RiverRapids:1920x1080 CAM_StairPath:1920x1080 CAM_TerraceWall:1920x1080 CAM_FromGateOut:1920x1080 CAM_Ref2Match:1920x1440 CAM_Overview:1920x1080 CAM_PlayerEyeSand:1920x1080 CAM_PeaksOverHall:1920x1080 CAM_Drum:1920x1080 CAM_HallVeranda:1920x1080 CU_HallUpperRoof:1920x1080 CU_Lantern:1920x1080 CAM_EastYard:1920x1080 CU_SandEye:1920x1080 CU_Training:1920x1080 > $V/logs/cap_timedA.out 2>&1; echo "$(date '+%F %T') timedA: $(tail -1 $V/logs/cap_timedA.out)" >> $V/logs/run_all.txt
bash $V/tools/capture_v.sh timedB CAM_LandscapeRef:1280x1920 CAM_RiverRapids:1920x1080 CAM_StairPath:1920x1080 CAM_TerraceWall:1920x1080 CAM_FromGateOut:1920x1080 CAM_Ref2Match:1920x1440 CAM_Overview:1920x1080 CAM_PlayerEyeSand:1920x1080 CAM_PeaksOverHall:1920x1080 CAM_Drum:1920x1080 CAM_HallVeranda:1920x1080 CU_HallUpperRoof:1920x1080 CU_Lantern:1920x1080 CAM_EastYard:1920x1080 CU_SandEye:1920x1080 CU_Training:1920x1080 > $V/logs/cap_timedB.out 2>&1; echo "$(date '+%F %T') timedB: $(tail -1 $V/logs/cap_timedB.out)" >> $V/logs/run_all.txt
py -3 -B $V/tools/snap.py snap $V/json/snap_dojolab_S4.json
py -3 -B $V/tools/snap.py diff $V/json/snap_dojolab_S0.json $V/json/snap_dojolab_S4.json > $V/json/diff_S0_S4.json
echo "$(date '+%F %T') AFTER_DONE" >> $V/logs/run_all.txt
