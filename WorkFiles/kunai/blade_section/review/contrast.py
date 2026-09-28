import json, numpy as np
from PIL import Image
for oid in ['current','A','B','C']:
    d=json.load(open(f'{oid}/views/photo_pose.png.json'))
    im=np.asarray(Image.open(f'{oid}/views/photo_pose.png').convert('RGB')).astype(float)/255
    L=im@[0.2126,0.7152,0.0722]
    et={round(p[0]):p[1:] for p in d['edge_top_px']}; eb={round(p[0]):p[1:] for p in d['edge_bot_px']}
    rt={round(p[0]):p[1:] for p in d['ridge_top_px']}
    ups=[];los=[]
    for x in range(40,116,5):
        if x not in et or x not in eb or x not in rt: continue
        r=np.array(rt[x]); a=np.array(et[x]); b=np.array(eb[x])
        for f in (0.35,0.5,0.65):
            pu=r+(a-r)*f; pl=r+(b-r)*f
            ups.append(L[int(pu[1]),int(pu[0])]); los.append(L[int(pl[1]),int(pl[0])])
    ups=np.array(ups); los=np.array(los)
    print(oid, 'upper %.3f lower %.3f  diff %.3f ratio %.2f'%(np.median(ups),np.median(los),np.median(ups)-np.median(los),np.median(ups)/np.median(los)))
