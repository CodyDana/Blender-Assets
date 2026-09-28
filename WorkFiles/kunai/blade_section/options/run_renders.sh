#!/bin/bash
# usage: run_renders.sh <id> <ridge base,tip,tip_at for the photo-pose meta>
O=C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/blade_section/options
BL="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
id=$1; ridge=$2
D=$O/$id
mkdir -p $D/views
cp $D/Shuriken_$id.blend $D/views/readonly_copy.blend          # every render opens this copy; nothing saves it
export PYTHONDONTWRITEBYTECODE=1
"$BL" -b --factory-startup --python C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/blade_section/ours/render_photo_pose.py -- \
  --blend $D/views/readonly_copy.blend --out $D/views/photo_pose.png --mode gallery --tex-dir $D/export/Textures \
  --ridge $ridge > $D/views/photo_pose.log 2>&1; echo "photo_pose exit $?"
"$BL" -b $D/views/readonly_copy.blend --factory-startup --python $O/render_3q.py -- $D/report/kunai_plain_report.json $D/views 160 3q:40 hero:-25 \
  > $D/views/render_3q.log 2>&1; echo "3q exit $?"; grep C3Q $D/views/render_3q.log
"$BL" -b $D/views/readonly_copy.blend --factory-startup --python $O/measure_mesh.py -- $D/report/kunai_plain_report.json $D/mesh_measure.json \
  > $D/views/measure.log 2>&1; echo "measure exit $?"; grep TEXEL $D/views/measure.log
