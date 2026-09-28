import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *; import numpy as np
ref = np.load(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy')[..., :3].astype(np.float32) * 255
PAN={'p1':(6, 756, 318, 1220),'p2':(323, 756, 629, 1220),'p3':(634, 756, 939, 1220),'p4':(946, 756, 1249, 1220)}
d=sys.argv[1]; top=[];bot=[]
for k,b in PAN.items():
    a=crop(ref,b); o=read_png(f'{d}/{k}.png')[...,:3][:a.shape[0],:a.shape[1]]
    top+= [a, np.full((a.shape[0],4,3),230.)]; bot+=[o, np.full((a.shape[0],4,3),230.)]
write_png(sys.argv[2], np.concatenate([np.concatenate(top[:-1],1), np.full((4, sum(t.shape[1] for t in top[:-1]),3),230.), np.concatenate(bot[:-1],1)],0))
