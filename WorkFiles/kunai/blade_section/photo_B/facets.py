import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg').convert('RGB')).astype(float)
L=0.299*im[...,0]+0.587*im[...,1]+0.114*im[...,2]
Ls=json.load(open('blade_lines.json'))
def line(k): return np.array(Ls[k]['c']),np.array(Ls[k]['d'])
def hit(P,v,k):
    c,d=line(k); A=np.column_stack([v,-d]); t=np.linalg.solve(A,c-P); return t[0]
Tt,Tb,tip,R,Rc,M=np.load('keypts.npy')
axd=np.array([np.cos(np.radians(-22.76)),np.sin(np.radians(-22.76))]); v=np.array([axd[1],-axd[0]])  # v: perpendicular toward top edge (up-left)
print('v',v)
def inter(k1,k2):
    (c1,d1),(c2,d2)=line(k1),line(k2); t=np.linalg.solve(np.column_stack([d1,-d2]),c2-c1); return c1+t[0]*d1
sh_top=inter('top_rear','grip_top'); sh_bot=inter('bot_rear','grip_bot')
ax0=M  # axial origin at the widest station
def axial(p): return (p-M)@axd
s_sh=(axial(sh_top)+axial(sh_bot))/2; s_tip=axial(tip); s_vis=axial(np.array([403.0,110.3]))
print('shoulder pts',sh_top,sh_bot,'axial: shoulder %.1f widest 0 visible end %.1f tip %.1f'%(s_sh,s_vis,s_tip))
res=dict(s_shoulder=s_sh,s_widest=0.0,s_visible_end=s_vis,s_tip=s_tip,shoulder_top=sh_top.tolist(),shoulder_bot=sh_bot.tolist())
rows=[]
for s in np.arange(s_sh+2,s_vis-3,3):
    P=M+s*axd; front=s>=0
    tt=hit(P,v,'top_front' if front else 'top_rear'); tb=hit(P,v,'bot_front' if front else 'bot_rear'); tr=hit(P,v,'ridge_front' if front else 'ridge_rear')
    def samp(a,b):
        vals=[]
        for ds in np.arange(-2,2.01,0.5):
            for f in np.linspace(0.3,0.7,5):
                q=P+ds*axd+(a+f*(b-a))*v; vals.append(L[int(round(q[1])),int(round(q[0]))])
        return float(np.median(vals))
    rows.append(dict(s=float(s),frac_vis=float((s-s_sh)/(s_vis-s_sh)),frac_tip=float((s-s_sh)/(s_tip-s_sh)),halfw=float((tt-tb)/2),off=float(tr-(tt+tb)/2),Lup=samp(tr,tt),Llo=samp(tb,tr)))
for r in rows: print('s=%6.1f fv=%.2f ft=%.2f hw=%5.2f off=%5.2f Lup=%5.1f Llo=%5.1f'%tuple(r.values()))
res['rows']=rows; json.dump(res,open('facets.json','w'),indent=1)
