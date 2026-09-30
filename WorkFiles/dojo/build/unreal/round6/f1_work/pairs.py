import sys
from PIL import Image
S=sys.argv[1]; out=sys.argv[2]; names=sys.argv[3:]
R='C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/unreal/round6/r6/'
w=900
rows=[]
for n in names:
    a,b=(Image.open(R+n+'.png') if not n.startswith('REF') else None), None
    ia=Image.open(R+n+'.png').convert('RGB'); ib=Image.open(S+'/'+n+'.png').convert('RGB')
    ia=ia.resize((w,int(ia.height*w/ia.width))); ib=ib.resize((w,int(ib.height*w/ib.width)))
    rows.append((ia,ib))
H=sum(max(a.height,b.height)+10 for a,b in rows)
G=Image.new('RGB',(2*w+10,H),'white'); y=0
for a,b in rows: G.paste(a,(0,y)); G.paste(b,(w+10,y)); y+=max(a.height,b.height)+10
G.save(out)
