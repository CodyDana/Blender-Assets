#!/usr/bin/env bash
# Petal chain: textures -> meshes (QA + export) -> sheet renders -> side-by-side + measurement. Run from the repo root.
# Lock first: py -3 -B Scripts/pipeline/lock.py claim DojoFX --agent claude --blend Assets/Dojo/DojoFX.blend
set -euo pipefail
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROUND="${1:-r0}"
OUT="WorkFiles/dojo/build/fx/renders/sheet_$ROUND"
py -3 -B Scripts/dojo/fx/make_petal_textures.py
"$B" -b --factory-startup --python Scripts/dojo/fx/build_petals.py 2>&1 | grep -E "^QA|^DIMS|Error|Traceback"
"$B" -b Assets/Dojo/DojoFX.blend --factory-startup --python Scripts/dojo/fx/render_petal_sheet.py -- --out "$OUT" --samples 128 2>&1 | grep -E "CALIB|DONE|Error|Traceback"
py -3 -B Scripts/dojo/fx/compose_petal_sheet.py --renders "$OUT"
