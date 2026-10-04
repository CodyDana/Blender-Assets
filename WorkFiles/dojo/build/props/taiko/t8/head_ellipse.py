"""how the head's top-outline ellipse (top 60 px, compose's fit) depends on the camera pitch: rasterise the head lip
torus (+X head) through photo_cam with the pitch varied"""
import math
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t7')
sys.path.insert(0, 'C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/props/taiko')
import photo_cam as PC
import taiko_uv as UVL

D = UVL.D_SHIFT
LIP_XC, LIP_RC, LIP_RHO = 0.758 - D, 0.528, 0.019


def fit_ellipse(xs, ys):
    M = np.c_[xs ** 2, ys ** 2, xs, ys]
    A, C, Dd, E = np.linalg.lstsq(M, np.ones_like(xs), rcond=None)[0]
    cx, cy = -Dd / (2 * A), -E / (2 * C)
    k = 1 + A * cx ** 2 + C * cy ** 2
    return cx, cy, math.sqrt(k / A), math.sqrt(k / C)


def head_pts():
    pts = []
    for a in np.linspace(-math.pi / 2, math.pi / 2, 25):     # lip roll half facing out / up
        x = LIP_XC + LIP_RHO * math.sin(a)
        r = LIP_RC + LIP_RHO * math.cos(a)
        th = np.linspace(-math.pi, math.pi, 1440)
        pts.append(PC.cyl(x, r, th))
    # the head face disc
    for r in np.linspace(0, 0.505, 30):
        pts.append(PC.cyl(0.771 - D, r, np.linspace(-math.pi, math.pi, 720)))
    # body below the lip (collar), to the tack band
    for x in np.linspace(0.55, LIP_XC, 40):
        pts.append(PC.cyl(x, UVL.body_r(x) + 0.0045, np.linspace(-math.pi, math.pi, 1440)))
    return np.vstack(pts)


P = head_pts()


def measure(pitch_deg):
    PC.PITCH = math.radians(pitch_deg)
    PC.FWD, PC.RIGHT, PC.UP = PC.basis()
    uv = PC.project_design(P)
    im = Image.new('L', (1024, 1024), 0)
    d = ImageDraw.Draw(im)
    for u, v in uv:
        d.point((u, v), fill=255)
    m = np.asarray(im) > 0
    pts = []
    for x in range(1024):
        col = np.where(m[:, x])[0]
        if len(col):
            pts.append((x, col.min()))
    pts = np.array(pts, float)
    y0 = pts[:, 1].min()
    pts = pts[pts[:, 1] < y0 + 60]
    return fit_ellipse(pts[:, 0], pts[:, 1])


p0 = math.degrees(PC.PITCH)
print('pitch0', p0, 'DH', PC.DH, 'HC', PC.HC)
for dp in ():
    print(round(p0 + dp, 2), [round(x, 2) for x in measure(p0 + dp)])
