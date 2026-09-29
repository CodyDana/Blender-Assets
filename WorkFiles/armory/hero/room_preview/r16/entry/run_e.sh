#!/bin/bash
# r16 entry round (mat + step beam): build the test copy INTO r16/entry (its Textures/ holds the new T_AK_HEntCoirB /
# HEntTimberP / HEntTimberF), walk check, review cameras. usage: bash run_e.sh
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/entry"
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1 || { tail -30 "$D/build_log.txt"; exit 1; }
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
R=d['routes']
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'], 'routes', sum(v['clear'] for k,v in R.items() if 'CONTROL' not in k), '/', sum(1 for k in R if 'CONTROL' not in k), 'max up', max(v['max_step_up_m'] for k,v in R.items() if 'CONTROL' not in k))
[print('  BLOCK',k,v['first_block']) for k,v in R.items() if not v['clear'] and 'CONTROL' not in k]
[print('  CONTROL',k,v['first_block']) for k,v in R.items() if 'CONTROL' in k]
[print('  ENTRY',k,v['max_step_up_m'],v['max_step_down_m']) for k,v in R.items() if k in ('outside_through_entrance_to_mat','mat_up_the_step_beam_to_case1','genkan_axis_up_the_beam')]
"
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'] += [{'name':'CE_EntryDown','loc':[4.4,4.9,2.5],'look_at':[5.4,1.7,-0.1],'lens_mm':24},
 {'name':'CE_EntryFront','loc':[6.0,-0.9,1.75],'look_at':[6.0,2.35,-0.1],'lens_mm':28}]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
echo built "$D"
