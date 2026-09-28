import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')).astype(float)
R,G,B=im[...,0],im[...,1],im[...,2]
# "orange-ness" of background vs grey/dark metal
orng=(R-B)
def bilin(a,x,y):
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    return (a[y0,x0]*(1-fx)*(1-fy)+a[y0,x0+1]*fx*(1-fy)+a[y0+1,x0]*(1-fx)*fy+a[y0+1,x0+1]*fx*fy)
c0=np.array([123.0,233.0])
print('orng bg sample', orng[230,123], orng[205,100], 'ring', orng[250,120], orng[215,110])
out=[];inn=[]
for ang in np.arange(0,360,3):
    t=np.radians(ang); d=np.array([np.cos(t),np.sin(t)])
    r=np.arange(4,36,0.1); xs=c0[0]+r*d[0]; ys=c0[1]+r*d[1]
    p=bilin(orng,xs,ys)
    out.append((ang,r,p))
np.save('ring_profiles.npy',np.array([o[2] for o in out]))
# print a few profiles
for ang,r,p in out[::10]:
    print(ang, ' '.join(f'{v:.0f}' for v in p[::10]))
