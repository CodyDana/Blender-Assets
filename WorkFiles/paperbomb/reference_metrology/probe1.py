# -*- coding: utf-8 -*-
"""DEBUG/METROLOGY probe 1 - reports stored-value stats for the two reference
images and our build's base colour. Measurement only; emits numbers, never art."""
import sys, os, json
import bpy, numpy as np

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology"

def load_stored(path):
    """Return HxWx4 float array of STORED (non-colour-managed) 0..1 values,
    row 0 = TOP of the image (numpy/screen order)."""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)
    a = a[::-1]  # Blender stores bottom-up; flip to top-down
    bpy.data.images.remove(img)
    return a

def stats(name, path):
    a = load_stored(path)
    h, w, _ = a.shape
    rgb = a[..., :3]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    sat = mx - mn
    lum = 0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]
    print(f"\n=== {name} {w}x{h} alpha_min={a[...,3].min():.3f} ===")
    print(" corner 8x8 means (TL,TR,BL,BR):")
    for lbl, sl in (("TL", (slice(0,8), slice(0,8))), ("TR",(slice(0,8), slice(w-8,w))),
                    ("BL",(slice(h-8,h), slice(0,8))), ("BR",(slice(h-8,h), slice(w-8,w)))):
        print("  ", lbl, np.round(rgb[sl[0], sl[1]].reshape(-1,3).mean(axis=0), 4).tolist())
    print(" centre 8x8 mean:", np.round(rgb[h//2-4:h//2+4, w//2-4:w//2+4].reshape(-1,3).mean(axis=0),4).tolist())
    for q in (0,1,2,5,10,25,50,75,90,95,99,100):
        print(f"  lum p{q:3d}={np.percentile(lum,q):.4f}  sat p{q:3d}={np.percentile(sat,q):.4f}")
    # Non-background mask candidates
    for thr in (0.02, 0.03, 0.05, 0.08):
        m = (sat > thr) | (lum < 1.0 - thr)
        ys, xs = np.nonzero(m)
        if len(xs):
            print(f"  mask sat>{thr} or lum<{1-thr:.2f}: n={m.sum()} bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]")
    return a

for nm, p in (("V1", r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png"),
              ("V2", r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"),
              ("BC", r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")):
    if os.path.exists(p):
        stats(nm, p)
    else:
        print("MISSING", p)
print("\nNumPy", np.__version__, "Blender", bpy.app.version_string)
