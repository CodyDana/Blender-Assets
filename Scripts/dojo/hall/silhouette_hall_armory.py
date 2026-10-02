"""HALL + ARMORY round (2026-10-01), stage 2: the courtyard silhouette before / after, measured as masks (read-only).
The hall's pieces render as solid alpha (Cycles, 1 sample, transparent film), every other object of the level as a
holdout, from the front ortho elevation and the courtyard layout cameras; 'before' = the hall as built (the 27
removed / replaced instances back, the new pieces and the armory hidden). Reported per view: mask pixels before / after,
pixels that changed (XOR) and, separately, XOR pixels ABOVE the hall's door head band (the roofs and the clerestory).
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase_HallArmory.blend --python Scripts/dojo/hall/silhouette_hall_armory.py
Out: WorkFiles/dojo/build/hall_armory/blender/silhouette.json
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUTD = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "blender"
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "hall"))
import render_hall_armory as R  # noqa: E402  (states and cameras; its main() is not run)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 1
sc.cycles.use_denoising = False
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
try:
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
except Exception:  # noqa: BLE001
    pass


def mask(cam, name, w, h):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    fp = OUTD / "renders" / f"sil_{name}.png"
    sc.render.filepath = str(fp)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(fp))
    buf = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)[:, :, 3] > 0.5


def set_state(which):
    R.state(which, "all")
    for o in R.ASM.objects:
        p = R.piece_of(o)
        o.is_holdout = not (p.startswith("SM_DKH_") or p.startswith("SM_AK_"))
    for o in R.REM.objects:
        o.is_holdout = not R.piece_of(o).startswith("SM_DKH_")


out = {}
views = [("front", R.ortho("S_front", (22.0, 20.0, 5.2), (0, 1, 0), 26.0), 2600, 1300, 2.67)]
cams = {c["name"]: c for c in R.L["cameras"]}
for nm in ("CAM_Establishing", "CAM_EstablishingRef2", "CAM_Ref2Match", "CAM_PlayerEyeSand", "CAM_HallVeranda"):
    c = cams[nm]
    W, H = c.get("out_wh", [1920, 1080])
    views.append((nm, R.persp("S_" + nm, c["loc"], c["look_at"], hfov=c["hfov_deg"]), W, H, None))
for name, cam, w, h, zcut in views:
    m = {}
    for which in ("before", "after"):
        set_state(which)
        m[which] = mask(cam, f"{name}_{which}", w, h)
    x = m["before"] ^ m["after"]
    rec = {"mask_before_px": int(m["before"].sum()), "mask_after_px": int(m["after"].sum()), "xor_px": int(x.sum()),
           "xor_share_of_mask": round(float(x.sum()) / max(1, int(m["before"].sum())), 6)}
    if zcut is not None:          # ortho: rows above the door head band (+2.67 world)
        row = int((zcut - (5.2 - 6.5)) / 13.0 * h)
        rec["xor_px_above_door_head"] = int(x[row:, :].sum())
    else:                         # perspective: the rows above the hall's eave in the before mask's top half
        rows = np.where(m["before"].any(axis=1))[0]
        if len(rows):
            mid = int((rows.min() + rows.max()) / 2)
            rec["xor_px_upper_half_of_hall"] = int(x[mid:, :].sum())
    ys, xs = np.where(x)
    rec["xor_bbox_px_from_bottom_left"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
    out[name] = rec
    print("SIL", name, rec, flush=True)
(OUTD / "silhouette.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
