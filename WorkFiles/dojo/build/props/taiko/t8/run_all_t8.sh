#!/bin/sh
# t8: textures -> build (export through Scripts/pipeline, qa_check) -> UCX cover -> measure (exported FBX) -> renders
# (review, then photo-studio light) -> gold sample -> sheets -> the judge r7 scripts re-run on t8 (pairs, tack fold,
# geometry) -> the ring hardware check and its finish. One Blender at a time, foreground, 4 threads.
set -e
cd C:/Users/Cody/Desktop/Blender_Projects
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
T=WorkFiles/dojo/build/props/taiko/t8
py -3 Scripts/dojo/props/taiko/make_taiko_textures.py --only Hide > $T/textures.log 2>&1
"$B" -b -t 4 --factory-startup --python Scripts/dojo/props/taiko/build_taiko.py > $T/build.log 2>&1
grep -q "QA: 3 pieces, hard fails 0" $T/build.log && grep -q "exported 3 FBX" $T/build.log || { echo "BUILD QA FAILED"; exit 1; }
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python Scripts/dojo/props/taiko/check_ucx_cover.py 2>&1 | grep UCXCOV > $T/ucx_cover.txt
"$B" -b -t 4 --factory-startup --python $T/measure_t8.py > $T/measure_t8.log 2>&1
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python $T/render_t8.py -- --only front,band,skirt,set,saddle,standend,saddlefelt,ring,ringlay,tacks > $T/render.log 2>&1
"$B" -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python $T/render_t8.py -- --photo --only front,band,skirt,sil,ring > $T/render_photo.log 2>&1
py -3 $T/gold_sample.py > $T/gold_sample.log 2>&1
py -3 $T/compose_t8.py > $T/compose.log 2>&1
py -3 $T/check_skirt_t8.py > $T/check_skirt.log 2>&1
py -3 $T/judge_style/pairs.py > $T/judge_style/pairs.log 2>&1
py -3 $T/judge_style/tack_fold.py > $T/judge_style/tack_fold.log 2>&1
py -3 $T/finish_t8.py > $T/finish.log 2>&1
py -3 $T/judge_style/ring_grid_t8.py > $T/judge_style/ring_grid.log 2>&1
"$B" -b -t 4 --factory-startup --python $T/judge_style/geo_check.py > $T/judge_style/geo_check.log 2>&1
"$B" -b -t 4 --factory-startup --python $T/ring_check_t8.py > $T/ring_check.log 2>&1
"$B" -b -t 4 --factory-startup --python $T/skirt_check_t8.py > $T/skirt_check.log 2>&1
echo "T8 DONE"
