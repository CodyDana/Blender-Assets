"""Stone kit FIX ROUND 2 (f2): compose the kit sheets (both tracks) from render_f2.py --what sheet, cut the reference
crops and make the side-by-side sheets (reference crop left | ours right, the same height, a 24 px white gap: the layout
of Scripts/armory/side_by_side.py) with round 0's framings and names.

  py -3 Scripts/dojo/stonekit/compose_f2.py [sheets|pairs|all]
Out: WorkFiles/dojo/build/stonekit/renders/f2/KIT_SHEET_<family>.png, KIT_SHEET_overview.png, refcrops/ref_<pair>.png,
     sbs_<pair>.png, pairs.json. Text on the sheets is labelling only.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
F2 = SK / "renders" / "f2"
SHEET = F2 / "sheet"
REF = ROOT / "References" / "Dojo" / "dojo_landscape_ref.png"
FAMILIES = [   # (key, title, name prefixes, include Sweep?)
    ("wall_straight", "Terrace wall: straight modules 2 m / 4 m x H 2 / 3 / 4 / 6 (straight 1:10 batter, default)",
     ("Wall_2m_", "Wall_4m_"), False),
    ("wall_corners", "Terrace wall: outside corners (sangi-zumi) / inside corners", ("Wall_CornerOut", "Wall_CornerIn"),
     False),
    ("wall_ends", "Terrace wall: ends returning into the slope", ("Wall_EndL", "Wall_EndR"), False),
    ("wall_stairs", "Terrace wall: stair openings H 2 / 3 / 4", ("Wall_StairOpening",), False),
    ("wall_topfoot", "Coping alone (darker squared cap stones) / continuous level footing course",
     ("WallCoping_", "WallFoot_"), False),
    ("wall_sweep", "OPTIONAL variant set: concave castle sweep (H 3 / 4 / 6), *_Sweep", ("Wall", ), True),
    ("stair_flights", "Stair path: flights (3-5 squared blocks a tread, staggered joints, small worn nosing)",
     ("Stair_Flight",), False),
    ("stair_landings", "Stair path: flush landings (large near-rectangular flags)", ("Stair_Landing",), False),
    ("stair_kerbs", "Stair path: low kerbs of squared blocks", ("Stair_Kerb",), False),
    ("stair_cheeks", "Stair path: cheeks (stepped, rounded base) and the single-course low variant",
     ("Stair_Cheek",), False),
    ("stair_rails", "Stair path: rails (round posts, squared rails housed into them)", ("Stair_Rail",), False),
    ("stair_lanterns", "Stair path: lanterns (timber = the reference; stone = kit extra)", ("Stair_Lantern",), False),
]
PAIRS = {   # pair (round 0's names): (reference box in the 1024 x 1536 reference, our render)
    "asm_terrace_wall": ((380, 820, 700, 1000), "asm_terrace_wall"),
    "stairs_low": ((0, 1250, 340, 1536), "match_stairs_low"),
    "stairs_mid": ((100, 1000, 340, 1300), "match_stairs_mid"),
    "close_stone_faces": ((430, 960, 520, 1030), "close_stone_faces"),
    "close_step_nosing": ((140, 1150, 290, 1260), "close_step_nosing"),
    "lanterns": ((170, 990, 340, 1110), "match_lanterns"),
    "rail_joint": ((180, 1376, 340, 1536), "cu_rail_joint"),
    # extras (f1's pairs)
    "wall_lower": ((236, 950, 506, 1060), "match_wall_lower"),
    "lantern_close": ((178, 1000, 236, 1080), "match_lantern_close"),
    "landing_flags": ((0, 1400, 260, 1536), "cu_landing_flags"),
}


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def label(n, c):
    size = c.get("size_m") or [0, 0, 0]
    tris = c.get("tris_lod0") or c.get("tris") or 0
    lods = c.get("lod_tris") or c.get("lods")
    perf = "Nanite (LOD0 only)" if c.get("nanite") else (f"LOD0-2 {lods}" if lods else "LOD0-2")
    return f"{size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m   {tris:,} tris   {perf}   UCX {len(c.get('ucx', []))}"


def sheets():
    cat = json.loads((SK / "kit_catalog.json").read_text(encoding="utf-8"))["pieces"]
    views = ("front", "side", "top", "persp")
    cell, lab = 360, 64
    f1, f2 = font(26), font(19)
    out = []
    for key, title, pre, sweep in FAMILIES:
        names = sorted(n for n in cat if n.startswith("SM_DKT_") and n[7:].startswith(pre)
                       and (n.endswith("_Sweep") == sweep))
        names = [n for n in names if (SHEET / f"{n[7:]}_persp.png").exists()]
        if not names:
            continue
        W = cell * len(views) + 20
        H = len(names) * (cell + lab) + 76
        im = Image.new("RGB", (W, H), (236, 236, 232))
        d = ImageDraw.Draw(im)
        d.text((12, 12), f"Dojo stone kit (f2): {title}", fill=(20, 20, 20), font=f1)
        d.text((12, 44), "ortho front | side | top | 3/4; studio grey; the dark figure is 1.8 m", fill=(70, 70, 70), font=f2)
        y = 76
        for n in names:
            short = n[7:]
            d.text((12, y + 6), short, fill=(10, 10, 10), font=f1)
            d.text((12, y + 38), label(n, cat[n]), fill=(60, 60, 60), font=f2)
            for i, v in enumerate(views):
                fp = SHEET / f"{short}_{v}.png"
                if fp.exists():
                    t = Image.open(fp).convert("RGB").resize((cell - 6, cell - 6), Image.LANCZOS)
                    im.paste(t, (10 + i * cell, y + lab))
            y += cell + lab
        fp = F2 / f"KIT_SHEET_{key}.png"
        im.save(fp)
        out.append(fp)
        print("sheet", fp, im.size, len(names))
    names = sorted(n for n in cat if n.startswith("SM_DKT_") and (SHEET / f"{n[7:]}_persp.png").exists())
    cols, cw = 10, 260
    rows = (len(names) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw + 20, rows * (cw + 30) + 60), (236, 236, 232))
    d = ImageDraw.Draw(im)
    d.text((12, 14), f"Dojo stone kit (f2): all {len(names)} pieces, 3/4 view with a 1.8 m figure", fill=(20, 20, 20),
           font=f1)
    for k, n in enumerate(names):
        x, y = 10 + (k % cols) * cw, 60 + (k // cols) * (cw + 30)
        im.paste(Image.open(SHEET / f"{n[7:]}_persp.png").convert("RGB").resize((cw - 6, cw - 6), Image.LANCZOS),
                 (x, y + 26))
        d.text((x + 2, y + 2), n[7:], fill=(10, 10, 10), font=font(14))
    fp = F2 / "KIT_SHEET_overview.png"
    im.save(fp)
    print("sheet", fp, im.size)
    return out + [fp]


def sbs(a, b, out):
    h = min(a.height, b.height)
    a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
    im = Image.new("RGB", (a.width + 24 + b.width, h), (255, 255, 255))
    im.paste(a, (0, 0))
    im.paste(b, (a.width + 24, 0))
    im.save(out)
    return im.size


def pairs():
    ref = Image.open(REF).convert("RGB")
    od = F2 / "refcrops"
    od.mkdir(parents=True, exist_ok=True)
    pj = {}
    for name, (box, ours) in PAIRS.items():
        c = ref.crop(box)
        k = max(1, round(900 / c.height))
        c = c.resize((c.width * k, c.height * k), Image.LANCZOS)
        fp = od / f"ref_{name}.png"
        c.save(fp)
        op = F2 / f"{ours}.png"
        if not op.exists():
            print("missing", op)
            continue
        size = sbs(c, Image.open(op).convert("RGB"), F2 / f"sbs_{name}.png")
        pj[name] = [str(fp), str(op), str(F2 / f"sbs_{name}.png")]
        print("pair", name, size)
    (F2 / "pairs.json").write_text(json.dumps(pj, indent=1), encoding="utf-8")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("pairs", "all"):
        pairs()
    if what in ("sheets", "all"):
        sheets()
