"""Aligns the Blender captures to the reference frame, builds the side-by-sides, overlays and matched-scale close-ups, and measures.
Run with blender -b --factory-startup --python compose.py (no scene needed)."""
import sys, os, json, bpy, math
sys.path.insert(0, os.path.dirname(__file__))
from common import D, REF, REF_W, REF_H, srgb_to_lin, lin_to_srgb, resize
from imgutil import load, save, lum
from align import best_align, warp, iou
import numpy as np

R = D + "renders/"; C = D + "compare/"; os.makedirs(C, exist_ok=True)
meas = {}

# ------------------------------------------------------------------ labels (rendered text, black on light grey)
_lbl_scene = None
def label(text, w, h=44):
    global _lbl_scene
    if _lbl_scene is None:
        _lbl_scene = bpy.data.scenes.new("LBL")
        _lbl_scene.render.engine = "BLENDER_WORKBENCH"; _lbl_scene.display.shading.light = "FLAT"
        _lbl_scene.display.shading.color_type = "OBJECT"; _lbl_scene.view_settings.view_transform = "Standard"
        w_ = bpy.data.worlds.new("LW"); _lbl_scene.world = w_; w_.color = (0.92, 0.92, 0.92)
        cam = bpy.data.cameras.new("LC"); cam.type = "ORTHO"; co = bpy.data.objects.new("LC", cam)
        _lbl_scene.collection.objects.link(co); _lbl_scene.camera = co; co.location = (0, 0, 10)
        _lbl_scene.render.film_transparent = False
    sc = _lbl_scene
    for o in list(sc.collection.objects):
        if o.type == "FONT": bpy.data.objects.remove(o, do_unlink=True)
    cu = bpy.data.curves.new("T", "FONT"); cu.body = text; cu.align_x = "LEFT"; cu.align_y = "CENTER"; cu.size = 1.0
    to = bpy.data.objects.new("T", cu); sc.collection.objects.link(to); to.color = (0, 0, 0, 1)
    cam = sc.camera; cam.data.ortho_scale = w / h * 1.6 if w > h else 1.6
    # ortho_scale spans the larger dimension (width): 1.6 units of height -> text size 1.0 about 60% of the bar
    cam.data.ortho_scale = 1.6 * w / h
    to.location = (-cam.data.ortho_scale / 2 + 0.25, 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = w, h
    p = C + "_lbl.png"; sc.render.filepath = p
    bpy.ops.render.render(write_still=True, scene=sc.name)
    a = load(p)[..., :3]; os.remove(p); return a

def with_label(img, text):
    h, w = img.shape[:2]
    return np.concatenate([label(text, w), img[..., :3]], 0)

def hstack(imgs, gap=8):
    H = max(i.shape[0] for i in imgs)
    out = []
    for k, i in enumerate(imgs):
        if i.shape[0] < H: i = np.concatenate([i, np.ones((H - i.shape[0], i.shape[1], 3))], 0)
        out.append(i)
        if k < len(imgs) - 1: out.append(np.full((H, gap, 3), 0.6))
    return np.concatenate(out, 1)

def vstack(imgs, gap=8):
    W = max(i.shape[1] for i in imgs)
    out = []
    for k, i in enumerate(imgs):
        if i.shape[1] < W: i = np.concatenate([i, np.ones((i.shape[0], W - i.shape[1], 3))], 1)
        out.append(i)
        if k < len(imgs) - 1: out.append(np.full((gap, W, 3), 0.6))
    return np.concatenate(out, 0)

def nearest_up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)

# ------------------------------------------------------------------ reference
ref = load(REF)[..., :3]
refl = lum(ref) * 255
refm = refl < 235; refm_strict = refl < 200
meas["ref_mask_px"] = int(refm.sum())

def ours(tag):
    comp = load(R + tag + ".png")[..., :3]
    mo = load(R + tag + "_mask_obj.png")
    return comp, mo

def cloak_mask(mo):
    # object mask pass: cloak black opaque, body parts coloured
    A = mo[..., 3] > 0.5
    dark = mo[..., :3].max(-1) < 0.2
    return A & dark, A

