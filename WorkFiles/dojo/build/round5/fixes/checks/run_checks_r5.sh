#!/usr/bin/env bash
# round 5 fixes track: every Blender check on this track's composed check scene (GASP capsule r 0.30, 1.72 m, step 0.45)
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /c/Users/Cody/Desktop/Blender_Projects
F=WorkFiles/dojo/build/round5/fixes
SB=$F/checks/DojoShowcase_r5.blend
W=$F/r5_runcheck.py
LY=round5/fixes/checks/showcase/layout_showcase.json
J=round5/fixes/checks/json
C=WorkFiles/dojo/build/unreal/round4/f1_work/checks
mkdir -p WorkFiles/dojo/build/$J
LAYSWAP='WORK / "showcase" / "layout_showcase.json"=>WORK / "round5" / "fixes" / "checks" / "showcase" / "layout_showcase.json"'
OUTSWAP='WORK / "unreal" / "round4" / "f1" / "json"=>WORK / "round5" / "fixes" / "checks" / "json"'
run() { local tag=$1; shift; echo "== $tag"; "$B" -b --factory-startup $SB --python $W -- "$@" > "WorkFiles/dojo/build/$J/$tag.log" 2>&1; echo "exit $?"; }
run walk --script Scripts/dojo/walk_check.py --layout $LY --out $J/walk_check_r5.json
run climb --script Scripts/dojo/climb_check.py --layout $LY --out $J/climb_check_r5.json --hover 0.019
run gate_roof --script Scripts/dojo/roof_walk_check.py --layout $LY --out $J/roof_walk_check_r5.json
run hall_roof --script Scripts/dojo/hall/hall_roof_walk.py --layout $LY --out $J/hall_roof_walk_r5.json
run ob_roof --script Scripts/dojo/outbuildings/ob_roof_walk.py --layout $LY --out $J/ob_roof_walk_r5.json
run corridors --script $C/f1_corridor_checks.py --swap "$LAYSWAP" --swap 'CW = WORK / "unreal" / "round4" / "f1" / "json"=>CW = WORK / "round5" / "fixes" / "checks" / "json"'
# the shed roof walk gets its own CONTROL (the r4 verifier's note): down the west edge onto the wall top, then on west
# into the 1v1 boundary ring on the wall's outer edge (X -1)
SHEDCTL='        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),=>        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),
        "CONTROL_1v1_west_edge_over_the_wall_top_into_the_boundary": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0), (-1.6, 2.0)]),'
run shed_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset shed --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "round5" / "fixes" / "checks" / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "round5" / "fixes" / "checks" / "json" / f"sp_roof_walk_{ASSET}_r5.json"' --swap "$SHEDCTL"
run pav_roof --script Scripts/dojo/shed/sp_roof_walk.py --asset pavilion --swap 'WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json"=>WORK / "round5" / "fixes" / "checks" / "showcase" / "layout_showcase.json"' --swap 'WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"=>WORK / "round5" / "fixes" / "checks" / "json" / f"sp_roof_walk_{ASSET}_r5.json"'
run clearance --script $C/f1_clearance.py --swap "$LAYSWAP" --swap "$OUTSWAP"
run ground_holes --script $C/f1_ground_holes.py --swap "$LAYSWAP" --swap "$OUTSWAP"
echo ALLDONE
