"""AR-01 L5 light match (plain Python; drives headless Blender renders of the side view from the baked maps):

    py -3 -B Scripts/guns/rifle/rifle_l5_fit.py [--samples 128] [--out DIR] [--json PATH]

The sheet is a lit image with unknown lights. The L5 rig is PHYSICAL (look-polish round, 2026-10-05): every light at
specular factor 1, so blued and bare steel show their real specular response (rifle_texrender.sheet_lights_physical:
one large overhead key tipped toward the camera at KEY_ELEV, a rim behind, the grey world at ENV as fill and as the
environment the metal reflects; no light behind the camera, so the side flats show their own colour). The r4 rig fitted
a specular factor on the stock's R/B and drove it to 0 (blued parts rendered black): retired.

ONE parameter is fitted, on ONE region: the light scale k on the receiver's linear luminance (the largest steel region;
the render is linear in k: lights and world env both scale with it, the backdrop seen by the camera stays 126). Every
other region is the test (rifle_l5.py --calib receiver). The wood regions' per-part tone ratios (rifle_wood_tone.py,
WorkFiles/guns/rifle/wood_tone.json) are calibrated on the same rig, which the gate record states.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
B = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W = ROOT / "WorkFiles" / "guns" / "rifle"
TMP = W / "scratch" / "l5fit"
KEY_ELEV, ENV = 70.0, 0.20          # the physical rig (fixed by design, not fitted): see the module docstring


def render(k, samples, out):
    out.mkdir(parents=True, exist_ok=True)
    log = TMP / "render.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([B, "-b", str(ROOT / "Assets" / "Guns" / "AR01.blend"), "--factory-startup", "--python",
                        str(HERE / "rifle_texrender.py"), "--", "--set", "side", "--samples", str(samples), "--out",
                        str(out), "--light", str(k), "--rig", "physical", "--key-elev", str(KEY_ELEV), "--env",
                        str(ENV)], stdout=f, stderr=subprocess.STDOUT, check=False)
    if "TEXRENDER_DONE" not in log.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("render failed: " + str(log))


def evaluate(png, k, js):
    subprocess.run([sys.executable, "-B", str(HERE / "rifle_l5.py"), "--render", str(png), "--light", str(k),
                    "--json", str(js), "--calib", "receiver"], stdout=subprocess.DEVNULL, check=True)
    return json.loads(Path(js).read_text())


def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--out", default=str(W / "review" / "tex"))
    ap.add_argument("--json", default=str(W / "scratch" / "game" / "l5.json"))
    ap.add_argument("--k0", type=float, default=1.3)
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    k, hist = a.k0, []
    for _ in range(4):
        render(k, 48, TMP)
        d = evaluate(TMP / "tex_side.png", k, TMP / "l5_try.json")
        rec = d["regions"]["receiver"]
        ratio = lum(rec["sheet"]["median_srgb"]) / lum(rec["ours"]["median_srgb"])
        hist.append({"k": round(k, 4), "receiver_lum_ratio": round(ratio, 4), "failed": d["failed"]})
        print("[l5fit]", hist[-1], flush=True)
        if abs(ratio - 1) < 0.01:
            break
        k *= ratio
    render(k, a.samples, Path(a.out))
    d = evaluate(Path(a.out) / "tex_side.png", k, a.json)
    d["fit"] = {"light_scale": k, "specular_factor": 1.0, "rig": {"name": "physical", "key_elev_deg": KEY_ELEV,
                                                                  "world_env": ENV}, "history": hist,
                "method": "physical lights (specular factor 1); k on the receiver luminance; every other region is "
                          "the test (the wood tones are calibrated on this rig: wood_tone.json)"}
    Path(a.json).write_text(json.dumps(d, indent=1))
    print("[l5fit] DONE k %.4f failed %s" % (k, d["failed"]))


if __name__ == "__main__":
    main()