# ------------------------------------------------------------------ (a) cloak alone, reference camera
aligned = {}
for tag in ("a_ref_cloak_game", "a2_ref_cloak_tiled", "b_ref_body_down_game"):
    comp, mo = ours(tag)
    mult = comp.shape[0] // REF_H
    cm, allm = cloak_mask(mo)
    cm1 = resize(cm.astype(np.float32)[..., None], REF_H, REF_W)[..., 0] > 0.5
    if tag.startswith("a_"):
        v, (s, tx, ty) = best_align(cm1, refm)
        meas["align"] = {"iou_lum235": float(v), "s": float(s), "tx": float(tx), "ty": float(ty),
                         "note": "x_ref = s*x_ours1x + tx; ours1x = the %dx render area-averaged to 417x674" % mult}
        m_al = warp(cm1.astype(np.float32), s, tx, ty, (REF_H, REF_W), 0) > 0.5
        meas["iou_strict_lum200"] = float(iou(m_al, refm_strict))
        A = meas["align"]
    s, tx, ty = A["s"], A["tx"], A["ty"]
    c1 = resize(comp, REF_H, REF_W)
    al1 = warp(c1, s, tx, ty, (REF_H, REF_W), 1)
    ok1 = warp(np.ones((REF_H, REF_W), np.float32), s, tx, ty, (REF_H, REF_W), 0) > 0.5
    al1[~ok1] = 1.0
    c2 = resize(comp, REF_H * 2, REF_W * 2)
    al2 = warp(c2, s, 2 * tx, 2 * ty, (REF_H * 2, REF_W * 2), 1)
    ok2 = warp(np.ones((REF_H * 2, REF_W * 2), np.float32), s, 2 * tx, 2 * ty, (REF_H * 2, REF_W * 2), 0) > 0.5
    al2[~ok2] = 1.0
    save(al1, C + tag + "_refframe_1x.png"); save(al2, C + tag + "_refframe_2x.png")
    aligned[tag] = (comp, al1, al2, mult, cm)

ref2 = resize(ref, REF_H * 2, REF_W * 2)
# (c) side by side: reference | (a) cloak alone | (b) with the male
sbs = hstack([with_label(ref2, "REFERENCE (user photo, 417x674 shown 2x)"),
              with_label(aligned["a_ref_cloak_game"][2], "OURS in-game cloak ALONE, game material (UV0 untiled)"),
              with_label(aligned["b_ref_body_down_game"][2], "OURS on the male (arms down), game material")])
save(sbs, C + "c_sidebyside_ref_a_b_2x.png")
sbs1 = hstack([ref, aligned["a_ref_cloak_game"][1], aligned["a2_ref_cloak_tiled"][1], aligned["b_ref_body_down_game"][1]], 4)
save(sbs1, C + "c_sidebyside_ref_a_a2_b_1x_refscale.png")
sbsT = hstack([with_label(ref2, "REFERENCE"),
               with_label(aligned["a_ref_cloak_game"][2], "OURS game material (UV0, what the game draws)"),
               with_label(aligned["a2_ref_cloak_tiled"][2], "OURS weave tiled 12.8 cm (NOT in game)")])
save(sbsT, C + "c_sidebyside_ref_game_vs_tiled_2x.png")

# silhouette overlay at ref scale
cm_al = warp(resize(aligned["a_ref_cloak_game"][4].astype(np.float32)[..., None], REF_H, REF_W)[..., 0], A["s"], A["tx"], A["ty"], (REF_H, REF_W), 0) > 0.5
ov = np.ones((REF_H, REF_W, 3))
ov[refm & cm_al] = (0.45, 0.45, 0.45); ov[refm & ~cm_al] = (0.9, 0.1, 0.1); ov[~refm & cm_al] = (0.1, 0.6, 0.95)
save(nearest_up(ov, 2), C + "overlay_silhouette_ref_red_ours_blue_2x.png")
meas["overlay_px"] = {"both": int((refm & cm_al).sum()), "ref_only_red": int((refm & ~cm_al).sum()), "ours_only_blue": int((~refm & cm_al).sum())}

# region-wise silhouette differences (rows bands), to locate where the outline disagrees
bands = {"collar_0_120": (0, 120), "shoulders_120_260": (120, 260), "wings_260_480": (260, 480), "lower_480_600": (480, 600), "hem_600_674": (600, 674)}
meas["overlay_by_band"] = {k: {"ref_only": int((refm & ~cm_al)[a:b].sum()), "ours_only": int((~refm & cm_al)[a:b].sum()),
                               "iou": float(iou(cm_al[a:b], refm[a:b]))} for k, (a, b) in bands.items()}

