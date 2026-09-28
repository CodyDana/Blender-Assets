import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *
D=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
def box(a,r):
    k=2*r+1; p=np.pad(a,r,mode='edge'); c=p.cumsum(0).cumsum(1); c=np.pad(c,((1,0),(1,0)))
    return (c[k:,k:]-c[:-k,k:]-c[k:,:-k]+c[:-k,:-k])/(k*k)
def erode(m,n):
    e=m.copy()
    for _ in range(n): e=e&np.roll(e,1,0)&np.roll(e,-1,0)&np.roll(e,1,1)&np.roll(e,-1,1)
    return e
def measures(img,mask):
    L=lum(img)*255; H,W=L.shape; R={}
    ys,xs=np.nonzero(mask); R['bbox']=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]
    R['h_over_w']=round((ys.max()-ys.min()+1)/(xs.max()-xs.min()+1),4)
    # collar
    cols=np.arange(120,280); top=[np.argmax(mask[:,x]) if mask[:,x].any() else H for x in cols]
    ct=int(min(top)); R['collar_top_y']=ct; R['collar_top_x']=int(cols[int(np.argmin(top))])
    for dy in (15,40):
        row=mask[ct+dy]; xx=np.nonzero(row[100:300])[0]+100
        R[f'collar_width_at_top+{dy}']=[int(xx.min()),int(xx.max()),int(xx.max()-xx.min()+1)]
    # left-most / right-most
    i=np.argmin(xs); R['left_extreme']=[int(xs[i]),int(ys[xs==xs[i]].mean())]
    sel=ys<470; i=np.argmax(np.where(sel,xs,-1)); R['right_extreme_upper']=[int(xs[i]),int(ys[(xs==xs[i])&sel].mean())]
    # bottom profile & tips
    bot=np.array([np.nonzero(mask[:,x])[0].max() if mask[:,x].any() else -1 for x in range(W)])
    tips={}
    for name,(a,b) in {'left':(0,140),'centre':(140,280),'right':(280,W)}.items():
        seg=bot[a:b]; j=int(np.argmax(seg)); tips[name]=[a+j,int(seg[j])]
    R['hem_lowest_by_third']=tips
    valid=bot>0; xv=np.nonzero(valid)[0]; bp=bot[valid].astype(float)
    sm=np.convolve(bp,np.ones(15)/15,mode='same'); R['hem_profile_roughness_px']=round(float(np.std((bp-sm)[10:-10])),3)
    # silhouette edge roughness (left and right contours, y 150..600)
    lc=np.array([np.nonzero(mask[y])[0].min() for y in range(150,600)],float); rc=np.array([np.nonzero(mask[y])[0].max() for y in range(150,600)],float)
    for n,c in (('left',lc),('right',rc)):
        sm=np.convolve(c,np.ones(9)/9,mode='same'); R[f'{n}_contour_hf_roughness_px']=round(float(np.std((c-sm)[5:-5])),3)
    # cloth luminance
    e=erode(mask,4); v=L[e]
    R['cloth_lum']={'mean':round(float(v.mean()),2),'std':round(float(v.std()),2),'p5':float(np.percentile(v,5)),'p50':float(np.percentile(v,50)),'p95':float(np.percentile(v,95))}
    rgb=img[...,:3][e]*255; R['cloth_rgb_mean']=[round(float(x),2) for x in rgb.mean(0)]
    # grain: high-pass
    hp=L-box(L,3); e2=erode(mask,8); h=hp[e2]
    R['grain_highpass_std']=round(float(h.std()),3)
    R['grain_highpass_rel']=round(float(h.std()/max(1,v.mean())),4)
    k=((h-h.mean())**4).mean()/h.var()**2; R['grain_highpass_kurtosis']=round(float(k),2)
    # spectral wavelength in flat patches
    patches={'mantle':(235,165,299,229),'front_panel':(270,330,334,394),'left_fall':(60,420,124,484)}
    out={}
    for n,(x0,y0,x1,y1) in patches.items():
        p=L[y0:y1,x0:x1].copy(); pm=e2[y0:y1,x0:x1]
        if pm.mean()<0.95: out[n]='not fully cloth'; continue
        p=p-box(p,6); p-=p.mean(); w=np.hanning(64); p=p*w[:,None]*w[None]
        F=np.abs(np.fft.fftshift(np.fft.fft2(p)))**2; yy,xx=np.mgrid[-32:32,-32:32]; r=np.sqrt(xx**2+yy**2)
        rad=np.array([F[(r>=k0)&(r<k0+1)].mean() for k0 in range(2,32)])
        cen=float((rad*np.arange(2,32)).sum()/rad.sum())
        out[n]={'hp_std':round(float(p.std()),3),'spectral_centroid_cycles_per_64px':round(cen,2),'wavelength_px':round(64/cen,2),'local_mean_lum':round(float(L[y0:y1,x0:x1].mean()),1)}
    R['grain_patches']=out
    # inner opening: darkest 10% of cloth in central lower region
    reg=np.zeros_like(mask); reg[300:650,120:300]=True; rr=e&reg; th=np.percentile(L[rr],10)
    d=rr&(L<=th); yy,xx=np.nonzero(d)
    R['inner_opening_dark10']={'thresh':float(th),'centroid':[round(float(xx.mean()),1),round(float(yy.mean()),1)],'x_p10_p90':[float(np.percentile(xx,10)),float(np.percentile(xx,90))],'y_p10_p90':[float(np.percentile(yy,10)),float(np.percentile(yy,90))]}
    # collar fold profile along x=collar_top_x column band
    cx=R['collar_top_x']; prof=L[ct:ct+110,cx-6:cx+7].mean(1); sm=np.convolve(prof,np.ones(5)/5,mode='same')
    pk=[i for i in range(3,len(sm)-3) if sm[i]==sm[i-3:i+4].max() and sm[i]-min(sm[max(0,i-8):i+9])>1.5]
    R['collar_profile_x']=cx; R['collar_fold_peaks_y']=[int(ct+i) for i in pk]
    R['collar_fold_spacing_px']=[int(b-a) for a,b in zip(pk,pk[1:])]
    return R
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"); refm=lum(ref)*255<235
res={'reference':measures(ref,refm)}
for t in sys.argv[sys.argv.index('--')+1:]:
    o=load(D+f"ours_{t}_refframe.png"); om=np.load(D+f"ours_{t}_mask.npy")>0.5
    res[t]=measures(o,om); res[t]['iou_vs_ref']=round(float((om&refm).sum()/(om|refm).sum()),4)
    res[t]['align']=json.load(open(D+f"render_{t}.json"))['align']
# src vs mhfit shape change
a=np.load(D+"ours_srcblend_mask.npy")>0.5; b=np.load(D+"ours_mhfit_mask.npy")>0.5
A=load(D+"ours_srcblend_refframe.png"); B=load(D+"ours_mhfit_refframe.png")
res['src_vs_mhfit']={'mask_iou':round(float((a&b).sum()/(a|b).sum()),4),'mean_abs_lum_diff':round(float(np.abs(lum(A)-lum(B)).mean()*255),2),'align_scale_src':json.load(open(D+'render_srcblend.json'))['align']['s'],'align_scale_mhfit':json.load(open(D+'render_mhfit.json'))['align']['s']}
json.dump(res,open(D+"measurements.json","w"),indent=1,default=float)
print(json.dumps(res,indent=0,default=float))
