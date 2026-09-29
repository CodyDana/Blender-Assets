#!/bin/bash
# r20 test copy round 2: build + walk + extra review cameras + plan drawing (renders: render_set.sh)
# usage: bash run_b.sh <tag>   -> WorkFiles/armory/hero/room_preview/r20/<tag>
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
R="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r20"
D="$R/$1"
mkdir -p "$D"
rm -rf "$D/Textures"; cp -r "$R/b2/Textures" "$D/"
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'])
[print('  BLOCK',k,v['first_block']) for k,v in d['routes'].items() if not v['clear'] and 'CONTROL' not in k]
"
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'] += [
 {'name':'CR_RearHigh','loc':[6.0,12.6,4.3],'look_at':[6.0,19.2,1.1],'lens_mm':22},
 # b3 (judge delta 8): the b2 overview stood at Y 0.70, +4.45, inside the entrance lintel (+4.30-4.72); now behind it,
 # under the cross beams' soffit (+4.40)
 {'name':'CO_Overview','loc':[6.0,1.5,4.2],'look_at':[6.0,10.5,0.0],'lens_mm':18},
 # b3 (judge delta 9): a 3/4 exterior from the south-west over the courtyard wall: the west long wall, eaves and roof
 {'name':'CE_Exterior34','loc':[-6.0,-10.5,10.0],'look_at':[6.0,9.0,1.5],'lens_mm':18,'exposure_ev':{'golden':-2.8,'night':0.3}},
 # round 3: the player's eye-level view from the courtyard's south-west corner along the west wall
 {'name':'CE_PlayerSW','loc':[-3.5,-3.0,1.7],'look_at':[3.0,12.0,3.0],'lens_mm':20,'exposure_ev':{'golden':-2.8,'night':0.3}},
]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
mkdir -p "$D/plan"
"/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/armory/armory_layout.py --layout "$D/layout.json" --out "$D/plan" > "$D/plan_log.txt" 2>&1 || echo "plan drawing failed"
echo built "$D"
