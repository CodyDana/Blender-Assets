#!/bin/bash
# r16 stairs+cases round: build the test copy INTO r16/stairs, walk check, review cameras. usage: bash run.sh [tex]
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/stairs"
if [ "$1" = "tex" ]; then   # the painting sheet for the new paper range (hero_backwall PAPER_Z0 / IMG_Z0), into D/Textures only
  "$B" -b --factory-startup --python Scripts/armory/hero/tex_backwall.py -- tall --out "$D/Textures" > "$D/tex_log.txt" 2>&1 || { tail -20 "$D/tex_log.txt"; exit 1; }
  grep wrote "$D/tex_log.txt"
fi
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
d['cameras'] += [{'name':'CS_Flight','loc':[6.0,13.4,1.65],'look_at':[6.0,17.4,0.45],'lens_mm':28},
 {'name':'CS_FlightSide','loc':[3.2,14.2,1.5],'look_at':[6.0,16.6,0.35],'lens_mm':28}]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
echo built "$D"
