#!/bin/bash
# r21/a test copy renders (entry mat removed, backlit upper windows): night + golden C1 at 1448x1086 (ref_aspect) and
# 1600x900, CW, CX, and two close views of the upper windows (CU_WestWindow, CU_EastWindow: added to a copy of the test
# layout, layout_cams.json; both look at the first bay from the entrance end, with its plum vase)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; P="C:/Users/Cody/Desktop/Blender_Projects"
D="$P/WorkFiles/armory/hero/room_preview/r21/a"; R="$P/Scripts/armory/render_armory.py"; L="$D/layout.json"
py -3 - "$L" "$D/layout_cams.json" <<'PY'
import json, sys
from pathlib import Path
lay = json.loads(Path(sys.argv[1]).read_text())
extra = [{"name": "CU_WestWindow", "loc": [4.2, 0.9, 2.55], "look_at": [0.0, 2.3, 3.35], "lens_mm": 30},
         {"name": "CU_EastWindow", "loc": [7.8, 0.9, 2.55], "look_at": [12.0, 2.3, 3.35], "lens_mm": 30}]
lay["cameras"] = [c for c in lay["cameras"] if not c["name"].startswith("CU_")] + extra
Path(sys.argv[2]).write_text(json.dumps(lay, indent=1))
PY
for PR in night golden; do
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$L" --preset $PR --cams C1_EntryReveal --res 1448x1086 --out "$D/ref_aspect" > "$D/log_ref_aspect_$PR.txt" 2>&1 || echo FAIL ref_aspect $PR
  "$B" -b --factory-startup "$D/ArmoryKit_preview.blend" --python "$R" -- --layout "$D/layout_cams.json" --preset $PR --cams C1_EntryReveal,CW_WestAisle,CX_FromPlatform,CU_WestWindow,CU_EastWindow --res 1600x900 --out "$D" > "$D/log_$PR.txt" 2>&1 || echo FAIL main $PR
done
grep -h "^rendered" "$D"/log*.txt | wc -l
