"""VERIFY r8: pixel identity of the plaque textures as UE holds them (exported from the texture SOURCE by the verify
commandlet, emblem_export/) vs the user's armory emblem (Exports/ArmoryKit/Textures/T_AK_Emblem_*.png).
Out: verify_r9/emblem_pixels.json"""
import hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VD = B / "WorkFiles/dojo/build/verify_r9"
res = {}
for ue, ak in (("T_DKD_Emblem_BC", "T_AK_Emblem_BC"), ("T_DKD_Emblem_N", "T_AK_Emblem_N"), ("T_DKD_Emblem_ORM", "T_AK_Emblem_ORM")):
    a = Image.open(VD / "emblem_export" / f"{ue}.png"); b = Image.open(B / "Exports/ArmoryKit/Textures" / f"{ak}.png")
    A = np.asarray(a.convert("RGBA")).astype(np.int32); Bb = np.asarray(b.convert("RGBA")).astype(np.int32)
    same_shape = A.shape == Bb.shape
    d = np.abs(A - Bb) if same_shape else None
    res[ue] = {"ue_mode": a.mode, "armory_mode": b.mode, "size": [a.size, b.size],
               "sha256_rgba_ue": hashlib.sha256(A.astype(np.uint8).tobytes()).hexdigest(),
               "sha256_rgba_armory": hashlib.sha256(Bb.astype(np.uint8).tobytes()).hexdigest(),
               "max_abs_diff": int(d.max()) if same_shape else None,
               "rgb_max_abs_diff": int(d[..., :3].max()) if same_shape else None,
               "n_diff_px": int((d.max(axis=2) > 0).sum()) if same_shape else None}
    res[ue]["pixel_identical_rgb"] = same_shape and res[ue]["rgb_max_abs_diff"] == 0
# the BC's design mask vs the armory's own emblem mask (T_AK_Emblem.png): correlation of luminance
bc = np.asarray(Image.open(VD / "emblem_export/T_DKD_Emblem_BC.png").convert("L").resize((512, 512))).astype(float)
m = np.asarray(Image.open(B / "Exports/ArmoryKit/Textures/T_AK_Emblem.png").convert("L").resize((512, 512))).astype(float)
res["bc_vs_armory_mask_corr"] = round(float(np.corrcoef(bc.ravel(), m.ravel())[0, 1]), 4)
res["passed"] = all(v["pixel_identical_rgb"] for k, v in res.items() if isinstance(v, dict))
(VD / "emblem_pixels.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
