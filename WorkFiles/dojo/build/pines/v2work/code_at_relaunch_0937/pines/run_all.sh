#!/usr/bin/env bash
# Pines chain (study 4.2): spec -> textures -> build (bake, QA, export) -> render -> compose. Run from the repo root.
# Lock first: py -3 -B Scripts/pipeline/lock.py claim DojoPines --agent claude --blend Assets/Dojo/DojoPines.blend
set -euo pipefail
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROUND="${1:-f1}"
OUT="WorkFiles/dojo/build/pines/renders/$ROUND"
py -3 -B Scripts/dojo/pines/make_spec.py
py -3 -B Scripts/dojo/pines/make_pine_textures.py
"$B" -b --factory-startup --python Scripts/dojo/pines/build_pines.py -- --samples 48
"$B" -b Assets/Dojo/DojoPines.blend --factory-startup --python Scripts/dojo/pines/render_pines.py -- \
    --out "$OUT" --samples 160 --res 1100 --closeups --context
py -3 -B Scripts/dojo/pines/compose_pines.py --renders "$OUT"
py -3 -B Scripts/dojo/pines/make_catalog.py --renders "$OUT"
