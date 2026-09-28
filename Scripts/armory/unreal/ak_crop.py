"""Capture post-step (system Python with Pillow: `py -3 ak_crop.py`), run by run_armory_unreal.sh after the capture.

A shift-lens camera (layout.json shift_y: f1's level C1) is captured level into a tall target that holds the shifted
window (ak_capture.target_size); this crops rows crop[0]..crop[1] of captures/raw/<name>.png into captures/<name>.png,
the same framing as the Blender render with that shift. Checks the result's size against capture.json "out_wh".
Prints AK_STEP_DONE crop passed=<bool>.
"""
import json
from pathlib import Path

from PIL import Image

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal")


def main():
    rep = json.loads((OUT / "capture.json").read_text(encoding="utf-8"))
    ok, done = True, {}
    for name, rec in rep.get("captures", {}).items():
        crop = rec.get("crop")
        if not crop:
            continue
        im = Image.open(rec["raw"])
        w, h = im.size
        top, bot = crop
        out = im.crop((0, top, w, bot))
        out.save(rec["final"])
        good = list(out.size) == list(rec["out_wh"]) and bot <= h
        ok &= good
        done[name] = {"raw_wh": [w, h], "rows": crop, "out_wh": list(out.size), "ok": good}
    rep["crop_step"] = done
    (OUT / "capture.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps(done))
    print(f"AK_STEP_DONE crop passed={ok}")


main()
