# -*- coding: utf-8 -*-
"""Font-ID common helpers.  Reads ONLY References/PaperBomb/paperbomb_guide_v2_real_glyphs.png
(V2).  Writes only under WorkFiles/paperbomb/exact/fontid/."""
import os, sys, json, hashlib
import numpy as np
ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
MET = os.path.join(ROOT, "WorkFiles", "paperbomb", "reference_metrology")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MET)
import pngread  # noqa  (pure decoder, read-only use)
V2 = os.path.join(ROOT, "References", "PaperBomb", "paperbomb_guide_v2_real_glyphs.png")
S1 = json.load(open(os.path.join(MET, "rg_s1_silhouette.json"), encoding="utf-8"))
XL = S1['sides']['L']['b']; XR = S1['sides']['R']['b']
YT = S1['sides']['T']['b']; YB = S1['sides']['B']['b']
WPX = XR - XL; HPX = YB - YT
PPMM = S1['ppmm']; CARD_W = 70.0; CARD_H = S1['card_h_mm_from_aspect']

def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def load_v2():
    a, info = pngread.read_png(V2)
    a = a.astype(np.float64) / (65535.0 if a.dtype == np.uint16 else 255.0)
    if a.ndim == 2: a = a[..., None]
    if a.shape[2] == 1: a = np.repeat(a, 3, 2)
    return a[..., :3]

def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

def mm2px(xmm, ymm):
    return XL + xmm / CARD_W * WPX, YT + ymm / CARD_H * HPX

def save_png(arr, path, scale=1):
    import bpy
    a = np.clip(np.asarray(arr, np.float64), 0, 1)
    if a.ndim == 2: a = np.repeat(a[..., None], 3, 2)
    if scale > 1: a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w = a.shape[:2]
    a = np.concatenate([a, np.ones((h, w, 1))], 2)
    img = bpy.data.images.new("fid_tmp", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(a[::-1].astype(np.float32).ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path
