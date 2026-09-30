#!/usr/bin/env bash
# look.sh + pad lab (pad $3 of $2) for round $1
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
W=WorkFiles/dojo/build/pines/v2work; B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
V=${2:-PineA1}; PI=${3:-2}
CLOSE=1 $W/look.sh $1 $V
"$B" -b $W/blend/look.blend --factory-startup --python $W/pad_lab.py -- $V $PI "C:/Users/Cody/Desktop/Blender_Projects/$W/$1" 2>&1 | grep -E "Error|Traceback" || true
py -3 -c "
from PIL import Image
S='$W/$1/'
ims=[Image.open(S+f'pad${PI}_{n}.png').convert('RGB').resize((600,467)) for n in ('front','top','under','side')]
o=Image.new('RGB',(1210,944),'white')
for k,im in enumerate(ims): o.paste(im,((k%2)*610,(k//2)*477))
o.save(S+'padlab.png')"
py -3 $W/cu.py $W/$1 $W/$1/cu.png
py -3 -c "
import json;r=json.load(open('WorkFiles/dojo/build/pines/build_report_fast.json'))['variants']['$V']
print('tris',r['tris'])
for p in r['pad_info']: print({k:p.get(k) for k in ('pad','rosettes','target','arms','fork_levels','thickness_m','width_m','max_shoot_rise_deg')})"
