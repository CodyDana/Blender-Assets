#!/usr/bin/env bash
# ROUND 5 showcase stage: every Blender check on the composed round-5 showcase (GASP capsule r 0.30, 1.72 m, step 0.45)
# (r5sc_runcheck.py = a copy of the fixes track's r5_runcheck.py: runs a check script with its ROOT pinned and text swaps)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
SB=Assets/Dojo/DojoShowcase.blend
C=WorkFiles/dojo/build/unreal/round5/checks
W=$C/r5sc_runcheck.py
LY=showcase/layout_showcase.json
J=unreal/round5/checks/json
F1=WorkFiles/dojo/build/unreal/round4/f1_work/checks
mkdir -p WorkFiles/dojo/build/$J
OUTSWAP='WORK / "unreal" / "round4" / "f1" / "json"=>WORK / "unreal" / "round5" / "checks" / "json"'
run() { local tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python $W -- "$@" > "WorkFiles/dojo/build/$J/$tag.log" 2>&1; echo "exit $?"; }
run walk --script Scripts/dojo/walk_check.py --layout $LY --out showcase/walk_check_showcase.json
run climb --script Scripts/dojo/climb_check.py --layout $LY --out showcase/climb_check_showcase.json --hover 0.019
run gate_roof --script Scripts/dojo/roof_walk_check.py --layout $LY --out showcase/roof_walk_check_showcase.json
run hall_roof --script Scripts/dojo/hall/hall_roof_walk.py --layout $LY --out showcase/hall_roof_walk_showcase.json
run ob_roof --script Scripts/dojo/outbuildings/ob_roof_walk.py --layout $LY --out $J/ob_roof_walk_r5.json
run corridors --script $F1/f1_corridor_checks.py --swap 'CW = WORK / "unreal" / "round4" / "f1" / "json"=>CW = WORK / "unreal" / "round5" / "checks" / "json"'
SHEDCTL='        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),=>        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),
        "CONTROL_1v1_west_edge_over_the_wall_top_into_the_boundary": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0), (-1.6, 2.0)]),'
run shed_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset shed --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "unreal" / "round5" / "checks" / "json" / f"sp_roof_walk_{ASSET}_r5.json"' --swap "$SHEDCTL"
run pav_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset pavilion --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "unreal" / "round5" / "checks" / "json" / f"sp_roof_walk_{ASSET}_r5.json"'
run clearance --script $F1/f1_clearance.py --swap "$OUTSWAP"
run ground_holes --script $F1/f1_ground_holes.py --swap "$OUTSWAP"
echo ALLDONE
