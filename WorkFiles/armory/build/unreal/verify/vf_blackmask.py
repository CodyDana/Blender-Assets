"""Verifier: side-by-side of Unreal capture | Blender render with near-black (<0.02 luminance) pixels painted cyan and
fully clipped pixels magenta, downscaled, for C1 and CW and C10. Writes vf_mask_<cam>.png here."""
import bpy, numpy as np, sys, os
OUTD = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--") + 1]))
CAP = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\captures"
REN = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\renders\fix1"
P = {"C1": ("C1_EntryReveal.png", "C1_EntryReveal_golden.png"), "CW": ("CW_WestAisle.png", "CW_WestAisle_golden.png"),
     "C10": ("C10_Hero.png", "C10_Hero_golden.png")}
def load(p):
    im = bpy.data.images.load(p); im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[:, :, :4].copy()
for k, (u, b) in P.items():
    outs = []
    for a in (load(os.path.join(CAP, u)), load(os.path.join(REN, b))):
        y = 0.2126*a[..., 0] + 0.7152*a[..., 1] + 0.0722*a[..., 2]
        a[y < 0.02, :3] = (0, 1, 1)
        a[a[..., :3].min(-1) > 0.98, :3] = (1, 0, 1)
        a[..., 3] = 1
        outs.append(a[::2, ::2])
    img = np.concatenate(outs, axis=1)
    h, w = img.shape[:2]
    o = bpy.data.images.new("m"+k, w, h, alpha=True); o.colorspace_settings.name = "Non-Color"
    o.pixels = img.ravel().tolist(); o.filepath_raw = os.path.join(OUTD, f"vf_mask_{k}.png"); o.file_format = "PNG"; o.save()
print("VF_MASK_DONE")
