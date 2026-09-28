import bpy, numpy as np
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/verify_look/"
FID = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels
    a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1].copy(); bpy.data.images.remove(im); return a[..., :3]
def save(a, p):
    h, w = a.shape[:2]
    a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    im = bpy.data.images.new("o", w, h, alpha=True); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(a[::-1]).astype(np.float32).ravel())
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
def lum(a): return 0.2126*a[..., 0]+0.7152*a[..., 1]+0.0722*a[..., 2]
ref = load(REF); ours = load(FID+"ours_lod0_front_refframe.png")
om = np.load(FID+"ours_lod0_front_mask.npy") > 0.5
Lr = lum(ref); Lo = lum(ours); rm = Lr < 150/255
def norm(L, m):
    lo, hi = np.percentile(L[m], 1), np.percentile(L[m], 99)
    out = np.clip((L-lo)/(hi-lo), 0, 1)*0.85
    out[~m] = 1.0
    return out
A = norm(Lr, rm); B = norm(Lo, om)
# grid lines every 50 px (red) and probe columns 195/283 (blue)
def rgbgrid(G):
    C = np.stack([G, G, G], 2)
    for y in range(0, G.shape[0], 50): C[y, :, :] = [1, 0.3, 0.3]
    for x in range(0, G.shape[1], 50): C[:, x, :] = [1, 0.3, 0.3]
    for x in (195, 283): C[:, x, :] = [0.2, 0.5, 1]
    return C
gap = np.ones((A.shape[0], 8, 3), np.float32)*0.5
comp = np.concatenate([rgbgrid(A), gap, rgbgrid(B)], 1)
# upscale 2x nearest
comp2 = comp.repeat(2, 0).repeat(2, 1)
save(comp2, OUT+"vl_levels_normalised_ref_vs_ours_grid.png")
# crops: top (y 0-320) and bottom (y 520-674)
save(comp[0:330].repeat(3, 0).repeat(3, 1), OUT+"vl_top_crop_x3.png")
save(comp[500:674].repeat(3, 0).repeat(3, 1), OUT+"vl_bottom_crop_x3.png")
print("ok")
