import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')).astype(float)
L=0.299*im[...,0]+0.587*im[...,1]+0.114*im[...,2]; O=im[...,0]-im[...,2]
def bilin(a,x,y):
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    return (a[y0,x0]*(1-fx)*(1-fy)+a[y0,x0+1]*fx*(1-fy)+a[y0+1,x0]*(1-fx)*fy+a[y0+1,x0+1]*fx*fy)
def trace(ch,p0,p1,half=5.0,n=None,mode='step',plat=1.5,verbose=False):
    p0=np.array(p0,float);p1=np.array(p1,float); d=p1-p0; Ln=np.hypot(*d); u=d/Ln; nrm=np.array([-u[1],u[0]])
    n=n or int(Ln)+1; pts=[]
    s=np.arange(-half,half+1e-9,0.05)
    for t in np.linspace(0,1,n):
        c=p0+t*d; xs=c[0]+s*nrm[0]; ys=c[1]+s*nrm[1]; p=bilin(ch,xs,ys)
        if mode=='step':
            a=p[s<-half+plat].mean(); b=p[s>half-plat].mean(); m=(a+b)/2
            if abs(a-b)<15: continue
            sg=np.sign(b-a); idx=np.where(np.diff(np.sign(p-m))!=0)[0]
            if len(idx)==0: continue
            # choose crossing closest to centre
            i=idx[np.argmin(abs(s[idx]))]
            off=s[i]+(m-p[i])/(p[i+1]-p[i])*0.05
        else: # peak (ridge-like line), sign +1 for bright line
            q=p*(1 if mode=='peak' else -1)
            q=q-np.convolve(q,np.ones(61)/61,'same')
            i=np.argmax(q[20:-20])+20
            if i<=0 or i>=len(q)-1: continue
            den=q[i-1]-2*q[i]+q[i+1]; off=s[i]+(0.5*(q[i-1]-q[i+1])/den*0.05 if den!=0 else 0)
        pts.append(c+off*nrm)
    return np.array(pts)
def fitline(P):
    c=P.mean(0); U,S,Vt=np.linalg.svd(P-c); d=Vt[0]; 
    if d[0]<0: d=-d
    nrm=np.array([-d[1],d[0]]); res=(P-c)@nrm
    return c,d,res
def inter(l1,l2):
    (c1,d1),(c2,d2)=l1,l2
    A=np.column_stack([d1,-d2]); t=np.linalg.solve(A,c2-c1); return c1+t[0]*d1
feat={
 'top_front':(O,(293,129.5),(385,113.5),'step'),
 'top_rear':(O,(261,164),(287,133),'step'),
 'bot_front':(O,(317,184.5),(385,137),'step'),
 'bot_rear':(O,(266,186.5),(309,188),'step'),
 'ridge_front':(L,(304,157),(390,116),'step'),
 'ridge_rear':(L,(266,171),(297,160),'step'),
 'crease_up':(L,(291.5,134),(299.5,155),'peak'),
 'grip_top':(O,(160,202),(250,168),'step'),
 'grip_bot':(O,(160,222),(250,190),'step'),
}
out={}; lines={}
for k,(ch,a,b,mode) in feat.items():
    P=trace(ch,a,b,half=(3.0 if k.startswith('crease') else 5.0),mode=mode)
    c,d,res=fitline(P)
    # iterate: drop outliers
    keep=abs(res)<max(2.5*np.std(res),0.3); P=P[keep]; c,d,res=fitline(P)
    lines[k]=(c,d); out[k]=dict(n=len(P),c=c.tolist(),d=d.tolist(),ang=float(np.degrees(np.arctan2(d[1],d[0]))),rms=float(np.std(res)),pts=P.tolist())
    print(f"{k:12s} n={len(P):3d} ang={out[k]['ang']:7.2f} rms={out[k]['rms']:.2f} c=({c[0]:.1f},{c[1]:.1f})")
json.dump(out,open('blade_lines.json','w'))
Tt=inter(lines['top_front'],lines['top_rear']); Tb=inter(lines['bot_front'],lines['bot_rear'])
tip=inter(lines['top_front'],lines['bot_front']); R=inter(lines['ridge_front'],lines['ridge_rear'])
Rc=inter(lines['crease_up'],lines['ridge_front'])
print('Ttop',Tt,'Tbot',Tb,'tip',tip,'R(ridges)',R,'R(crease_up x ridge_front)',Rc)
# grip axis
gc=(lines['grip_top'][0]+lines['grip_bot'][0])/2; gd=lines['grip_top'][1]+lines['grip_bot'][1]; gd/=np.hypot(*gd)
print('grip axis ang',np.degrees(np.arctan2(gd[1],gd[0])),'grip widths', )
# bisector of front edges
d1=lines['top_front'][1]; d2=lines['bot_front'][1]; bis=d1+d2; bis/=np.hypot(*bis)
print('front-edge bisector ang',np.degrees(np.arctan2(bis[1],bis[0])))
M=(Tt+Tb)/2; ch=Tb-Tt; print('chord ang',np.degrees(np.arctan2(ch[1],ch[0])),'half chord',np.hypot(*ch)/2,'M',M)
np.save('keypts.npy',np.array([Tt,Tb,tip,R,Rc,M]))
