#!/bin/sh
# Trace pilot v2 (traced relief) full pipeline: relief -> maps -> HIGH/LOW -> bake -> pilot blend -> renders -> compare
set -e
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D=/c/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4/trace
P=/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot
W=$P/work
cd $D
[ "${SKIP_RELIEF:-0}" = 1 ] || "$B" -b --factory-startup --python tp_relief.py 2>&1 | grep -E "H range|Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_rmaps.py 2>&1 | grep -E "maps|Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_rbuild.py 2>&1 | grep -E "tris|BVH|Error|Trace|line [0-9]" || true
"$B" -b $W/tp_high.blend --factory-startup --python tp_rbake.py 2>&1 | grep -E "LOD0|Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_context.py 2>&1 | grep -E "TP-CTX|Error|Trace|line [0-9]" || true
TP_SAMPLES=${TP_SAMPLES:-48} "$B" -b $P/SnowFlower_Sheath_TracePilot.blend --factory-startup --python tp_views.py -- ${VIEWS:-front q34l} 2>&1 | grep -E "Error|Trace|line [0-9]" || true
"$B" -b --factory-startup --python tp_compare.py 2>&1 | grep -E "iou|mean_abs" || true
