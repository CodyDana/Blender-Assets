import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')).astype(float)
L=0.299*im[...,0]+0.587*im[...,1]+0.114*im[...,2]
def bilin(a,x,y):
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    return (a[y0,x0]*(1-fx)*(1-fy)+a[y0,x0+1]*fx*(1-fy)+a[y0+1,x0]*(1-fx)*fy+a[y0+1,x0+1]*fx*fy)
rf=json.load(open('ring_fit.json'))['45']
def rad(f,a):
    c=np.array(f['center']); A=f['semi_major']; B=f['semi_minor']; md=np.radians(f['minor_dir_deg'])
    th=a-md  # angle from minor axis
    return 1/np.sqrt((np.cos(th)/B)**2+(np.sin(th)/A)**2)
c=(np.array(rf['inner']['center'])+np.array(rf['outer']['center']))/2
pairs=[]
for adeg in np.arange(0,360,2):
    if adeg>=305 or adeg<=25: continue
    a=np.radians(adeg); ri=rad(rf['inner'],a); ro=rad(rf['outer'],a); rc=(ri+ro)/2; rho=(ro-ri)/2
    for sp in np.linspace(-0.8,0.8,17):
        r=rc+sp*rho; x=c[0]+r*np.cos(a); y=c[1]+r*np.sin(a)
        up=np.degrees(np.arcsin(sp*(-np.sin(a))))
        pairs.append((up,bilin(L,np.array([x]),np.array([y]))[0],adeg,sp))
P=np.array(pairs)
bins=np.arange(-50,52,4); curve=[]
for b0 in bins:
    m=(P[:,0]>=b0-2)&(P[:,0]<b0+2)
    if m.sum()>5: curve.append((b0,float(np.median(P[m,1])),float(np.percentile(P[m,1],25)),float(np.percentile(P[m,1],75)),int(m.sum())))
for r in curve: print('up %4d  L med %5.1f  IQR %5.1f-%5.1f n=%d'%r)
json.dump(dict(center=c.tolist(),curve=[[float(v) for v in r] for r in curve]),open('ring_probe.json','w'),indent=1)
