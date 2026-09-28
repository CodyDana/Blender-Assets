import bpy, numpy as np, json
M = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/"
OUT = M + "verify/"
J = json.load(open(OUT + "vf_measure.json"))
def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.empty(w * h * im.channels, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, im.channels)[::-1][..., :3].copy(); bpy.data.images.remove(im); return a
def save(arr, path):
    h, w = arr.shape[:2]; im = bpy.data.images.new("o", w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = arr
    im.pixels.foreach_set(rgba[::-1].ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
def warp2(img, s, tx, ty, H2, W2, src_scale):
    # target pixel in ref*2 frame; x_ref = s*x_src1x + tx ; src image is src_scale x its 1x
    yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
    xr = xx / 2.0; yr = yy / 2.0
    sx = np.round((xr - tx) / s * src_scale).astype(int); sy = np.round((yr - ty) / s * src_scale).astype(int)
    h, w = img.shape[:2]; ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
    out = np.ones((H2, W2, 3), np.float32); out[ok] = img[sy[ok], sx[ok]]; return out
ref = load("C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png")
H, W = ref.shape[:2]
ref2 = np.repeat(np.repeat(ref, 2, 0), 2, 1)
s, tx, ty = J["UE"]["s_tx_ty"]
ue = warp2(load(M + "unreal/shots/front_cloak_only_yaw+0.png"), s, tx, ty, 2 * H, 2 * W, 2)
uep = warp2(load(M + "unreal/shots/DIAG_front_cloak_only_plus2EV.png"), s, tx, ty, 2 * H, 2 * W, 2)
sb, txb, tyb = J["BL"]["s_tx_ty"]
bl = warp2(load(M + "blender/compare/a_ref_cloak_game_refframe_2x.png"), sb, txb, tyb, 2 * H, 2 * W, 2)
def brighten(a, g):  # display gain in linear for dark-cloth reading (same gain on all panels)
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4) * g
    lin = np.clip(lin, 0, 1); return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
def grid(a, x0, y0, step=10):
    a = a.copy(); h, w = a.shape[:2]
    for gx in range(0, w, step * 2):
        a[:, gx] = [1, 0.2, 0.2] if ((gx // 2 + x0) % 50 == 0) else [0.2, 0.8, 0.2]
    for gy in range(0, h, step * 2):
        a[gy, :] = [1, 0.2, 0.2] if ((gy // 2 + y0) % 50 == 0) else [0.2, 0.8, 0.2]
    return a
regions = {"collar_clasp": (60, 0, 300, 200), "hem": (0, 540, 417, 674), "leftwing": (0, 290, 150, 674), "rightshoulder": (230, 40, 417, 260)}
for name, (x0, y0, x1, y1) in regions.items():
    cr = lambda a: a[2 * y0:2 * y1, 2 * x0:2 * x1]
    # ref brightened 3x, UE brightened by the median-matching gain, BL by its gain -> all to ref-like display
    gU = 2.79 * 3; gB = (0.0130 / 0.00873) * 3
    panels = [brighten(cr(ref2), 3), brighten(cr(ue), gU), brighten(cr(bl), gB)]
    if name == "collar_clasp":
        panels = [grid(p, x0, y0) for p in panels]
    sep = np.full((2 * (y1 - y0), 6, 3), 0.5, np.float32)
    row = np.concatenate(sum([[p, sep] for p in panels], [])[:-1], 1)
    save(row, OUT + "vf_crop_%s_REF_UE_BL_x2_gain3.png" % name)
print("VF_CROPS_DONE")
