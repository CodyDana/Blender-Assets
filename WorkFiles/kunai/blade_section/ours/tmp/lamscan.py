import sys, json, math, numpy as np
sys.path.insert(0,'.')
import section_procedure as SP
import run_validate2 as V
from run_validate import FV, x_of_fvis, analytic
def go(name,k,scale,lam,step,persp=False):
    png=V.HERE/'validate'/f'{name}.png'; meta=json.loads(open(str(png)+'.json').read())
    lum0,al0=SP.load_lum(png); lum,al=V.resize(lum0,scale),V.resize(al0,scale)
    blade=SP.blade_from_meta(meta,scale=scale,visible_x=x_of_fvis(1.0)); pr=meta['probe']
    c=np.array(pr['centre_px'])*scale; cl=[[p[0]*scale,p[1]*scale] for p in pr['centreline_px']]; tube=pr['tube_r_px']*scale
    sig=0.35*max(scale,0.5); fn,box=SP.ring_d_centreline(c,cl,tube); pix=SP.probe_pixels(fn,box,1-(0.5+2*sig)/tube)
    W,H=lum.shape[1],lum.shape[0]
    mc=SP.DeblurMatcap(lum,fn,pix,sig_psf=sig,step=step,lam=lam,persp=((meta['args']['focal']/36*W),W/2,H/2) if persp else None)
    out=[]
    for f in FV[2:]:
        x=x_of_fvis(f); s=blade.s_of_x(x); q,*_=SP.ridge_offset(lum,blade,s,alpha=al)
        r=SP.run2(lum,blade,mc,[s],lambda _s:q,alpha=al,gain1=False)[0]
        out.append(r['ratio_r']/analytic(x,k)['face_slope'])
    return np.median(out), np.min(out), np.max(out), mc.fit_rms
for step in (0.05,0.1):
  for lam in (0.03,0.1,0.3,1.0):
    for persp in (False,True):
      res=[]
      for name,k in (('v1_z1',1),('v3_z2',2),('v8_z35_roll0',3.5),('v7_z1_roll6',1)):
        m,lo,hi,rms=go(name,k,0.7,lam,step,persp); res.append('%s %.2f[%.2f-%.2f]'%(name[:3],m,lo,hi))
      print('step',step,'lam',lam,'persp',persp,' | '.join(res),flush=True)
