#!/bin/bash
# r16 COMBINED test copy (stairs+cases, glass, corner niches, wall bays, entry): textures, build, walk, cameras.
# r16 fix round (2026-09-29): + HEntCoirL (the looped-row coir); the tall painting regenerated for PAPER_IMG_W 2.36
# usage: bash run_final.sh [tex]
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
BPY="/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r16/final"
if [ "$1" = "tex" ]; then
  "$BPY" Scripts/armory/hero/tex_entrance.py HEntCoirB HEntCoirL HEntTimberP HEntTimberF --out "$D/Textures" > "$D/tex_entrance_log.txt" 2>&1 || { tail -20 "$D/tex_entrance_log.txt"; exit 1; }
  "$B" -b --factory-startup --python Scripts/armory/hero/tex_walls.py -- --out "$D/Textures" --board > "$D/tex_walls_log.txt" 2>&1 || { tail -20 "$D/tex_walls_log.txt"; exit 1; }
  "$B" -b --factory-startup --python Scripts/armory/hero/tex_backwall.py -- tall --out "$D/Textures" > "$D/tex_backwall_log.txt" 2>&1 || { tail -20 "$D/tex_backwall_log.txt"; exit 1; }
  ls "$D/Textures"
fi
"$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1 || { tail -30 "$D/build_log.txt"; exit 1; }
grep "QA" "$D/build_log.txt" | tail -3
"$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
R=d['routes']
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'], 'routes', sum(v['clear'] for k,v in R.items() if 'CONTROL' not in k), '/', sum(1 for k in R if 'CONTROL' not in k), 'max up', max(v['max_step_up_m'] for k,v in R.items() if 'CONTROL' not in k))
[print('  BLOCK',k,v['first_block']) for k,v in R.items() if not v['clear'] and 'CONTROL' not in k]
[print('  CONTROL',k,v['first_block']) for k,v in R.items() if 'CONTROL' in k]
"
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'] += [{'name':'CE_EntryDown','loc':[4.4,4.9,2.5],'look_at':[5.4,1.7,-0.1],'lens_mm':24},
 {'name':'CE_EntryFront','loc':[6.0,-0.9,1.75],'look_at':[6.0,2.35,-0.1],'lens_mm':28}]
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
print([c['name'] for c in d['cameras']])
"
echo built "$D"
