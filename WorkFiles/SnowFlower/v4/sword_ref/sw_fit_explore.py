"""Explore blade outline vs a straight reference-outline sheath (static fit). Pure numpy."""
import json, numpy as np
prof=json.load(open('sw_ref_profile.json'))['front']
MMPX=1256.3/1206.0
seat,tip=338,1215
rows=np.arange(seat,tip+1)
L=np.array([prof[r][0] for r in rows],float); R=np.array([prof[r][1] for r in rows],float)
spine0=np.median(L[(rows>380)&(rows<900)])
t=(rows-seat)/(tip-seat)
sheet_sweep=(spine0-L)*MMPX            # + = toward the spine side
sheet_w=(R-L)*MMPX
print('spine0',spine0,'sweep at tip mm',sheet_sweep[-1],'max',sheet_sweep.max())
for tt in (0,.05,.1,.2,.3,.4,.5,.6,.7,.75,.8,.85,.9,.95,.98,1.0):
    i=np.argmin(abs(t-tt)); print(f't {tt:.2f} row {rows[i]} sweep {sheet_sweep[i]:6.1f} width {sheet_w[i]:5.1f}')
# sheath outer width px vs ref row (spec)
def sheath_w_px(row):
    if row<169: return 97
    if row<=322: return 97 if row<287 else 96
    if row<=1250: return 96+(72-96)*(row-322)/(1250-322)
    if row<=1292: return 72
    if row<=1387: return 72+(84-72)*min(1,(row-1292)/40)
    # ogive to point at 1496
    u=(row-1387)/(1496-1387); return 84*np.sqrt(max(0,1-u**2))
def fit(sweep_scale,k,wall=2.5,clr=1.0,Lb=918.0):
    sw=sheet_sweep*sweep_scale
    sp=sw; ed=sw-sheet_w
    s_mm=t*Lb
    ref_row=31+s_mm/k+3/k
    hw=np.array([sheath_w_px(r)*k/2 for r in ref_row])-wall-clr
    best=None
    for c in np.linspace(-45,15,601):
        m=np.min(hw-np.maximum(abs(sp-c),abs(ed-c)))
        if best is None or m>best[0]: best=(m,c)
    return best
for sc in (1.0,.8,.6,.5,.4,.3,0.0):
    for k in (0.687,0.70,0.72):
        m,c=fit(sc,k); print(f'sweep x{sc:.1f} ({sheet_sweep[-1]*sc:5.1f} mm) k {k}: best margin {m:6.2f} mm at axis c {c:5.1f} mm from spine line')
# where is the limit?
for sc in (1.0,0.5,0.0):
    k=0.70; sw=sheet_sweep*sc; ed=sw-sheet_w; s_mm=t*918.0; ref_row=31+s_mm/k+3/k
    hw=np.array([sheath_w_px(r)*k/2 for r in ref_row])-3.5
    m,c=fit(sc,k); marg=hw-np.maximum(abs(sw-c),abs(ed-c)); i=np.argmin(marg)
    print('scale',sc,'limit at t',round(t[i],3),'row',round(ref_row[i]),'margin',round(marg[i],2),'halfwidth',round(hw[i],1),'c',c)
