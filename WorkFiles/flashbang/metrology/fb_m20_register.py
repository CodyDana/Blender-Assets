import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
OUTD = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/ref"
ref = load_srgb()
E = json.load(open(DBG + "/fb_edges.json"))
YB = dict(v1=720.5, v2=716.8, v3=717.0, v4=717.0)
Dt = 200.0
CW, CH, AX, BY = 440, 820, 220, 790
reg = {}
tiles = []
tiles2 = []
for v in ['v1', 'v2', 'v3', 'v4']:
    ws = [E[v][k]['width'] for k in ('body_web_A_B', 'body_web_B_C', 'body_low')]
    cs = [E[v][k]['centre'] for k in ('body_web_A_B', 'body_web_B_C', 'body_low')]
    Dv = float(np.mean(ws)); cv = float(np.mean(cs)); s = Dt / Dv
    s_common = Dt / 175.31
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float64)
    sx = cv + (xx - AX)/s; sy = YB[v] + (yy - BY)/s
    img = bilinear(ref, sx, sy)
    BOX = dict(v1=(40, 345), v2=(345, 615), v3=(615, 950), v4=(950, 1240))[v]
    out_of = (sx < BOX[0]) | (sx > BOX[1]) | (sy < 0) | (sy > 745)
    img[out_of] = 0.12
    save_png(f"{OUTD}/fb_ref_{v}_registered_D200.png", img)
    reg[v] = dict(body_centre_x_ref=round(cv, 2), body_width_px=round(Dv, 2), bottom_y_ref=YB[v], scale_to_D200=round(s, 5),
                  mapping="reg_x = 220 + (ref_x - body_centre_x)*scale ; reg_y = 790 + (ref_y - bottom_y)*scale ; D = 200 px, bottom contact at row 790")
    tiles.append(img)
    sx2 = cv + (xx - AX)/s_common; sy2 = YB[v] + (yy - BY)/s_common
    img2 = bilinear(ref, sx2, sy2); img2[(sx2 < BOX[0]) | (sx2 > BOX[1]) | (sy2 < 0) | (sy2 > 745)] = 0.12
    save_png(f"{OUTD}/fb_ref_{v}_registered_common.png", img2); tiles2.append(img2)
    reg[v]['scale_common'] = round(s_common, 5)
strip = np.concatenate(tiles, 1)
save_png(f"{OUTD}/fb_ref_top_row_registered_common.png", np.concatenate(tiles2, 1))
save_png(f"{OUTD}/fb_ref_top_row_registered_D200.png", strip)
# guide-line version
G = strip.copy()
for H_D, col in ((0.0, [1, 0, 0]), (0.5, [0.3, 0.3, 1]), (1.0, [0.3, 0.3, 1]), (1.5, [0.3, 0.3, 1]), (2.0, [0.3, 0.3, 1]), (2.5, [0.3, 0.3, 1]), (3.0, [0.3, 0.3, 1]), (3.5, [0.3, 0.3, 1])):
    r = int(round(BY - H_D*Dt))
    if 0 <= r < CH: G[r, ::2] = col
for k in range(4):
    x0 = k*CW
    for dx in (-100, 100): G[::2, x0 + AX + dx] = [0, 0.8, 0.8]
    G[::3, x0 + AX] = [0.8, 0.8, 0]
save_png(f"{OUTD}/fb_ref_top_row_registered_D200_guides.png", G)
# native crops of the bottom close-up panels and the untouched full reference copy crops
PANELS = dict(p1_fuze_head=(6, 756, 318, 1220), p2_perforated_body=(323, 756, 629, 1220), p3_base_end=(634, 756, 939, 1220), p4_hole_inner_tube=(946, 756, 1249, 1220))
for n, (a, b, c, d) in PANELS.items():
    save_png(f"{OUTD}/fb_ref_{n}_native.png", ref[b:d, a:c])
    save_png(f"{OUTD}/fb_ref_{n}_x2.png", upscale(ref[b:d, a:c], 2))
json.dump(dict(views=reg, panels_ref_px_box_x0y0x1y1=PANELS), open(f"{OUTD}/fb_registration.json", "w"), indent=1)
print(json.dumps(reg, indent=0))
