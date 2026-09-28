#!/bin/bash
# usage: try.sh <tag> [extra drape args...]   (drape -> assemble(save) -> gate+export -> ID check -> geom check)
cd "C:/Users/Cody/Desktop/Blender_Projects"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
T=$1; shift
W=WorkFiles/BlackCloak_MH_v2/build
"$B" -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_drape.py -- --tag $T "$@" > $W/logs/drape_$T.log 2>&1
grep -E "BCV2 drape" $W/logs/drape_$T.log | cut -c1-400
"$B" -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_assemble.py -- --tag $T > $W/logs/assemble_$T.log 2>&1
py -c "
import json;d=json.load(open('$W/assemble_$T.json'));print('ASM selfx', d['self_intersections']['by_pair'], 'tris', d['tris'])"
"$B" -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/build_garment.py -- --out Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx > $W/logs/export_$T.log 2>&1
grep -E "BUILD_GARMENT" $W/logs/export_$T.log | cut -c1-200
bash $W/idcheck.sh $W/idtest jin front q34 q34_other side_r side_l back photo
"$B" -b --factory-startup --python WorkFiles/BlackCloak_MH_v2/spec/scripts/v2m_geom_check.py -- --out $W/selfmeasure/geom_$T.json > $W/logs/geom_$T.log 2>&1
py -c "
import json;d=json.load(open('$W/selfmeasure/geom_$T.json'))
print('GEOM fails', [k for k,v in d['pass'].items() if not v], d['foldover'], d.get('self_intersections'), d['hem'].get('z_min'), d['hem'].get('hem_length_on_floor_m'))"
S=WorkFiles/BlackCloak_MH_v2/spec/scripts
"$B" -b --factory-startup --python $S/v2m_render.py -- --view jin --body 1 --samples 96 --out $W/selfmeasure/jin_$T --tag jin > $W/logs/jin_$T.log 2>&1
"$B" -b --factory-startup --python $S/v2m_jin_score.py -- $W/selfmeasure/jin_$T jin > $W/logs/jinscore_$T.log 2>&1
py -c "
import json;d=json.load(open('$W/selfmeasure/jin_$T/jin_jin.json'));print('JIN', {k:{kk:d[k][kk] for kk in ('cross_-50_10','fan_15_120','fan_spread_deg')} for k in ('r0.35m','r0.55m')})"
