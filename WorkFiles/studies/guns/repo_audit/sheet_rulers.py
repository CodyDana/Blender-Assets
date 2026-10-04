import numpy as np
from PIL import Image
R="C:/Users/Cody/Desktop/Blender_Projects/.claude/worktrees/gun-assets-creation-261bad/References/Guns/"
def ruler(name,path,box,dark=True):
    im=np.asarray(Image.open(path).convert("L")).astype(float)
    x0,y0,x1,y1=box; a=im[y0:y1,x0:x1]
    bg=np.median(a)
    m=(a<bg-40) if dark else (a>bg+40)
    rows=m.sum(1); r=int(np.argmax(rows))
    xs=np.nonzero(m[r])[0]
    # longest run
    runs=[];s=xs[0];p=xs[0]
    for x in xs[1:]:
        if x!=p+1: runs.append((s,p)); s=x
        p=x
    runs.append((s,p)); s,e=max(runs,key=lambda t:t[1]-t[0])
    # ticks: columns with dark pixels above/below the line
    band=m[max(r-8,0):r-1]
    cols=np.nonzero(band.sum(0)>=3)[0]
    ticks=[]; 
    for c in cols:
        if not ticks or c>ticks[-1][-1]+1: ticks.append([c])
        else: ticks[-1].append(c)
    tc=[x0+np.mean(t) for t in ticks]
    print(name,"line y",y0+r,"x",x0+s,x0+e,"len",e-s+1,"ticks",[round(t,1) for t in tc])
ruler("carbine",R+"Carbine/carbine_sheetA.webp",(10,430,620,470))
ruler("longrifle",R+"LongRifle/longrifle_sheetA.webp",(10,480,620,515),dark=False)
ruler("rifle",R+"Rifle/rifle_sheetAB.webp",(10,255,762,280))
ruler("smg",R+"SMG/smg_sheetA.webp",(10,480,620,515))
ruler("pistol",R+"Pistol/pistol_sheetA.webp",(10,530,620,555))
