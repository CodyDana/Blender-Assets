import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *; from align import warp
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
tag=sys.argv[sys.argv.index('--')+1]
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")[...,:3]
J=json.load(open(D+f"render_{tag}.json")); s,tx,ty=J['align']['s'],J['align']['tx'],J['align']['ty']
raw=load(D+f"render_{tag}_raw.png"); rgb=raw[...,:3]*raw[...,3:4]+(1-raw[...,3:4])
def crop_pair(x0,y0,x1,y1,name,up=4):
    r=ref[y0:y1,x0:x1]; r=np.repeat(np.repeat(r,up,0),up,1)
    # ours from raw at up x ref scale: ref coord -> raw coord
    H,W=(y1-y0)*up,(x1-x0)*up
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    rx=x0+(xx+0.5)/up; ry=y0+(yy+0.5)/up
    sx=(rx-tx)/s-0.5; sy=(ry-ty)/s-0.5
    ix=np.clip(sx.round().astype(int),0,rgb.shape[1]-1); iy=np.clip(sy.round().astype(int),0,rgb.shape[0]-1)
    o=rgb[iy,ix]
    save(np.concatenate([r,np.ones((H,8,3)),o],1),D+f"inspect/{tag}_{name}.png")
for n,b in {"collar":(100,0,320,160),"upper":(40,40,400,260),"leftwing":(0,200,200,460),"rightwing":(230,180,417,460),"hem":(0,480,417,674),"mid":(100,250,320,500)}.items():
    crop_pair(*b,n,up=3 if n!='hem' else 2)
