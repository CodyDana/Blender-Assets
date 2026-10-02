#!/usr/bin/env bash
# HALL + ARMORY round stage 2: the Blender checks on the composed blend (GASP capsule r 0.30, 1.72 m, step 0.45)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase_HallArmory.blend
LY=hall_armory/blender/layout_checks.json
O=hall_armory/blender/checks
G=WorkFiles/dojo/build/$O
mkdir -p $G
run() { local tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python "$@" > "$G/$tag.log" 2>&1; echo "exit $?"; }
run walk Scripts/dojo/walk_check.py -- --layout $LY --out $O/walk_check.json
run climb Scripts/dojo/climb_check.py -- --layout $LY --out $O/climb_check.json --hover 0.019
run gate_roof Scripts/dojo/roof_walk_check.py -- --layout $LY --out $O/roof_walk_check.json
run hall_roof Scripts/dojo/hall/hall_roof_walk.py -- --layout $LY --out $O/hall_roof_walk.json
run rear_roof Scripts/dojo/hall/hall_rear_roof_walk.py -- --layout $LY --out $O/rear_roof_walk.json
echo ALLDONE
