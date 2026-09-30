"""Stone kit FIX ROUND 1: compose the kit sheets (both tracks) from render_f1.py --what sheet, and cut the reference
crops for the side-by-side pairs (Scripts/armory/side_by_side.py makes the pairs: reference left, ours right).

  py -3 Scripts/dojo/stonekit/compose_f1.py [sheets|crops|all]
Out: WorkFiles/dojo/build/stonekit/renders/f1/KIT_SHEET_<family>.png, KIT_SHEET_overview.png, refcrops/ref_<pair>.png,
     pairs.json (pair name -> [reference crop, our render]). Text on the sheets is labelling only.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
F1 = SK / "renders" / "f1"
SHEET = F1 / "sheet"
REF = ROOT / "References" / "Dojo" / "dojo_landscape_ref.png"
FAMILIES = [
    ("wall_straight", "Terrace wall: straight modules 2 m / 4 m x H 2 / 3 / 4 / 6", ("Wall_2m_", "Wall_4m_")),
    ("wall_corners", "Terrace wall: outside corners (sangi-zumi, upswept) / inside corners (H6: 3 m arms)",
     ("Wall_CornerOut", "Wall_CornerIn")),
    ("wall_ends", "Terrace wall: ends returning into the slope", ("Wall_EndL", "Wall_EndR")),
    ("wall_stairs", "Terrace wall: stair openings H 2 / 3 / 4", ("Wall_StairOpening",)),
    ("wall_topfoot", "Top course alone / base course + flat buried skirt", ("WallCoping_", "WallFoot_")),
    ("stair_flights", "Stair path: flights (1-2 slabs a step, nosing overhang, wall-stone sides)", ("Stair_Flight",)),
    ("stair_landings", "Stair path: flush flagstone landings", ("Stair_Landing",)),
    ("stair_cheeks", "Stair path: low cheeks (+0.15 m over the treads)", ("Stair_Cheek",)),
    ("stair_rails", "Stair path: rails (round poles through posts; slopes carry both end posts)", ("Stair_Rail",)),
    ("stair_lanterns", "Stair path: lanterns (timber = the reference; stone = kit extra)", ("Stair_Lantern",)),
]
PAIRS = {   # pair: (reference box in the 1024 x 1536 reference, our render)
    "terrace_wall": ((380, 820, 700, 1000), "asm_terrace_wall"),
    "stair_head": ((180, 880, 540, 1100), "asm_stair_head"),
    "stair_path": ((0, 940, 420, 1536), "asm_stair_path"),
    "overview": ((0, 780, 1024, 1536), "asm_overview"),
    "stone_faces": ((430, 960, 520, 1030), "close_stone_faces"),
    "wall_lower": ((236, 950, 506, 1060), "match_wall_lower"),
    "step_nosing": ((140, 1150, 290, 1260), "cu_step_nosing"),
    "stairs_low": ((0, 1250, 340, 1536), "match_stairs_low"),
    "stairs_mid": ((100, 1000, 340, 1300), "match_stairs_mid"),
    "lanterns": ((170, 990, 340, 1110), "match_lanterns"),
    "lantern_close": ((178, 1000, 236, 1080), "match_lantern_close"),
    "rail_joint": ((180, 1376, 340, 1536), "cu_rail_joint"),
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
    for key, title, pre in FAMILIES:
        names = sorted(n for n in cat if n.startswith("SM_DKT_") and n[7:].startswith(pre))
        names = [n for n in names if (SHEET / f"{n[7:]}_persp.png").exists()]
        if not names:
            continue
        W = cell * len(views) + 20
        H = len(names) * (cell + lab) + 76
        im = Image.new("RGB", (W, H), (236, 236, 232))
        d = ImageDraw.Draw(im)
        d.text((12, 12), f"Dojo stone kit (f1): {title}", fill=(20, 20, 20), font=f1)
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
        fp = F1 / f"KIT_SHEET_{key}.png"
        im.save(fp)
        out.append(fp)
        print("sheet", fp, im.size)
    names = sorted(n for n in cat if n.startswith("SM_DKT_") and (SHEET / f"{n[7:]}_persp.png").exists())
    cols, cw = 8, 280
    rows = (len(names) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw + 20, rows * (cw + 30) + 60), (236, 236, 232))
    d = ImageDraw.Draw(im)
    d.text((12, 14), f"Dojo stone kit (f1): all {len(names)} pieces, 3/4 view with a 1.8 m figure", fill=(20, 20, 20),
           font=f1)
    for k, n in enumerate(names):
        x, y = 10 + (k % cols) * cw, 60 + (k // cols) * (cw + 30)
        im.paste(Image.open(SHEET / f"{n[7:]}_persp.png").convert("RGB").resize((cw - 6, cw - 6), Image.LANCZOS),
                 (x, y + 26))
        d.text((x + 2, y + 2), n[7:], fill=(10, 10, 10), font=font(15))
    fp = F1 / "KIT_SHEET_overview.png"
    im.save(fp)
    print("sheet", fp, im.size)
    return out + [fp]


def crops():
    ref = Image.open(REF).convert("RGB")
    od = F1 / "refcrops"
    od.mkdir(parents=True, exist_ok=True)
    pj = {}
    for name, (box, ours) in PAIRS.items():
        c = ref.crop(box)
        k = max(1, round(900 / c.height))
        c = c.resize((c.width * k, c.height * k), Image.LANCZOS)
        fp = od / f"ref_{name}.png"
        c.save(fp)
        pj[name] = [str(fp), str(F1 / f"{ours}.png"), str(F1 / f"sbs_{name}.png")]
    (F1 / "pairs.json").write_text(json.dumps(pj, indent=1), encoding="utf-8")
    print("crops", len(pj))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("crops", "all"):
        crops()
    if what in ("sheets", "all"):
        sheets()
