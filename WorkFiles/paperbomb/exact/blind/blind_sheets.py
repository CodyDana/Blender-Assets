import bpy, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/blind/pairs3/"
def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels; a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1, :, :3].copy(); bpy.data.images.remove(im); return a
def save(a, p):
    a = np.clip(a, 0, 1).astype(np.float32); h, w = a.shape[:2]
    rgba = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)[::-1]
    im = bpy.data.images.new("o", w, h, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
names = ["emblem", "centre_baku", "col_TL", "col_TR", "col_BR_yakujin", "col_BC_shungyo", "seal_big", "small_seal",
         "ring", "rule_top", "rule_left", "chain", "corner_TL", "corner_TR", "corner_BL", "corner_BR"]
for view in ("gallery", "thumb"):
    tiles = [load(D + "%s__%s.png" % (n, view)) for n in names]
    # lay out in a grid of 4 columns, each tile on a white cell, separated by blue bars
    cols = 4; cw = max(t.shape[1] for t in tiles) + 12; ch = max(t.shape[0] for t in tiles) + 12
    rows = (len(tiles)+cols-1)//cols
    S = np.full((rows*ch, cols*cw, 3), 1.0, np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols); y = r*ch+6; x = c*cw+6
        S[y:y+t.shape[0], x:x+t.shape[1]] = t
        S[r*ch:r*ch+2, c*cw:(c+1)*cw] = [0, 0.3, 1]; S[r*ch:(r+1)*ch, c*cw:c*cw+2] = [0, 0.3, 1]
    save(S, D + "../sheet_%s.png" % view)
    print(view, S.shape)
