#!/bin/sh
# t6: textures -> build (export through Scripts/pipeline) -> UCX cover -> measure (exported FBX) -> renders -> gold
# sample -> sheets. One Blender at a time, foreground, 4 threads.
set -e
cd C:/Users/Cody/Desktop/Blender_Projects
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
T=WorkFiles/dojo/build/props/taiko/t6
py -3 Scripts/dojo/props/taiko/make_taiko_textures.py --only Lacquer,Collar > $T/textures.log 2>&1
"$B" -b -t 4 --factory-startup --python Scripts/dojo/props/taiko/build_taiko.py > $T/build.log 2>&1
grep -q "QA: 3 pieces, hard fails 0" $T/build.log && grep -q "exported 3 FBX" $T/build.log || { echo "BUILD QA FAILED"; exit 1; }
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python Scripts/dojo/props/taiko/check_ucx_cover.py 2>&1 | grep UCXCOV > $T/ucx_cover.txt
"$B" -b -t 4 --factory-startup --python $T/measure_t6.py > $T/measure_t6.log 2>&1
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python $T/render_t6.py > $T/render.log 2>&1
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python $T/render_t6.py -- --photo --only front,band,skirt > $T/render_photo.log 2>&1
py -3 $T/gold_sample.py > $T/gold_sample.log 2>&1
py -3 $T/compose_t6.py > $T/compose.log 2>&1
