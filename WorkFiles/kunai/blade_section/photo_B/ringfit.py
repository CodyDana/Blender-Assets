import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')).astype(float)
orng=im[...,0]-im[...,2]
def bilin(a,x,y):
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    return (a[y0,x0]*(1-fx)*(1-fy)+a[y0,x0+1]*fx*(1-fy)+a[y0+1,x0]*(1-fx)*fy+a[y0+1,x0+1]*fx*fy)
def fit_ellipse(P):
    x,y=P[:,0],P[:,1]
    D=np.column_stack([x*x,x*y,y*y,x,y,np.ones_like(x)])
    S=D.T@D; C=np.zeros((6,6)); C[0,2]=C[2,0]=2; C[1,1]=-1
    w,v=np.linalg.eig(np.linalg.solve(S,C))
    a=None
    for i in range(6):
        vv=np.real(v[:,i]); 
        if 4*vv[0]*vv[2]-vv[1]**2>0: a=vv
    A,Bc,Cc,Dd,E,F=a
    M=np.array([[A,Bc/2],[Bc/2,Cc]]); ctr=np.linalg.solve(2*M,[-Dd,-E])
    Fc=F+ (A*ctr[0]**2+Bc*ctr[0]*ctr[1]+Cc*ctr[1]**2+Dd*ctr[0]+E*ctr[1]) - (A*ctr[0]**2+Bc*ctr[0]*ctr[1]+Cc*ctr[1]**2)*0
    # value at centre
    Fc=A*ctr[0]**2+Bc*ctr[0]*ctr[1]+Cc*ctr[1]**2+Dd*ctr[0]+E*ctr[1]+F
    ev,evec=np.linalg.eigh(M)
    axes=np.sqrt(-Fc/ev)
    i=np.argmax(axes); j=1-i
    major=axes[i]; minor=axes[j]; dmaj=evec[:,i]; dmin=evec[:,j]
    ang=np.degrees(np.arctan2(dmin[1],dmin[0]))%180
    # residuals (approx geometric): radial
    res=[]
    for p in P:
        q=p-ctr; th=np.arctan2(q@dmin,q@dmaj)
        rr=1/np.sqrt((np.cos(th)/major)**2+(np.sin(th)/minor)**2); res.append(np.hypot(*q)-rr)
    return dict(center=ctr.tolist(),semi_major=float(major),semi_minor=float(minor),ratio=float(minor/major),minor_dir_deg=float(ang),rms=float(np.sqrt(np.mean(np.square(res)))),conic=a.tolist()), np.array(res)
def run(c0,excl,thr=45,step=2):
    outer=[];inner=[];angs=[]
    for ang in np.arange(0,360,step):
        if excl[0]<=ang or ang<=excl[1]: continue
        t=np.radians(ang); d=np.array([np.cos(t),np.sin(t)])
        r=np.arange(3,36,0.05); p=bilin(orng,c0[0]+r*d[0],c0[1]+r*d[1])
        below=p<thr
        if not below.any(): continue
        i0=np.argmax(below); i1=len(p)-1-np.argmax(below[::-1])
        # interpolate crossings
        ri=r[i0-1]+(thr-p[i0-1])/(p[i0]-p[i0-1])*(r[i0]-r[i0-1])
        ro=r[i1]+(thr-p[i1])/(p[i1+1]-p[i1])*(r[i1+1]-r[i1])
        inner.append(c0+ri*d); outer.append(c0+ro*d); angs.append(ang)
    return np.array(inner),np.array(outer),np.array(angs)
res={}
for thr in (30,45,60):
    c0=np.array([123.0,233.0])
    for it in range(2):
        I,O,A=run(c0,(305,25),thr)
        fi,ri=fit_ellipse(I); fo,ro=fit_ellipse(O)
        c0=(np.array(fi['center'])+np.array(fo['center']))/2
    # mean "centreline" ellipse = average of both
    res[thr]=dict(inner=fi,outer=fo)
    print('thr',thr)
    for k,f in (('inner',fi),('outer',fo)):
        print(' ',k,'ctr %.2f %.2f a %.2f b %.2f ratio %.3f minor_dir %.1f rms %.2f'%(*f['center'],f['semi_major'],f['semi_minor'],f['ratio'],f['minor_dir_deg'],f['rms']))
    np.save(f'ring_pts_{thr}.npy',np.concatenate([I,O]))
json.dump({str(k):v for k,v in res.items()},open('ring_fit.json','w'),indent=1)
