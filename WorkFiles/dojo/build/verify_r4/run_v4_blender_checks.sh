#!/usr/bin/env bash
# VERIFY r4: every Blender traversal check, fresh headless processes on DojoShowcase.blend (read-only; outputs in verify_r4/)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase.blend
V=WorkFiles/dojo/build/verify_r4
run() { tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python "$@" > "$V/$tag.log" 2>&1; echo "exit $?"; }
run walk_check Scripts/dojo/walk_check.py -- --layout showcase/layout_showcase.json --out verify_r4/walk_check.json
run climb_check Scripts/dojo/climb_check.py -- --layout showcase/layout_showcase.json --out verify_r4/climb_check.json --hover 0.019
run roof_walk_check Scripts/dojo/roof_walk_check.py -- --layout showcase/layout_showcase.json --out verify_r4/roof_walk_check.json
run hall_roof_walk Scripts/dojo/hall/hall_roof_walk.py -- --layout showcase/layout_showcase.json --out verify_r4/hall_roof_walk.json
run ob_roof_walk Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout showcase/layout_showcase.json --out verify_r4/ob_roof_walk.json
run corridor_checks $V/v4_corridor_checks.py
run sp_roof_walk_shed $V/v4_sp_roof_walk.py -- --asset shed
run sp_roof_walk_pavilion $V/v4_sp_roof_walk.py -- --asset pavilion
echo ALLDONE
