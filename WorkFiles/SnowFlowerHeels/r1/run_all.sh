#!/bin/bash
# Snow Flower heels round 1: full chain (stages A-G). Run from the project root.
set -e
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S=Scripts/SnowFlowerHeels
TAG=${1:-r1}
"$B" -b WorkFiles/SnowFlowerHeels/foot_posed.blend --factory-startup --python $S/hb_a_last.py 2>&1 | grep -E "^\[A|Error|Traceback" | tail -2
"$B" -b --factory-startup --python $S/hb_b_body.py 2>&1 | grep -E "saved|Error|Traceback" | tail -2
"$B" -b --factory-startup --python $S/hb_c_heel.py 2>&1 | grep -E "HEEL_OK|Error|Traceback" | tail -2
"$B" -b --factory-startup --python $S/hb_e_insole.py 2>&1 | grep -E "INSOLE_OK|Error|Traceback" | tail -2
rm -f Assets/SnowFlowerHeels/SnowFlowerHeels.blend
"$B" -b --factory-startup --python $S/hb_d_assemble.py 2>&1 | grep -E "saved|game orn|Error|Traceback" | tail -3
"$B" -b Assets/SnowFlowerHeels/SnowFlowerHeels.blend --factory-startup --python $S/hb_f_build.py -- --stage all > WorkFiles/SnowFlowerHeels/r1/build_log.txt 2>&1 || true
grep -E "FAIL|LOD [0-9]|BUILD|textures|exported|Traceback" WorkFiles/SnowFlowerHeels/r1/build_log.txt | cut -c1-220
"$B" -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python $S/hb_g_render.py -- --samples 64 --tag $TAG 2>&1 | grep -E "RENDER_OK|Error|Traceback" | tail -3
echo CHAIN_DONE
