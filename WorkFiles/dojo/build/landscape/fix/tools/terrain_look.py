"""Analysis: grazing-sun hillshade (9 deg from the west) of LS_Valley near field + height profiles. usage: terrain_look.py <npy> <out_png>"""
import sys, numpy as np
from PIL import Image
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\landscape")
import ls_geo as G
T = np.load(sys.argv[1]).astype(np.float64)
ls = G.LS_VALLEY; xs, ys = G.grid_axes(ls)
def idx(x, y): return int(round((ys[0]-y)/0.5)), int(round((x-xs[0])/0.5))
r0, c0 = idx(-60, 110); r1, c1 = idx(160, -90)
A = T[r0:r1, c0:c1]
gy, gx = np.gradient(A, 0.5)
# level frame: column -> +x, row -> -y
nx, ny, nz = -gx, gy, np.ones_like(A)
n = np.sqrt(nx*nx+ny*ny+1)
el = np.radians(9.08); az = np.radians(187.29)
L = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
hs = np.clip((nx*L[0]+ny*L[1]+nz*L[2])/n, 0, 1)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
im = np.stack([hs, hs, hs], -1)
im[slope > 60] = [1, 0.2, 0.2]
Image.fromarray((im*255).astype(np.uint8)).save(sys.argv[2])
print("crop x -60..160 y 110..-90; steep(>60deg) px", int((slope>60).sum()))
for name,(x,y0,y1) in {"x=-12 (west strip out)":(-12,-5,60),"x=22 north":(22,30,90)}.items():
    pass
for y in (10, 30, 40):
    row = [round(float(T[idx(x,y)]),2) for x in range(-30,1,2)]
    print("y",y,"x -30..0:",row)
for x in (0, 22, 44):
    col = [round(float(T[idx(x,y)]),2) for y in range(40,70,2)]
    print("x",x,"y 40..68:",col)
