"""Stage 25: labelled layout overlays (DEBUG, NEVER SHIP). fan2: camera-model outer edge (D=3.0 L, alpha=11.5, s=344), leaf inner
edge, 26 stick axes (guard axes 9.4 and 172.6 deg, 25 equal gaps), rib creases/notches, lobe, rivet, tassel parts.
fan1: 30 stick axes (16.85 .. 159.8 deg, 29 gaps), circle R=396, leaf inner edge 183."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
RED, YEL, CYA, MAG, GRN, ORA, WHT, BLU = [1,0,0], [1,1,0], [0,1,1], [1,0,1], [0,1,0], [1,0.5,0], [1,1,1], [0.2,0.4,1]
def model(rx, ry, D, alpha, s, rho, t):
    f = s*D; a = np.radians(alpha); X0 = (rx-400)/f*D; Y0 = -(ry-400)/f*D
    ct, st = np.cos(t), np.sin(t)
    X = X0 + rho*ct; Y = Y0 + rho*st*np.cos(a); Z = D + rho*st*np.sin(a)
    return 400 + f*X/Z, 400 - f*Y/Z
def to_img(rx, ry, D, alpha, s, rho, tdeg):
    # tdeg = plane angle; returns image point
    x, y = model(rx, ry, D, alpha, s, rho, np.radians(tdeg)); return float(x), float(y)
# ---- fan2
a = np.clip(load(2)*2.2, 0, 1)*0.55 + 0.1
rx, ry = 398.2, 547.0; D, al, s = 3.0, 11.5, 344.0
# plane angle for image angle phi: invert tan(phi) ~ cos(alpha) tan(t) (rays through the rivet are not affected by the depth factor)
def plane_t(phi):
    return np.degrees(np.arctan2(np.sin(np.radians(phi))/np.cos(np.radians(al)), np.cos(np.radians(phi))))
for rho, col in ((1.0, CYA), (0.431, YEL), (0.106, ORA)):
    ts = np.linspace(0, 180, 721) if rho > 0.2 else np.linspace(180, 360, 361)
    pts = [to_img(rx, ry, D, al, s, rho, t) for t in ts]
    for p0, p1 in zip(pts[:-1], pts[1:]): draw_line(a, p0, p1, col, 1)
g0, g1 = 9.4, 172.6
for k in range(26):
    phi = g0 + (g1-g0)*k/25; t = plane_t(phi)
    p_in = to_img(rx, ry, D, al, s, 0.0, t); p_out = to_img(rx, ry, D, al, s, 1.0, t)
    draw_line(a, p_in, p_out, RED if k in (0, 25) else [1, 0.35, 0.35], 1)
S20 = json.load(open(os.path.join(OUT, "fm_s20_scallop.json")))
for phi in S20["2"]["inward_notches_deg"]:
    x = rx + 349*np.cos(np.radians(phi)); y = ry - 349*np.sin(np.radians(phi)); draw_circle(a, (x, y), 2, GRN, 1)
draw_circle(a, (rx, ry), 6, WHT, 1)
T = json.load(open(os.path.join(OUT, "fm_s21_tassel.json")))
ne, ft = np.array(T['near_end_px']), np.array(T['far_tip_px']); dvec = (ft-ne)/np.linalg.norm(ft-ne)
draw_line(a, (rx, ry), tuple(ne), MAG, 1)
draw_circle(a, tuple(ne + dvec*36), 8, MAG, 1)
draw_line(a, tuple(ne + dvec*50), tuple(ft), BLU, 1)
save_png(a, "DEBUG_NEVER_SHIP_fan2_layout_LABELLED")
# ---- fan1
b = np.clip(load(1)*2.2, 0, 1)*0.55 + 0.1
rx1, ry1 = 391.6, 600.3
for rho, col in ((396, CYA), (183, YEL), (33, ORA)):
    ts = np.linspace(0, 180, 721) if rho > 60 else np.linspace(180, 360, 361)
    pts = [(rx1 + rho*np.cos(np.radians(t)), ry1 - rho*np.sin(np.radians(t))) for t in ts]
    for p0, p1 in zip(pts[:-1], pts[1:]): draw_line(b, p0, p1, col, 1)
for k in range(30):
    phi = 16.85 + (159.8-16.85)*k/29
    draw_line(b, (rx1, ry1), (rx1 + 396*np.cos(np.radians(phi)), ry1 - 396*np.sin(np.radians(phi))), RED if k in (0, 29) else [1, 0.35, 0.35], 1)
draw_circle(b, (rx1, ry1), 5, WHT, 1)
save_png(b, "DEBUG_NEVER_SHIP_fan1_layout_LABELLED")
print("done")
