import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")[...,:3]
ours=load(D+"ours_lod0_front_refframe.png")[...,:3]
x0,y0,x1,y1=120,100,417,400; up=2; out=[]
for a in (ref,ours):
    c=np.clip((a[y0:y1,x0:x1]-0.02)*4.0,0,1); c=np.repeat(np.repeat(c,up,0),up,1)
    for x in range(0,x1-x0):
        if (x0+x)%20==0: c[:,x*up]=(1,0,0) if (x0+x)%100==0 else (0,0.8,0)
    for y in range(0,y1-y0):
        if (y0+y)%20==0: c[y*up]=(1,0,0) if (y0+y)%100==0 else (0,0.8,0)
    out.append(c)
save(np.concatenate([out[0],np.ones((out[0].shape[0],10,3)),out[1]],1),D+"inspect/grid_mantle_pair.png")
