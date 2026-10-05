"""AR-01 realism set in the ROUGH LOOK (plain Python; renders via headless Blender, gunlib/realism_job.py):

    py -3 -B Scripts/guns/rifle/rifle_realism.py [--out WorkFiles/guns/rifle/review/realism_form3] [--samples 128]

Four views a realism judge looks at (RIFLE_BUILD_PLAN 9, L7 realism): the first-person crop (eye 35 cm from the
receiver, behind / left / above the gun as a right-handed player holds it, 70 deg FOV), the ADS sight picture (eye on
the sight line 0.25 m behind the rear notch, 55 deg FOV), the third-person view (camera 3 m away, 60 deg FOV) and a
hero 3/4 from the front right. Renders the review blend (the build + the grip's checker bake source, as the textured
asset will show it) and writes <out>/<shot>.png, contact.png and shots.json (the cameras).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SPEC, GRIP, REVIEW, SCRATCH, ROOT  # noqa: E402

import gunlib  # noqa: E402
import rifle_detail as RDT  # noqa: E402


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def ads_eye():
    """The ADS eye of gate B4 (rifle_b4.py): 0.25 m behind the Sight socket ON its line (R48: the socket sits at the
    notch top centre and points at the post tip, the real-pattern sight picture: tip level with the notch top)."""
    import math
    soc = {s["socket"]: s for s in SPEC.sockets["rifle"]}["Sight"]
    p = math.radians(soc["unreal_rotation_deg"]["pitch"])
    d = np.array([math.cos(p), 0.0, math.sin(p)])
    sight = np.array(soc["M_mm"], float)
    post = np.array(SPEC.key["sight_line"]["post_tip_M"], float)
    return sight - 250.0 * d, post


def shots(out: Path):
    ads_e, ads_t = ads_eye()
    fp_r = np.array([350.0, 0.0, 0.0])                          # receiver centre: the eye is 35 cm from it
    fp_eye = fp_r + 350.0 * _unit([-0.93, 0.22, 0.30])            # behind, left, above (right-handed hold)
    fp_t = np.array([620.0, 0.0, 10.0])                         # looking forward along the gun
    hero_t = np.array([450.0, 0.0, -20.0])
    S = [("fp_35cm", fp_eye, fp_t, 70.0, 1.1,
          "first person: eye 35 cm from the receiver, behind / left / above (right-handed hold), 70 deg FOV"),
         ("ads_55deg", ads_e, ads_t, 55.0, 1.1,
          "ADS: eye 0.25 m behind the Sight socket on its line (notch top -> post tip), 55 deg FOV"),
         ("tp_3m", hero_t + 3000.0 * _unit([-0.45, -0.85, 0.28]), hero_t, 60.0, 3.2,
          "third person: camera 3 m from the gun, right side, 60 deg FOV"),
         ("hero_34", hero_t + 1500.0 * _unit([0.55, -0.78, 0.30]), hero_t, 38.0, 1.6,
          "hero 3/4 front right, 1.5 m, 38 deg FOV")]
    return [{"name": n, "eye_M": [float(v) for v in e], "target_M": [float(v) for v in t], "fov_deg": f,
             "res": [1600, 900], "light_dist_m": ld, "out": str(out / f"{n}.png"), "note": note}
            for n, e, t, f, ld, note in S]


def contact(out: Path, sh):
    tiles = []
    for s in sh:
        im = Image.open(s["out"]).convert("RGB").resize((800, 450), Image.LANCZOS)
        ImageDraw.Draw(im).text((10, 8), s["name"] + ": " + s["note"], fill=(255, 255, 255))
        tiles.append(im)
    W = Image.new("RGB", (1600, 900), (40, 40, 40))
    for k, im in enumerate(tiles):
        W.paste(im, ((k % 2) * 800, (k // 2) * 450))
    W.save(out / "contact.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REVIEW / "realism_form3"))
    ap.add_argument("--samples", type=int, default=128)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    blend = RDT.make_review_blend()
    sh = shots(out)
    job = {"offset_M": [float(v) for v in GRIP], "samples": a.samples, "wood_slots": ["M_AR01_Furniture"],
           "worn_steel_objects": ["butt_plate"], "env": 0.55, "light": 1.35, "bg_rgb": [126, 126, 126], "shots": sh}
    jp = SCRATCH / "realism_job.json"
    jp.write_text(json.dumps(job, indent=1))
    log = SCRATCH / "logs" / "realism.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(blend), "--factory-startup", "--python",
                        str(ROOT / "Scripts" / "guns" / "gunlib" / "realism_job.py"), "--", "--job", str(jp)],
                       stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "REALISM_JOB_DONE" not in txt:
        raise SystemExit(f"realism render failed, see {log}")
    contact(out, sh)
    rel = [dict(s, out=str(Path(s["out"]).resolve().relative_to(ROOT.resolve())).replace("\\", "/")) for s in sh]
    (out / "shots.json").write_text(json.dumps({"look": "ROUGH LOOK (gunlib.look); not the final textures",
                                                "blend": "scratch/AR01_review.blend (build + checker bake source)",
                                                "shots": rel}, indent=1))
    print("[realism] wrote", out)


if __name__ == "__main__":
    main()
