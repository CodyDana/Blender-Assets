import sys,os,random; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *; from align import warp
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
B=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/blind/"
os.makedirs(B,exist_ok=False)
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")[...,:3]
refm=lum(ref)*255<235
bgv=float(np.median(ref[~refm]))
ours=load(D+"ours_lod0_front_refframe.png")[...,:3]; om=np.load(D+"ours_lod0_front_mask.npy")
ours=ours-(1-np.clip(om,0,1))[...,None]*(1-bgv)   # match reference paper white
sil_r=np.where(refm,0.0,bgv)[...,None].repeat(3,2); sil_o=np.where(om>0.5,0.0,bgv)[...,None].repeat(3,2)
regions=[("full",(0,0,417,674),674),("full",(0,0,417,674),337),("c",(120,0,280,130),0),("c",(85,55,155,125),0),
 ("c",(180,180,340,320),0),("c",(260,120,380,230),0),("c",(0,230,140,470),0),("c",(300,280,417,470),0),
 ("c",(190,330,330,560),0),("c",(0,520,180,674),0),("c",(230,520,417,674),0),("c",(120,520,300,674),0),
 ("c",(30,420,110,540),0),("c",(320,580,410,670),0),("c",(240,170,336,266),0),("c",(262,192,310,240),0),
 ("c",(140,330,240,560),0),("sil",(0,0,417,674),500),("c",(40,40,380,300),0),("c",(0,300,417,674),0)]
def up(img,box,target_long):
    x0,y0,x1,y1=box; c=img[y0:y1,x0:x1]; w,h=x1-x0,y1-y0
    if not target_long: target_long=440
    k=target_long/max(w,h); W,H=int(round(w*k)),int(round(h*k))
    return np.clip(warp(c,k,0,0,(H,W),1) if k!=1 else c,0,1)
rng=random.Random(int.from_bytes(os.urandom(8),'little'))
key=[]
for i,(kind,box,t) in enumerate(regions,1):
    if kind=="sil": a,b=up(sil_r,box,t),up(sil_o,box,t)
    else: a,b=up(ref,box,t),up(ours,box,t)
    # fill warp edge zeros with bg
    for z in (a,b): z[z.sum(2)==0]=bgv
    side=rng.choice(("left","right")); key.append(side)
    L,R=(b,a) if side=="left" else (a,b)
    gap=np.full((a.shape[0],16,3),0.5,np.float32)
    save(np.concatenate([L,gap,R],1),B+f"pair_{i:02d}.png")
print("KEY",key)
