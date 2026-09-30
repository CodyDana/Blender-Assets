#!/usr/bin/env bash
# mound lab: look.sh round + mound close-ups + compare. usage: mound.sh ROUND VARIANT
set -e
cd /c/Users/Cody/Desktop/Blender_Projects
W=WorkFiles/dojo/build/pines/v2fwork; B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
$W/look.sh $1 $2 2>&1 | grep -E "^\[|IoU|rror|Trace" || true
"$B" -b $W/blend/look.blend --factory-startup --python $W/mound_lab.py -- $2 "C:/Users/Cody/Desktop/Blender_Projects/$W/$1" 2>&1 | grep -E "Error|Trace" | grep -v HIPEW || true
py -3 -c "
from PIL import Image
L='$W/$1/'; v='$2'
box={'PineA1':(70,270,300,340),'PineB1':(800,270,1030,340),'PineC1':(240,640,560,745),'PineD1':(856,560,1091,745),'PineD2':(1222,560,1448,745)}[v]
ref=Image.open('References/Dojo/dojo_japanese_pine_ref.png').crop(box); ref=ref.resize((1000,int(1000*ref.size[1]/ref.size[0])),Image.LANCZOS)
a=Image.open(L+f'mound_{v}_front.png').convert('RGB'); b=Image.open(L+f'mound_{v}_high.png').convert('RGB')
o=Image.new('RGB',(2010,ref.size[1]+720),'white'); o.paste(ref,(0,0)); o.paste(a,(0,ref.size[1]+10)); o.paste(b,(1010,ref.size[1]+10)); o.save(L+f'mound_cmp_{v}.png')"
