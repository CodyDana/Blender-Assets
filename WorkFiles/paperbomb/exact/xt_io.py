# -*- coding: utf-8 -*-
"""exact/ helpers: PNG IO through OpenImageIO (Blender's bundled Python)."""
import numpy as np
import OpenImageIO as oiio

V2 = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"

def read(path):
    buf = oiio.ImageBuf(path)
    spec = buf.spec()
    a = buf.get_pixels(oiio.FLOAT)
    return np.asarray(a, np.float64), spec

def write(path, arr, scale=1):
    a = np.clip(np.asarray(arr, np.float64), 0, 1)
    if a.ndim == 2:
        a = a[..., None]
    if scale > 1:
        a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w, c = a.shape
    spec = oiio.ImageSpec(w, h, c, oiio.UINT8)
    out = oiio.ImageOutput.create(path)
    out.open(path, spec)
    out.write_image((a * 255 + 0.5).astype(np.uint8))
    out.close()
    return path
