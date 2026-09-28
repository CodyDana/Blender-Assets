import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
args=sys.argv[sys.argv.index('--')+1:]
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")
for name,a in (("ref",ref),)+tuple((p,load(p)) for p in args):
    L=lum(a)*255; m=L<200
    # erode mask by 4 px
    e=m.copy()
    for k in range(4): e=e&np.roll(e,1,0)&np.roll(e,-1,0)&np.roll(e,1,1)&np.roll(e,-1,1)
    v=L[e]; print(name[-40:],"mean",v.mean().round(2),"std",v.std().round(2),"p5,50,95",np.percentile(v,[5,50,95]).round(1),"area",m.sum())
