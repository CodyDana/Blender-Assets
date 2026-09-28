#!/bin/bash
# fp_iter.sh CACHE NAME [CLOTH_JSON] [SHADING_JSON] - paint + reference-view render + metrics (final pass scratch)
cd "C:/Users/Cody/Desktop/Blender_Projects"
PY="C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
BL="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
T=WorkFiles/smokebomb/rewind/build5/tools
F=WorkFiles/smokebomb/final_pass
export PYTHONUTF8=1
C=$1; N=$2; CL=${3:-"{}"}; SH=${4:-'{"specular": 0.5, "spec_detail_gain": 1.0, "spec_detail_power": 4.0, "detail_power": 2.0}'}
SS=${SS:-2}; SAMPLES=${SAMPLES:-256}
T0=$(date +%s)
"$PY" $T/b5_paint.py $F/$C $F/$N --cloth "$CL" --shading "$SH" --ss $SS --workers 24 2>&1 | grep -E "B4_PAINT|Error|Traceback|error|line " | cut -c1-400
T1=$(date +%s)
"$BL" -b --factory-startup --python $T/b5_render.py -- $F/$C $F/$N $F/$N --shading "$SH" --samples $SAMPLES 2>&1 | grep -E "Error|Traceback" | grep -v HIPEW
T2=$(date +%s)
echo "paint $((T1-T0)) s, render $((T2-T1)) s"
"$PY" $T/b5_metrics.py $F/$N/ref_front_lod0.npy 2>&1 | grep -E "OURS|REL" | cut -c1-900
"$PY" $F/tools/fp_crop.py $F/$N/pair_half.png 0 0 1254 1254 1 References/SmokeBomb/smokebomb.png $F/$N/ref_front_lod0.png
"$PY" - <<PYE
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
from wd_png import read_png, write_png
a = read_png(r"$F/$N/pair_half.png")[..., :3]
write_png(r"$F/$N/pair_half.png", a[::2, ::2])
PYE
