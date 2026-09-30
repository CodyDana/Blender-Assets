"""Scratch: XOR overlay (ref only = red, ours only = blue, both = grey) for variant views, normalised like G4."""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,'Scripts/dojo/pines'); sys.path.insert(0,'Scripts/vegetation')
import compose_pines as cp, measure_tree as mt, ref_panels as rp
rdir=Path(sys.argv[1]); V=sys.argv[2]; views=sys.argv[3].split(','); out=sys.argv[4]
meta=json.loads((rdir/'render_meta.json').read_text())
sheet=mt.load_rgb(str(Path(rp.SHEET))); bg=mt.background_colour(sheet[20:60,300:700])
tiles=[]
for view in views:
    rn=cp.ref_panel_name(V,view); pine=cp.SPEC[V]['pine']
    rm,rbase,_=cp.ref_masks(sheet,bg,rn); om,obase,opxm=cp.our_masks(rdir,V,view,meta,pine)
    if pine==4: a,b=rm['fg'],om['fg']
    else: a=rm['foliage']|rm['wood']; b=om['foliage']|om['wood']
    na=mt.normalise(a,rbase); nb=mt.normalise(b,obase)
    img=np.full(na.shape+(3,),235,np.uint8); img[na&nb]=(120,120,120); img[na&~nb]=(220,40,40); img[nb&~na]=(40,80,220)
    tiles.append(Image.fromarray(img))
H=max(t.size[1] for t in tiles); W=sum(t.size[0] for t in tiles)+10*len(tiles)
o=Image.new('RGB',(W,H),'white'); x=0
for t in tiles: o.paste(t,(x,0)); x+=t.size[0]+10
o.save(out)
