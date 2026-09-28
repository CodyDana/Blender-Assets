#!/bin/bash
# usage: run_build.sh <tag> [extra build args]   full build, log + report under exact/, copy shipped bytes to exact/<tag>/
cd /c/Users/Cody/Desktop/Blender_Projects
TAG=$1; shift
OUT=WorkFiles/paperbomb/exact/$TAG
mkdir -p $OUT
start=$(date +%s)
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/props/build_paper_bomb.py -- --report-name exact/${TAG}_report.json "$@" > WorkFiles/paperbomb/exact/${TAG}.log 2>&1
rc=$?
end=$(date +%s)
cp -p Exports/PaperBomb/SM_PaperBomb.fbx Exports/PaperBomb/SM_PaperBomb.sockets.json Exports/PaperBomb/README.txt $OUT/
mkdir -p $OUT/Textures $OUT/Renders
cp -p Exports/PaperBomb/Textures/*.png $OUT/Textures/
cp -p Renders/PaperBomb/*.png $OUT/Renders/
cp -p Assets/PaperBomb.blend $OUT/
( cd $OUT && sha256sum Textures/*.png Renders/*.png SM_PaperBomb.fbx SM_PaperBomb.sockets.json PaperBomb.blend > hashes.txt )
"/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/paperbomb/fbx_content_hash.py $OUT/SM_PaperBomb.fbx >> $OUT/hashes.txt 2>&1
echo "rc=$rc seconds=$((end-start))" >> $OUT/hashes.txt
tail -5 WorkFiles/paperbomb/exact/${TAG}.log
cat $OUT/hashes.txt
