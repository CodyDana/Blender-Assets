"""Per-region scores on a BC: black/red IoU (half level), edge (mm), core dE, pixel dE. usage: r2_region.py <bc.npy|shipped>"""
import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T, paperbomb_tracedart as TA, paperbomb_fidelity as FD, paperbomb_trace as PT
from props_lib import atlas as AT, paperbomb_art as A
from props_lib.spec import PAPER_BOMB
import xt_io
plan = AT.plan_for(PAPER_BOMB)
m=TA.reference_model(); L=m.L; fit=L.fit
if sys.argv[1]=="shipped":
    a,_=xt_io.read(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
    bc=T.srgb_to_linear(a[:plan.raster[1],:plan.raster[0],:3])
    cfg = A.ArtConfig(ppmm=plan.ppmm, pad_mm=plan.pad_mm, supersample=1)
    W_,H_=A.raster_size(cfg); card,_=A._card_mask(cfg, A.LAYOUT, W_, H_); card=card[:bc.shape[0],:bc.shape[1]]
else:
    bc=np.load(sys.argv[1]); card=np.load(sys.argv[1].replace("_bc","_card"))
ph=FD.photograph(bc, card, plan.ppmm, plan.pad_mm, L.src, fit)
ps=T.Source(path="p",sha256="",nbytes=0,rgb=ph,info={}); k2,r2,_=T.ink_layers(ps,fit)
de=T.delta_e2000(T.srgb_to_lab(L.src.rgb),T.srgb_to_lab(ph))
REG={"ruleTop_black":((25,5.2,47,8.0),"black"),"cTL_knob_black":((2.0,7.0,6.0,11.0),"black"),
     "sealTL_spark":((7.2,124.5,12.0,129.3),"red"),"sealBR_spark":((18.7,144.2,22.9,148.4),"red"),
     "dou_box":((59.0,146.0,61.6,149.8),"red")}
out={}
for n,(box,layer) in REG.items():
    reg=(L.xm>=box[0])&(L.xm<box[2])&(L.ym>=box[1])&(L.ym<box[3])
    obs=L.black if layer=="black" else L.red_behind; ours=k2 if layer=="black" else r2
    sc=PT.score_fields(ours,obs,reg,fit.ppmm)
    core=reg&((obs>0.5)|(ours>0.5))
    rc=T.srgb_to_lab(np.median(L.src.rgb[reg&(obs>0.5)],0)); oc=T.srgb_to_lab(np.median(ph[reg&(ours>0.5)],0))
    out[n]={"iou":sc["iou"],"edge_mean_mm":sc.get("edge_mean_mm"),"edge_p95_mm":sc.get("edge_p95_mm"),
            "core_dE":round(float(T.delta_e2000(rc,oc)),3),"px_dE_mean":round(float(de[reg].mean()),3),"px_dE_p90":round(float(np.percentile(de[reg],90)),3)}
    print(n, out[n])
json.dump(out,open(sys.argv[2] if len(sys.argv)>2 else "r2_region.json","w"),indent=1)
