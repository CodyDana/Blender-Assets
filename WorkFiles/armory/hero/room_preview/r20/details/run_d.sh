#!/bin/bash
# r20 rear round ("fix the rest"): build + walk + review cameras + plan drawing into details/<tag>
# usage: bash run_d.sh <tag>
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
R="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r20"
D="$R/details/$1"
mkdir -p "$D"
rm -rf "$D/Textures"; cp -r "$R/b2/Textures" "$D/"; cp -n "$R/../r20_mat/Textures/"* "$D/Textures/" 2>/dev/null || true  # the parallel mat session's new entrance sets (read only)
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1 || { tail -30 "$D/build_log.txt"; exit 1; }
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'], 'routes', sum(v['clear'] for k,v in d['routes'].items() if 'CONTROL' not in k), '/', sum(1 for k in d['routes'] if 'CONTROL' not in k), 'max up', max(v['max_step_up_m'] for k,v in d['routes'].items() if 'CONTROL' not in k))
[print('  BLOCK',k,v['first_block']) for k,v in d['routes'].items() if not v['clear'] and 'CONTROL' not in k]
"
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'] += [
 {'name':'CR_RearHigh','loc':[6.0,12.6,4.3],'look_at':[6.0,19.2,1.1],'lens_mm':22},
 {'name':'CO_Overview','loc':[6.0,1.5,4.2],'look_at':[6.0,10.5,0.0],'lens_mm':18},
 # rear round: a view of each rear corner (the corner niche, the rack alcove, the wing plinth, the stair-foot lantern)
 {'name':'CK_WestCorner','loc':[3.4,14.4,1.9],'look_at':[1.2,19.6,2.1],'lens_mm':26},
 {'name':'CK_EastCorner','loc':[8.6,14.4,1.9],'look_at':[10.8,19.6,2.1],'lens_mm':26},
 # rear round: the wing, the cheek and the stair-foot lantern at eye level from the west aisle
 {'name':'CS_StairFootW','loc':[4.3,13.2,1.65],'look_at':[3.3,16.4,0.6],'lens_mm':28},
]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
mkdir -p "$D/plan"
"/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/armory/armory_layout.py --layout "$D/layout.json" --out "$D/plan" > "$D/plan_log.txt" 2>&1 || echo "plan drawing failed"
echo built "$D"
