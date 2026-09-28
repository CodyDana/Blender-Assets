import numpy as np, math, itertools, importlib.util, sys
sys.argv=['x']
src = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/final_pass/hull_proto.py").read().split('for n_az, elevs')[0]
exec(src)
old = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/UnrealVerify_indep_v1/truth_UCX_SM_BlackHat_LOD0_00_verts_cm.npy")*10
gap=(old@T.T).max(0)-hp
print("old hull verts",len(old),"gap max %.2f p95 %.2f mean %.2f"%(gap.max(),np.percentile(gap,95),gap.mean()), "ztop", old[:,2].max()-body[:,2].max())
# antiprism rim + staggered cone rings
def ringhull(n, m=1.0):
    r = np.hypot(body[:,0], body[:,1]); z = body[:,2]
    z0 = z.min()-m; ztop = z.max()+m
    # choose z1 (rim top ring) as the height of max radius band top
    best=None
    for z1 in np.linspace(z0+6, z0+40, 18):
        for zc in (ztop,):
            pts=[]
            ph0=np.arange(n)*2*math.pi/n; ph1=ph0+math.pi/n
            # radii solved by containment: start tight then inflate uniformly
            for k in np.linspace(1.0,1.2,201):
                ra = r.max()*k
                cr = 40.0
                V = np.concatenate([np.c_[ra*np.cos(ph0), ra*np.sin(ph0), np.full(n,z0)],
                                    np.c_[ra*np.cos(ph1), ra*np.sin(ph1), np.full(n,z1)],
                                    [[0,0,zc]]])
                # inside test via support planes of V: use polytope planes from triples (slow) -> use gap on dirs: containment if support of V >= support of body in all T dirs (approx)
                if ((V@T.T).max(0) - hp >= 0).all():
                    break
            gap=(V@T.T).max(0)-hp
            cand=(gap.mean(), z1, k, len(V), gap.max())
            if best is None or cand[0]<best[0]: best=cand
    return best
for n in (16, 20, 24):
    print("antiprism+apex", n, ringhull(n))
