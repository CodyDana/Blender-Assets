import numpy as np, json, bpy
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
VIEW_BOX = {"v1": (40, 30, 345, 725), "v2": (345, 30, 615, 725), "v3": (615, 30, 950, 725), "v4": (950, 30, 1240, 725)}
def load_png(path):
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size; c = im.channels
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(im)
    return a
def ref():
    return load_png(ROOT + "References/Flashbang/flashbang_reference.png")[..., :3] * 255.0
def poly_mask(poly, H=1254, W=1254):
    poly = np.asarray(poly, float)
    yy, xx = np.mgrid[0:H, 0:W]
    sy, sx = yy + 0.5, xx + 0.5
    ins = np.zeros((H, W), bool)
    for i in range(len(poly)):
        xa, ya = poly[i]; xb, yb = poly[(i + 1) % len(poly)]
        ins ^= ((ya > sy) != (yb > sy)) & (sx < (xb - xa) * (sy - ya) / (yb - ya + 1e-12) + xa)
    return ins
def ref_sil(v):
    spec = json.load(open(ROOT + "WorkFiles/flashbang/flashbang_spec.json"))
    return poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"])
def paint_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (np.abs(R - G) <= 8) & ((G - B) >= 8) & (G >= 25)
