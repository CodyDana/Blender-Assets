import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
for t in ("lod0_front","mhfit"):
    a=load(D+f"render_{t}_raw.png"); m=a[...,3]>0.5; ys,xs=np.nonzero(m); J=json.load(open(D+f"render_{t}.json"))['align']
    s,tx,ty=J['s'],J['tx'],J['ty']
    print(t,"raw bbox",xs.min(),xs.max(),ys.min(),ys.max(),"in ref px: x",round(s*xs.min()+tx,1),round(s*xs.max()+tx,1),"y",round(s*ys.min()+ty,1),round(s*ys.max()+ty,1),"h/w",round((ys.max()-ys.min())/(xs.max()-xs.min()),4))
