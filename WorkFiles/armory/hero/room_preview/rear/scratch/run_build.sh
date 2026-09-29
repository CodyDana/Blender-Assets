#!/bin/bash
# rear dais test copy: build + walk + renders into WorkFiles/armory/hero/room_preview/rear/<tag>
# usage: bash run_build.sh <tag> [skip-build]
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
R="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/rear"
D="$R/$1"
mkdir -p "$D"
if [ "$2" != "skip-build" ]; then
  rm -rf "$D/Textures"; cp -r "$R/Textures" "$D/"
  "$B" -b --factory-startup --python Scripts/armory/build_armory_kit.py -- --preview-dir "$D" > "$D/build_log.txt" 2>&1
  grep "QA:" "$D/build_log.txt"
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/walk_check.py > "$D/walk_log.txt" 2>&1
  py -3 -c "
import json;d=json.load(open(r'$D/walk_check.json'))
print('WALK passed',d['passed'],'control',d['control_blocked'],'entry',d['entry_steps_ok'])
[print('  BLOCK',k,v['first_block']) for k,v in d['routes'].items() if not v['clear'] and 'CONTROL' not in k]
"
fi
py -3 -c "
import json
d=json.load(open(r'$D/layout.json'))
d['cameras'].append({'name':'CR_RearHigh','loc':[6.0,8.6,4.3],'look_at':[6.0,15.2,1.1],'lens_mm':22})
json.dump(d,open(r'$D/layout_cams.json','w'),indent=1)
"
for P in golden night; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/render_armory.py -- --layout "$D/layout_cams.json" --out "$D/$P/ref_aspect" --preset $P --cams C1_EntryReveal --res 1448x1086 > "$D/render_${P}_c1.log" 2>&1
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python Scripts/armory/render_armory.py -- --layout "$D/layout_cams.json" --out "$D/$P" --preset $P --cams CX_FromPlatform,C10_Hero,CR_RearHigh > "$D/render_${P}.log" 2>&1
done
ls "$D"/golden "$D"/night "$D"/golden/ref_aspect "$D"/night/ref_aspect
