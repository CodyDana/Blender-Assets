"""Lay the per-view panels out as a model sheet like the reference (front + figure | side + figure | top | 3/4), on the
reference's own plain light grey (sRGB 171, 170, 171, measured from the sheet's corner). Front, side and top share one
pixel scale (px per metre in <key>_info.json) and one ground line; the 3/4 view is scaled to the same height.
Also cuts the matching reference crops and writes the reference | ours comparison sheets through
Scripts/armory/side_by_side.py (Blender) when --sbs is given.

Run: py -3 Scripts/dojo/props/stone/compose_stone.py [--dir WorkFiles/dojo/build/props/stone/renders/r0] [--sbs]
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "stone"
REF = ROOT / "References" / "Dojo" / "dojo_courtyard_stone_ref.png"
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
ARGS = sys.argv[1:]
DIR = (Path(ARGS[ARGS.index("--dir") + 1]) if "--dir" in ARGS else WORK / "renders" / "r0").resolve()
BG = (171, 170, 171)
GAP = 40

# reference crops (x0, y0, x1, y1) on the 1448 x 1086 sheet, per our sheet key
REF_CROPS = {
    "lantern_tall": (20, 0, 760, 365),
    "lantern_short": (815, 110, 1400, 365),
    "well": (60, 370, 560, 720),
    "well_gable": (560, 370, 1290, 720),
    "well_ring": (180, 540, 520, 720),
    "well_cover": (940, 405, 1275, 705),
    "well_bucket": (290, 500, 420, 590),
    "well_pulley": (300, 420, 400, 520),
    "well_rope": (270, 420, 440, 600),
    "cistern": (40, 735, 1300, 1086),
    "crate": (40, 735, 1300, 1086),       # not on the sheet: compared against the cistern whose language it follows
    "crate_half": (40, 735, 1300, 1086),
}


def on_bg(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    return Image.alpha_composite(bg, im).convert("RGB")


def compose(key):
    info = json.loads((DIR / "parts" / f"{key}_info.json").read_text(encoding="utf-8"))
    front, side, top, persp = (on_bg(DIR / "parts" / f"{key}_{v}.png") for v in ("front", "side", "top", "persp"))
    H = front.size[1]
    ps = persp.resize((int(persp.size[0] * H / persp.size[1]), H), Image.LANCZOS)
    W = front.size[0] + side.size[0] + top.size[0] + ps.size[0] + GAP * 5
    Hs = max(H, top.size[1]) + GAP * 2
    sheet = Image.new("RGB", (W, Hs), BG)
    x = GAP
    for im, valign in ((front, "bottom"), (side, "bottom"), (top, "middle"), (ps, "bottom")):
        y = GAP + (max(H, top.size[1]) - im.size[1]) if valign == "bottom" else GAP + (max(H, top.size[1]) - im.size[1]) // 2
        sheet.paste(im, (x, y))
        x += im.size[0] + GAP
    out = DIR / f"sheet_{key}.png"
    sheet.save(out)
    print("sheet", out, sheet.size, "ppm", round(info["ppm"], 1))
    return out


def main():
    keys = sorted(p.name[:-10] for p in (DIR / "parts").glob("*_info.json"))
    ref = Image.open(REF).convert("RGB")
    (DIR / "refcrops").mkdir(exist_ok=True)
    for k in keys:
        out = compose(k)
        if "--sbs" in ARGS:
            crop = DIR / "refcrops" / f"ref_{k}.png"
            rc = ref.crop(REF_CROPS[k])
            # f1: upscale the (often tiny) reference crop to our sheet's height first, so side_by_side keeps our sheet
            # at full resolution instead of shrinking it to the crop (the bucket crop is 90 px tall)
            sh = Image.open(out).size[1]
            rc.resize((int(rc.size[0] * sh / rc.size[1]), sh), Image.LANCZOS).save(crop)
            sbs = DIR / f"sbs_{k}.png"
            subprocess.run([BLENDER, "-b", "--factory-startup", "--python",
                            str(ROOT / "Scripts" / "armory" / "side_by_side.py"), "--", str(crop), str(out), str(sbs)],
                           check=True, capture_output=True)
            print("sbs", sbs)


main()
