#!/bin/sh
# usage: run_wip.sh <outsub> <samples> label... : quick fix-6 previews (no --save) into final4/<outsub>
cd /c/Users/Cody/Desktop/Blender_Projects
SUB=$1; S=$2; shift 2
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/previews/hero_cases/final4/$SUB"
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
for label in "$@"; do
  case $label in
    case_L) pieces="SM_AK_Case_L_Plinth;SM_AK_Case_L_Glass@0,0,0.50";;
    case_LN) pieces="SM_AK_Case_LN_Plinth;SM_AK_Case_LN_Glass@0,0,0.45";;
    case_M) pieces="SM_AK_Case_M_Plinth;SM_AK_Case_M_Glass@0,0,0.70";;
    case_S) pieces="SM_AK_Case_S_Plinth;SM_AK_Case_S_Glass@0,0,0.90";;
    case_Tall) pieces="SM_AK_Case_Tall_Plinth;SM_AK_Case_Tall_Glass@0,0,0.50";;
    hero_plinth) pieces="SM_AK_Case_Hero_Plinth";;
  esac
  "$B" -b --factory-startup --python Scripts/armory/hero/preview_hero.py -- --module hero_cases --pieces "$pieces" \
      --front -y --label "$label" --out "$OUT" --samples "$S" 2>&1 | grep -E "^PREVIEW|Traceback|rror" | cut -c1-600
done
