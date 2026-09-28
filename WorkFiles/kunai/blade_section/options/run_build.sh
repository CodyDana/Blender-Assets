#!/bin/bash
# usage: run_build.sh <id> [extra build_pack args]   (id = current | A | B | C)
O=C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/blade_section/options
id=$1; shift
D=$O/$id
mkdir -p $D/export/Textures $D/report $D/renders $D/diag
if [ "$id" = "current" ]; then unset KUNAI_SECTION_JSON; else export KUNAI_SECTION_JSON=$D/section.json; fi
export PYTHONDONTWRITEBYTECODE=1
start=$(date +%s)
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python-exit-code 3 \
  --python $O/proto_tree/Scripts/shuriken/build_pack.py -- --forms kunai_plain \
  --blend $D/Shuriken_$id.blend --export-dir $D/export --texture-dir $D/export/Textures \
  --report-dir $D/report --render-dir $D/renders --diag-dir $D/diag "$@" > $D/build.log 2>&1
echo "EXIT $? after $(( $(date +%s) - start )) s" >> $D/build.log
tail -1 $D/build.log
