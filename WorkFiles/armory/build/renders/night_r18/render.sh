#!/bin/bash
# r18 live night renders: C1 at 1448x1086 (ref_aspect), then C1, CX, C10, C3, C5, CW, C4, CG at 1600x900, and the
# west corner niche close-up CN_WestNiche (the r18 round's camera, added to a copy of layout.json: layout_cams.json)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; P="C:/Users/Cody/Desktop/Blender_Projects"
D="$P/WorkFiles/armory/build/renders/night_r18"; R="$P/Scripts/armory/render_armory.py"; L="$P/WorkFiles/armory/build/layout.json"
py -3 - "$L" "$D/layout_cams.json" <<'PY'
import json, sys
from pathlib import Path
lay = json.loads(Path(sys.argv[1]).read_text())
extra = [{"name": "CN_WestNiche", "loc": [3.1, 16.9, 1.9], "look_at": [1.05, 19.6, 1.45], "lens_mm": 30}]
lay["cameras"] = [c for c in lay["cameras"] if c["name"] != "CN_WestNiche"] + extra
Path(sys.argv[2]).write_text(json.dumps(lay, indent=1))
PY
"$B" -b --factory-startup "$P/Assets/Armory/ArmoryKit.blend" --python "$R" -- --layout "$L" --preset night --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/log_ref_aspect.txt" 2>&1 || echo FAIL ref_aspect
"$B" -b --factory-startup "$P/Assets/Armory/ArmoryKit.blend" --python "$R" -- --layout "$L" --preset night --cams C1_EntryReveal,CX_FromPlatform,C10_Hero,C3_Case3,C5_CloakCase,CW_WestAisle,C4_ShurikenTray,CG_Garden --res 1600x900 --out "$D" > "$D/log.txt" 2>&1 || echo FAIL main
"$B" -b --factory-startup "$P/Assets/Armory/ArmoryKit.blend" --python "$R" -- --layout "$D/layout_cams.json" --preset night --cams CN_WestNiche --res 1600x900 --out "$D" > "$D/log_niche.txt" 2>&1 || echo FAIL niche
grep -h "rendered" "$D"/log*.txt | wc -l
