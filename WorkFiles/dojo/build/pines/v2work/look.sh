#!/usr/bin/env bash
# quick A1 look: build (fast) + render front/side/3q + pad close-ups + quick_look. usage: look.sh ROUND [VARIANTS]
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W=WorkFiles/dojo/build/pines/v2work
R=$1; V=${2:-PineA1}
py -3 -B Scripts/dojo/pines/make_spec.py >/dev/null
"$B" -b --factory-startup --python Scripts/dojo/pines/build_pines.py -- --variants $V --fast --out-blend $W/blend/look.blend 2>&1 | grep -E "^\[|Error|Traceback|line [0-9]" || true
"$B" -b $W/blend/look.blend --factory-startup --python Scripts/dojo/pines/render_pines.py -- --out $W/$R --variants $V --samples 48 --res 900 ${CLOSE:+--closeups} 2>&1 | grep -E "Error|Traceback" || true
py -3 -B Scripts/dojo/pines/quick_look.py --renders $W/$R --variants $V
