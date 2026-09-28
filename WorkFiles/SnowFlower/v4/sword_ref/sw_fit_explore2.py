import json, numpy as np
exec(open('sw_fit_explore.py').read().split('# where is the limit?')[0].split('for sc in (1.0,.8')[0])
from numpy import convolve
wv=np.minimum(sheet_w,52.0); wv=np.convolve(np.pad(wv,7,mode='edge'),np.ones(15)/15,'valid')
shape=np.clip(sheet_sweep-np.interp(t,[0,.6],[0,0]),0,None)
shape[t<0.55]=0; shape=np.convolve(np.pad(shape,7,mode='edge'),np.ones(15)/15,'valid'); shape/=shape[-1]
def fit2(S,k,wall,clr,Lb=918.0):
    sp=S*shape; ed=sp-wv; s_mm=t*Lb; rr=31+s_mm/k+3/k
    hw=np.array([sheath_w_px(r)*k/2 for r in rr])-wall-clr
    best=(-1e9,0)
    for c in np.linspace(-45,15,1201):
        m=np.min(hw-np.maximum(abs(sp-c),abs(ed-c)))
        if m>best[0]: best=(m,c)
    m,c=best; marg=hw-np.maximum(abs(sp-c),abs(ed-c)); i=np.argmin(marg)
    return m,c,t[i]
for S in (0,2,4,6,8,10,12,15,19.8):
    print(f'S {S:5.1f}:', '  '.join(f'k{k} w{w}/{c}: {fit2(S,k,w,c)[0]:5.2f}' for k in (0.687,0.70) for (w,c) in ((2.5,1.0),(2.0,0.75))))
