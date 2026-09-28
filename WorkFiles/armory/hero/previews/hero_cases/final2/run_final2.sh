#!/bin/sh
# usage: run_final2.sh [samples]   renders every hero_cases assembly (+ the all-cases row) into final2, with --save
cd /c/Users/Cody/Desktop/Blender_Projects
S=${1:-64}
OUT="C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\previews\hero_cases\final2"
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
for spec in "case_L|SM_AK_Case_L_Plinth;SM_AK_Case_L_Glass@0,0,0.50" \
            "case_LN|SM_AK_Case_LN_Plinth;SM_AK_Case_LN_Glass@0,0,0.45" \
            "case_M|SM_AK_Case_M_Plinth;SM_AK_Case_M_Glass@0,0,0.70" \
            "case_S|SM_AK_Case_S_Plinth;SM_AK_Case_S_Glass@0,0,0.90" \
            "case_Tall|SM_AK_Case_Tall_Plinth;SM_AK_Case_Tall_Glass@0,0,0.50" \
            "hero_plinth|SM_AK_Case_Hero_Plinth" \
            "all_cases|SM_AK_Case_L_Plinth@0.9,0,0;SM_AK_Case_L_Glass@0.9,0,0.50;SM_AK_Case_LN_Plinth@3.0,0,0;SM_AK_Case_LN_Glass@3.0,0,0.45;SM_AK_Case_M_Plinth@5.1,0,0;SM_AK_Case_M_Glass@5.1,0,0.70;SM_AK_Case_S_Plinth@7.1,0,0;SM_AK_Case_S_Glass@7.1,0,0.90;SM_AK_Case_Tall_Plinth@8.95,0,0;SM_AK_Case_Tall_Glass@8.95,0,0.50;SM_AK_Case_Hero_Plinth@11.3,0,0"; do
  label=${spec%%|*}; pieces=${spec#*|}
  "$B" -b --factory-startup --python Scripts/armory/hero/preview_hero.py -- --module hero_cases --pieces "$pieces" \
      --front -y --label "$label" --out "$OUT" --samples "$S" --save 2>&1 | grep -E "^PREVIEW|Traceback|rror:" | cut -c1-4000
done
