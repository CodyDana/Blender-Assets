#!/usr/bin/env bash
# round 4 fix f1: every Blender check on the composed showcase (GASP capsule r 0.30, 1.72 m, step 0.45)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase.blend
J=WorkFiles/dojo/build/unreal/round4/f1/json
C=WorkFiles/dojo/build/unreal/round4/f1_work/checks
mkdir -p $J
run() { echo "== $1"; "$B" -b --factory-startup $SB --python "$@" > "$J/$(basename $1 .py)_${TAGX}.log" 2>&1; echo "exit $?"; }
TAGX=main run Scripts/dojo/walk_check.py -- --layout showcase/layout_showcase.json --out showcase/walk_check_showcase.json
TAGX=main run Scripts/dojo/climb_check.py -- --layout showcase/layout_showcase.json --out showcase/climb_check_showcase.json --hover 0.019
TAGX=main run Scripts/dojo/roof_walk_check.py -- --layout showcase/layout_showcase.json --out showcase/roof_walk_check_showcase.json
TAGX=main run Scripts/dojo/hall/hall_roof_walk.py -- --layout showcase/layout_showcase.json --out showcase/hall_roof_walk_showcase.json
TAGX=main run Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout showcase/layout_showcase.json --out unreal/round4/f1/json/ob_roof_walk_showcase.json
TAGX=main run $C/f1_corridor_checks.py
TAGX=shed run $C/f1_sp_roof_walk.py -- --asset shed
TAGX=pav run $C/f1_sp_roof_walk.py -- --asset pavilion
TAGX=main run $C/f1_clearance.py
TAGX=main run $C/f1_ground_holes.py
echo ALLDONE
