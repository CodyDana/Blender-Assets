#!/bin/bash
# fast procedural iteration render: fast.sh <tag> [extra build_pack args]
S="C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad"
T="$S/$1"; shift; mkdir -p "$T"
cd "C:/Users/Cody/Desktop/Blender_Projects"
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate --blend "$T/Shuriken.blend" --export-dir "$T/exp" --report-dir "$T/rep" --render-dir "$T/ren" --diag-dir "$T/diag" --texture-dir "$T/tex" --no-export --samples 48 "$@" > "$T/log.txt" 2>&1
echo "exit $?"; grep -n "Traceback\|Error:" "$T/log.txt" | head
PY="/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe"
W="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/restyle_pass2"
R="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/style_reference"
"$PY" "$W/summarize.py" "$T/rep" 2>&1 | grep -v "^$"
"$PY" - <<PYEOF 2>/dev/null
import sys
for shot in ("persp", "top"):
    sys.argv = ["x", "--", "--out", r"$T/sheet_%s.png" % shot, "--cols", "2", "--cell-w", "960",
                "R::$R/ref_rig_scaled100_%s.png" % shot] + ["%s::$T/ren/%s_%s.png" % (f, f, shot) for f in ("four_point", "eight_point", "square_plate")]
    exec(open(r"$W/grid_sheet.py").read())
PYEOF
"$PY" "$W/crop.py" "$T/crop_hero.png" 600 250 700 450 1.0 "$T/ren/four_point_persp.png" > /dev/null
