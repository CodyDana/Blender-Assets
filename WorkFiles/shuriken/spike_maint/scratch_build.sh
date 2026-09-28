#!/usr/bin/env bash
# Spike-only build into a scratch directory (project outputs untouched), then the summary.
#   bash scratch_build.sh <scratch_dir> [forms]
S="$1"; FORMS="${2:-spike}"
P="C:/Users/Cody/Desktop/Blender_Projects"
mkdir -p "$S"
cd "$P"
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python-exit-code 3 --python Scripts/shuriken/build_pack.py -- --forms "$FORMS" --blend "$S/Shuriken.blend" --render-dir "$S/renders" --diag-dir "$S/diag" --texture-dir "$S/tex" --export-dir "$S/export" --report-dir "$S/reports" > "$S/build.log" 2>&1
echo "exit=$?"
grep -n "Traceback" -A 12 "$S/build.log" | head -30
