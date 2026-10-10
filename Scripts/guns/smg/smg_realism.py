"""SMG01 early realism set in the ROUGH LOOK, adapted to black polymer + phosphated steel (plain Python; renders via
headless Blender, gunlib/realism_job.py, Cycles). SMG_BUILD_PLAN 14.1 L8 (early, per part group) + the L7 views:

  per part group at 35 cm (eye 0.35 m from the group's centre, 40 deg FOV):
    g1_receiver_rails       receiver + rails (left 3/4 from above)
    g2_grip_trigger_sel     grip + trigger group + selector (left, low)
    g3_magazine_well        magazine + well (front left, low)
    g4_stock_extended       stock + hinge, extended (right rear 3/4)
    g5_stock_folded         stock folded (right side)
    g6_front_end            muzzle + front sight (front left)
    g7_rear_sight           rear sight (left rear, high)
  fp_35cm (first person, 70 deg), ads (55 deg FOV, eye 0.25 m behind the aperture on the sight line), hero_34 (front
  left 1.5 m, 38 deg), tp_3m (3 m, 60 deg)

    py -3 -B Scripts/guns/smg/smg_realism.py [--out WorkFiles/guns/smg/review/early_realism] [--samples 96]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import GRIP, REVIEW, SCRATCH, ROOT, BLEND, socket, dims  # noqa: E402

import gunlib  # noqa: E402


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def at35(target, direction, fov=40.0, d=350.0):
    t = np.asarray(target, float)
    return t + d * _unit(direction), t, fov


STOCK = ["stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad"]


def fold_pose():
    SH = dims("stock_hinge")
    p = (np.array([SH["axis_X"], SH["axis_Y"], 0.0]) - GRIP) / 1000.0     # frame B, metres
    R = np.diag([-1.0, -1.0, 1.0])                                         # 180 deg about +Z
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - R @ p
    return M.tolist()


def shots(out: Path):
    sight = np.array(socket("Sight")["M_mm"], float)
    post = np.array(socket("SightFront")["M_mm"], float)
    ads_eye = sight - 250.0 * _unit(post - sight)
    S = []
    groups = [("g1_receiver_rails", (430.0, 0.0, 20.0), (-0.25, 0.75, 0.62), {}),
              ("g2_grip_trigger_sel", (330.0, 0.0, -60.0), (0.1, 1.0, -0.05), {}),
              ("g3_magazine_well", (440.0, 0.0, -75.0), (0.65, 0.7, 0.0), {}),
              ("g4_stock_extended", (190.0, 0.0, 0.0), (-0.45, -0.8, 0.4), {}),
              ("g5_stock_folded", (380.0, -60.0, 0.0), (0.0, -1.0, 0.35), {"poses": True}),
              ("g6_front_end", (575.0, 0.0, 25.0), (0.75, 0.6, 0.25), {}),
              ("g7_rear_sight", (300.0, 0.0, 55.0), (-0.5, 0.6, 0.62), {})]
    for name, tgt, d, extra in groups:
        e, t, f = at35(tgt, d)
        S.append((name, e, t, f, 0.6, "%s at 35 cm, 40 deg FOV" % name, extra))
    fp_r = np.array([360.0, 0.0, 10.0])
    S.append(("fp_35cm", fp_r + 350.0 * _unit([-0.93, 0.22, 0.30]), np.array([620.0, 0.0, 10.0]), 70.0, 1.1,
              "first person: eye 35 cm from the receiver, behind / left / above (right-handed hold), 70 deg FOV", {}))
    S.append(("ads", ads_eye, post, 55.0, 1.1, "ADS: eye 0.25 m behind the aperture on the sight line, 55 deg FOV", {}))
    hero_t = np.array([380.0, 0.0, -30.0])
    S.append(("hero_34", hero_t + 1500.0 * _unit([0.55, 0.78, 0.30]), hero_t, 38.0, 1.6,
              "hero 3/4 front left (the sheet's 3/4 side), 1.5 m, 38 deg FOV", {}))
    S.append(("tp_3m", hero_t + 3000.0 * _unit([-0.45, -0.85, 0.28]), hero_t, 60.0, 3.2,
              "third person: camera 3 m from the gun, right side, 60 deg FOV", {}))
    return [{"name": n, "eye_M": [float(v) for v in e], "target_M": [float(v) for v in t], "fov_deg": f,
             "res": [1600, 900], "light_dist_m": ld, "out": str(out / f"{n}.png"), "note": note, **x}
            for n, e, t, f, ld, note, x in S]


def contact(out: Path, sh, name="contact.png"):
    tiles = []
    for s in sh:
        im = Image.open(s["out"]).convert("RGB").resize((640, 360), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), s["name"], fill=(255, 255, 255))
        tiles.append(im)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    W = Image.new("RGB", (640 * cols, 360 * rows), (40, 40, 40))
    for k, im in enumerate(tiles):
        W.paste(im, ((k % cols) * 640, (k // cols) * 360))
    W.save(out / name)


def run(job, tag):
    jp = SCRATCH / f"realism_job_{tag}.json"
    jp.write_text(json.dumps(job, indent=1))
    log = SCRATCH / "logs" / f"realism_{tag}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(BLEND), "--factory-startup", "--python",
                        str(ROOT / "Scripts" / "guns" / "gunlib" / "realism_job.py"), "--", "--job", str(jp)],
                       stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "REALISM_JOB_DONE" not in txt:
        raise SystemExit(f"realism render failed, see {log}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REVIEW / "early_realism"))
    ap.add_argument("--samples", type=int, default=96)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sh = shots(out)
    base = {"offset_M": [float(v) for v in GRIP], "samples": a.samples, "wood_slots": [],
            "polymer_slots": ["M_SMG01_Furniture", "M_SMG01_Mag"], "steel_style": "phosphate",
            "env": 0.3, "light": 0.85, "bg_rgb": [126, 126, 126]}
    plain = [s for s in sh if not s.get("poses")]
    folded = [s for s in sh if s.get("poses")]
    run(dict(base, shots=plain), "plain")
    if folded:
        run(dict(base, shots=folded, poses={n: fold_pose() for n in STOCK}), "folded")
    contact(out, sh)
    rel = [dict(s, out=str(Path(s["out"]).resolve().relative_to(ROOT.resolve())).replace("\\", "/")) for s in sh]
    (out / "shots.json").write_text(json.dumps({"look": "ROUGH LOOK (gunlib.look 0.2.1): black polymer (furniture, "
                                                        "magazine) + phosphated steel; not the final textures",
                                                "blend": "Assets/Guns/SMG01.blend", "shots": rel}, indent=1))
    print("[realism] wrote", out)


if __name__ == "__main__":
    main()
