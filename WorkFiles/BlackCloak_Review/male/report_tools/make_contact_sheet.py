# Contact sheet for the male-worn black cloak review. Built from EXISTING images only.
# Run: blender -b --factory-startup --python make_contact_sheet.py
import bpy, numpy as np, json, os

R = "C:/Users/Cody/Desktop/Blender_Projects/"
M = R + "WorkFiles/BlackCloak_Review/male/"
PIE = "C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Saved/Claude/Shots/metahuman_cloak/final/"
OUT = M + "MALE_CLOAK_contact_sheet.png"
REF = R + "References/BlackCloak/blackcloak.png"

def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1]
    bpy.data.images.remove(im)
    return np.ascontiguousarray(a[..., :3])

def save(a, p):
    h, w = a.shape[:2]
    a = np.concatenate([np.clip(a, 0, 1), np.ones((h, w, 1), np.float32)], 2)
    im = bpy.data.images.new("sheet_out", w, h, alpha=False)
    im.pixels.foreach_set(np.ascontiguousarray(a[::-1]).astype(np.float32).ravel())
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

def resize(a, H=None, W=None):
    h, w = a.shape[:2]
    if H is None: H = int(round(h * W / w))
    if W is None: W = int(round(w * H / h))
    # area-ish: bilinear on a pre-box-filtered image when shrinking a lot
    f = max(1, int(min(h / H, w / W)))
    if f > 1:
        hh, ww = (h // f) * f, (w // f) * f
        a = a[:hh, :ww].reshape(hh // f, f, ww // f, f, 3).mean((1, 3)); h, w = a.shape[:2]
    ys = np.clip((np.arange(H) + 0.5) * h / H - 0.5, 0, h - 1.001); xs = np.clip((np.arange(W) + 0.5) * w / W - 0.5, 0, w - 1.001)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int); fy = (ys - y0)[:, None, None]; fx = (xs - x0)[None, :, None]
    A = a[y0][:, x0]; B = a[y0][:, x0 + 1]; C = a[y0 + 1][:, x0]; D = a[y0 + 1][:, x0 + 1]
    return (A * (1 - fx) + B * fx) * (1 - fy) + (C * (1 - fx) + D * fx) * fy

# ---- tiny 5x7 bitmap font ----
G = {
'A':"01110 10001 10001 11111 10001 10001 10001",'B':"11110 10001 10001 11110 10001 10001 11110",
'C':"01110 10001 10000 10000 10000 10001 01110",'D':"11110 10001 10001 10001 10001 10001 11110",
'E':"11111 10000 10000 11110 10000 10000 11111",'F':"11111 10000 10000 11110 10000 10000 10000",
'G':"01110 10001 10000 10111 10001 10001 01111",'H':"10001 10001 10001 11111 10001 10001 10001",
'I':"01110 00100 00100 00100 00100 00100 01110",'J':"00111 00010 00010 00010 00010 10010 01100",
'K':"10001 10010 10100 11000 10100 10010 10001",'L':"10000 10000 10000 10000 10000 10000 11111",
'M':"10001 11011 10101 10101 10001 10001 10001",'N':"10001 11001 10101 10011 10001 10001 10001",
'O':"01110 10001 10001 10001 10001 10001 01110",'P':"11110 10001 10001 11110 10000 10000 10000",
'Q':"01110 10001 10001 10001 10101 10010 01101",'R':"11110 10001 10001 11110 10100 10010 10001",
'S':"01111 10000 10000 01110 00001 00001 11110",'T':"11111 00100 00100 00100 00100 00100 00100",
'U':"10001 10001 10001 10001 10001 10001 01110",'V':"10001 10001 10001 10001 10001 01010 00100",
'W':"10001 10001 10001 10101 10101 10101 01010",'X':"10001 10001 01010 00100 01010 10001 10001",
'Y':"10001 10001 01010 00100 00100 00100 00100",'Z':"11111 00001 00010 00100 01000 10000 11111",
'0':"01110 10001 10011 10101 11001 10001 01110",'1':"00100 01100 00100 00100 00100 00100 01110",
'2':"01110 10001 00001 00010 00100 01000 11111",'3':"11110 00001 00001 01110 00001 00001 11110",
'4':"00010 00110 01010 10010 11111 00010 00010",'5':"11111 10000 11110 00001 00001 10001 01110",
'6':"00110 01000 10000 11110 10001 10001 01110",'7':"11111 00001 00010 00100 01000 01000 01000",
'8':"01110 10001 10001 01110 10001 10001 01110",'9':"01110 10001 10001 01111 00001 00010 01100",
' ':"00000 00000 00000 00000 00000 00000 00000",'.':"00000 00000 00000 00000 00000 01100 01100",
',':"00000 00000 00000 00000 01100 00100 01000",':':"00000 01100 01100 00000 01100 01100 00000",
'-':"00000 00000 00000 11111 00000 00000 00000",'/':"00001 00010 00010 00100 01000 01000 10000",
'(':"00010 00100 01000 01000 01000 00100 00010",')':"01000 00100 00010 00010 00010 00100 01000",
'=':"00000 00000 11111 00000 11111 00000 00000",'+':"00000 00100 00100 11111 00100 00100 00000",
'%':"11001 11010 00010 00100 01000 01011 10011","'":"00100 00100 01000 00000 00000 00000 00000",
'|':"00100 00100 00100 00100 00100 00100 00100",'>':"01000 00100 00010 00001 00010 00100 01000",
'<':"00010 00100 01000 10000 01000 00100 00010",'#':"01010 11111 01010 01010 01010 11111 01010",
}
def text(img, s, x, y, sc=3, col=(0, 0, 0), bg=None):
    s = s.upper(); w = len(s) * 6 * sc
    if bg is not None:
        img[max(0, y - sc):y + 8 * sc, max(0, x - sc):x + w + sc] = bg
    for i, ch in enumerate(s):
        g = G.get(ch, G[' ']).split()
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '1':
                    yy, xx = y + r * sc, x + (i * 6 + c) * sc
                    img[yy:yy + sc, xx:xx + sc] = col

def canvas(h, w, v=1.0): return np.full((h, w, 3), v, np.float32)

ref = load(REF)                      # 417 x 674
H1 = 700
row1 = [
 ("REFERENCE (USER PHOTO)", ref),
 ("OURS: UE ENGINE, CLOAK ONLY, REST", load(M + "unreal/shots/front_cloak_only_yaw+0.png")),
 ("OURS ON THE MALE, REST (UE)", load(M + "unreal/shots/front_with_body.png")),
 ("ON THE MALE, CLOTH SETTLED IOU 0.80", load(M + "unreal/shots/front_with_body_cloth_SIE_settled.png")),
 ("BLENDER CYCLES, MALE ARMS DOWN", load(M + "blender/renders/b_ref_body_down_game.png")),
]
panels1 = [(t, resize(a, H=H1)) for t, a in row1]

# ---- blind pairs, sides labelled by matching the reference crop ----
bp = json.load(open(M + "blind_tools/blind_params.json"))
regs = bp["regions"]
pairs = [(3, "COLLAR: RINGS VS DIAGONAL WRAPS"), (4, "CLASP: THIN RING + PIN, NO STRAP"),
         (13, "HEM: SQUARE STRIPS VS FLARED HEM"), (14, "EDGE: CLEAN CUT VS FRAYED"),
         (16, "FABRIC: STREAKS VS SLUB GRAIN"), (18, "SILHOUETTE (IOU 0.94 ALIGNED)")]
H2 = 330
panels2 = []; sides = {}
for idx, title in pairs:
    im = load(M + f"blind/pair_{idx:02d}.png"); h, w = im.shape[:2]; hw = (w - 16) // 2
    L, Rr = im[:, :hw], im[:, hw + 16:]
    kind, (x0, y0, x1, y1), t = regs[idx - 1]
    if kind == "sil":
        refc = np.where((0.2126*ref[..., 0]+0.7152*ref[..., 1]+0.0722*ref[..., 2]) < 0.45, 0.0, 1.0)[..., None].repeat(3, 2)
    else:
        refc = ref
    rc = resize(refc[y0:y1, x0:x1], H=h, W=hw)
    eL = float(np.mean((L - rc) ** 2)); eR = float(np.mean((Rr - rc) ** 2))
    ref_side = "left" if eL < eR else "right"; sides[idx] = [ref_side, round(eL, 5), round(eR, 5)]
    lab = ("REF", "OURS") if ref_side == "left" else ("OURS", "REF")
    L2 = resize(L, H=H2); R2 = resize(Rr, H=H2)
    text(L2, lab[0], 6, 6, 3, (1, 1, 1), bg=(0.75, 0.1, 0.1) if lab[0] == "OURS" else (0.1, 0.35, 0.1))
    text(R2, lab[1], 6, 6, 3, (1, 1, 1), bg=(0.75, 0.1, 0.1) if lab[1] == "OURS" else (0.1, 0.35, 0.1))
    gap = canvas(H2, 8, 0.5)
    panels2.append((f"PAIR {idx}: " + title, np.concatenate([L2, gap, R2], 1)))

# ---- PIE shots (cropped around the character) ----
H3 = 520
pie = [
 ("PIE IDLE FRONT: FACE COVERED, LEGS SHOW", PIE + "b01_front.png", (520, 330, 1080, 900)),
 ("PIE CLOSE: COWL TO UNDER THE EYES", PIE + "b05_close.png", (420, 560, 1180, 900)),
 ("PIE RUN SIDE: FLAT BOARD CAPE", PIE + "a05_run_side.png", (430, 440, 1200, 900)),
 ("PIE FLIP LAND: STRIPS FLY AS RIBBONS", PIE + "a15_flip_land.png", (620, 300, 1260, 900)),
]
panels3 = []
for t, p, (x0, y0, x1, y1) in pie:
    a = load(p)[y0:y1, x0:x1]; panels3.append((t, resize(a, H=H3)))

def row(panels, H, pad=14, title_h=34):
    Wt = sum(a.shape[1] for _, a in panels) + pad * (len(panels) + 1)
    c = canvas(H + title_h + pad, Wt, 1.0); x = pad
    for t, a in panels:
        c[title_h:title_h + a.shape[0], x:x + a.shape[1]] = a
        tt = t
        while len(tt) * 12 > a.shape[1] and len(tt) > 4: tt = tt[:-1]
        text(c, tt, x, 8, 2, (0, 0, 0)); x += a.shape[1] + pad
    return c

rows = [row(panels1, H1), row(panels2[:3], H2), row(panels2[3:], H2), row(panels3, H3)]
W = max(r.shape[1] for r in rows)
head = canvas(110, W, 1.0)
text(head, "BLACK CLOAK ON THE MALE (MH_PLAYERDEFAULT) VS THE USER REFERENCE - 2026-09-27", 14, 12, 4)
text(head, "BLIND JUDGE 20/20 CORRECT (18 CONFIDENT); PASS MARK 13 OR FEWER.  SILHOUETTE IOU 0.92 RAW / 0.94 ALIGNED AT REST; 0.80 WITH CLOTH SETTLED.", 14, 58, 2)
text(head, "ROW 1: REFERENCE | OUR CLOAK | ON THE MALE.  ROWS 2-3: 6 OF THE 20 BLIND PAIRS (EXPOSURE-MATCHED, SIDES LABELLED AFTER JUDGING).  ROW 4: IN-GAME PIE SHOTS.", 14, 84, 2)
out = [head]
for r in rows:
    if r.shape[1] < W: r = np.concatenate([r, canvas(r.shape[0], W - r.shape[1])], 1)
    out.append(r); out.append(canvas(6, W, 0.8))
sheet = np.concatenate(out, 0)
save(sheet, OUT)
json.dump({"out": OUT, "size": [sheet.shape[1], sheet.shape[0]], "pair_ref_side_mse": sides},
          open(M + "report_tools/contact_sheet_log.json", "w"), indent=1)
print("SHEET", sheet.shape, sides)
