import sys;sys.path.insert(0,'Scripts/dojo/pines')
import numpy as np, make_pine_textures as m
from PIL import Image
H,col,ao,r=m.bark_v4()
im=m.lit_preview(H,col,ao)
Image.fromarray(im).crop((0,0,440,512)).resize((604,703)).save('WorkFiles/dojo/build/pines/v2fwork/bark_v4_preview.png')
ref=Image.open('References/Dojo/dojo_japanese_pine_ref.png').crop((0,757,371,1086)).resize((751,666))
o=Image.new('RGB',(1370,703),'white');o.paste(ref,(0,0));o.paste(Image.open('WorkFiles/dojo/build/pines/v2fwork/bark_v4_preview.png'),(760,0));o.save('WorkFiles/dojo/build/pines/v2fwork/bark_v4_cmp.png')
c=m.to_srgb8(col).reshape(-1,3).astype(float); L=c@[0.2126,0.7152,0.0722]; rust=(c[:,0]>c[:,1]*1.25)&(c[:,0]>80)
print('albedo median',np.median(c,0),'L',np.percentile(L,[10,50,90]).round(),'rust',rust.mean().round(3),'dark<30',(L<30).mean().round(3),'pale>140',(L>140).mean().round(3))
