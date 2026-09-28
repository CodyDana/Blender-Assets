#!/bin/sh
# Trace pilot v2 (relief) look-dev loop: relief -> maps -> meshes -> quick HIGH preview
set -e
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D=/c/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4/trace
W=/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work
cd $D
[ "${SKIP_RELIEF:-0}" = 1 ] || "$B" -b --factory-startup --python tp_relief.py 2>&1 | grep -E "H range|Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_rmaps.py 2>&1 | grep -E "maps|Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_rbuild.py 2>&1 | grep -E "tris|Error|Trace|line [0-9]" || true
"$B" -b $W/tp_high.blend --factory-startup --python tp_rprev.py -- ${TAG:-b} ${VIEWS:-front q34} 2>&1 | grep -E "Error|Trace|line [0-9]" || true
