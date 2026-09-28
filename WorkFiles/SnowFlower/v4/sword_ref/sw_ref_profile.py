"""Per-row silhouette of the reference front/side/back views (background = near-white, low saturation)."""
import numpy as np, json
a=np.load('sw_ref.npy')[...,:3]
lum=a@np.array([.2126,.7152,.0722])
sat=a.max(2)-a.min(2)
fg=(lum<0.93)|(sat>0.06)
out={}
for name,(x0,x1) in {'front':(215,345),'side':(440,540),'back':(610,740)}.items():
    rows=[]
    for r in range(a.shape[0]):
        idx=np.nonzero(fg[r,x0:x1])[0]
        rows.append(None if len(idx)==0 else [int(x0+idx[0]),int(x0+idx[-1])])
    out[name]=rows
json.dump(out,open('sw_ref_profile.json','w'))
f=out['front'];s=out['side']
first=min(i for i,v in enumerate(f) if v); last=max(i for i,v in enumerate(f) if v)
print('front rows',first,last, 'side', min(i for i,v in enumerate(s) if v), max(i for i,v in enumerate(s) if v))
for r in range(0,1240,10): print(r,f[r],s[r],out['back'][r])
