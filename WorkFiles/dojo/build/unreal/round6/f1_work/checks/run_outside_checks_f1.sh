#!/usr/bin/env bash
# ROUND 6 outside track: every Blender check on the new compose (Assets/Dojo/DojoOutside.blend), headless, one at a
# time. Outputs: WorkFiles/dojo/build/round6/build/checks_f1/ (the ox_* checks write outside/checks/ and are copied over).
set -u
cd "C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
BL="Assets/Dojo/DojoOutside.blend"
C="WorkFiles/dojo/build/round6/build/checks_f1"
LY="outside/layout_outside_checks.json"
mkdir -p "$C"
run() { local log="$1"; shift; "$B" -b --factory-startup "$BL" --python "$@" > "$C/$log" 2>&1; echo "$log exit $?"; }
run seal.log Scripts/dojo/outside/checks/ox_alley_seal.py -- --out round6/build/checks_f1/alley_seal.json
run walk.log Scripts/dojo/walk_check.py -- --layout $LY --out round6/build/checks_f1/walk_check.json
run climb.log Scripts/dojo/climb_check.py -- --layout $LY --out round6/build/checks_f1/climb_check.json --hover 0.019
run rw_kit1.log Scripts/dojo/roof_walk_check.py -- --layout $LY --out round6/build/checks_f1/roof_walk_kit1.json
run rw_hall.log Scripts/dojo/hall/hall_roof_walk.py -- --layout $LY --out round6/build/checks_f1/roof_walk_hall.json
run rw_ob.log Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout $LY --out round6/build/checks_f1/roof_walk_outbuildings.json
run rw_corr.log Scripts/dojo/outside/checks/ox_corridor_checks.py
run rw_shed.log Scripts/dojo/outside/checks/ox_sp_roof_walk.py -- --asset shed
run rw_pavilion.log Scripts/dojo/outside/checks/ox_sp_roof_walk.py -- --asset pavilion
run clearance.log Scripts/dojo/outside/checks/ox_clearance.py
run measure.log Scripts/dojo/outside/checks/ox_measure.py
for f in corridor_roof_walk_outside corridor_clearance_outside sp_roof_walk_shed_outside sp_roof_walk_pavilion_outside \
         clearance_outside measure_outside; do
  cp "WorkFiles/dojo/build/outside/checks/$f.json" "$C/$f.json"
done
echo CHECKS_DONE
