"""fp_mips - the recolour and specular contracts on the SHIPPED PNG bytes, at every mip (final pass).

Unreal (TMGS_FROM_TEXTURE_GROUP, World group = SimpleAverage) builds each mip as a 2x2 box of the
level above; an sRGB texture is decoded to linear first (BC, and now Detail), a linear one (ORM)
averaged as stored.  Each mip is re-quantised to 8 bits in its own encoding, as Unreal does.
    1. BaseColor = Detail.R x Tint (Detail sRGB ON) against BC, luminance mean / median / p10 per mip
    2. Specular = 0.5 x ORM.A: its mean at each ORM mip against the correctly filtered mean of the
       full-resolution float mask reconstructed from the Detail (0.5 x d^2)
usage: python fp_mips.py TEXDIR SIDECAR OUT.json
"""
import sys, json, hashlib
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import read_png

tex, side, out = sys.argv[1:4]
sc = json.load(open(side, encoding="utf8"))
tint = np.array(sc["material"]["tint_default_linear"], float)
LUMA = np.array([0.2126, 0.7152, 0.0722])


def dec(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def enc(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def box(a):
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def q8(a):
    return np.rint(np.clip(a, 0, 1) * 255.0) / 255.0


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


P = {k: f"{tex}/T_SmokeBomb_{k}.png" for k in ("BC", "Detail", "ORM")}
bc = read_png(P["BC"])[..., :3].astype(np.float64) / 255.0
dt = read_png(P["Detail"]).astype(np.float64)[..., 0] / 255.0
orm = read_png(P["ORM"]).astype(np.float64) / 255.0
res = {"sha256": {k: sha(v) for k, v in P.items()}, "tint_linear": tint.tolist(), "mips": [], "spec_mips": []}
bl = dec(bc)            # linear
dl = dec(dt)            # linear detail d
lvl = 0
while bl.shape[0] >= 16:
    Lb = bl @ LUMA
    Ld = dl * float(tint @ LUMA)
    r = {"mip": lvl, "size": bl.shape[0],
         "mean_pct": round(float((Ld.mean() / Lb.mean() - 1) * 100), 3),
         "median_pct": round(float((np.median(Ld) / np.median(Lb) - 1) * 100), 3),
         "p10_pct": round(float((np.percentile(Ld, 10) / np.percentile(Lb, 10) - 1) * 100), 3),
         "max_abs_lin": round(float(np.abs(dl[..., None] * tint - bl).max()), 5),
         "max_srgb8_levels": int(np.abs(np.rint(enc(dl[..., None] * tint) * 255) - np.rint(enc(bl) * 255)).max())}
    res["mips"].append(r)
    # next level: linear box, re-quantised in the stored (sRGB) encoding
    bl = dec(q8(enc(box(bl))))
    dl = dec(q8(enc(box(dl))))
    lvl += 1
# specular: the truth is the full-res float mask 0.5 x d^2 (from the quantised Detail), box-filtered
d0 = dec(dt)
truth = 0.5 * np.clip(d0, 0, 1) ** 2
a = orm[..., 3] if orm.shape[-1] == 4 else None
f = d0.shape[0] // orm.shape[0]
t = truth.copy()
for _ in range(int(np.log2(f))):
    t = box(t)
lvl = 0
if a is not None:
    while a.shape[0] >= 16:
        res["spec_mips"].append({"orm_mip": lvl, "size": a.shape[0], "mean_orm_spec": round(float(0.5 * a.mean()), 6),
                                 "mean_truth": round(float(t.mean()), 6),
                                 "pct": round(float((0.5 * a.mean() / t.mean() - 1) * 100), 3)})
        a = q8(box(a)); t = box(t); lvl += 1
res["orm_has_alpha"] = a is not None
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({"mips": [(m["mip"], m["mean_pct"], m["median_pct"], m["p10_pct"]) for m in res["mips"]],
                  "spec": [(m["orm_mip"], m["pct"]) for m in res["spec_mips"]]}))
