"""r16 entry side-by-sides (PIL) and numbers: reference 2 / the user's entry crop against the r20 state (before) and this
round (after), golden and night. Usage: py -3 compare.py [outdir=final]"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RUN = HERE / (sys.argv[1] if len(sys.argv) > 1 else "final")
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference")
BEFORE = {"golden": HERE.parents[1] / "r20" / "final" / "golden" / "ref_aspect" / "C1_EntryReveal_golden.png",
          "night": HERE.parents[3] / "build" / "renders" / "night_20m" / "ref_aspect" / "C1_EntryReveal_night.png"}
out = RUN / "compare"
out.mkdir(parents=True, exist_ok=True)
ref = Image.open(REF / "armory3_reference2.png").convert("RGB")
crop = Image.open(REF / "entry_foreground_crop.png").convert("RGB")


def stack(ims, labels, path, w=None):
    w = w or max(i.width for i in ims)
    ims = [i.resize((w, round(i.height * w / i.width)), Image.LANCZOS) for i in ims]
    im = Image.new("RGB", (w, sum(i.height + 26 for i in ims)), (20, 20, 20))
    d = ImageDraw.Draw(im)
    y = 0
    for i, lab in zip(ims, labels):
        d.text((6, y + 6), lab, fill=(230, 230, 230))
        im.paste(i, (0, y + 26))
        y += i.height + 26
    im.save(path)
    print("wrote", path.name, im.size)


def side(ims, labels, path):
    h = min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h)) for i in ims]
    im = Image.new("RGB", (sum(i.width for i in ims) + 16 * (len(ims) - 1), h + 26), (20, 20, 20))
    d = ImageDraw.Draw(im)
    x = 0
    for i, lab in zip(ims, labels):
        im.paste(i, (x, 26))
        d.text((x + 6, 6), lab, fill=(230, 230, 230))
        x += i.width + 16
    im.save(path)
    print("wrote", path.name, im.size)


def lum(a):
    return np.asarray(a.convert("L")).astype(float)


for P in ("golden", "night"):
    after = Image.open(RUN / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    before = Image.open(BEFORE[P]).convert("RGB")
    side([ref, after], ["reference 2", f"r16 entry {P} C1 1448x1086"], out / f"C1_ref_vs_r16entry_{P}.png")
    strip = (0, 830, 1448, 1086)            # the crop is reference 2's bottom strip
    stack([crop, before.crop(strip), after.crop(strip)],
          ["user crop (entry_foreground_crop.png)", f"before (r20 / night_20m) {P} C1 y 830-1086",
           f"after (r16 entry) {P} C1 y 830-1086"], out / f"entry_crop_before_after_{P}.png")
    zb = (300, 880, 800, 1086)
    stack([ref.crop(zb), before.crop(zb), after.crop(zb)],
          ["reference 2 (x 300-800, y 880-1086)", f"before {P}", f"after {P}"], out / f"beam_mat_zoom_{P}.png", w=1000)
    zr = (960, 880, 1460 - 12, 1086)
    stack([ref.crop(zr), before.crop(zr), after.crop(zr)],
          ["reference 2 (x 960-1448, y 880-1086)", f"before {P}", f"after {P}"], out / f"beam_mat_zoomR_{P}.png", w=1000)
    # numbers: mean RGB of the hall above the beam, the beam top, its face and the mat field (C1, x 440-1030)
    A = np.asarray(after).astype(float)
    Bf = np.asarray(before).astype(float)
    R = np.asarray(ref).astype(float)
    def m(X, y0, y1, x0=560, x1=900):
        return X[y0:y1, x0:x1].reshape(-1, 3).mean(0).round(0).tolist()
    print(P, "field ref", m(R, 960, 1040), "before", m(Bf, 960, 1040), "after", m(A, 960, 1040))
    # beam rows (column x 520-900 mean luminance per row)
    for nm, X in (("ref", R), ("before", Bf), ("after", A)):
        L = X[880:960, 520:900].mean(axis=(1, 2))
        print(P, nm, "rows 880-958:", " ".join(str(int(v)) for v in L[::2]))
    for cam in ("CE_EntryDown", "CE_EntryFront"):
        p = RUN / P / f"{cam}_{P}.png"
        q = HERE.parents[1] / "r20" / "final" / P / f"{cam}_{P}.png"
        if p.exists() and q.exists():
            side([Image.open(q).convert("RGB"), Image.open(p).convert("RGB")], [f"before (r20) {cam} {P}",
                 f"after (r16 entry) {cam} {P}"], out / f"{cam}_before_after_{P}.png")
        elif p.exists():
            stack([crop, Image.open(p).convert("RGB")], ["user crop (entry_foreground_crop.png)",
                  f"r16 entry {cam} {P} (new view: from the doorway down at the mat and the beam's face)"],
                  out / f"{cam}_vs_crop_{P}.png", w=1600)
