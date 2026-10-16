#!/usr/bin/env bash
# SR01 W5 on the realism-round-2 bytes: new content folder, start sha256, passes A, A3, A2, B, C, E (Unreal, each a
# fresh process behind sr_guard.ps1), D (Blender headless), F (summary), end sha256. Stops at the first failed pass.
cd "$(dirname "$0")"
H="$(pwd)"
L=$H/w5_r2.log
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
echo "/Game/GunCheck/SR01_1016r2" > content_path.txt
mkdir -p ../scratch/w5_1014b_records && cp -n *.json ../scratch/w5_1014b_records/ 2>/dev/null
echo "w5 r2 start $(date +%T)" > $L
py -3 -B -c "import json,sr_common as C;json.dump(C.all_hashes(),open('SHA256_at_start.json','w'),indent=1);print('start files',len(C.all_hashes()))" >> $L 2>&1 || exit 1
run() { bash run_ue.sh "$1" "$2" "$3" >> $L 2>&1; r=$?; [ $r -eq 0 ] || { echo "PASS_FAIL $1 rc=$r" >> $L; exit 1; }
        grep -q "LogPython: Error" "$2" && { echo "PASS_FAIL $1 python error" >> $L; exit 1; }; return 0; }
run srA_import.py srA_import.log cmd
run srA3_abp.py srA3_abp.log tools
run srA2_level.py srA2_level.log cmd
run srB_verify.py srB_verify.log cmd
run srC_render.py srC_render.log render
powershell.exe -NoProfile -ExecutionPolicy Bypass -File run_game_ue.ps1 >> $L 2>&1 || { echo "PASS_FAIL E" >> $L; exit 1; }
# one headless Blender at a time: wait for the r2 chain's after stage (review renders) to finish
until grep -qE "MASTER_DONE|ABORT" ../scratch/r2/logs/master.log; do sleep 30; done
"$B" -b --factory-startup --python srD_analyse.py > srD_r2.log 2>&1
grep -q Traceback srD_r2.log && { echo "PASS_FAIL D" >> $L; exit 1; }
py -3 -B -c "import json,sr_common as C;json.dump(C.all_hashes(),open('SHA256_at_end.json','w'),indent=1)" >> $L 2>&1
py -3 -B srF_summary.py >> $L 2>&1
py -3 -c "import json;d=json.load(open('verification_summary.json'));g=d.get('gates',d.get('rows',[]));print('SUMMARY',d.get('status'),d.get('engine_verified'),d.get('content_path'))" >> $L 2>&1
echo "W5_R2_DONE $(date +%T)" >> $L
