#!/usr/bin/env bash
# DojoFX chain (landscape round FX stage). Run from the repo root, holding the DojoFX lock:
#   py -3 -B Scripts/pipeline/lock.py claim DojoFX --agent claude --blend Assets/Dojo/DojoFX.blend
set -euo pipefail
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROUND="${1:-final}"
py -3 -B Scripts/dojo/fx/measure_petal_ref.py                 # sheet petal numbers
py -3 -B Scripts/dojo/fx/measure_petal_ref.py --outline       # traced mean outline
bash Scripts/dojo/fx/run_petals.sh "$ROUND"                   # textures, meshes (QA + export), sheet, SBS
"$B" -b Assets/Dojo/DojoFX.blend --factory-startup --python Scripts/dojo/fx/render_petal_scenes.py -- \
    --out "WorkFiles/dojo/build/fx/renders/scenes_$ROUND" --samples 256     # sunset drift, fallen tests, decal bake
"$B" -b --factory-startup --python Scripts/dojo/fx/render_flipbooks.py -- --only puff,wisp,haze --cell 512 --samples 256
"$B" -b --factory-startup --python Scripts/dojo/fx/spray_sim.py -- --scene rock --res 176 --cell 512 --samples 192
py -3 -B Scripts/dojo/fx/compose_scenes.py --renders "WorkFiles/dojo/build/fx/renders/scenes_$ROUND"
py -3 -B Scripts/dojo/fx/make_foam.py
py -3 -B Scripts/dojo/fx/compose_mist.py
py -3 -B Scripts/dojo/fx/texture_qa.py
py -3 -B Scripts/dojo/fx/make_catalog.py
