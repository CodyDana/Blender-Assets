#!/bin/bash
# r20 fix round (blind judge 7/10 deltas): build the test copy INTO r20 (keeps r20/Textures: the r20 painting sheet, the
# mat's sets and the new T_AK_HEntRib), walk check, review cameras, plan drawing. usage: bash run_f.sh
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r20"
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1 || { tail -30 "$D/build_log.txt"; exit 1; }
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'], 'routes', sum(v['clear'] for k,v in d['routes'].items() if 'CONTROL' not in k), '/', sum(1 for k in d['routes'] if 'CONTROL' not in k), 'max up', max(v['max_step_up_m'] for k,v in d['routes'].items() if 'CONTROL' not in k))
[print('  BLOCK',k,v['first_block']) for k,v in d['routes'].items() if not v['clear'] and 'CONTROL' not in k]
[print('  CONTROL',k,v['first_block']) for k,v in d['routes'].items() if 'CONTROL' in k]
"
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'] += [{'name':'CE_EntryDown','loc':[4.4,4.9,2.5],'look_at':[5.4,1.7,-0.1],'lens_mm':24},
 {'name':'CS_StairFoot','loc':[6.0,13.4,1.65],'look_at':[6.0,17.4,0.6],'lens_mm':28}]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
mkdir -p "$D/plan"
"/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/armory/armory_layout.py --layout "$D/layout.json" --out "$D/plan" > "$D/plan_log.txt" 2>&1 || echo "plan drawing failed"
echo built "$D"
