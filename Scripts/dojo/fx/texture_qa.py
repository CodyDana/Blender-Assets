"""QA of every shipped DojoFX texture and FBX (plain Python 3).

    py -3 -B Scripts/dojo/fx/texture_qa.py

Per texture: power-of-two size, channel count, the Unreal colour space / compression it must be imported with (by
suffix), alpha present and meaningful where it carries opacity, normal maps unit length with z > 0 (DirectX: the
check reports the mean green so a flipped map is visible), no NaN / empty maps. Per FBX: present, non-empty and the
Blender qa_check result from petals_qa.json. Writes WorkFiles/dojo/build/fx/json/texture_qa.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402

RULES = [  # suffix, colour space, UE compression, expects alpha
    ("_BC", "sRGB", "Default (BC7 with alpha: opacity mask)", True),
    ("_N", "Linear", "Normalmap (DirectX: Flip Green OFF)", False),
    ("_ORM", "Linear", "Masks (no sRGB)", False),
    ("_SSS", "Linear", "Grayscale (no sRGB)", False),
    ("_M", "Linear", "Masks (no sRGB)", False),
    ("_SixWayP", "Linear", "Default BC7, sRGB OFF", True),
    ("_SixWayN", "Linear", "Default BC7, sRGB OFF", True),
]


def rule_for(stem):
    for suf, cs, comp, alpha in RULES:
        if stem.endswith(suf):
            return suf, cs, comp, alpha
    return None


def main():
    res = {"textures": {}, "fbx": {}, "passed": True}
    for p in sorted(fx.TEX.glob("T_DKF_*.png")):
        im = Image.open(p)
        w, h = im.size
        arr = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
        r = rule_for(p.stem)
        checks = {"power_of_two": (w & (w - 1)) == 0 and (h & (h - 1)) == 0, "mode": im.mode,
                  "size": [w, h], "finite": bool(np.isfinite(arr).all()), "not_empty": float(arr[..., :3].std()) > 1e-3}
        if r is None:
            checks["rule"] = "NO RULE"
            ok = False
        else:
            suf, cs, comp, alpha = r
            checks.update({"colour_space": cs, "ue_compression": comp})
            ok = checks["power_of_two"] and checks["finite"] and checks["not_empty"]
            if alpha:
                a = arr[..., 3]
                checks["alpha_coverage"] = round(float((a > 0.5).mean()), 4)
                checks["alpha_has_range"] = bool(a.min() < 0.02 and a.max() > 0.9)
                ok = ok and im.mode == "RGBA" and checks["alpha_has_range"]
            if suf == "_N":
                n = arr[..., :3] * 2 - 1
                ln = np.linalg.norm(n, axis=-1)
                checks["normal_len_mean"] = round(float(ln.mean()), 4)
                checks["normal_z_min"] = round(float(n[..., 2].min()), 4)
                checks["mean_green"] = round(float(arr[..., 1].mean()), 4)
                ok = ok and abs(checks["normal_len_mean"] - 1) < 0.03 and checks["normal_z_min"] > 0
        checks["passed"] = bool(ok)
        res["textures"][p.name] = checks
        res["passed"] = res["passed"] and bool(ok)
    qa = fx.load_json(fx.WORK / "json/petals_qa.json") if (fx.WORK / "json/petals_qa.json").exists() else {}
    for p in sorted(fx.EXPORT.glob("SM_DKF_*.fbx")):
        name = p.stem
        entry = qa.get("petals", {}).get(name) or qa.get("drifts", {}).get(name) or {}
        ok = p.stat().st_size > 1000 and (entry.get("passed") or entry.get("passed_except_shared_uv0", False))
        res["fbx"][p.name] = {"bytes": p.stat().st_size, "triangles": entry.get("triangles"),
                              "qa_passed": entry.get("passed"),
                              "qa_passed_except_shared_uv0": entry.get("passed_except_shared_uv0"), "passed": bool(ok)}
        res["passed"] = res["passed"] and bool(ok)
    fx.write_json(fx.WORK / "json/texture_qa.json", res)
    for k, v in res["textures"].items():
        print(("PASS " if v["passed"] else "FAIL ") + k, v["size"], v.get("colour_space"))
    for k, v in res["fbx"].items():
        print(("PASS " if v["passed"] else "FAIL ") + k, v["triangles"])
    print("ALL PASSED" if res["passed"] else "SOME FAILED")


if __name__ == "__main__":
    main()
