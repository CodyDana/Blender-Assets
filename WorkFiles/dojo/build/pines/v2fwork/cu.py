import sys
from PIL import Image
S=sys.argv[1]; out=sys.argv[2]
ref=Image.open('References/Dojo/dojo_japanese_pine_ref.png')
def g(p):
    im=Image.open(p).convert('RGBA'); bg=Image.new('RGBA',im.size,(182,182,182,255)); bg.alpha_composite(im); return bg.convert('RGB')
tiles=[ref.crop((374,757,787,1086)), g(S+'/closeup_pad_side.png'), ref.crop((790,757,1077,1086)), g(S+'/closeup_pad_top.png')]
H=450; tiles=[t.resize((int(t.size[0]*H/t.size[1]),H)) for t in tiles]
o=Image.new('RGB',(sum(t.size[0] for t in tiles)+30,H),'white'); x=0
for t in tiles: o.paste(t,(x,0)); x+=t.size[0]+10
o.save(out)
