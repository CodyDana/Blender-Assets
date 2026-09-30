"""Stone kit track 8: lay the sheet renders (render_wall.py --what sheet) out as kit sheets on the reference sheets'
light grey (#A0A0A0) with plain 1.8 m silhouettes standing on the ground line of the front and side ortho views
(scale from views.json, so the figure is exactly 1.8 m), piece names under the front view; and the reference-crop |
render pairs for the assembly views.

Run (system Python with Pillow): py -3 Scripts/dojo/stonekit/compose_wall.py [sheets|pairs|all]
Out: WorkFiles/dojo/build/stonekit/renders/wall/KIT_SHEET_<family>.png, KIT_SHEET_all.png (a contact page), and
     sbs_*.png via Scripts/armory/side_by_side.py's layout (reference left, ours right, same height)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit" / "renders" / "wall"
REF = ROOT / "References" / "Dojo" / "dojo_landscape_ref.png"
BG = (160, 160, 160, 255)
SIL = (108, 108, 108, 255)
_R = [(0.0, 1.80), (0.045, 1.795), (0.080, 1.77), (0.100, 1.72), (0.104, 1.67), (0.095, 1.62), (0.070, 1.585),
      (0.058, 1.555), (0.130, 1.525), (0.200, 1.49), (0.232, 1.44), (0.245, 1.30), (0.255, 1.12), (0.258, 0.95),
      (0.250, 0.84), (0.225, 0.80), (0.205, 0.83), (0.200, 0.96), (0.185, 1.20), (0.180, 1.02), (0.170, 0.90),
      (0.165, 0.60), (0.150, 0.30), (0.145, 0.08), (0.165, 0.02), (0.160, 0.0), (0.035, 0.0), (0.040, 0.08),
      (0.050, 0.45), (0.030, 0.82), (0.0, 0.86)]
FRONT = _R + [(-x, z) for (x, z) in reversed(_R[:-1])]
FAMS = ["straight", "corners", "ends", "stairs", "topfoot"]
TITLES = {"straight": "Terrace wall: straight modules 2 m / 4 m x H 2 / 3 / 4 / 6 m",
          "corners": "Terrace wall: outside corners (sangi-zumi, upswept) / inside corners",
          "ends": "Terrace wall: ends returning into the slope (L / R)",
          "stairs": "Terrace wall: stair openings H 2 / 3 / 4 m (track 9 grid: riser 1/6, tread 1/3, 1.8 m clear)",
          "topfoot": "Top course alone / base course + buried skirt"}


def font(sz):
    for f in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_figure(canvas, x_px, ground_y, ppm):
    ImageDraw.Draw(canvas).polygon([(x_px + x * ppm, ground_y - z * ppm) for (x, z) in FRONT], fill=SIL)


def sheet(fam, V):
    names = [f"sheet_{fam}_{v}" for v in ("front", "side", "top", "34")]
    if not all((D / f"{n}.png").exists() for n in names):
        print("missing views for", fam)
        return None
    W = 2600
    ims = {n: Image.open(D / f"{n}.png").convert("RGBA") for n in names}
    # scale ortho views to one common px/m so the figure is the same size in front and side
    target_w = W - 360
    vf = V[names[0]]
    ppm = min(target_w / (ims[names[0]].width / vf["ppm"]), 150.0)
    rows = []
    for n in names[:3]:
        v = V[n]
        pr = min(ppm, target_w / (ims[n].width / v["ppm"]))       # a row wider than the canvas gets its own scale
        f = pr / v["ppm"]
        im = ims[n].resize((max(1, round(ims[n].width * f)), max(1, round(ims[n].height * f))), Image.LANCZOS)
        rows.append((n, im, dict(v, _ppm=pr)))
    im34 = ims[names[3]]
    k = min(target_w / im34.width, 1.0)
    im34 = im34.resize((round(im34.width * k), round(im34.height * k)), Image.LANCZOS)
    def head(im, v, n):
        """Extra space above a row so the 1.8 m figure standing on its ground line stays clear of the row above."""
        if n.endswith("_top"):
            return 0
        g = im.height / 2 + v["centre"][2] * v["_ppm"]
        return max(0, int(1.85 * v["_ppm"] - g) + 10)
    H = 110 + sum(r[1].height + 60 + head(r[1], r[2], r[0]) for r in rows) + im34.height + 60
    cv = Image.new("RGBA", (W, H), BG)
    dr = ImageDraw.Draw(cv)
    dr.text((40, 30), TITLES.get(fam, fam), fill=(30, 30, 30, 255), font=font(40))
    y = 110
    for (n, im, v) in rows:
        x0 = 300
        y += head(im, v, n)
        cv.alpha_composite(im, (x0, y))
        if not n.endswith("_top"):
            # ground line: world z = 0 sits at row (h/2 + zc * ppm) of the scaled render
            g_row = y + im.height / 2 + v["centre"][2] * v["_ppm"]
            draw_figure(cv, 150, g_row, v["_ppm"])
            dr.text((80, g_row + 8), "1.8 m", fill=(40, 40, 40, 255), font=font(24))
        if n.endswith("_front"):
            for pl in v.get("placed", []):
                # world x of the piece's bbox centre -> px
                xc = (pl["x0"] + pl["x1"]) / 2
                px = x0 + im.width / 2 + (xc - v["centre"][0]) * v["_ppm"]
                lab = pl["piece"].replace("SM_DKT_", "")
                tw = dr.textlength(lab, font=font(20))
                dr.text((px - tw / 2, y + im.height + 6), lab, fill=(25, 25, 25, 255), font=font(20))
        dr.text((40, y + 10), {"front": "FRONT", "side": "SIDE", "top": "TOP"}[n.split("_")[-1]], fill=(40, 40, 40, 255),
                font=font(28))
        y += im.height + 60
    cv.alpha_composite(im34, ((W - im34.width) // 2, y))
    dr.text((40, y + 10), "3/4", fill=(40, 40, 40, 255), font=font(28))
    out = D / f"KIT_SHEET_{fam}.png"
    cv.convert("RGB").save(out)
    print("saved", out, cv.size)
    return out


def contact(paths):
    ims = [Image.open(p).convert("RGB") for p in paths if p]
    if not ims:
        return
    w = 1300
    sc = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in ims]
    cols = 2
    rows_h = []
    for i in range(0, len(sc), cols):
        rows_h.append(max(im.height for im in sc[i:i + cols]))
    cv = Image.new("RGB", (w * cols + 20 * (cols + 1), sum(rows_h) + 20 * (len(rows_h) + 1)), BG[:3])
    y = 20
    for r, i in enumerate(range(0, len(sc), cols)):
        x = 20
        for im in sc[i:i + cols]:
            cv.paste(im, (x, y))
            x += w + 20
        y += rows_h[r] + 20
    cv.save(D / "KIT_SHEET_all.png")
    print("saved", D / "KIT_SHEET_all.png", cv.size)


# reference crop (x0, y0, x1, y1) in dojo_landscape_ref.png for each matching view
PAIRS = {
    "asm_terrace_wall": (380, 820, 700, 1000),     # the terrace wall under the compound, the plaster wall on it
    "asm_stair_head": (180, 880, 540, 1100),       # the lower wall, the gate steps and rails above it
    "asm_stair_path": (0, 940, 420, 1536),         # the stair path with rails and lanterns climbing the cliff
    "asm_overview": (0, 780, 1024, 1536),          # the whole lower half: wall, river side, path
    "close_stone_faces": (430, 960, 520, 1030),    # the lower wall's stones, close
    "close_step_nosing": (140, 1150, 290, 1260),   # the path's steps and nosings
}


def pairs():
    ref = Image.open(REF).convert("RGB")
    for name, box in PAIRS.items():
        p = D / f"{name}.png"
        if not p.exists():
            continue
        a = ref.crop(box)
        b = Image.open(p).convert("RGB")
        h = max(a.height, b.height, 900)
        a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
        b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
        cv = Image.new("RGB", (a.width + 24 + b.width, h), (255, 255, 255))
        cv.paste(a, (0, 0))
        cv.paste(b, (a.width + 24, 0))
        out = D / f"sbs_{name}.png"
        cv.save(out)
        print("saved", out, cv.size)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    V = json.loads((D / "views.json").read_text(encoding="utf-8")) if (D / "views.json").exists() else {}
    if what in ("sheets", "all"):
        contact([sheet(f, V) for f in FAMS])
    if what in ("pairs", "all"):
        pairs()
