"""bhstudy_weave_fft.py - weave periodicity on front-facing skin patches of blackhat_guide.png.
Vertical FFT (image y ~ slant direction, foreshortened by sin(pitch+elev)) finds the circumferential strand pitch;
horizontal FFT (image x ~ circumference at the front) finds the spacing of the cross divisions.
Also colour of the light worn patches vs the dark field."""
import json, numpy as np, OpenImageIO as oiio
ROOT="C:/Users/Cody/Desktop/Blender_Projects"; OUT=ROOT+"/WorkFiles/blackhat/study_calc"
px=oiio.ImageBuf(ROOT+"/References/BlackHat/blackhat_guide.png").get_pixels(oiio.FLOAT)[...,:3].astype(np.float64)
L=0.2126*px[...,0]+0.7152*px[...,1]+0.0722*px[...,2]
def peak(sig, pmin=1.8, pmax=40):
    sig=sig-sig.mean(); n=len(sig); w=np.hanning(n); F=np.abs(np.fft.rfft(sig*w))**2; fr=np.fft.rfftfreq(n)
    per=np.where(fr>0,1/np.maximum(fr,1e-9),np.inf); ok=(per>=pmin)&(per<=pmax)
    i=np.argmax(np.where(ok,F,0)); return float(per[i]), float(F[i]/F[ok].mean())
patches={"front_left":(180,290,260,370),"front_mid":(260,300,330,380),"front_right":(400,300,460,380),"left":(80,300,140,360)}
res={}
for k,(x0,y0,x1,y1) in patches.items():
    P=L[y0:y1,x0:x1]
    v=[peak(P[:,j]) for j in range(P.shape[1])]; h=[peak(P[i,:],4,40) for i in range(P.shape[0])]
    vp=np.array([a for a,_ in v]); hp=np.array([a for a,_ in h])
    # average spectrum approach
    def avgspec(M, axis, pmin, pmax):
        M=M-M.mean(axis=axis,keepdims=True); n=M.shape[axis]; w=np.hanning(n)
        W=w[:,None] if axis==0 else w[None,:]
        F=(np.abs(np.fft.rfft(M*W,axis=axis))**2).mean(axis=1-axis); fr=np.fft.rfftfreq(n)
        per=np.where(fr>0,1/np.maximum(fr,1e-9),np.inf); ok=(per>=pmin)&(per<=pmax)
        order=np.argsort(-np.where(ok,F,0))[:3]; return [(round(float(per[i]),2), round(float(F[i]/F[ok].mean()),1)) for i in order]
    res[k]={"box":[x0,y0,x1,y1],"vertical_avg_spectrum_top3":avgspec(P,0,1.8,30),"horizontal_avg_spectrum_top3":avgspec(P,1,3,40),
            "vertical_median_peak_px":float(np.median(vp)),"horizontal_median_peak_px":float(np.median(hp))}
# worn patches: body pixels (front skin region) above p90 luma vs below p50
reg=L[250:400,60:460]; C=px[250:400,60:460]
lin=np.where(C<=0.04045,C/12.92,((C+0.055)/1.055)**2.4)
hi=reg>np.percentile(reg,92); lo=(reg<np.percentile(reg,50))&(reg>np.percentile(reg,10))
for nm,m in (("light_p92",hi),("dark_p10_50",lo)):
    mu=lin[m].mean(0); res[nm+"_linear_mean"]=[round(float(a),4) for a in mu]; res[nm+"_hue"]=[1,round(float(mu[1]/mu[0]),3),round(float(mu[2]/mu[0]),3)]
res["light_fraction_gt_stored_0.35"]=float((reg>0.35).mean())
json.dump(res,open(OUT+"/bhstudy_weave_fft.json","w"),indent=1); print(json.dumps(res,indent=1))