# silhouette landmarks
def landmarks(m):
    ys, xs = np.nonzero(m)
    L = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
    L["h_over_w"] = float((ys.max() - ys.min()) / (xs.max() - xs.min()))
    for k in (15, 40):
        row = m[ys.min() + k]; xx = np.nonzero(row)[0]
        L["width_at_top+%d" % k] = int(xx.max() - xx.min()) if len(xx) else 0
    L["left_extreme_xy"] = [int(xs.min()), int(np.median(ys[xs == xs.min()]))]
    L["right_extreme_xy"] = [int(xs.max()), int(np.median(ys[xs == xs.max()]))]
    low = [int(np.nonzero(m[:, x])[0].max()) if m[:, x].any() else -1 for x in range(m.shape[1])]
    L["hem_lowest_y_by_x_every20"] = {x: low[x] for x in range(0, m.shape[1], 20)}
    prof = np.array([l for l in low if l > 0]); L["hem_profile_std_px"] = float(prof[len(prof)//5: -len(prof)//5].std())
    # holes: background pixels enclosed inside the outline rows (gaps between strips)
    holes = 0
    for y in range(ys.min(), ys.max()):
        xx = np.nonzero(m[y])[0]
        if len(xx): holes += int((~m[y, xx.min():xx.max()]).sum())
    L["background_inside_outline_px"] = holes
    return L
meas["landmarks_ref"] = landmarks(refm)
meas["landmarks_ours"] = landmarks(cm_al)

# ------------------------------------------------------------------ tone and grain (at reference scale, inside both masks)
def gblur(a, sig):
    r = int(3 * sig); x = np.arange(-r, r + 1); k = np.exp(-x ** 2 / (2 * sig ** 2)); k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 1, a)
inner = refm & cm_al
er = inner.copy()
for _ in range(3):  # erode 3 px so edges do not count as grain
    er = er & np.roll(er, 1, 0) & np.roll(er, -1, 0) & np.roll(er, 1, 1) & np.roll(er, -1, 1)
def tone(img, m):
    L = lum(img) * 255; v = L[m]
    hp = (L - gblur(L, 2.0))[m]
    return {"mean": float(v.mean()), "p5": float(np.percentile(v, 5)), "p50": float(np.percentile(v, 50)), "p95": float(np.percentile(v, 95)),
            "rgb_mean": [float(img[..., i][m].mean() * 255) for i in range(3)], "grain_highpass_std": float(hp.std()),
            "grain_rel": float(hp.std() / max(v.mean(), 1e-3))}
meas["tone_refscale"] = {"ref": tone(ref, er), "ours_game": tone(aligned["a_ref_cloak_game"][1], er), "ours_tiled": tone(aligned["a2_ref_cloak_tiled"][1], er)}
PATCH = {"mantle": (200, 150, 264, 214), "front_panel": (190, 380, 254, 444), "left_fall": (60, 330, 124, 394)}
def patch_hp(img, box):
    x0, y0, x1, y1 = box; L = lum(img)[y0:y1, x0:x1] * 255
    hp = L - gblur(L, 2.0); return {"mean": float(L.mean()), "hp_std": float(hp.std())}
meas["grain_patches_refscale"] = {k: {"ref": patch_hp(ref, b), "ours_game": patch_hp(aligned["a_ref_cloak_game"][1], b),
                                      "ours_tiled": patch_hp(aligned["a2_ref_cloak_tiled"][1], b)} for k, b in PATCH.items()}

# ------------------------------------------------------------------ (e) matched-scale close-ups
BOX = {"collar": (110, 0, 300, 130), "clasp": (70, 50, 170, 140), "mantle_edge": (170, 130, 410, 330),
       "wing_viewer_left": (0, 180, 150, 560), "wing_viewer_right": (270, 190, 417, 620), "front_panels": (110, 280, 310, 580),
       "hem": (10, 540, 410, 674), "fabric_mantle_64px": PATCH["mantle"], "fabric_front_panel_64px": PATCH["front_panel"]}
g4, t4 = aligned["a_ref_cloak_game"][0], aligned["a2_ref_cloak_tiled"][0]
b4 = aligned["b_ref_body_down_game"][0]
M = aligned["a_ref_cloak_game"][3]
def crop_native(img4, box, outw, outh):
    x0, y0, x1, y1 = box
    # ref coords -> ours1x -> ours Mx
    X0 = (x0 - A["tx"]) / A["s"] * M; X1 = (x1 - A["tx"]) / A["s"] * M
    Y0 = (y0 - A["ty"]) / A["s"] * M; Y1 = (y1 - A["ty"]) / A["s"] * M
    H, W = img4.shape[:2]
    xi0, xi1 = int(max(0, round(X0))), int(min(W, round(X1))); yi0, yi1 = int(max(0, round(Y0))), int(min(H, round(Y1)))
    c = img4[yi0:yi1, xi0:xi1]
    return resize(c, outh, outw)
closeups = []
for name, box in BOX.items():
    x0, y0, x1, y1 = box; bw, bh = x1 - x0, y1 - y0
    k = 4 if max(bw, bh) <= 250 else 2
    if max(bw, bh) <= 70: k = 8
    refc = nearest_up(ref[y0:y1, x0:x1], k)
    oursc = nearest_up(aligned["a_ref_cloak_game"][1][y0:y1, x0:x1], k)
    nat_g = crop_native(g4, box, bw * k, bh * k)
    nat_t = crop_native(t4, box, bw * k, bh * k)
    nat_b = crop_native(b4, box, bw * k, bh * k)
    lw = bw * k
    row = hstack([with_label(refc, "REF %s (1x px, x%d)" % (name, k)), with_label(oursc, "OURS game @ ref scale (x%d)" % k),
                  with_label(nat_g, "OURS game, %dx render" % M), with_label(nat_t, "OURS tiled 12.8cm, %dx render" % M),
                  with_label(nat_b, "OURS on male, %dx render" % M)])
    save(row, C + "e_closeup_%s.png" % name)
    closeups.append(C + "e_closeup_%s.png" % name)
meas["closeup_boxes_refpx_xyxy"] = BOX

# ------------------------------------------------------------------ other views sheet
def load_rgb(p): return load(p)[..., :3]
views = [("d_front_body_down_game", "front, arms down"), ("d_q34_body_down_game", "3/4 (clasp side)"),
         ("d_q34other_body_down_game", "3/4 (other side)"), ("d_side_r_body_down_game", "side (clasp side)"),
         ("d_side_l_body_down_game", "side (other)"), ("d_back_body_down_game", "back, arms down"),
         ("d_back_body_rest_game", "back, REST A-pose"), ("b2_ref_body_rest_game", "ref cam, REST A-pose"),
         ("d_front_cloak_game", "front, cloak alone")]
tiles = []
for t, lab in views:
    if os.path.exists(R + t + ".png"):
        im = load_rgb(R + t + ".png"); im = resize(im, im.shape[0] // 2, im.shape[1] // 2)
        tiles.append(with_label(im, lab))
rows = [hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)]
save(vstack(rows), C + "d_views_sheet.png")
mac = []
for t, lab in (("e_macro_mantle_game", "mantle @0.75 m, GAME"), ("e_macro_mantle_tiled", "mantle @0.75 m, TILED 12.8 cm"),
               ("e_macro_panel_game", "front panel @0.75 m, GAME"), ("e_macro_panel_tiled", "front panel @0.75 m, TILED")):
    if os.path.exists(R + t + ".png"):
        im = load_rgb(R + t + ".png"); mac.append(with_label(resize(im, im.shape[0] // 2, im.shape[1] // 2), lab))
if mac: save(hstack(mac), C + "e_fabric_macro_game_vs_tiled.png")

# body visibility per view
vis = {}
for f in sorted(os.listdir(R)):
    if f.endswith(".json"):
        j = json.load(open(R + f))
        if "visible_body_by_region" in j:
            vis[f[:-5]] = {k: v["px_at_ref_scale"] for k, v in j["visible_body_by_region"].items()}
meas["visible_body_px_at_ref_scale"] = vis
json.dump(meas, open(C + "measurements_male.json", "w"), indent=1)
print("MEAS", json.dumps(meas)[:6000])
