#!/bin/bash
# r18 niche round renders: <outname> -> C1 at 1448x1086 (ref aspect) + CN_WestNiche / CN_EastNiche at 1600x900, golden + night
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT=/c/Users/Cody/Desktop/Blender_Projects
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r18/niche"
O="$D/$1"; mkdir -p "$O"
py -3 - "$D" <<'PY'
import json, sys
D = sys.argv[1]; d = json.load(open(D + "/layout.json"))
extra = [{"name": "CN_WestNiche", "loc": [3.1, 16.9, 1.9], "look_at": [1.05, 19.6, 1.45], "lens_mm": 30},
         {"name": "CN_EastNiche", "loc": [8.9, 16.9, 1.9], "look_at": [10.95, 19.6, 1.45], "lens_mm": 30}]
d["cameras"] = [c for c in d["cameras"] if c["name"] not in {e["name"] for e in extra}] + extra
json.dump(d, open(D + "/layout_cams.json", "w"), indent=1)
PY
for P in ${2:-golden night}; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout_cams.json" --preset $P --cams CN_WestNiche,CN_EastNiche --res 1600x900 --out "$O/$P" > "$O/render_${P}.log" 2>&1 || echo FAIL $P
  if [ "$3" != corners ]; then
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$ROOT/Scripts/armory/render_armory.py" -- \
    --layout "$D/layout.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$O/$P/ref_aspect" > "$O/render_${P}_c1.log" 2>&1 || echo FAIL $P c1
  fi
done
grep -h "^rendered" "$O"/render_*.log
