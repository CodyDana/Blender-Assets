import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
args=sys.argv[sys.argv.index('--')+1:]; tag=args[0]
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")[...,:3]
ours=load(D+f"ours_{tag}_refframe.png")[...,:3]
H,W=ref.shape[:2]; gap=np.ones((H,12,3),np.float32)
save(np.concatenate([ref,gap,ours],1),D+f"sidebyside_{tag}.png")
rm=lum(ref)*255<235; om=np.load(D+f"ours_{tag}_mask.npy")>0.5
ov=np.ones((H,W,3),np.float32)
ov[rm&om]=(0.55,0.55,0.55); ov[rm&~om]=(0.9,0.15,0.15); ov[~rm&om]=(0.15,0.35,0.95)
blend=0.5*ref+0.5*ours
save(np.concatenate([ov,gap,blend],1),D+f"overlay_{tag}.png")
print("IOU",(rm&om).sum()/(rm|om).sum(),"ref_only",(rm&~om).sum(),"ours_only",(~rm&om).sum())
