# -*- coding: utf-8 -*-
"""Decisive test: is the shipped atlas the SAME drawing as the art map?
2-D ink-mask IoU over a scale/offset search."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P

ART = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png"
ATL = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"

a = P.load_stored(ART)[..., :3]
b = P.load_stored(ATL)[..., :3]
La, Lb = P.luma_stored(a).astype(np.float64), P.luma_stored(b).astype(np.float64)


def inkmask(L, win=None):
    reg = L if win is None else L[win[1]:win[3], win[0]:win[2]]
    p = float(np.percentile(reg, 75)); fl = float(np.percentile(reg, 0.5))
    return L < 0.5 * (p + fl)


ma = inkmask(La)
mb = inkmask(Lb, (0, 0, 930, 2048))
mb[:, 930:] = False
Ha, Wa = ma.shape

best = None
for sx in np.linspace(0.93, 1.005, 31):
    for sy in np.linspace(0.975, 1.02, 19):
        for tx in np.linspace(0, 60, 31):
            for ty in np.linspace(-25, 25, 21):
                ii = np.arange(0, Wa, 4)
                jj = np.arange(0, Ha, 4)
                X = np.clip((sx * ii + tx).astype(int), 0, mb.shape[1] - 1)
                Y = np.clip((sy * jj + ty).astype(int), 0, mb.shape[0] - 1)
                A = ma[jj][:, ii]
                B = mb[Y][:, X]
                inter = np.count_nonzero(A & B)
                uni = np.count_nonzero(A | B)
                iou = inter / max(uni, 1)
                if best is None or iou > best[0]:
                    best = (iou, sx, sy, tx, ty)
print(f"coarse best IoU={best[0]:.4f} sx={best[1]:.4f} sy={best[2]:.4f} tx={best[3]:.2f} ty={best[4]:.2f}")

_, sx0, sy0, tx0, ty0 = best
best2 = None
for sx in np.linspace(sx0 - 0.01, sx0 + 0.01, 21):
    for sy in np.linspace(sy0 - 0.008, sy0 + 0.008, 17):
        for tx in np.linspace(tx0 - 3, tx0 + 3, 25):
            for ty in np.linspace(ty0 - 3, ty0 + 3, 25):
                ii = np.arange(0, Wa, 2)
                jj = np.arange(0, Ha, 2)
                X = np.clip((sx * ii + tx).astype(int), 0, mb.shape[1] - 1)
                Y = np.clip((sy * jj + ty).astype(int), 0, mb.shape[0] - 1)
                A = ma[jj][:, ii]
                B = mb[Y][:, X]
                inter = np.count_nonzero(A & B)
                uni = np.count_nonzero(A | B)
                iou = inter / max(uni, 1)
                if best2 is None or iou > best2[0]:
                    best2 = (iou, sx, sy, tx, ty)
print(f"fine   best IoU={best2[0]:.4f} sx={best2[1]:.5f} sy={best2[2]:.5f} tx={best2[3]:.2f} ty={best2[4]:.2f}")
iou, sx, sy, tx, ty = best2
ppmm, pad = 12.923, 1.6
x0, y0, w, h = pad * ppmm, pad * ppmm, 70.0 * ppmm, 156.0 * ppmm
print(f"implied ATLAS card rect: x0={x0*sx+tx:.2f} y0={y0*sy+ty:.2f} w={w*sx:.2f} h={h*sy:.2f}")
print(f"   atlas px/mm x={w*sx/70:.4f} y={h*sy/156:.4f}  anisotropy={(h*sy/156)/(w*sx/70):.4f}")
print(f"   atlas island aspect = {(w*sx)/(h*sy):.5f}  (true card 70/156 = {70/156:.5f})")
print(f"   ink coverage art={ma.mean():.4f}  atlas(left island)={mb.mean()*2048*2048/(w*sx*h*sy):.4f}")
