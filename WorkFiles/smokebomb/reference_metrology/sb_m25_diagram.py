"""Stage 25: the labelled strip-layout debug diagram (DEBUG, NEVER SHIP). Edges coloured by the strip that owns
them, strip labels, over/under junction tags (X>Y = X lies over Y), limb-exit ticks with image angles."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S
from sb_m08_segments import text

rgb = L.load_srgb(); Y = L.lum(rgb)
base = L.stretch(L.gauss_blur(Y, 1.5), 0.02, 0.30)
img = np.repeat(base[..., None], 3, 2).astype(np.float32) * 0.55 + 0.12
img[Y > 0.6] = 0.97
H, W = Y.shape
tr = json.load(open(os.path.join(L.D, "sb_trace.json")))['edges']
OWN = {"WTW": "W", "WUP": "W", "WLO": "W", "ALO": "A", "BUP": "B", "BLO": "B", "CUP": "C", "CLO": "C", "LIN": "R", "L3L": "L",
       "LA": "R", "LB": "R", "LC": "R", "UA": "U", "UC": "U", "UD": "U", "UE": "U", "UF": "U", "WHV": "G", "D9": "D", "D57": "D",
       "D14": "D", "D19": "D", "D27": "D"}
COL = {"W": (1, 0.9, 0.1), "A": (0.1, 0.9, 1), "B": (1, 0.3, 1), "C": (1, 0.55, 0.1), "R": (0.3, 1, 0.3), "L": (0.55, 0.75, 1),
       "U": (0.8, 0.6, 1), "G": (1, 1, 1), "D": (1, 0.35, 0.35)}


def line(im, a, b, col, w=2):
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 2
    for f in np.linspace(0, 1, n):
        x = int(round(a[0] + f * (b[0] - a[0]))); y = int(round(a[1] + f * (b[1] - a[1])))
        if 0 <= x < im.shape[1] - w and 0 <= y < im.shape[0] - w:
            im[y:y + w, x:x + w] = col


for k, e in tr.items():
    P = np.array(e['pts'], float); c = np.array(COL[OWN[k]], np.float32)
    for a_, b_ in zip(P[:-1], P[1:]):
        line(img, a_, b_, c, 3)
# circle fit
for t in np.linspace(0, 2 * np.pi, 6000):
    x = int(round(S.CX + S.R * np.cos(t))); y = int(round(S.CY - S.R * np.sin(t)))
    img[y, x] = (0.2, 0.6, 1.0)
M = 60
out = np.ones((H + 2 * M, W + 2 * M, 3), np.float32)
out[M:M + H, M:M + W] = img


def T(s, x, y, col, sc=3):
    text(out, s, M + x + 1, M + y + 1, np.zeros(3, np.float32), sc)
    text(out, s, M + x, M + y, np.array(col, np.float32), sc)


LAB = [("W", 915, 712, "W"), ("W TWIST", 420, 452, "W"), ("A", 600, 700, "A"), ("A", 420, 560, "A"), ("B", 880, 460, "B"),
       ("X", 975, 600, "W"), ("C", 300, 790, "C"), ("L3", 285, 575, "L"), ("L4", 226, 600, "L"), ("L5", 176, 640, "R"),
       ("RIN", 410, 330, "R"), ("R2", 330, 290, "R"), ("R3", 330, 222, "R"), ("U0", 440, 395, "U"), ("U1", 590, 330, "U"),
       ("U2", 690, 380, "U"), ("U3", 790, 330, "U"), ("U4", 870, 330, "U"), ("U5", 945, 330, "U"), ("DA", 380, 960, "D"),
       ("DB", 505, 935, "D"), ("DC", 620, 930, "D"), ("E", 820, 960, "A"), ("WHORL", 700, 200, "G")]
for s, x, y, c in LAB:
    T(s, x, y, COL[c], 4 if len(s) <= 2 else 3)
JX = [("W>A", 800, 745), ("W>X", 955, 660), ("W>B", 560, 530), ("W>U0", 470, 490), ("R>W", 330, 375), ("R>A", 250, 440),
      ("B>X", 925, 565), ("B>U", 780, 410), ("A>C", 360, 690), ("A>C", 610, 860), ("A>L3", 300, 640), ("A>E", 900, 935),
      ("C>L", 240, 725), ("C>D", 430, 880), ("GAP", 510, 470), ("GAP", 650, 240), ("L4>L3?", 150, 520), ("C = B UNDER A AND W (INFERRED)", 420, 660)]
for s, x, y in JX:
    T(s, x, y, (1, 1, 1), 2)
# limb exits
for ang, lab in ((348.8, "W 349"), (333.5, "W 334"), (330.0, "A 330"), (25.5, "B 26"), (11.7, "B 12"), (197.6, "C 198"),
                 (220.6, "C 221"), (139.5, "R3 140"), (156.4, "LB 156"), (167.3, "LC 167")):
    t = np.radians(ang)
    a_ = (S.CX + (S.R + 4) * np.cos(t) + M, S.CY - (S.R + 4) * np.sin(t) + M)
    b_ = (S.CX + (S.R + 40) * np.cos(t) + M, S.CY - (S.R + 40) * np.sin(t) + M)
    line(out, a_, b_, np.array((0.9, 0.1, 0.1), np.float32), 2)
    tx = S.CX + (S.R + 44) * np.cos(t) + M; ty = S.CY - (S.R + 44) * np.sin(t) + M
    text(out, lab, int(tx - (len(lab) * 8 if np.cos(t) < 0 else 0)), int(ty - 5), np.array((0.8, 0.1, 0.1), np.float32), 2)
text(out, "DEBUG NEVER SHIP - SMOKE BOMB STRIP LAYOUT - X>Y MEANS X OVER Y - ANGLES CCW FROM 3 OCLOCK", 10, 8,
     np.array((0.8, 0.1, 0.1), np.float32), 2)
L.save_png(os.path.join(L.DBG, "DEBUG_NEVER_SHIP_sb_strip_layout_LABELLED.png"), out)
print("saved")
