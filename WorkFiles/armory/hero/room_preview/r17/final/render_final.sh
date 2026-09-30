#!/bin/bash
# r17 fix round renders: night + golden; C1 at 1448x1086 (ref_aspect) and 1600x900 with CX, C10, C3, C4, C5, CW, plus
# the niche (CN_*) and mat (CE_MatDown) close-ups from layout_cams.json (layout.json + the niche / mat rounds' cameras)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r17/final"; R=/c/Users/Cody/Desktop/Blender_Projects/Scripts/armory/render_armory.py
py -3 - "$D" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); lay = json.loads((d / "layout.json").read_text())
extra = [{"name": "CN_WestNiche", "loc": [3.1, 16.9, 1.9], "look_at": [1.05, 19.6, 1.45], "lens_mm": 30},
         {"name": "CN_EastNiche", "loc": [8.9, 16.9, 1.9], "look_at": [10.95, 19.6, 1.45], "lens_mm": 30},
         {"name": "CE_MatDown", "loc": [6.0, 3.3, 2.3], "look_at": [6.0, 1.85, -0.12], "lens_mm": 30}]
lay["cameras"] = [c for c in lay["cameras"] if c["name"] not in {e["name"] for e in extra}] + extra
(d / "layout_cams.json").write_text(json.dumps(lay, indent=1))
PY
for P in night golden; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/render_${P}_c1ref.log" 2>&1 || echo FAIL $P c1ref
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout.json" --preset $P --cams C1_EntryReveal,CX_FromPlatform,C10_Hero,C3_Case3,C4_ShurikenTray,C5_CloakCase,CW_WestAisle --res 1600x900 --out "$D" > "$D/render_${P}.log" 2>&1 || echo FAIL $P
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout_cams.json" --preset $P --cams CN_WestNiche,CN_EastNiche,CE_MatDown --res 1600x900 --out "$D/closeups" > "$D/render_${P}_closeups.log" 2>&1 || echo FAIL $P closeups
done
grep -h "rendered" "$D"/render_*.log | wc -l
