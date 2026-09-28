import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_tracedart as TA, paperbomb_fidelity as FD
from props_lib import atlas as AT
from props_lib.spec import PAPER_BOMB
plan = AT.plan_for(PAPER_BOMB)
m=TA.reference_model(); L=m.L
bc=np.load("r2_a_bc.npy"); card=np.load("r2_a_card.npy")
ph=FD.photograph(bc, card, plan.ppmm, plan.pad_mm, L.src, L.fit)
np.set_printoptions(linewidth=250, precision=2, suppress=True)
sl=(slice(40,48),slice(25,32))
lr=T.srgb_to_lab(L.src.rgb[sl]); lo=T.srgb_to_lab(ph[sl])
print("ref L"); print(lr[...,0]); print("ours L"); print(lo[...,0])
print("ref a"); print(lr[...,1]); print("ours a"); print(lo[...,1])
print("dE"); print(T.delta_e2000(lr,lo))
psrc=T.Source(path="p",sha256="",nbytes=0,rgb=ph,info={}); k2,b2,_=T.ink_layers(psrc,L.fit)
print("ref black"); print(L.black[sl]); print("ours black"); print(k2[sl])
