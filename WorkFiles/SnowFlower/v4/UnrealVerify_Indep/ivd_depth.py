"""Render-based containment (Blender headless, numpy only) on Unreal's OWN scene-depth captures (ivc_render.py).
Same ortho camera for 'sheath only' and 'sword only' (sword attached to the Holster socket).  For every pixel past the
mouth where the sword is visible, the sheath must also be visible AND nearer to the camera, from all four sides.
Writes ivD_depth.json and renders/iv_depth_containment.png (grey = sheath, red = sword pixel NOT covered, green = covered).
"""
import bpy, json
from pathlib import Path
import numpy as np

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep")
C = json.loads((HERE / "ivC_render.json").read_text())
B = json.loads((HERE / "ivB_verify.json").read_text())
mouth = B["attach"]["mouth_socket"]
mz = mouth["t"][2]
BG = 1.0e4


def load(name):
    im = bpy.data.images.load(str(HERE / "renders" / (name + ".exr")))
    im.colorspace_settings.name = "Non-Color"
    a = np.array(im.pixels[:], dtype=np.float64).reshape(im.size[1], im.size[0], im.channels)[..., 0]
    return a  # row 0 = bottom of the image


res = {"mouth_z_cm": mz, "views": {}}
tiles = []
for vn in ("py", "ny", "px", "nx"):
    shot = next(s for s in C["depth_shots"] if s["name"] == f"depth_{vn}_sheath")
    W, H = shot["px"]; ow = shot["ortho_w"]; zc = shot["zc"]
    px = ow / W
    z = zc - H * px / 2 + (np.arange(H) + 0.5) * px  # per row (bottom-up)
    sh = load(f"depth_{vn}_sheath"); sw = load(f"depth_{vn}_sword")
    sh_vis = sh < BG; sw_vis = sw < BG
    deep = (z > mz + 0.1)[:, None] & np.ones((1, W), bool)  # 1 mm past the mouth plane and deeper
    test = sw_vis & deep
    covered = test & sh_vis & (sh < sw)
    uncovered = test & ~covered
    sep = (sw - sh)[covered]
    rows_sw = np.where(sw_vis.any(1))[0]
    res["views"][vn] = {
        "px_cm": px,
        "sword_pixels_past_mouth": int(test.sum()),
        "covered_by_nearer_sheath": int(covered.sum()),
        "uncovered": int(uncovered.sum()),
        "uncovered_rows_z_cm": sorted(set(np.round(z[np.where(uncovered)[0]], 2).tolist()))[:10],
        "min_depth_separation_mm": float(sep.min() * 10) if sep.size else None,
        "p1_depth_separation_mm": float(np.percentile(sep, 1) * 10) if sep.size else None,
        "sword_z_extent_cm": [float(z[rows_sw.min()]), float(z[rows_sw.max()])] if rows_sw.size else None,
        "sheath_z_extent_cm": [float(z[np.where(sh_vis.any(1))[0].min()]), float(z[np.where(sh_vis.any(1))[0].max()])],
        "depth_quantum_cm": float(np.min(np.diff(np.unique(sh[sh_vis])))) if sh_vis.sum() > 2 else None,
    }
    img = np.zeros((H, W, 4)); img[..., 3] = 1
    img[sh_vis] = (0.35, 0.35, 0.38, 1)
    img[covered] = (0.1, 0.75, 0.2, 1)
    img[uncovered] = (1, 0, 0, 1)
    img[sw_vis & ~deep] = (0.9, 0.8, 0.2, 1)  # hilt side (outside the mouth), for orientation
    tiles.append(img)
    tiles.append(np.zeros((H, 12, 4)) + (0, 0, 0, 1))
mosaic = np.concatenate(tiles[:-1], axis=1)
out = bpy.data.images.new("iv_depth", mosaic.shape[1], mosaic.shape[0], alpha=True)
out.pixels = mosaic.ravel().astype(np.float32)
out.filepath_raw = str(HERE / "renders" / "iv_depth_containment.png")
out.file_format = "PNG"
out.save()
res["all_views_pass"] = all(v["uncovered"] == 0 and v["sword_pixels_past_mouth"] > 0 for v in res["views"].values())
(HERE / "ivD_depth.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("IVD", json.dumps(res))
