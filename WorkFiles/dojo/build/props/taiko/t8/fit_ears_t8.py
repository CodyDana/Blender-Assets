"""t8 (judge r7 item 3, the solid rolled bead: the ears refitted, the roll no longer a parameter; adapted from t7/fit_ears_t7.py). t7: fit each skirt ear (taiko_skirt.EARS: angle, width, lift H, hem depth, flare exponent, roll) to the photo's
outline rows in its fitted camera (judge r6 item 1: top-left ear lower and round, bottom-right curled up, skirt rows
within +-8 px). The drum's outline per row = the lathe (body, collar, tack envelope, lip) + both skirts, rasterised
(check_skirt_t7.py); cost = mean |ours - photo| + 0.3 max over the ear's rows. A seeded random search, then a
coordinate refinement. Writes t7/fit_ears.json (paste the result into taiko_skirt.EARS)."""
import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

T7 = Path(__file__).resolve().parent.parent / "t7"
T8 = Path(__file__).resolve().parent
sys.path.insert(0, str(T7))
SCR = Path(sys.argv[sys.argv.index("--scripts") + 1]) if "--scripts" in sys.argv else Path(
    "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/props/taiko")
sys.path.insert(0, str(SCR))
import photo_cam as PC  # noqa: E402
import taiko_skirt as SK  # noqa: E402
import check_skirt_t7 as CK  # noqa: E402

tr = json.loads((SCR / "skirt_trace_t7.json").read_text(encoding="utf-8"))
ROWS = {(1, -1): ("upper_left", range(185, 315)), (1, 1): ("upper_right", range(180, 315)),
        (-1, -1): ("lower_left", range(690, 830)), (-1, 1): ("lower_right", range(690, 830))}
BOUNDS = {"th": (-14.0, 14.0), "w": (0.07, 0.24), "H": (0.010, 0.060), "a_low": (0.030, 0.112), "p": (0.35, 2.0),
          "sh_H": (0.0008, 0.030), "sh_alow": (0.030, 0.112), "sh_p": (0.4, 2.0),
          "bk_H": (0.0008, 0.030), "bk_alow": (0.030, 0.112), "bk_p": (0.4, 2.0)}
LATHE = {}


def lathe_px(side):
    if side not in LATHE:
        q = PC.project_design(CK.lathe_outline_pts(84 * side))
        LATHE[side] = q
    return LATHE[side]


def outline_rows(ears, s, side, rows):
    v, f, _uv, _info = SK.mesh(s, ears=ears)
    V = np.array(v)
    th = np.degrees(np.arctan2(V[:, 2], V[:, 1]))
    keep_v = np.abs(((th - 90 * side) + 180) % 360 - 180) < 45
    P = PC.project_design(V)
    im = Image.new("L", (1024, 1024), 0)
    d = ImageDraw.Draw(im)
    for q in f:
        if keep_v[list(q)].any():
            d.polygon([tuple(P[i]) for i in q], fill=255)
    for u, vv in lathe_px(side):
        d.rectangle((u - 0.7, vv - 0.7, u + 0.7, vv + 0.7), fill=255)
    m = np.asarray(im) > 0
    out = {}
    for r in rows:
        xs = np.where(m[r])[0]
        if len(xs):
            out[r] = (xs.min() - 0.5) if side < 0 else (xs.max() + 0.5)
    return out


def cost(ears, key):
    s, side = key
    name, rows = ROWS[key]
    ph = dict((int(a), b) for a, b in tr["silhouette_rows_v_u"][name])
    o = outline_rows(ears, s, side, rows)
    d = [((ph[r] - o[r]) if side < 0 else (o[r] - ph[r])) for r in rows if r in o and r in ph]
    if not d:
        return 1e9, []
    d = np.array(d)
    return float(np.mean(np.abs(d)) + 0.3 * np.max(np.abs(d))), d


def main():
    ears = copy.deepcopy(SK.EARS)
    base = {k: dict(v) for k, v in ears.items()}
    rng = random.Random(77)
    res = {}
    keys = [tuple(json.loads(a)) for a in sys.argv[sys.argv.index("--keys") + 1].split(";")] if "--keys" in sys.argv \
        else list(ROWS)
    n_rand = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 60
    for key in keys:
        best = (cost(ears, key)[0], dict(ears[key]))
        print(key, "start", round(best[0], 2), best[1])
        th0 = 88.0 * key[1] + math.degrees(PC.VIEW_TH)
        for it in range(n_rand):
            cand = dict(best[1])
            for p_, (lo, hi) in BOUNDS.items():
                if rng.random() < 0.5:
                    if p_ == "th":
                        cand["th"] = th0 + rng.uniform(lo, hi)
                    else:
                        span = hi - lo
                        cand[p_] = min(hi, max(lo, cand[p_] + rng.gauss(0, 0.25 * span)))
            ears[key] = cand
            c = cost(ears, key)[0]
            if c < best[0]:
                best = (c, dict(cand))
                print("  ", it, round(c, 2), {k: round(v, 4) for k, v in cand.items()})
        ears[key] = best[1]
        c, d = cost(ears, key)
        res[str(key)] = {"cost": round(c, 2), "params": {k: round(v, 4) for k, v in best[1].items()},
                         "diff_px_min_max": [float(d.min()), float(d.max())], "mean_abs_px": round(float(np.mean(np.abs(d))), 2)}
        print(key, "best", res[str(key)])
    (T8 / "fit_ears.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if "--write" in sys.argv:
        old = json.loads((SCR / "skirt_ears_t8.json").read_text(encoding="utf-8")) if (SCR / "skirt_ears_t8.json").exists() else {}
        old.update(res)
        (SCR / "skirt_ears_t8.json").write_text(json.dumps(old, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
