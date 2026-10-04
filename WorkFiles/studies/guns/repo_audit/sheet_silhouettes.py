import numpy as np, sys, json
from PIL import Image
from scipy import ndimage as ndi
R="C:/Users/Cody/Desktop/Blender_Projects/.claude/worktrees/gun-assets-creation-261bad/References/Guns/"
def panel_mask(path, box):
    im=np.asarray(Image.open(path).convert("RGB")).astype(float)
    x0,y0,x1,y1=box; a=im[y0:y1,x0:x1]
    g=a.mean(2)
    # background: median of border
    bg=np.median(np.concatenate([g[:8].ravel(),g[-8:].ravel(),g[:,:8].ravel(),g[:,-8:].ravel()]))
    m=g<bg-28
    m=ndi.binary_opening(m,iterations=1)
    lab,n=ndi.label(m); 
    if n==0: return None
    sizes=ndi.sum(m,lab,range(1,n+1)); k=np.argmax(sizes)+1
    m=lab==k
    return m
def prof(name,path,box,step):
    m=panel_mask(path,box)
    ys,xs=np.nonzero(m)
    L=xs.max()-xs.min()+1; H=ys.max()-ys.min()+1
    bot=[(int(x), int(np.nonzero(m[:,x])[0].max()) if m[:,x].any() else -1) for x in range(xs.min(),xs.max()+1,step)]
    top=[(int(x), int(np.nonzero(m[:,x])[0].min()) if m[:,x].any() else -1) for x in range(xs.min(),xs.max()+1,step)]
    print(name,"L",L,"H",H,"x",xs.min(),xs.max(),"y",ys.min(),ys.max())
    print(" bottom",bot); print(" top",top)
prof("carbine_L",R+"Carbine/carbine_sheetA.webp",(10,10,620,430),10)
prof("longrifle_L",R+"LongRifle/longrifle_sheetA.webp",(5,35,620,480),10)
prof("rifle_L",R+"Rifle/rifle_sheetAB.webp",(10,22,762,255),15)
prof("smg_L",R+"SMG/smg_sheetA.webp",(10,10,620,480),10)
prof("sniper_L",R+"Sniper/sniper_sheetA.webp",(8,8,620,560),10)
prof("pistol_L",R+"Pistol/pistol_sheetA.webp",(5,25,620,525),10)
