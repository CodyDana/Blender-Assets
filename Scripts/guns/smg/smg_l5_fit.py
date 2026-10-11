"""SMG01 L5 light match (plain Python; drives headless Blender renders of the side view from the baked maps; the
AR-01's rifle_l5_fit.py):

    py -3 -B Scripts/guns/smg/smg_l5_fit.py [--blend PATH] [--tex DIR] [--samples 128] [--out DIR] [--json PATH]

The physical rig (smg_texrender.physical_rig: one large overhead key tipped toward the camera at KEY_ELEV, a rim
behind, the grey world at ENV as fill and environment; specular factor 1, no light behind the camera, so the side
flats show their own colour). ONE parameter is fitted on ONE region: the light scale k on the upper receiver's linear
luminance (the largest polymer region; the render is linear in k). Every other region is the test.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
B = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
W = ROOT / "WorkFiles" / "guns" / "smg"
KEY_ELEV, ENV = 70.0, 0.20


def render(blend, tex, k, samples, out, tmp):
    out.mkdir(parents=True, exist_ok=True)
    log = tmp / "render.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([B, "-b", str(blend), "--factory-startup", "--python", str(HERE / "smg_texrender.py"), "--",
                        "--set", "side", "--samples", str(samples), "--out", str(out), "--tex", str(tex), "--light",
                        str(k), "--key-elev", str(KEY_ELEV), "--env", str(ENV), "--right"],
                       stdout=f, stderr=subprocess.STDOUT, check=False)
    if "TEXRENDER_DONE" not in log.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("render failed: " + str(log))


def evaluate(png, k, js):
    subprocess.run([sys.executable, "-B", str(HERE / "smg_l5.py"), "--render", str(png), "--light", str(k), "--json",
                    str(js)], stdout=subprocess.DEVNULL, check=True)
    return json.loads(Path(js).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", default=str(ROOT / "Assets" / "Guns" / "SMG01.blend"))
    ap.add_argument("--tex", default=str(ROOT / "Exports" / "Guns" / "SMG01" / "Textures"))
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--out", default=str(W / "review" / "realism_tex"))
    ap.add_argument("--json", default=str(W / "scratch" / "l5" / "l5.json"))
    ap.add_argument("--k0", type=float, default=1.0)
    a = ap.parse_args()
    tmp = W / "scratch" / "l5"
    tmp.mkdir(parents=True, exist_ok=True)
    k, hist = a.k0, []
    for _ in range(4):
        render(a.blend, a.tex, k, 32, tmp, tmp)
        d = evaluate(tmp / "tex_side.png", k, tmp / "l5_try.json")
        ratio = d["calibration"]["linear_luminance_ratio_sheet_over_ours"]
        hist.append({"k": round(k, 4), "receiver_lum_ratio": ratio, "failed": d["failed"]})
        print("[l5fit]", hist[-1], flush=True)
        if abs(ratio - 1) < 0.01:
            break
        k *= ratio
    render(a.blend, a.tex, k, a.samples, Path(a.out), tmp)
    d = evaluate(Path(a.out) / "tex_side.png", k, a.json)
    d["fit"] = {"light_scale": k, "specular_factor": 1.0, "rig": {"name": "physical", "key_elev_deg": KEY_ELEV,
                                                                  "world_env": ENV}, "history": hist,
                "method": "physical lights (specular factor 1); k on the upper receiver's luminance; every other "
                          "region is the test"}
    Path(a.json).write_text(json.dumps(d, indent=1))
    print("[l5fit] DONE k %.4f failed %s" % (k, d["failed"]))


if __name__ == "__main__":
    main()
