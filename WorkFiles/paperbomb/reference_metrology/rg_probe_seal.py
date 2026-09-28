import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rg_lib as R
S1 = json.load(open(os.path.join(HERE, "rg_s1_silhouette.json"), encoding="utf-8"))
XL=S1['sides']['L']['b']; XR=S1['sides']['R']['b']; YT=S1['sides']['T']['b']; YB=S1['sides']['B']['b']
WPX=XR-XL; HPX=YB-YT; PPMM=S1['ppmm']; CW=70.0; CH=S1['card_h_mm_from_aspect']
mmx=lambda x:(x-XL)/WPX*CW; mmy=lambda y:(y-YT)/HPX*CH
a,_=R.read_stored(R.RG); H,W=a.shape[:2]
lu=R.luma(a); rex=a[...,0]-.5*(a[...,1]+a[...,2])
red = (rex > 0.47)
# small seal: column profile of red in y 535..600
z=np.zeros((H,W),bool); z[535:600,215:275]=True
m=red&z
for x in range(215,275):
    c=int(m[:,x].sum())
    if c: print('x',x,'mm %.2f'%mmx(x),'redrows',c)
print('---rows---')
for y in range(535,600):
    c=int(m[y].sum())
    xs=np.flatnonzero(m[y])
    if c: print('y',y,'mm %.2f'%mmy(y),'n',c,'x',xs.min(),xs.max())
