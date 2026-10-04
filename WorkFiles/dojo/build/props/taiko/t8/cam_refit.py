"""judge r7 item 4: lower the photo camera's elevation (camera height HC, pitch re-aimed at the same point) until our
head's top-outline ellipse (top 60 px) has the photo's minor axis 51.6 px, then see where the plate, the ring and the
lower head's bottom land in the judge's head-aligned frame (our head ellipse scaled / moved onto the photo's)"""
import math
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t8')
import head_ellipse as HE
PC, UVL = HE.PC, HE.UVL
REF = (524.13, 91.53, 321.69, 51.57)
HC0, P0, CY0 = PC.HC, math.radians(PC._cf["pitch_down_deg"]), PC.CY
D = UVL.D_SHIFT
LIP_XC, LIP_RC, LIP_RHO = 0.758 - D, 0.528, 0.019
HW_X, R0 = 0.0083, UVL.body_r(0.0083)
phi = math.radians(5.681)
probe = {
    'plate_c': np.array([[HW_X, (R0 + 0.004) * math.cos(phi), (R0 + 0.004) * math.sin(phi)]]),
    'lower_lip_front_bottom': PC.cyl(-(LIP_XC + LIP_RHO * 0.0), LIP_RC + LIP_RHO, np.linspace(-0.6, 0.6, 400) + PC.VIEW_TH),
    'belly_left': PC.cyl(np.linspace(-0.3, 0.3, 50), UVL.body_r(0.0), PC.contour_th(UVL.body_r(0.0), -1)),
    'lower_collar_left': PC.cyl(np.linspace(-0.55, -0.45, 50), UVL.body_r(0.5) + 0.03, PC.contour_th(UVL.body_r(0.5), -1)),
}


def setcam(hc, pitch):
    PC.HC = hc
    PC.C = np.array([0.0, -PC.DH, hc])
    PC.PITCH = pitch
    PC.FWD, PC.RIGHT, PC.UP = PC.basis()


def frame():
    cx, cy, a, b = HE.measure(math.degrees(PC.PITCH))
    s = REF[2] / a
    out = {'ellipse': [round(cx, 2), round(cy, 2), round(a, 2), round(b, 2)]}
    for k, P in probe.items():
        uv = PC.project_design(P)
        uv = np.c_[REF[0] + (uv[:, 0] - cx) * s, REF[1] + (uv[:, 1] - cy) * s]
        if k == 'lower_lip_front_bottom':
            out[k] = round(float(uv[:, 1].max()), 2)
        elif k.endswith('left'):
            out[k] = round(float(uv[:, 0].min()), 2)
        else:
            out[k] = [round(float(x), 2) for x in uv[0]]
    return out


# HE.measure sets the pitch itself: keep the aim point (the camera looks at the same spot) by re-aiming the pitch
aim_z = PC.HC - PC.DH * math.tan(P0)
base = None
for hc in (HC0, HC0 - 0.15, HC0 - 0.2, HC0 - 0.25, HC0 - 0.3, HC0 - 0.35):
    pitch = math.atan((hc - aim_z) / PC.DH)
    setcam(hc, pitch)
    r = frame()
    if base is None:
        base = r
    print(round(hc, 3), round(math.degrees(pitch), 3), r)
