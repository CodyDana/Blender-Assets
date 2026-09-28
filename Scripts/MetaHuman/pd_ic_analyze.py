"""pd_ic_analyze.py -- offline analysis of the pd_ic_verify.py captures (plain Python + Pillow; no Unreal).

usage: py Scripts/MetaHuman/pd_ic_analyze.py
Reads  WorkFiles/MetaHuman/player_default/integrity_check/captures/ic_*.png and the fixer's captures/after_*.png
Writes WorkFiles/MetaHuman/player_default/integrity_check/ic_image_metrics.json and sheets/*.png
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
IC = ROOT / "integrity_check"
CAP = IC / "captures"
FIX = ROOT / "captures"
SHEETS = IC / "sheets"
SHEETS.mkdir(parents=True, exist_ok=True)
M: dict = {}


def load(p: Path) -> Image.Image:
    return Image.open(p).convert("RGB")


def diff_stats(a: Image.Image, b: Image.Image) -> dict:
    d = ImageChops.difference(a, b)
    mean = sum(ImageStat.Stat(d).mean) / 3.0
    mx = d.split()
    big = ImageChops.lighter(ImageChops.lighter(mx[0], mx[1]), mx[2]).point(lambda v: 255 if v > 24 else 0)
    frac = ImageStat.Stat(big).mean[0] / 255.0
    return {"mean_abs_diff": round(mean, 3), "frac_pixels_maxdiff_gt24": round(frac, 5)}


# 1) fresh captures vs the fixer's verify_3 captures (same rig, same cameras)
SUFFIX = {"studio": "", "ambient": "_ambient", "rimspec0": "_rimspec0", "rimshadow": "_rimshadow", "base": "_base"}
cmp = {}
for p in sorted(CAP.glob("ic_pd_*.png")):
    variant, view = p.stem[len("ic_pd_"):].split("_", 1)
    if variant not in SUFFIX:
        continue
    f = FIX / f"after_{view}{SUFFIX[variant]}.png"
    if f.exists():
        cmp[p.stem] = {"fixer": f.name, **diff_stats(load(p), load(f))}
M["fresh_vs_fixer_after"] = cmp


# 2) chroma see-through test: green pixels NOT connected to the image border = background seen through the body
def green_mask(im: Image.Image):
    w, h = im.size
    px = im.load()
    g = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, gg, b = px[x, y]
            if gg > 90 and gg > r + 50 and gg > b + 50:
                g[y * w + x] = 1
    return g, w, h


def enclosed(im: Image.Image):
    g, w, h = green_mask(im)
    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            i = y * w + x
            if g[i] and not seen[i]:
                seen[i] = 1
                q.append(i)
    for y in range(h):
        for x in (0, w - 1):
            i = y * w + x
            if g[i] and not seen[i]:
                seen[i] = 1
                q.append(i)
    while q:
        i = q.popleft()
        x, y = i % w, i // w
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                j = ny * w + nx
                if g[j] and not seen[j]:
                    seen[j] = 1
                    q.append(j)
    comps = []
    done = bytearray(w * h)
    total = 0
    for i in range(w * h):
        if g[i] and not seen[i] and not done[i]:
            n = 0
            x0 = y0 = 10 ** 9
            x1 = y1 = -1
            q.append(i)
            done[i] = 1
            while q:
                k = q.popleft()
                n += 1
                x, y = k % w, k // w
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if g[j] and not seen[j] and not done[j]:
                            done[j] = 1
                            q.append(j)
            total += n
            comps.append({"px": n, "bbox": [x0, y0, x1, y1]})
    comps.sort(key=lambda c: -c["px"])
    return {"green_px": sum(g), "enclosed_green_px": total, "components": comps[:8]}


M["chroma_seethrough"] = {p.stem: enclosed(load(p)) for p in sorted(CAP.glob("ic_*_chroma_*.png"))}


# 3) jaw: near-black fraction (max RGB < 16) in a band under the jaw; whole-frame for JawClose
def near_black_frac(im: Image.Image, box=None) -> float:
    if box:
        im = im.crop(box)
    mx = im.split()
    m = ImageChops.lighter(ImageChops.lighter(mx[0], mx[1]), mx[2]).point(lambda v: 255 if v < 16 else 0)
    return round(ImageStat.Stat(m).mean[0] / 255.0, 5)


JAW_BAND_TQ = (330, 820, 900, 1020)   # Face_ThreeQuarter: underside of the jaw to below the ear (1000x1200 frame)
jaw = {}
for p in sorted(CAP.glob("ic_*_*_JawClose.png")) + sorted(CAP.glob("ic_*_*_JawLow.png")):
    jaw[p.stem] = {"near_black_frame": near_black_frac(load(p))}
for p in sorted(CAP.glob("ic_*_*_Face_ThreeQuarter.png")):
    jaw[p.stem] = {"near_black_jawband": near_black_frac(load(p), JAW_BAND_TQ)}
M["jaw_near_black"] = jaw


# 4) ear glint: near-white pixels (min RGB >= 150) in the EarR close-up and in the Face_Front image-left ear box
def white_count(im: Image.Image, box=None) -> int:
    if box:
        im = im.crop(box)
    mn = im.split()
    m = ImageChops.darker(ImageChops.darker(mn[0], mn[1]), mn[2]).point(lambda v: 255 if v >= 150 else 0)
    return int(round(ImageStat.Stat(m).mean[0] / 255.0 * im.size[0] * im.size[1]))


EAR_BOX_FRONT = (240, 560, 320, 760)
ear = {}
for p in sorted(CAP.glob("ic_*_*_EarR.png")):
    ear[p.stem] = {"white_px_frame": white_count(load(p), (0, 0, 600, 1200))}
for p in sorted(CAP.glob("ic_*_*_Face_Front.png")):
    ear[p.stem] = {"white_px_earbox": white_count(load(p), EAR_BOX_FRONT)}
M["ear_glint"] = ear


# 5) sheets
def sheet(name: str, items, scale=0.5, cols=None, box=None, title=""):
    ims = []
    for lab, p in items:
        if not Path(p).exists():
            continue
        im = load(Path(p))
        if box:
            im = im.crop(box)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        ims.append((lab, im))
    if not ims:
        return None
    cols = cols or len(ims)
    w = max(i.width for _, i in ims)
    h = max(i.height for _, i in ims) + 18
    rows = (len(ims) + cols - 1) // cols
    top = 22 if title else 0
    s = Image.new("RGB", (w * cols, h * rows + top), (25, 25, 25))
    d = ImageDraw.Draw(s)
    if title:
        d.text((4, 5), title, fill=(255, 255, 255))
    for k, (lab, im) in enumerate(ims):
        x, y = (k % cols) * w, top + (k // cols) * h
        s.paste(im, (x, y + 18))
        d.text((x + 3, y + 3), lab, fill=(255, 255, 120))
    out = SHEETS / name
    s.save(out)
    return str(out)


def c(n):
    return CAP / f"{n}.png"


S = {}
S["jaw"] = sheet("ic_jaw.png", [(n, c(n)) for n in (
    "ic_pd_studio_Face_ThreeQuarter", "ic_pd_headlight_Face_ThreeQuarter", "ic_pd_ambient_Face_ThreeQuarter",
    "ic_pd_base_Face_ThreeQuarter", "ic_pd_studio_JawClose", "ic_pd_headlight_JawClose", "ic_pd_ambient_JawClose",
    "ic_pd_base_JawClose", "ic_pd_studio_JawLow", "ic_pd_headlight_JawLow", "ic_pd_ambient_JawLow",
    "ic_facec_headlight_JawLow")], scale=0.4, cols=4, title="MH_PlayerDefault jaw: studio | headlight | ambient | base")
S["jaw_ref"] = sheet("ic_jaw_refs.png", [(n, c(n)) for n in (
    "ic_facec_studio_Face_ThreeQuarter", "ic_facec_headlight_Face_ThreeQuarter", "ic_facec_studio_JawClose",
    "ic_facec_headlight_JawClose", "ic_kelvin_studio_Face_ThreeQuarter", "ic_kelvin_headlight_Face_ThreeQuarter",
    "ic_kelvin_studio_JawClose", "ic_kelvin_headlight_JawClose", "ic_kelvin_ambient_Face_ThreeQuarter",
    "ic_kelvin_ambient_JawClose")], scale=0.4, cols=4, title="FaceC dup + Epic preset Kelvin (grooms hidden), same rig")
S["ear"] = sheet("ic_ear.png", [(n, c(n)) for n in (
    "ic_pd_studio_EarR", "ic_pd_rimspec0_EarR", "ic_pd_rimshadow_EarR", "ic_pd_headlight_EarR", "ic_pd_base_EarR",
    "ic_pd_ambient_EarR", "ic_kelvin_studio_EarR", "ic_kelvin_rimspec0_EarR")], scale=0.4, cols=4,
    title="image-left ear: PD studio | rim spec 0 | rim shadow | headlight | base | ambient | Kelvin studio | Kelvin rim spec 0")
S["shoulders_chroma"] = sheet("ic_shoulders_chroma.png", [(n, c(n)) for n in (
    "ic_pd_chroma_Shoulders_Front", "ic_pd_chroma_Shoulders_High", "ic_pd_chroma_ShoulderL_TQ",
    "ic_pd_chroma_ShoulderR_TQ", "ic_pd_chroma_Shoulders_Back", "ic_pd_chroma_Face_ThreeQuarter",
    "ic_facec_chroma_Shoulders_Front", "ic_facec_chroma_ShoulderL_TQ")], scale=0.4, cols=4,
    title="chroma (green = background): any green inside the body = see-through")
S["shoulders_zoom"] = sheet("ic_shoulders_zoom.png", [(n, c(n)) for n in (
    "ic_pd_chroma_ShoulderL_TQ", "ic_pd_chroma_ShoulderR_TQ", "ic_pd_studio_ShoulderL_TQ", "ic_pd_studio_ShoulderR_TQ")],
    scale=1.0, cols=2, box=(250, 250, 850, 750), title="shoulder tops, zoom (chroma top, studio bottom)")
S["hair_back"] = sheet("ic_hair_back.png", [(n, c(n)) for n in (
    "ic_pd_studio_Head_Back", "ic_pd_rimshadow_Head_Back", "ic_pd_ambient_Head_Back", "ic_pd_studio_Head_Back34",
    "ic_pd_rimshadow_Head_Back34", "ic_pd_studio_Head_Top", "ic_pd_studio_Body_Back", "ic_pd_rimshadow_Body_Back",
    "ic_pd_ambient_Body_Back")], scale=0.4, cols=3, title="hair from behind: studio | rim shadow | ambient")
S["identity"] = sheet("ic_identity.png", [(n, c(n)) for n in (
    "ic_pd_studio_Face_Front", "ic_pd_studio_Face_ThreeQuarter", "ic_pd_studio_Face_Profile",
    "ic_pd_ambient_Face_Front", "ic_pd_studio_Eyes", "ic_pd_studio_Body_Front")], scale=0.45, cols=3,
    title="MH_PlayerDefault identity (fresh session)")
S["fresh_vs_fixer"] = sheet("ic_fresh_vs_fixer.png", [
    ("FRESH studio Face_ThreeQuarter", c("ic_pd_studio_Face_ThreeQuarter")),
    ("FIXER after_Face_ThreeQuarter", FIX / "after_Face_ThreeQuarter.png"),
    ("FRESH studio EarR", c("ic_pd_studio_EarR")), ("FIXER after_EarR", FIX / "after_EarR.png"),
    ("FRESH studio Shoulders_Back", c("ic_pd_studio_Shoulders_Back")),
    ("FIXER after_Shoulders_Back", FIX / "after_Shoulders_Back.png")], scale=0.4, cols=6,
    title="fresh integrity-check captures vs the fixer's verify_3 captures")
M["sheets"] = S
(IC / "ic_image_metrics.json").write_text(json.dumps(M, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in M.items() if k != "chroma_seethrough"}, indent=1)[:6000])
print(json.dumps({k: {"green": v["green_px"], "enclosed": v["enclosed_green_px"], "comps": v["components"][:3]}
                  for k, v in M["chroma_seethrough"].items()}, indent=1))
