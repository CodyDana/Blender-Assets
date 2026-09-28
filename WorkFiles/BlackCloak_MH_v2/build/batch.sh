#!/bin/bash
# builder helper: bash batch.sh <listfile>; each line "<tag> <drape args>"
cd "C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"; W=WorkFiles/BlackCloak_MH_v2/build
while read -r T ARGS; do
  [ -z "$T" ] && continue
  timeout 470 "$B" -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_drape.py -- --tag $T --frames 300 $ARGS > $W/logs/drape_$T.log 2>&1
  echo "== $T $ARGS"
  grep -E "BCV2 (fine drape|fan|DONE)|Traceback" $W/logs/drape_$T.log | cut -c1-300
  grep -oE '"self_intersections": [0-9]+|"front_foldover": [0-9.]+|"hem_on_floor_frac": [0-9.]+' $W/logs/drape_$T.log | tr '\n' ' '; echo
done < "$1"
