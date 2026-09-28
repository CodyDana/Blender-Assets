import sys, json, math, numpy as np, time
sys.path.insert(0,'.')
import section_procedure as SP
import run_validate2 as V
from run_validate import FV, x_of_fvis, analytic
def go(name,k,scale,persp=False,log=True):
    png=V.HERE/'validate'/f'{name}.png'; meta=json.loads(open(str(png)+'.json').read())
    lum0,al0=SP.load_lum(png); lum,al=V.resize(lum0,scale),V.resize(al0,scale)
    blade=SP.blade_from_meta(meta,scale=scale,visible_x=x_of_fvis(1.0)); pr=meta['probe']
    c=np.array(pr['centre_px'])*scale; cl=[[p[0]*scale,p[1]*scale] for p in pr['centreline_px']]; tube=pr['tube_r_px']*scale
    sig=0.35*max(scale,0.5); fn,box=SP.ring_d_centreline(c,cl,tube); pix=SP.probe_pixels(fn,box,1-(0.5+2*sig)/tube)
    W,H=lum.shape[1],lum.shape[0]
    mc=SP.ParamMatcap(lum,fn,pix,sig_psf=sig,persp=((meta['args']['focal']/36*W),W/2,H/2) if persp else None,log=log)
    out=[]
    for f in FV:
        x=x_of_fvis(f); s=blade.s_of_x(x); q,*_=SP.ridge_offset(lum,blade,s,alpha=al)
        r=SP.run2(lum,blade,mc,[s],lambda _s:q,alpha=al,gain1=False)[0]
        out.append((r['ratio_r'],analytic(x,k)['face_slope']))
    return out, mc
for name,k in (('v1_z1',1),('v7_z1_roll6',1),('v4_z1_probe035',1),('v3_z2',2),('v8_z35_roll0',3.5),('v5_z35_probe035',3.5)):
  for scale in (1.0,0.7):
    for persp in (False,True):
     for log in (True,False):
      t=time.time(); out,mc=go(name,k,scale,persp,log)
      rat=[a/b for a,b in out[2:]]
      print(('L' if log else 'lin')+' %-16s s%.1f p%d med %.2f [%.2f-%.2f] rear %.2f %.2f | rms %.3f | %s  (%.0fs)'%(name,scale,persp,np.median(rat),min(rat),max(rat),out[0][0]/out[0][1],out[1][0]/out[1][1],mc.rms,' '.join('%.3f/%.3f'%o for o in out),time.time()-t),flush=True)
