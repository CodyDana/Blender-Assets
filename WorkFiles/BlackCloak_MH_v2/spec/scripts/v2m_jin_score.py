"""Jin_Cloak-intent measures on a Jin-framing render (v2m_render.py --view jin, beauty + json): the fold fan radiating
from the clasp, and the dark funnel interior. Also runs on the Jin illustration itself (--selftest) so the detector
is calibrated on the reference: there it counts the ink fold lines.

blender -b --factory-startup --python v2m_jin_score.py -- <render_dir> <tag> [<out_json>]
blender -b --factory-startup --python v2m_jin_score.py -- --selftest

Fan: luma sampled on arcs of radius 0.35 m and 0.55 m (at the clasp's depth) around the projected clasp centre;
angle 0 = image right (towards HIS LEFT), 90 = straight down, sampled -60..125 deg every 0.1 deg. The profile is
high-passed (minus a 6-deg moving mean); a fold crossing = a local minimum whose depth below the higher of its two
neighbouring maxima (within 4 deg) is >= max(0.8 x the robust local std, 1.5/255). Sectors: 'cross' -50..10 deg (the
swags from the clasp across the chest towards his left shoulder) and 'fan' 15..120 deg (the long folds down and across).
On the Jin illustration (ink lines) this detector gives the reference counts written to spec/out/spec_jin_measure.json."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import bpy
import v2m_lib as L

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPEC = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"


def load_rgba(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; x = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(x); bpy.data.images.remove(im)
    return x.reshape(h, w, 4)[::-1].astype(np.float64)


def arc_profile(lum, mask, cx, cy, r):
    angs = np.arange(-60.0, 125.0001, 0.1)
    t = np.radians(angs); xs = cx + r * np.cos(t); ys = cy + r * np.sin(t)
    v = L.bilinear(lum, xs, ys, np.nan)
    inside = L.bilinear(mask.astype(float), xs, ys, 0.0) > 0.5
    return angs, v, inside


def crossings(angs, v, inside, step=0.1):
    k = int(6 / step) | 1
    vv = np.where(inside, v, np.nan)
    ok = ~np.isnan(vv)
    if ok.sum() < 20: return []
    filled = np.interp(np.arange(len(vv)), np.nonzero(ok)[0], vv[ok])
    hp = filled - L.smooth1d(filled, k)
    sm = L.smooth1d(hp, 5)
    win = int(4 / step)
    loc_std = np.array([np.std(sm[max(0, i - 60):i + 60]) for i in range(len(sm))])
    out = []
    for i in range(win, len(sm) - win):
        if not inside[i]: continue
        if sm[i] == sm[i - 3:i + 4].min() and sm[i] < sm[i - 1] and sm[i] <= sm[i + 1]:
            left = sm[i - win:i].max(); right = sm[i + 1:i + 1 + win].max()
            depth = min(left, right) - sm[i]
            if depth >= max(1.2 * loc_std[i], 2.0):
                if out and angs[i] - out[-1] < 1.5: continue
                out.append(float(angs[i]))
    return out


def score(lum, mask, cx, cy, px_per_m):
    """fold crossings that persist over three arcs r-2cm, r, r+2cm (within 2.5 deg) on luma pre-blurred by ~1.2 cm
    (removes the fabric grain / weave so only fold shading and ink lines remain)."""
    k = max(3, int(round(0.012 * px_per_m)) | 1)
    lb = L.blur2d(lum, k)
    res = {}
    for rm in (0.35, 0.55):
        sets = []
        for dr in (-0.02, 0.0, 0.02):
            angs, v, ins = arc_profile(lb, mask, cx, cy, (rm + dr) * px_per_m)
            sets.append((crossings(angs, v, ins), ins))
        mid = sets[1][0]
        cr = [c for c in mid if sum(any(abs(c - o) <= 2.5 for o in sets[j][0]) for j in (0, 2)) >= 1]
        res["r%.2fm" % rm] = {"radius_px": rm * px_per_m, "blur_px": k, "crossings_deg": cr, "raw_crossings_mid": len(mid),
                              "cross_-50_10": sum(-50 <= c <= 10 for c in cr), "fan_15_120": sum(15 <= c <= 120 for c in cr),
                              "fan_spread_deg": (max([c for c in cr if 15 <= c <= 120], default=0) - min([c for c in cr if 15 <= c <= 120], default=0)),
                              "arc_inside_frac": float(sets[1][1].mean())}
    return res


if a and a[0] == "--selftest":
    im = load_rgba(os.path.join(SPEC, "spec_jin_full.png")); lum = L.lum(im[..., :3] * 255)
    J = json.load(open(os.path.join(SPEC, "spec_jin_measure.json")))
    mask = lum < 90   # the dark cloak + ink vs the grey backdrop / skin
    px_per_m = 207.0 / 0.072   # Jin IPD 207 px == the male's 7.2 cm eye-front IPD
    res = score(lum, mask, 563, 1320, px_per_m)
    J["fan_detector_selftest"] = {"px_per_m": px_per_m, "note": "v2m_jin_score detector on the illustration", **res}
    json.dump(J, open(os.path.join(SPEC, "spec_jin_measure.json"), "w"), indent=1)
    print("V2M JIN_SELFTEST", json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "crossings_deg"} for k, v in res.items()}))
    sys.exit(0)

RD, TAG = os.path.abspath(a[0]), a[1]
OUTJ = os.path.abspath(a[2]) if len(a) > 2 else os.path.join(RD, TAG + "_jin.json")
info = json.load(open(os.path.join(RD, TAG + ".json")))
im = load_rgba(os.path.join(RD, TAG + ".png"))
lum = L.lum(L.lin_to_srgb01(L.srgb_to_lin01(im[..., :3]) * im[..., 3:4] + (1 - im[..., 3:4])) * 255)
alpha = load_rgba(os.path.join(RD, TAG + "_alpha.png"))[..., 3] > 0.5
cam = info["camera"]; H = info["resolution"][1]
R = {"render": TAG, "camera": cam}
if "clasp_centre" not in info["landmarks_px"]:
    R["error"] = "no clasp slot found (material name must contain 'Clasp')"
else:
    cx, cy, _ = info["landmarks_px"]["clasp_centre"]
    c3 = np.array(info["landmarks_3d"]["clasp_centre"]); d = float(np.linalg.norm(c3 - np.array(cam["cam_loc"])))
    px_per_m = H * cam["focal"] / (24.0 * d)
    R["clasp_px"] = [cx, cy]; R["px_per_m_at_clasp"] = px_per_m
    R.update(score(lum, alpha, cx, cy, px_per_m))
    ref = json.load(open(os.path.join(SPEC, "spec_jin_measure.json"))).get("fan_detector_selftest", {})
    R["jin_reference"] = {k: {kk: vv for kk, vv in v.items() if kk != "crossings_deg"} for k, v in ref.items() if k.startswith("r")}
    r1, r2 = R["r0.35m"], R["r0.55m"]
    R["pass"] = {"fan_r0.35_ge7": r1["fan_15_120"] >= 7, "cross_r0.35_ge4": r1["cross_-50_10"] >= 4, "fan_r0.55_ge6": r2["fan_15_120"] >= 6,
                 "fan_spread_r0.35_ge70deg": r1["fan_spread_deg"] >= 70}
    R["all_pass"] = all(R["pass"].values())
R["face_landmark_visibility"] = info.get("face_landmark_visibility")
json.dump(R, open(OUTJ, "w"), indent=1, default=float)
print("V2M JIN", json.dumps({k: R.get(k) for k in ("pass", "face_landmark_visibility")}, default=float))
