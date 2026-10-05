"""AR-01 L5 light match (plain Python; drives headless Blender renders of the side view from the baked maps):

    py -3 -B Scripts/guns/rifle/rifle_l5_fit.py

The sheet is a lit image with unknown lights. Two light parameters are fitted, each on ONE region, and every other
region is then the test (rifle_l5.py): the light scale k on the receiver's luminance (the largest steel region) and the
lights' specular factor s on the stock's R/B (how much white light the varnished wood reflects in the sheet's light).
Alternates k and s (secant on s) for a few renders at 48 spp, then renders the final side view at 128 spp and writes
the L5 record (scratch/game/l5.json, with the fitted k and s).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
B = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W = ROOT / "WorkFiles" / "guns" / "rifle"
OUT = W / "review" / "tex"
TMP = W / "scratch" / "l5fit"
TMP.mkdir(parents=True, exist_ok=True)


def render(k, s, samples, out):
    log = TMP / "render.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([B, "-b", str(ROOT / "Assets" / "Guns" / "AR01.blend"), "--factory-startup", "--python",
                        str(HERE / "rifle_texrender.py"), "--", "--set", "side", "--samples", str(samples), "--out",
                        str(out), "--light", str(k), "--spec", str(s)], stdout=f, stderr=subprocess.STDOUT, check=False)
    if "TEXRENDER_DONE" not in log.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("render failed: " + str(log))


def evaluate(png, k, s, js):
    subprocess.run([sys.executable, "-B", str(HERE / "rifle_l5.py"), "--render", str(png), "--light", str(k),
                    "--json", str(js)], stdout=subprocess.DEVNULL, check=True)
    d = json.loads(Path(js).read_text())
    return d


def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def main():
    k, s = 0.75, 1.0
    hist = []
    prev = None
    for it in range(6):
        render(k, s, 48, TMP)
        d = evaluate(TMP / "tex_side.png", k, s, TMP / "l5_try.json")
        rec, st = d["regions"]["receiver"], d["regions"]["stock"]
        ratio = lum(rec["sheet"]["median_srgb"]) / lum(rec["ours"]["median_srgb"])
        rb_err = st["ours"]["rb"] - st["sheet"]["rb"]
        hist.append({"k": round(k, 4), "s": round(s, 4), "receiver_lum_ratio": round(ratio, 4), "stock_rb_err":
                     round(rb_err, 4), "failed": d["failed"]})
        print("[l5fit]", hist[-1], flush=True)
        if abs(ratio - 1) < 0.02 and abs(rb_err) < 0.05:
            break
        k_new = k * ratio
        # R/B falls as s rises: secant on (s, rb_err), first step a fixed slope guess
        # R/B falls as s rises (measured: about -1.0 per unit of s on the walnut): s_new = s - err / slope
        if prev is None or abs(s - prev[0]) < 1e-6:
            s_new = s + rb_err / 1.0
        else:
            slope = (rb_err - prev[1]) / (s - prev[0])
            s_new = s - rb_err / slope if slope < -1e-3 else s + rb_err / 1.0
        prev = (s, rb_err)
        k, s = k_new, min(max(s_new, 0.0), 1.0)
    render(k, s, 128, OUT)
    d = evaluate(OUT / "tex_side.png", k, s, W / "scratch" / "game" / "l5.json")
    d["fit"] = {"light_scale": k, "specular_factor": s, "history": hist,
                "method": "k on the receiver luminance, s on the stock R/B; every other region is the test"}
    (W / "scratch" / "game" / "l5.json").write_text(json.dumps(d, indent=1))
    print("[l5fit] DONE k %.4f s %.4f failed %s" % (k, s, d["failed"]))


if __name__ == "__main__":
    main()
