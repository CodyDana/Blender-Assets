#!/usr/bin/env bash
# ROUND 5 dressing: every Blender traversal check, fresh headless processes on DojoDressing.blend (read-only)
# with the showcase layout + the SM_DKD_* plaques (dressing/layout_dressing_checks.json)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoDressing.blend
V=WorkFiles/dojo/build/dressing/checks
LX=dressing/layout_dressing_checks.json
run() { tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python "$@" > "$V/$tag.log" 2>&1; echo "exit $?"; }
run walk_check Scripts/dojo/walk_check.py -- --layout $LX --out dressing/checks/walk_check.json
run climb_check Scripts/dojo/climb_check.py -- --layout $LX --out dressing/checks/climb_check.json --hover 0.019
run roof_walk_check Scripts/dojo/roof_walk_check.py -- --layout $LX --out dressing/checks/roof_walk_check.json
run hall_roof_walk Scripts/dojo/hall/hall_roof_walk.py -- --layout $LX --out dressing/checks/hall_roof_walk.json
run ob_roof_walk Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout $LX --out dressing/checks/ob_roof_walk.json
echo ALLDONE
