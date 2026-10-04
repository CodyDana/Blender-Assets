"""Render-based containment (Blender headless, numpy only) on Unreal's OWN scene-depth captures (kvC_render.py).
Same ortho camera for 'saya only' and 'katana only' (katana attached to the Holster socket, saya at an arbitrary world
transform, cameras placed in the saya's local frame).  For every pixel more than 1 mm past the mouth plane where the
katana is visible, the saya must also be visible AND nearer to the camera, from all four sides.
Writes kvD_depth.json and renders/kv_depth_containment.png (grey = saya, green = covered katana pixel,
red = katana pixel NOT covered, yellow = katana outside the mouth).
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final/ivd_depth.py.
"""
import bpy, json, sys
import numpy as np
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final")
import kv_common as C  # noqa: E402

HERE = C.HERE
Cr = json.loads((HERE / "kvC_render.json").read_text())
B = json.loads((HERE / "kvB_verify.json").read_text())
mz = B["attach"]["socket_Mouth"]["t"][2]
BG = 1.0e4


def load(name):
    im = bpy.data.images.load(str(HERE / "renders" / (name + ".exr")))
    im.colorspace_settings.name = "Non-Color"
    return np.array(im.pixels[:], dtype=np.float64).reshape(im.size[1], im.size[0], im.channels)[..., 0]


res = {"mouth_z_cm": mz, "views": {}}
tiles = []
for vn in ("py", "ny", "px", "nx"):
    shot = next(s for s in Cr["depth_shots"] if s["name"] == f"depth_{vn}_saya")
    W, H = shot["px"]; ow = shot["ortho_w"]; zc = shot["zc"]
    px = ow / W
    z = zc - H * px / 2 + (np.arange(H) + 0.5) * px
    sh = load(f"depth_{vn}_saya"); sw = load(f"depth_{vn}_katana")
    sh_vis = sh < BG; sw_vis = sw < BG
    deep = (z > mz + 0.1)[:, None] & np.ones((1, W), bool)
    test = sw_vis & deep
    covered = test & sh_vis & (sh < sw)
    uncovered = test & ~covered
    sep = (sw - sh)[covered]
    rows_sw = np.where(sw_vis.any(1))[0]
    rows_sh = np.where(sh_vis.any(1))[0]
    res["views"][vn] = {
        "px_cm": px,
        "katana_pixels_past_mouth": int(test.sum()),
        "covered_by_nearer_saya": int(covered.sum()),
        "uncovered": int(uncovered.sum()),
        "uncovered_rows_z_cm": sorted(set(np.round(z[np.where(uncovered)[0]], 2).tolist()))[:10],
        "min_depth_separation_mm": float(sep.min() * 10) if sep.size else None,
        "katana_z_extent_cm": [float(z[rows_sw.min()]), float(z[rows_sw.max()])] if rows_sw.size else None,
        "saya_z_extent_cm": [float(z[rows_sh.min()]), float(z[rows_sh.max()])] if rows_sh.size else None,
    }
    img = np.zeros((H, W, 4)); img[..., 3] = 1
    img[sh_vis] = (0.35, 0.35, 0.38, 1)
    img[covered] = (0.1, 0.75, 0.2, 1)
    img[uncovered] = (1, 0, 0, 1)
    img[sw_vis & ~deep] = (0.9, 0.8, 0.2, 1)
    tiles.append(img)
    tiles.append(np.zeros((H, 12, 4)) + (0, 0, 0, 1))
mosaic = np.concatenate(tiles[:-1], axis=1)
out = bpy.data.images.new("kv_depth", mosaic.shape[1], mosaic.shape[0], alpha=True)
out.pixels = mosaic.ravel().astype(np.float32)
out.filepath_raw = str(HERE / "renders" / "kv_depth_containment.png")
out.file_format = "PNG"
out.save()
res["all_views_pass"] = all(v["uncovered"] == 0 and v["katana_pixels_past_mouth"] > 0 for v in res["views"].values())
(HERE / "kvD_depth.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("KVD", json.dumps(res))
