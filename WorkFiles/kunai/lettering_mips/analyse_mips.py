"""Mip vs no-mip lettering: error against an 8x supersampled reference and shimmer across 4 sub-pixel shifts."""
import json
import numpy as np
from PIL import Image

F = "frames2"
def lum(path):
    a = np.asarray(Image.open(f"{F}/{path}").convert("RGB")).astype(np.float64) / 255.0
    return a @ [0.2126, 0.7152, 0.0722]

out = {}
for v in ("d100", "d250", "d500"):
    H, W = lum(f"{v}_blank_0.png").shape
    cy, cx = H // 2, W // 2
    hh, hw = H // 16, W // 16                       # the 8x reference covers W/8 x H/8 of the main frame
    crop = lambda a: a[cy - hh:cy + hh, cx - hw:cx + hw]
    down = lambda a: a.reshape(2 * hh, 8, 2 * hw, 8).mean(axis=(1, 3))
    ref = down(lum(f"{v}_mip_ref.png"))
    ref_blank = down(lum(f"{v}_blank_ref.png"))
    # register: the narrow-FOV reference and the main frame's centre crop can sit a few px apart
    tgt = crop(lum(f"{v}_blank_0.png"))
    best = None
    for dy in range(-12, 13):
        for dx in range(-40, 41):
            sh = np.roll(np.roll(ref_blank, dy, 0), dx, 1)
            e = ((sh - tgt)[15:-15, 45:-45] ** 2).mean()
            if best is None or e < best[0]:
                best = (e, dy, dx)
    _, sdy, sdx = best
    ref = np.roll(np.roll(ref, sdy, 0), sdx, 1)
    ref_blank = np.roll(np.roll(ref_blank, sdy, 0), sdx, 1)
    band = np.abs(ref - ref_blank) > 0.01            # where the lettering shows in the ground truth
    grow = band.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            grow |= np.roll(np.roll(band, dy, 0), dx, 1)
    rec = {"band_px": int(grow.sum()), "ref_shift_px": [sdy, sdx], "blank_rms_after_shift": float(np.sqrt(best[0]))}
    for k in ("mip", "nomip"):
        fr = [crop(lum(f"{v}_{k}_{i}.png")) for i in range(4)]
        e = fr[0] - ref
        ink = fr[0] - crop(lum(f"{v}_blank_0.png"))          # the lettering's own contribution
        ink_ref = ref - ref_blank
        ie = ink - ink_ref
        rec[k] = {"ink_rms_err_vs_ref": float(np.sqrt((ie[grow] ** 2).mean())),
                  "ink_energy_ratio": float((ink[grow] ** 2).sum() / max((ink_ref[grow] ** 2).sum(), 1e-12)),
                  "rms_err_vs_ref": float(np.sqrt((e[grow] ** 2).mean())),
                  "mean_err_vs_ref": float(e[grow].mean()),
                  "shimmer_px_std": float(np.std(np.stack(fr), axis=0)[grow].mean()),
                  "shimmer_band_mean_std": float(np.std([f[grow].mean() for f in fr]))}
        Image.fromarray((np.clip(fr[0], 0, 1) * 255).astype("uint8")).resize((4 * 2 * hw, 4 * 2 * hh), Image.NEAREST).save(f"{F}/{v}_{k}_crop4x.png")
    Image.fromarray((np.clip(ref, 0, 1) * 255).astype("uint8")).resize((4 * 2 * hw, 4 * 2 * hh), Image.NEAREST).save(f"{F}/{v}_ref_crop4x.png")
    out[v] = rec
json.dump(out, open("mip_analysis.json", "w"), indent=1)
for v, r in out.items():
    print(v, "ink rms err mip %.4f nomip %.4f | ink energy/ref mip %.2f nomip %.2f" % (r["mip"]["ink_rms_err_vs_ref"], r["nomip"]["ink_rms_err_vs_ref"], r["mip"]["ink_energy_ratio"], r["nomip"]["ink_energy_ratio"]))
    print(v, "band px", r["band_px"], "| rms err mip %.4f nomip %.4f | shimmer px-std mip %.4f nomip %.4f | band-mean std mip %.5f nomip %.5f" % (
        r["mip"]["rms_err_vs_ref"], r["nomip"]["rms_err_vs_ref"], r["mip"]["shimmer_px_std"], r["nomip"]["shimmer_px_std"],
        r["mip"]["shimmer_band_mean_std"], r["nomip"]["shimmer_band_mean_std"]))
