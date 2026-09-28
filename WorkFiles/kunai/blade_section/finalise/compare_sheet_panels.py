"""Compare the six frozen forms' panels of the regenerated gallery sheets with the pre_blade_section (PREP) snapshot.
modern_line_sheet: 7 columns x 800 px (hero row + top row); columns 0-5 are the six frozen forms.
style_comparison: 8 columns (reference + 7 forms) of PANEL_W 1.6 at 600 px/unit with 0.1 gaps; the full-width banner
(top 0.26 units) is excluded; each column is compared over its slot (panel + half the gaps either side).
    py -3 compare_sheet_panels.py <new_line_sheet> <new_style_sheet> <out.json>
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
PRE = P / "WorkFiles/shuriken/regression/pre_blade_section/extras/renders"
FORMS = ["four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross", "kunai_plain"]
def load(p): return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
new_line, new_style, out = sys.argv[1:4]
res = {"prep_snapshot": str(PRE), "line_sheet": {}, "style_comparison": {}}
a, b = load(new_line), load(PRE / "modern_line_sheet.png")
res["line_sheet"].update(new=str(new_line), new_sha256=sha(new_line), prep_sha256=sha(PRE / "modern_line_sheet.png"),
                         size_new=list(a.shape[:2][::-1]), size_prep=list(b.shape[:2][::-1]))
tw = a.shape[1] // 7
for i, f in enumerate(FORMS):
    d = np.abs(a[:, i*tw:(i+1)*tw] - b[:, i*tw:(i+1)*tw])
    res["line_sheet"][f] = {"cols_px": [i*tw, (i+1)*tw], "max_abs": int(d.max()), "px_differing": int((d.max(2) > 0).sum()),
                            "pixel_identical": bool(d.max() == 0)}
a, b = load(new_style), load(PRE / "style_comparison.png")
res["style_comparison"].update(new=str(new_style), new_sha256=sha(new_style), prep_sha256=sha(PRE / "style_comparison.png"),
                               size_new=list(a.shape[:2][::-1]), size_prep=list(b.shape[:2][::-1]))
U, GAP, PW = 600, 0.10, 1.6
y0 = int(round((GAP + 0.16) * U))    # below the banner
for col, f in enumerate(["reference"] + FORMS):
    x0 = int(round((GAP + col * (PW + GAP) - GAP / 2) * U)); x1 = int(round((GAP + col * (PW + GAP) + PW + GAP / 2) * U))
    x0, x1 = max(0, x0), min(a.shape[1], x1)
    d = np.abs(a[y0:, x0:x1] - b[y0:, x0:x1])
    res["style_comparison"][f] = {"cols_px": [x0, x1], "rows_px": [y0, a.shape[0]], "max_abs": int(d.max()),
                                  "px_differing": int((d.max(2) > 0).sum()), "pixel_identical": bool(d.max() == 0)}
d = np.abs(a[:y0] - b[:y0]); res["style_comparison"]["banner_rows"] = {"rows_px": [0, y0], "px_differing": int((d.max(2) > 0).sum())}
six = ["four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross"]
res["six_panels_pixel_identical"] = {"line_sheet": all(res["line_sheet"][f]["pixel_identical"] for f in six),
                                     "style_comparison": all(res["style_comparison"][f]["pixel_identical"] for f in six),
                                     "style_reference_column": res["style_comparison"]["reference"]["pixel_identical"]}
Path(out).write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps(res["six_panels_pixel_identical"]), json.dumps({f: (res["line_sheet"][f]["px_differing"], res["style_comparison"][f]["px_differing"]) for f in FORMS}), res["style_comparison"]["banner_rows"])
