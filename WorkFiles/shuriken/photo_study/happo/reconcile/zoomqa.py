import sys, os, numpy as np, json, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R
im=bpy.data.images.load(R.BASE+"/happo_overlay_reconciled.png"); w,h=im.size
buf=np.empty(w*h*4,np.float32); im.pixels.foreach_get(buf); o=buf.reshape(h,w,4)[::-1,:,:3]
G=json.load(open(R.BASE+"/reconcile/reconciled_geom.json"))
def crop(cx,cy,half=60,z=3):
    x0,y0=int(cx-half),int(cy-half); c=np.ones((2*half,2*half,3),np.float32)*0.2
    xs=slice(max(0,x0),min(w,x0+2*half)); ys=slice(max(0,y0),min(h,y0+2*half))
    c[ys.start-y0:ys.stop-y0, xs.start-x0:xs.stop-x0]=o[ys,xs]
    return np.repeat(np.repeat(c,z,0),z,1)
N=G['notches']; T=G['tips']
# T3-N2 midpoint
t3=np.array(T['3']['vertex']); n2=np.array(N['2']['vertex']); m=(t3+n2)/2
tiles=[crop(*N['1']['vertex']), crop(*N['0']['vertex']), crop(*m), crop(*T['6']['vertex']), crop(*T['5']['vertex'][:1], 1180), crop(*N['4']['vertex'])]
row1=np.hstack(tiles[:3]); row2=np.hstack(tiles[3:])
sep=np.ones((6,row1.shape[1],3),np.float32)
R.save_png(np.vstack([row1,sep,row2]), R.BASE+"/reconcile/zoom_qa.png")
print('ok')
