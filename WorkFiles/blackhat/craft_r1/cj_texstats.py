import bpy, numpy as np, json, os
T="C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/Textures/"
def load(n, cs):
    im=bpy.data.images.load(T+n+".png"); im.colorspace_settings.name=cs
    a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],im.channels); return a
def s2l(x): return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
res={}
side=json.load(open("C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/SM_BlackHat.sockets.json"))
for part,mat in (("Straw","M_BlackHat_Straw"),("Cloth","M_BlackHat_Cloth")):
    bc=load(f"T_BlackHat_{part}_BC","Non-Color"); det=load(f"T_BlackHat_{part}_Detail","Non-Color")
    orm=load(f"T_BlackHat_{part}_ORM","Non-Color"); n=load(f"T_BlackHat_{part}_N","Non-Color")
    tint=np.array(side["materials"][mat]["tint_default_linear"])
    bcl=s2l(bc[...,:3]); dl=s2l(det[...,0])
    # coverage mask: pixels where alpha>0 or non-uniform? use orm alpha / det > 0
    q=np.quantile
    r={}
    r["det_srgb_q"]=[float(q(det[...,0],p)) for p in (0,.001,.01,.5,.99,.999,1)]
    r["det_lin_mean"]=float(dl.mean())
    r["bc_lin_q_lum"]=[float(q(bcl.mean(-1),p)) for p in (0,.01,.5,.99,1)]
    pred=dl[...,None]*tint[None,None,:]
    err=np.abs(s2l(bc[...,:3])-pred)
    r["bc_vs_detxtint_maxabs_lin"]=float(err.max()); r["bc_vs_detxtint_p99_lin"]=float(q(err,.99))
    # predicted in 8-bit sRGB
    def l2s(x): return np.where(x<=0.0031308,x*12.92,1.055*np.power(np.clip(x,0,None),1/2.4)-0.055)
    e8=np.abs(np.round(l2s(pred)*255)-np.round(bc[...,:3]*255))
    r["bc_vs_detxtint_max_8bit"]=float(e8.max()); r["frac_8bit_err_gt1"]=float((e8>1).mean())
    # chroma of bc
    r["bc_chroma_std"]=float((bcl/np.maximum(bcl.mean(-1,keepdims=True),1e-5)).reshape(-1,3).std(0).mean())
    # mip check level 4 box: filter in linear
    def box(a,k): h,w=a.shape[:2]; return a.reshape(h//k,k,w//k,k,*a.shape[2:]).mean((1,3))
    for k in (4,16,64):
        bm=box(bcl,k); dm=box(dl,k); r[f"mip{k}_err_max"]=float(np.abs(bm-dm[...,None]*tint).max())
    for i,c in enumerate("ORMA"):
        r[f"orm_{c}_q"]=[float(q(orm[...,i],p)) for p in (0,.01,.5,.99,1)]
    nx=n[...,0]*2-1; ny=n[...,1]*2-1; nz=n[...,2]*2-1
    r["n_len_q"]=[float(q(np.sqrt(nx**2+ny**2+nz**2),p)) for p in (.01,.5,.99)]
    r["n_z_min"]=float(nz.min()); r["n_xy_std"]=[float(nx.std()),float(ny.std())]
    # empty coverage: fraction of det==0 texels
    r["det_zero_frac"]=float((det[...,0]<=0.0).mean())
    # high-pass energy by row/col to detect strand frequency; FFT peak
    g=dl-dl.mean()
    F=np.abs(np.fft.rfft2(g[::2,::2]))
    F[0,0]=0
    idx=np.unravel_index(np.argsort(F.ravel())[-5:],F.shape)
    r["fft_top_peaks_(ky,kx)_on1024"]=[(int(a),int(b)) for a,b in zip(*idx)]
    res[part]=r
print("CJT"+json.dumps(res))
