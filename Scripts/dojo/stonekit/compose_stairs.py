"""Stone kit track (9) STAIR PATH: compose the kit sheets and cut the reference crops for the side-by-sides.

  py -3 Scripts/dojo/stonekit/compose_stairs.py            (after render_stairs.py --sheet)
Writes WorkFiles/dojo/build/stonekit/renders/stairs/:
  KIT_SHEET_<group>.png   one row per piece: ortho front | side | top | 3/4 (studio grey, 1.8 m silhouette), labelled
                          with the measured size, triangles, Nanite / LODs (from stairs/measure.json + kit_catalog.json)
  refcrops/ref_*.png      reference crops (References/Dojo/dojo_landscape_ref.png) for Scripts/armory/side_by_side.py
Text on the sheets is labelling only (nothing here goes into a texture).
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
RD = WORK / "renders" / "stairs"
SHEET = RD / "sheet"
P = "SM_DKT_Stair_"
REF = ROOT / "References" / "Dojo" / "dojo_landscape_ref.png"
GROUPS = [("flights", "Flight_"), ("landings", "Landing"), ("cheeks", "Cheek"), ("rails", "Rail_"),
          ("lanterns", "Lantern_")]
CROPS = {   # name: (box in the 1024 x 1536 reference, upscale)
    "stairs_low": ((0, 1250, 340, 1536), 3),
    "stairs_mid": ((100, 1000, 340, 1300), 3),
    "lanterns": ((170, 990, 340, 1110), 5),
    "lantern_close": ((178, 1000, 236, 1080), 8),
    "gate_steps": ((250, 880, 440, 990), 4),
}


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def sheets():
    meas = json.loads((WORK / "stairs" / "measure.json").read_text(encoding="utf-8"))
    cat = json.loads((WORK / "kit_catalog.json").read_text(encoding="utf-8"))["pieces"]
    views = ("front", "side", "top", "persp")
    cell, lab = 330, 64
    f1, f2 = font(24), font(18)
    out = []
    for gname, key in GROUPS:
        names = sorted(n for n in cat if n.startswith(P) and n[len(P):].startswith(key))
        if not names:
            continue
        W = cell * len(views) + 20
        H = len(names) * (cell + lab) + 70
        im = Image.new("RGB", (W, H), (236, 236, 232))
        d = ImageDraw.Draw(im)
        d.text((12, 14), f"Dojo stone kit - stair path: {gname}   (ortho front | side | top | 3/4; grey studio; the dark "
                         f"figure is 1.8 m)", fill=(20, 20, 20), font=f1)
        y = 70
        for n in names:
            short = n[len(P):]
            m, c = meas.get(n, {}), cat[n]
            size = m.get("size_m", c.get("size_m"))
            lods = c.get("lod_tris")
            perf = "Nanite (LOD0 only)" if c.get("nanite") else (f"LOD0-2 {lods}" if lods else "LOD0-2")
            extra = ""
            if "risers_measured_m" in m:
                extra = (f"  risers {m['risers_measured_m']['min']:.3f}-{m['risers_measured_m']['max']:.3f} m, "
                         f"ramp {m['ucx_ramp_deg']} deg")
            d.text((12, y + 6), f"{short}", fill=(10, 10, 10), font=f1)
            d.text((12, y + 36), f"{size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m   {c['tris_lod0']:,} tris   {perf}"
                                 f"   UCX {len(c['ucx'])} ({c['class']}){extra}", fill=(60, 60, 60), font=f2)
            for i, v in enumerate(views):
                fp = SHEET / f"{short}_{v}.png"
                if fp.exists():
                    t = Image.open(fp).convert("RGB").resize((cell - 6, cell - 6), Image.LANCZOS)
                    im.paste(t, (10 + i * cell, y + lab))
            y += cell + lab
        fp = RD / f"KIT_SHEET_{gname}.png"
        im.save(fp)
        out.append(fp)
        print("sheet", fp)
    # the overview: every piece's 3/4 view in one grid
    names = sorted(n for n in cat if n.startswith(P))
    cols, cw = 6, 300
    rows = (len(names) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw + 20, rows * (cw + 34) + 60), (236, 236, 232))
    d = ImageDraw.Draw(im)
    d.text((12, 14), f"Dojo stone kit - stair path: all {len(names)} pieces (3/4 view, 1.8 m figure)", fill=(20, 20, 20),
           font=f1)
    for k, n in enumerate(names):
        short = n[len(P):]
        x, y = 10 + (k % cols) * cw, 60 + (k // cols) * (cw + 34)
        fp = SHEET / f"{short}_persp.png"
        if fp.exists():
            im.paste(Image.open(fp).convert("RGB").resize((cw - 6, cw - 6), Image.LANCZOS), (x, y + 30))
        d.text((x + 2, y + 4), short, fill=(10, 10, 10), font=f2)
    fp = RD / "KIT_SHEET_overview.png"
    im.save(fp)
    print("sheet", fp)
    return out + [fp]


def crops():
    ref = Image.open(REF).convert("RGB")
    od = RD / "refcrops"
    od.mkdir(parents=True, exist_ok=True)
    for n, (box, k) in CROPS.items():
        c = ref.crop(box)
        c = c.resize((c.width * k, c.height * k), Image.LANCZOS)
        c.save(od / f"ref_{n}.png")
        print("crop", od / f"ref_{n}.png", c.size)


if __name__ == "__main__":
    crops()
    sheets()
