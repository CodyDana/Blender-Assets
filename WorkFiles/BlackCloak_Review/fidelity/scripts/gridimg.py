import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")[...,:3]
ours=load(D+"ours_lod0_front_refframe.png")[...,:3]
def gain(a): return np.clip(a*3.0,0,1)  # brighten to read darks
for name,a in (("ref",ref),("ours",ours)):
    for rn,(x0,y0,x1,y1) in {"top":(0,0,417,300),"bottom":(0,280,417,674)}.items():
        c=gain(a[y0:y1,x0:x1].copy()); up=2; c=np.repeat(np.repeat(c,up,0),up,1)
        for x in range(0,x1-x0,20):
            col=(1,0,0) if (x0+x)%100==0 else (0,0.8,0); c[:,x*up]=col
        for y in range(0,y1-y0,20):
            yy=y0+y
            if yy%20: continue
            col=(1,0,0) if yy%100==0 else (0,0.8,0); c[y*up]=col
        save(c,D+f"inspect/grid_{name}_{rn}.png")
