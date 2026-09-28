"""One-page default-look comparison: for every item the three-quarter view of the look verifier's matched-lighting sheet
(look_verify/compare/<mesh>_lit_gallery_texel_ue.png: Blender gallery graph | Blender, texel-exact filtering |
Unreal 5.8.3 default MIs). The final pass left every default base-colour capture bit-identical (smoke bomb: 2 of
16.8 M texels differ by 1 level; final/default_captures_before_after.json), so these renders stand for the final build.
    blender -b --factory-startup --python make_look_sheet.py"""
import sys
from pathlib import Path
import bpy
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.path.insert(0, str(P / "WorkFiles/materials/final/recolour"))
sys.dont_write_bytecode = True
import recolour_common as rc
from fs_font import draw_text
C = P / "WorkFiles/materials/look_verify/compare"
ITEMS = ["SM_Shuriken_FourPoint", "SM_Shuriken_EightPoint", "SM_Shuriken_SquarePlate", "SM_Shuriken_SixPoint",
         "SM_Shuriken_Spike", "SM_Shuriken_HookedCross", "SM_Kunai_Plain", "SM_SmokeBomb", "SM_BlackHat", "SM_PaperBomb"]
def load(p):
    img = bpy.data.images.load(str(p), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a); bpy.data.images.remove(img)
    return (a.reshape(h, w, 4)[::-1, :, :3] * 255.0)
T, LAB, HEAD = 386, 330, 80
rows = []
for it in ITEMS:
    a = load(C / f"{it}_lit_gallery_texel_ue.png")
    n = a.shape[0] // 3
    row = a[:n]                                   # three-quarter view row: 3 panels
    h, w = row.shape[:2]
    f = 2
    row = row[: h // f * f, : w // f * f].reshape(h // f, f, w // f, f, 3).mean(axis=(1, 3))
    rows.append((it, row))
W = LAB + max(r.shape[1] for _, r in rows)
H = HEAD + sum(r.shape[0] + 8 for _, r in rows)
canvas = np.full((H, W, 3), 24, np.int32)
draw_text(canvas, 12, 10, "DEFAULT LOOK: BLENDER VS UNREAL 5.8.3 (MATCHED LIGHTS, SAME FBX LOD0)", (235, 235, 235), 3)
draw_text(canvas, 12, 44, "COLUMNS: BLENDER GALLERY GRAPH | BLENDER, LINEAR-FILTERED MAPS | UNREAL DEFAULT MI (FINAL BUILD, BIT-IDENTICAL BASE COLOUR)", (180, 180, 180), 1)
y = HEAD
for it, r in rows:
    draw_text(canvas, 12, y + 10, it.replace("SM_", "").upper(), (235, 235, 235), 2)
    if r.shape[1] > 1200:
        draw_text(canvas, 12, y + 40, "4TH COLUMN: UNREAL WITH", (180, 180, 180), 1)
        draw_text(canvas, 12, y + 52, "CLOTH SHEEN ON (OPTIONAL)", (180, 180, 180), 1)
    canvas[y:y + r.shape[0], LAB:LAB + r.shape[1]] = np.clip(np.rint(r), 0, 255).astype(np.int32)
    y += r.shape[0] + 8
rgba = np.concatenate([canvas, np.full((H, W, 1), 255, np.int32)], -1)
out = P / "WorkFiles/materials/final/default_look_comparison.png"
rc.png_write(out, rgba, 8)
print("LOOK_SHEET", out, W, H)
