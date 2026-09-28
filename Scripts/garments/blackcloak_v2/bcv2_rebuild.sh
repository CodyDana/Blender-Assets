#!/bin/bash
# BlackCloak_MH_v2 stage 2: rebuild the work file, gate, export and render from scratch (one command).
#
#   bash Scripts/garments/blackcloak_v2/bcv2_rebuild.sh [tag=r1] [render_dir=Renders/BlackCloak_MH_v2/<tag>] [samples=256]
#
# 1. bcv2_drape.py     cut the flat pattern pieces, drape them with Blender cloth on the fitting body (ARMS_DOWN_V2)
#                      -> WorkFiles/BlackCloak_MH_v2/build/drape_<tag>.npz (deterministic: same inputs, same drape)
# 2. bcv2_assemble.py  rebuild GARMENT / GARMENT_SIM in Assets/Garments/BlackCloak_MH_v2.blend (made once by
#                      Scripts/garments/new_garment.py --name BlackCloak_MH_v2 --type cloak) and save it
# 3. build_garment.py  --gate-only, then the export (Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx + sidecars)
# 4. bcv2_sidecars.py  SK_BlackCloak_MH_v2.material_params.json + SK_BlackCloak_MH_v2.cloth.json
# 5. bcv2_render.py    builder renders of the exported FBX (calibrated studio, Standard view transform)
# The drape parameters of the shipped round are the script defaults (frames 300, bending 1.5, mass 0.5).
set -e
cd "C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
TAG=${1:-r1}
RDIR=${2:-Renders/BlackCloak_MH_v2/$TAG}
SPP=${3:-256}
W=WorkFiles/BlackCloak_MH_v2/build
mkdir -p $W/logs
[ -f Assets/Garments/BlackCloak_MH_v2.blend ] || "$B" -b --factory-startup --python Scripts/garments/new_garment.py -- --name BlackCloak_MH_v2 --type cloak
"$B" -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_drape.py -- --tag $TAG --frames 300 > $W/logs/drape_$TAG.log 2>&1
grep -E "BCV2 (drape|DONE)" $W/logs/drape_$TAG.log
"$B" -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_assemble.py -- --tag $TAG > $W/logs/assemble_$TAG.log 2>&1
grep -E "BCV2A SAVED" $W/logs/assemble_$TAG.log
"$B" -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/build_garment.py -- --out Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx --gate-only > $W/logs/gate_$TAG.log 2>&1 || true
grep -E "BUILD_GARMENT" $W/logs/gate_$TAG.log
cp Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.qa.json $W/gate_only_$TAG.qa.json
"$B" -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/build_garment.py -- --out Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx > $W/logs/export_$TAG.log 2>&1
grep -E "BUILD_GARMENT" $W/logs/export_$TAG.log
PYTHONUTF8=1 py Scripts/garments/blackcloak_v2/bcv2_sidecars.py --tag $TAG
"$B" -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_render.py -- --out $RDIR --samples $SPP > $W/logs/render_$TAG.log 2>&1
grep -E "BCV2R" $W/logs/render_$TAG.log
