#!/bin/sh
# Trace pilot pipeline (after the trace stages): HIGH -> game mesh -> bake -> pilot blend -> front compare renders
set -e
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D=/c/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4/trace
W=/c/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot
cd $D
"$B" -b --factory-startup --python tp_build.py 2>&1 | grep -E "HIGH parts|Error|Trace" || true
TP_LOWRES=1 "$B" -b --factory-startup --python tp_build.py 2>&1 | grep -E "LOWGEO|Error|Trace" || true
"$B" -b $W/work/tp_high.blend --factory-startup --python tp_lowbake.py -- 7900 > $W/work/lowbake.log 2>&1
grep -E "TP-LOW.*(LOD0|density|saved)|Error|Trace" $W/work/lowbake.log || true
"$B" -b --factory-startup --python tp_context.py 2>&1 | grep -E "TP-CTX|Error|Trace" || true
TP_SAMPLES=${TP_SAMPLES:-64} "$B" -b $W/SnowFlower_Sheath_TracePilot.blend --factory-startup --python tp_views.py -- ${VIEWS:-front q34l} 2>&1 | grep -E "Error|Trace" || true
"$B" -b --factory-startup --python tp_compare.py 2>&1 | grep -E "iou|mean_abs" || true
