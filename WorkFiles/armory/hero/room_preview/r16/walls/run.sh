#!/bin/bash
# r16 walls round: build the test copy into r16/walls, walk check. usage: bash run.sh
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/walls"
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1 || { tail -30 "$D/build_log.txt"; exit 1; }
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'], 'routes', sum(v['clear'] for k,v in d['routes'].items() if 'CONTROL' not in k), '/', sum(1 for k in d['routes'] if 'CONTROL' not in k), 'max up', max(v['max_step_up_m'] for k,v in d['routes'].items() if 'CONTROL' not in k))
[print('  BLOCK',k,v['first_block']) for k,v in d['routes'].items() if not v['clear'] and 'CONTROL' not in k]
[print('  CONTROL',k,v['first_block']) for k,v in d['routes'].items() if 'CONTROL' in k]
"
echo built "$D"
