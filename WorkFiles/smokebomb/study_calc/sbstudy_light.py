"""SMOKEBOMB_STUDY.md section 3: how the reference is lit - mean stored luma of the cloth in 8 sectors and 3 rings
of the disc, and the backdrop just outside the silhouette (is there a cast / contact shadow?).
Writes sbstudy_light.json.  Run: blender -b --factory-startup --python sbstudy_light.py"""
import bpy, numpy as np, os, json
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
HERE = os.path.dirname(os.path.abspath(__file__))
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
CX, CY, R = 627.3, 629.1, 463.9
yy, xx = np.mgrid[0:h, 0:w]
dx, dy = xx - CX, CY - yy
r = np.hypot(dx, dy) / R
ang = (np.degrees(np.arctan2(dy, dx)) + 360.0) % 360.0
out = {"sectors_deg_ccw_from_right": {}, "rings": {}, "backdrop": {}}
for s in range(8):
    a0 = s * 45.0 - 22.5
    m = ((ang - a0) % 360.0 < 45.0) & (r > 0.30) & (r < 0.92) & (L < 0.8)
    out["sectors_deg_ccw_from_right"][f"{int(s*45)}"] = {"mean": round(float(L[m].mean()), 4),
                                                         "p50": round(float(np.median(L[m])), 4),
                                                         "p90": round(float(np.percentile(L[m], 90)), 4)}
for lo, hi in ((0.0, 0.4), (0.4, 0.75), (0.75, 0.95), (0.95, 1.0)):
    m = (r >= lo) & (r < hi) & (L < 0.8)
    out["rings"][f"{lo}-{hi}"] = {"mean": round(float(L[m].mean()), 4), "p50": round(float(np.median(L[m])), 4)}
for name, (lo, hi, a0, a1) in {"below_ball_1.02-1.10R": (1.02, 1.10, 240, 300),
                               "above_ball_1.02-1.10R": (1.02, 1.10, 60, 120),
                               "left_1.02-1.10R": (1.02, 1.10, 150, 210),
                               "right_1.02-1.10R": (1.02, 1.10, -30, 30)}.items():
    m = (r >= lo) & (r < hi) & (((ang - a0) % 360.0) < ((a1 - a0) % 360.0))
    out["backdrop"][name] = {"mean": round(float(L[m].mean()), 4), "min": round(float(L[m].min()), 4),
                             "p05": round(float(np.percentile(L[m], 5)), 4)}
# the whole frame's backdrop gradient (is it flat white?)
bgm = r > 1.15
out["backdrop"]["frame_outside_1.15R"] = {"mean": round(float(L[bgm].mean()), 4), "min": round(float(L[bgm].min()), 4),
                                         "p01": round(float(np.percentile(L[bgm], 1)), 4)}
json.dump(out, open(os.path.join(HERE, "sbstudy_light.json"), "w"), indent=1)
print("SBLIGHT", json.dumps(out))
