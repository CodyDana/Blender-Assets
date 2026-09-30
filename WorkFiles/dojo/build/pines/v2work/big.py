import sys
from PIL import Image
sys.path.insert(0,'Scripts/dojo/pines')
import ref_panels as rp
S, V, view, out = sys.argv[1:5]
name={'front':'F','side':'S','3q':'Q'}[view]
pan={'PineA1':'P1','PineA2':'P1','PineB1':'P2','PineB2':'P2','PineC1':'P3','PineC2':'P3','PineD1':'P4','PineD2':'P4'}[V]+name
if V in ('PineA2','PineB2','PineC2','PineD2') and view=='front': pan=pan[:2]+'Q'
ref=Image.open('References/Dojo/dojo_japanese_pine_ref.png').crop(rp.PANELS[pan]['box'])
im=Image.open(f'{S}/{V}_{view}_final.png').convert('RGBA'); bg=Image.new('RGBA',im.size,(182,182,182,255)); bg.alpha_composite(im); a=bg.convert('RGB')
bb=im.getchannel('A').point(lambda x:255 if x>20 else 0).getbbox(); a=a.crop((bb[0]-10,bb[1]-10,bb[2]+10,bb[3]+10))
H=800; r=ref.resize((int(ref.size[0]*H/ref.size[1]),H),Image.LANCZOS); a=a.resize((int(a.size[0]*H/a.size[1]),H),Image.LANCZOS)
o=Image.new('RGB',(r.size[0]+a.size[0]+10,H),'white'); o.paste(r,(0,0)); o.paste(a,(r.size[0]+10,0)); o.save(out)
