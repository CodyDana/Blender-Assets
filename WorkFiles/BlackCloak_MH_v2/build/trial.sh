#!/bin/bash
# bash trial.sh <tag> <drape args...>: one drape trial + preview contact strip (builder working helper)
cd "C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"; W=WorkFiles/BlackCloak_MH_v2/build
T=$1; shift
timeout 460 "$B" -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_drape.py -- --tag $T --frames 300 "$@" > $W/logs/drape_$T.log 2>&1
grep -E "BCV2 (pattern|fine mesh|fine drape|drape|fan|DONE)|Error|Trace" $W/logs/drape_$T.log | cut -c1-500
cd $W; "$B" -b --factory-startup --python ../spec/scripts/v2m_contact.py -- contact_$T.png 700 preview_${T}_front.png preview_${T}_q34.png preview_${T}_side.png preview_${T}_q34l.png preview_${T}_jin.png preview_${T}_jinfine.png 2>&1 | grep CONTACT
