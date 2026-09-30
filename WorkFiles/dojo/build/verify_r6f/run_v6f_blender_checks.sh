#!/usr/bin/env bash
# VERIFY r6f: every Blender traversal check, fresh headless processes on DojoShowcase.blend (read-only; outputs in verify_r6f/)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase.blend
V=WorkFiles/dojo/build/verify_r6f
W=$V/v6f_runcheck.py
LY=showcase/layout_showcase.json
F1=WorkFiles/dojo/build/unreal/round4/f1_work/checks
run() { local tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python $W -- "$@" > "$V/$tag.log" 2>&1; echo "exit $?"; }
run walk --script Scripts/dojo/walk_check.py --layout $LY --out verify_r6f/walk_check.json
run climb --script Scripts/dojo/climb_check.py --layout $LY --out verify_r6f/climb_check.json --hover 0.019
run gate_roof --script Scripts/dojo/roof_walk_check.py --layout $LY --out verify_r6f/roof_walk_check.json
run hall_roof --script Scripts/dojo/hall/hall_roof_walk.py --layout $LY --out verify_r6f/hall_roof_walk.json
run ob_roof --script Scripts/dojo/outbuildings/ob_roof_walk.py --layout $LY --out verify_r6f/ob_roof_walk.json
run corridors --script $F1/f1_corridor_checks.py --swap 'CW = WORK / "unreal" / "round4" / "f1" / "json"=>CW = WORK / "verify_r6f"'
SHEDCTL='        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),=>        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),
        "CONTROL_1v1_west_edge_over_the_wall_top_into_the_boundary": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0), (-1.6, 2.0)]),'
run shed_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset shed --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "verify_r6f" / f"sp_roof_walk_{ASSET}.json"' --swap "$SHEDCTL"
run pav_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset pavilion --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "verify_r6f" / f"sp_roof_walk_{ASSET}.json"'
run clearance --script $F1/f1_clearance.py --swap 'WORK / "unreal" / "round4" / "f1" / "json"=>WORK / "verify_r6f"'
run ground_holes --script $F1/f1_ground_holes.py --swap 'WORK / "unreal" / "round4" / "f1" / "json"=>WORK / "verify_r6f"'
echo ALLDONE
