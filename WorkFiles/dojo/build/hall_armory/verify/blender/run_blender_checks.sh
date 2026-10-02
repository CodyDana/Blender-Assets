#!/usr/bin/env bash
# VERIFIER (hall + armory): Blender traversal checks, fresh headless processes, read-only on the composed blend; outputs only in hall_armory/verify/blender
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase_HallArmory.blend
LY=hall_armory/verify/blender/layout_verify.json
O=hall_armory/verify/blender
G=WorkFiles/dojo/build/$O
run() { local tag=$1; shift; echo "== $tag $(date +%T)"; "$B" -b --factory-startup $SB --python "$@" > "$G/$tag.log" 2>&1; echo "exit $?"; }
run walk Scripts/dojo/walk_check.py -- --layout $LY --out $O/walk_check.json
run climb Scripts/dojo/climb_check.py -- --layout $LY --out $O/climb_check.json --hover 0.019
run gate_roof Scripts/dojo/roof_walk_check.py -- --layout $LY --out $O/roof_walk_check.json
run hall_roof Scripts/dojo/hall/hall_roof_walk.py -- --layout $LY --out $O/hall_roof_walk.json
run rear_roof Scripts/dojo/hall/hall_rear_roof_walk.py -- --layout $LY --out $O/rear_roof_walk.json
run ob_roof Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout $LY --out $O/ob_roof_walk.json
echo ALLDONE $(date +%T)
