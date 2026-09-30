"""v2f finishing: sbs_rock_closeup.png and gates_v2f.json (v2 -> v2f per-view numbers) in renders/v2f."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
B = ROOT / "WorkFiles/dojo/build/pines"
R, R2 = B / "renders/v2f", B / "renders/v2"
ref = Image.open(ROOT / "References/Dojo/dojo_japanese_pine_ref.png").convert("RGB")
def g(p):
    im = Image.open(p).convert("RGBA"); bg = Image.new("RGBA", im.size, (182, 182, 182, 255)); bg.alpha_composite(im); return bg.convert("RGB")
tiles = [ref.crop((880, 560, 1091, 745)), g(R / "PineD1_rock_front.png"), ref.crop((1230, 560, 1448, 745)), g(R / "PineD2_rock_front.png")]
H = 700
tiles = [t.resize((int(t.size[0] * H / t.size[1]), H), Image.LANCZOS) for t in tiles]
o = Image.new("RGB", (sum(t.size[0] for t in tiles) + 30, H), "white"); x = 0
for t in tiles:
    o.paste(t, (x, 0)); x += t.size[0] + 10
o.save(R / "sbs_rock_closeup.png")
m2, m = json.loads((R2 / "measure.json").read_text()), json.loads((R / "measure.json").read_text())
look = json.loads((R / "look_numbers.json").read_text())
rep = json.loads((B / "build_report.json").read_text())
out = {"round": "v2f", "note": "per view: sheet silhouette IoU / width error / row fill, v2 -> v2f; tris; colour", "views": {}}
for k, v in m.items():
    a = m2.get(k, {})
    out["views"][k] = {"ref": v.get("ref_panel"), "iou": [a.get("iou"), v.get("iou")], "width_err": [a.get("width_err"), v.get("width_err")],
                       "row_fill_ref_v2_v2f": [v["row_fill"][0], a.get("row_fill", [None, None])[1], v["row_fill"][1]],
                       "crown_w_m_ref_ours": v.get("crown_w_m"), "height_m_ref_ours": v.get("height_m")}
ious = [v["iou"][1] for v in out["views"].values()]; ious2 = [v["iou"][0] for v in out["views"].values() if v["iou"][0] is not None]
out["iou_mean"] = {"v2": round(float(np.mean(ious2)), 3), "v2f": round(float(np.mean(ious)), 3)}
out["tris"] = {k: v["tris"] for k, v in rep["variants"].items()}
out["over_budget_foliage_150k"] = {k: v["tris"]["foliage"] for k, v in rep["variants"].items() if v["tris"]["foliage"] > 150000}
out["over_budget_trunk_80k"] = {k: v["tris"]["trunk"] for k, v in rep["variants"].items() if v["tris"]["trunk"] > 80000}
out["needle_len_cm"] = {k: v.get("needle_len_cm") for k, v in rep["variants"].items()}
out["colour"] = look
out["qa_all_passed"] = rep.get("qa_all_passed")
(R / "gates_v2f.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out["views"].items():
    print(k, v["ref"], "IoU v2->v2f", v["iou"], "row_fill", v["row_fill_ref_v2_v2f"])
print("mean", out["iou_mean"], "over", out["over_budget_foliage_150k"], out["over_budget_trunk_80k"], "qa", out["qa_all_passed"])
