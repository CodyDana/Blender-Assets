"""pd_pd_sheets.py -- before/after sheets + pixel metrics for MH_PlayerDefault (plain Python + Pillow, outside Unreal).

Reads WorkFiles/MetaHuman/player_default/captures/{before_,after_}*.png written by pd_player_default.py (PD_MODE=verify:
before = scratch duplicate of MH_PlayerBase_FaceC, after = the saved MH_PlayerDefault, same session, same studio
rig + cameras as pb_conform.py, one MetaHuman actor in the world at a time).
Writes captures/before_after_*.png and image_metrics.json.

usage: py Scripts/MetaHuman/pd_pd_sheets.py
"""
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
CAP = OUT / "captures"
try:
    FONT = ImageFont.truetype("arial.ttf", 18)
except Exception:  # noqa: BLE001
    FONT = ImageFont.load_default()


def load(name):
    p = CAP / name
    if not p.exists():
        im = Image.new("RGB", (1000, 1200), (70, 0, 0))
        ImageDraw.Draw(im).text((20, 20), "MISSING " + name, fill=(255, 255, 255), font=FONT)
        return im
    return Image.open(p).convert("RGB")


def sheet(out_name, cols, crop, scale, title):
    """cols = list of (column label, view file suffix); rows = before / after."""
    tiles = []
    for who, prefix in (("BEFORE  MH_PlayerBase_FaceC", "before_"), ("AFTER  MH_PlayerDefault", "after_")):
        row = []
        for label, suffix in cols:
            im = load(prefix + suffix)
            c = crop.get(suffix, crop.get("*")) if isinstance(crop, dict) else crop
            if c:
                im = im.crop(c)
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
            row.append((f"{who.split()[0]}  {label}", im))
        tiles.append(row)
    w = max(t.width for r in tiles for _, t in r)
    h = max(t.height for r in tiles for _, t in r)
    lab, top = 26, 34
    sh = Image.new("RGB", (len(cols) * w, top + 2 * (h + lab)), (25, 25, 25))
    d = ImageDraw.Draw(sh)
    d.text((6, 6), title, fill=(255, 255, 255), font=FONT)
    for r, row in enumerate(tiles):
        for c, (label, t) in enumerate(row):
            x, y = c * w, top + r * (h + lab)
            sh.paste(t, (x, y + lab))
            d.text((x + 4, y + 3), label, fill=(255, 255, 160) if r == 0 else (160, 255, 200), font=FONT)
    sh.save(CAP / out_name)
    print(out_name, sh.size)
    return str(CAP / out_name)


def near_black_frac(name, thr=16, box=None):
    im = load(name)
    if box:
        im = im.crop(box)
    px = list(im.getdata())
    n = sum(1 for p in px if max(p) < thr)
    return round(n / len(px), 5), n


def white_count(name, thr=205, box=None):
    im = load(name)
    if box:
        im = im.crop(box)
    return sum(1 for p in im.getdata() if min(p) >= thr)


def mask_ortho(name, z_max_cm):
    """Silhouette of an orthographic base-colour shot (backdrop hidden -> black); rows below z_max_cm only.
    Ortho: 1200 px over 240 cm centred at z=95 -> row = (215 - z) / 0.2."""
    im = load(name)
    r0 = int((215.0 - z_max_cm) / 0.2)
    w, h = im.size
    px = im.load()
    return {(x, y) for y in range(r0, h) for x in range(w) if max(px[x, y]) > 6}


# shoulder-top regions of the base-colour shots (1000x1200), everything above the chin excluded
SHOULDER_BOXES = {"Shoulders_Front_base.png": (0, 320, 1000, 1200), "Shoulders_High_base.png": (0, 480, 1000, 1200),
                  "ShoulderL_TQ_base.png": (0, 150, 1000, 1200), "ShoulderR_TQ_base.png": (0, 150, 1000, 1200),
                  "Shoulders_Back_base.png": (0, 400, 1000, 1200)}


def enclosed_background(name, box):
    """BASE-COLOUR capture (backdrop = pure black there, skin / painted underwear never are): black pixels inside
    `box` that are NOT connected to the image border = see-through holes in the silhouette. (The lit captures cannot
    be used: the painted tank top's grey matches the backdrop grey.)"""
    im = load(name).crop(box)
    w, h = im.size
    px = im.load()
    bg = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            bg[y][x] = max(px[x, y]) <= 3
    seen = [[False] * w for _ in range(h)]
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and bg[ny][nx] and not seen[ny][nx]:
                seen[ny][nx] = True
                q.append((nx, ny))
    return sum(1 for y in range(h) for x in range(w) if bg[y][x] and not seen[y][x])


PB = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base")


def load_any(path):
    if not Path(path).exists():
        im = Image.new("RGB", (1000, 1200), (70, 0, 0))
        ImageDraw.Draw(im).text((20, 20), "MISSING " + str(path), fill=(255, 255, 255), font=FONT)
        return im
    return Image.open(path).convert("RGB")


def strip(out_name, title, entries, crop, scale):
    """entries = [(label, path)] in one row, same crop for all."""
    tiles = [(lab, load_any(pth).crop(crop)) for lab, pth in entries]
    tiles = [(lab, t.resize((int(t.width * scale), int(t.height * scale)), Image.LANCZOS)) for lab, t in tiles]
    w = max(max(t.width for _, t in tiles), 230)
    h = max(t.height for _, t in tiles)
    lab_h, top = 26, 34
    sh = Image.new("RGB", (len(tiles) * w, top + lab_h + h), (25, 25, 25))
    d = ImageDraw.Draw(sh)
    d.text((6, 6), title, fill=(255, 255, 255), font=FONT)
    for i, (lab, t) in enumerate(tiles):
        sh.paste(t, (i * w, top + lab_h))
        d.text((i * w + 4, top + 3), lab, fill=(255, 255, 160) if lab.startswith(("FaceC", "conform", "BEFORE")) else (160, 255, 200), font=FONT)
    sh.save(CAP / out_name)
    print(out_name, sh.size)
    return str(CAP / out_name)


def origin_sheets():
    """Each reported defect on the capture it was reported on, next to the fresh-session verify captures."""
    mh, fb = PB / "captures", PB / "faces/captures"
    return [strip("defect1_jaw_origin_vs_after.png",
                  "Defect 1 jaw line: reported capture -> PlayerDefault studio rig -> eval rig -> ambient rig",
                  [("FaceC build session 3/4 (reported)", fb / "FaceC_Face_ThreeQuarter.png"),
                   ("conform mh_ 3/4", mh / "mh_Face_ThreeQuarter.png"),
                   ("AFTER studio rig", CAP / "after_Face_ThreeQuarter.png"),
                   ("AFTER eval rig", CAP / "after_Face_ThreeQuarter_eval.png"),
                   ("AFTER ambient rig", CAP / "after_Face_ThreeQuarter_ambient.png")],
                  (300, 700, 900, 1050), 0.8),
            strip("defect2_ear_origin_vs_after.png",
                  "Defect 2 image-left ear patch: reported -> PlayerDefault studio -> rim spec 0 -> no rim -> eval -> ambient",
                  [("FaceC build (reported)", fb / "FaceC_Face_Front.png"),
                   ("conform mh_", mh / "mh_Face_Front.png"),
                   ("AFTER studio", CAP / "after_Face_Front.png"),
                   ("AFTER rim spec 0", CAP / "after_Face_Front_rimspec0.png"),
                   ("AFTER no rim", CAP / "after_Face_Front_norim.png"),
                   ("AFTER eval rig", CAP / "after_Face_Front_eval.png"),
                   ("AFTER ambient", CAP / "after_Face_Front_ambient.png")],
                  (230, 580, 340, 760), 2.0),
            strip("defect3_shoulders_origin_vs_after.png",
                  "Defect 3 shoulder slivers (front): conform session mh_ (reported) vs FaceC build session vs fresh BEFORE / AFTER",
                  [("conform mh_ front (reported)", mh / "mh_Face_Front.png"),
                   ("FaceC build session front", fb / "FaceC_Face_Front.png"),
                   ("BEFORE fresh FaceC", CAP / "before_Face_Front.png"),
                   ("AFTER fresh PlayerDefault", CAP / "after_Face_Front.png")],
                  (0, 960, 1000, 1200), 0.6),
            strip("defect3_shoulders34_origin_vs_after.png",
                  "Defect 3 shoulder slivers (3/4): conform session mh_ (reported) vs FaceC build session vs fresh BEFORE / AFTER",
                  [("conform mh_ 3/4 (reported)", mh / "mh_Face_ThreeQuarter.png"),
                   ("FaceC build session 3/4", fb / "FaceC_Face_ThreeQuarter.png"),
                   ("BEFORE fresh FaceC", CAP / "before_Face_ThreeQuarter.png"),
                   ("AFTER fresh PlayerDefault", CAP / "after_Face_ThreeQuarter.png")],
                  (60, 950, 560, 1200), 0.9)]


def origin_metrics():
    mh, fb = PB / "captures", PB / "faces/captures"

    def nb(path, box, thr=16):
        px = list(load_any(path).crop(box).getdata())
        return round(sum(1 for p in px if max(p) < thr) / len(px), 5)

    def gl(path, box, thr=150):
        return sum(1 for p in load_any(path).crop(box).getdata() if min(p) >= thr)
    jaw_box = (150, 700, 900, 1000)
    ear_box = (240, 560, 320, 760)
    return {"jaw_band_near_black_frac_ThreeQuarter_box_150_700_900_1000": {
                "FaceC_build_session_reported": nb(fb / "FaceC_Face_ThreeQuarter.png", jaw_box),
                "conform_mh": nb(mh / "mh_Face_ThreeQuarter.png", jaw_box),
                "after_studio": nb(CAP / "after_Face_ThreeQuarter.png", jaw_box),
                "after_eval": nb(CAP / "after_Face_ThreeQuarter_eval.png", jaw_box),
                "after_ambient": nb(CAP / "after_Face_ThreeQuarter_ambient.png", jaw_box)},
            "imageLeftEar_glint_px_Front_box_240_560_320_760": {
                "FaceC_build_session_reported": gl(fb / "FaceC_Face_Front.png", ear_box),
                "conform_mh": gl(mh / "mh_Face_Front.png", ear_box),
                "after_studio": gl(CAP / "after_Face_Front.png", ear_box),
                "after_rimspec0": gl(CAP / "after_Face_Front_rimspec0.png", ear_box),
                "after_norim": gl(CAP / "after_Face_Front_norim.png", ear_box),
                "after_eval": gl(CAP / "after_Face_Front_eval.png", ear_box),
                "after_ambient": gl(CAP / "after_Face_Front_ambient.png", ear_box)}}


def main():
    sheets = []
    sheets.append(sheet("before_after_face.png",
                        [("Face_Front", "Face_Front.png"), ("Face_ThreeQuarter", "Face_ThreeQuarter.png"),
                         ("Face_Profile", "Face_Profile.png")],
                        (170, 180, 870, 1200), 0.62, "Face, studio rig (pb_conform key/fill/rim + sky, same cameras)"))
    sheets.append(sheet("before_after_body.png",
                        [("Body_Front", "Body_Front.png"), ("Body_Side", "Body_Side.png"), ("Body_Back", "Body_Back.png")],
                        (250, 60, 750, 1150), 0.7, "Body, studio rig (body geometry identical; see body_compare.json)"))
    sheets.append(sheet("before_after_hands.png",
                        [("Hand_xneg_Front", "Hand_xneg_Front.png"), ("Hand_xneg_Outer", "Hand_xneg_Outer.png"),
                         ("Hand_xpos_Front", "Hand_xpos_Front.png"), ("Hand_xpos_Outer", "Hand_xpos_Outer.png")],
                        (150, 150, 850, 1050), 0.45, "Hands, studio rig"))
    sheets.append(sheet("before_after_jaw.png",
                        [("JawClose studio", "JawClose.png"), ("JawClose +bounce", "JawClose_bounce.png"),
                         ("JawClose eval rig", "JawClose_eval.png"), ("JawClose ambient", "JawClose_ambient.png"),
                         ("JawClose base colour", "JawClose_base.png"),
                         ("JawLow studio", "JawLow.png"), ("JawLow +bounce", "JawLow_bounce.png"),
                         ("JawLow ambient", "JawLow_ambient.png")],
                        None, 0.32, "Jaw: studio rig vs +bounce up-light vs eval rig vs ambient (sky light capturing the grey backdrop) vs base colour"))
    sheets.append(sheet("before_after_ear.png",
                        [("EarR studio", "EarR.png"), ("EarR rim spec 0", "EarR_rimspec0.png"),
                         ("EarR no rim", "EarR_norim.png"), ("EarR rim shadow", "EarR_rimshadow.png"),
                         ("EarR eval rig", "EarR_eval.png"), ("EarR ambient", "EarR_ambient.png"),
                         ("EarR base colour", "EarR_base.png"),
                         ("EarRSide studio", "EarRSide.png")],
                        (0, 150, 700, 1100), 0.4,
                        "Image-left ear (character's right): studio rig vs rim-light specular off / rim off / rim shadow vs base colour"))
    sheets.append(sheet("before_after_shoulders.png",
                        [("Shoulders_Front", "Shoulders_Front.png"), ("Shoulders_High", "Shoulders_High.png"),
                         ("ShoulderL_TQ", "ShoulderL_TQ.png"), ("ShoulderR_TQ", "ShoulderR_TQ.png"),
                         ("Shoulders_Back", "Shoulders_Back.png"), ("Shoulders_Front base", "Shoulders_Front_base.png"),
                         ("ShoulderL_TQ base", "ShoulderL_TQ_base.png")],
                        None, 0.33, "Shoulder tops, fresh session, one MetaHuman actor in the world (base = albedo on black)"))
    sheets.append(sheet("before_after_eyes_hair.png",
                        [("Eyes", "Eyes.png"), ("Head_Back34", "Head_Back34.png"), ("Head_Top", "Head_Top.png")],
                        {"Eyes.png": (0, 380, 1000, 820), "*": (150, 150, 850, 1050)}, 0.55,
                        "Identity: eyes, hair (back 3/4, top)"))
    sheets.append(sheet("before_after_eval_rig.png",
                        [("Face_Front eval", "Face_Front_eval.png"), ("Face_ThreeQuarter eval", "Face_ThreeQuarter_eval.png"),
                         ("Face_Profile eval", "Face_Profile_eval.png"), ("Head_Back34 eval", "Head_Back34_eval.png"),
                         ("Body_Front eval", "Body_Front_eval.png")],
                        {"Body_Front_eval.png": (250, 60, 750, 1150), "Head_Back34_eval.png": (150, 150, 850, 1050),
                         "*": (170, 180, 870, 1200)}, 0.5,
                        "Evaluation rig = studio + weak unshadowed up-light + rim light casting shadows at 0.3 specular"))
    sheets.append(sheet("before_after_ambient.png",
                        [("Face_Front ambient", "Face_Front_ambient.png"),
                         ("Face_ThreeQuarter ambient", "Face_ThreeQuarter_ambient.png"),
                         ("Face_Profile ambient", "Face_Profile_ambient.png"), ("EarR ambient", "EarR_ambient.png"),
                         ("Body_Front ambient", "Body_Front_ambient.png")],
                        {"Body_Front_ambient.png": (250, 60, 750, 1150), "EarR_ambient.png": (0, 150, 700, 1100),
                         "*": (170, 180, 870, 1200)}, 0.5,
                        "Ambient rig = studio key/fill/rim UNCHANGED + the same sky light made to capture the grey backdrop (real ambient)"))
    sheets += origin_sheets()

    m = {"thresholds": {"near_black_maxRGB_lt": 16, "glint_minRGB_ge": 150}}
    for who in ("before", "after"):
        mm = {}
        # lit captures only (in base colour the backdrop itself is black)
        for v in ("JawClose.png", "JawClose_bounce.png", "JawClose_eval.png",
                  "Face_ThreeQuarter.png", "Face_ThreeQuarter_bounce.png", "Face_ThreeQuarter_eval.png",
                  "Face_Front.png", "Face_Front_bounce.png", "Face_Front_eval.png", "JawLow.png", "JawLow_bounce.png",
                  "JawClose_ambient.png", "JawLow_ambient.png", "Face_ThreeQuarter_ambient.png", "Face_Front_ambient.png"):
            box = (150, 700, 900, 1000) if v.startswith("Face_") else None     # face shots: jaw band only
            mm["near_black_" + v] = near_black_frac(f"{who}_{v}", box=box)
        # ear glint: near-white pixels (min RGB >= 150; lit ear skin tops out near R 125-175 with low G/B) on the ear of
        # the EarR close-up (box x 330-530, y 380-880) and on the image-left ear of Face_Front (x 240-320, y 560-760)
        for v in ("EarR.png", "EarR_rimspec0.png", "EarR_norim.png", "EarR_rimshadow.png", "EarR_eval.png",
                  "EarR_ambient.png", "EarR_base.png"):
            mm["glint_px_ear_" + v] = white_count(f"{who}_{v}", thr=150, box=(330, 380, 530, 880))
        for v in ("Face_Front.png", "Face_Front_rimspec0.png", "Face_Front_norim.png", "Face_Front_rimshadow.png",
                  "Face_Front_eval.png", "Face_Front_ambient.png"):
            mm["glint_px_imageLeftEar_" + v] = white_count(f"{who}_{v}", thr=150, box=(240, 560, 320, 760))
        # shoulder region only (below the chin): in the base-colour pass the groom strands, pupils and nostrils are
        # also ~black, so a whole-frame count measures the new hair, not holes (checked: pdfix_holes_locate)
        for v, box in SHOULDER_BOXES.items():
            mm["seethrough_holes_px_" + v] = enclosed_background(f"{who}_{v}", box)
        m[who] = mm
    a = mask_ortho("after_Ortho_Front.png", 148.0)
    b = mask_ortho("before_Ortho_Front.png", 148.0)
    m["ortho_front_below_z148_silhouette"] = {"after_px": len(a), "before_px": len(b), "xor_px": len(a ^ b),
                                              "iou": round(len(a & b) / max(1, len(a | b)), 6)}
    a = mask_ortho("after_Ortho_Side.png", 148.0)
    b = mask_ortho("before_Ortho_Side.png", 148.0)
    m["ortho_side_below_z148_silhouette"] = {"after_px": len(a), "before_px": len(b), "xor_px": len(a ^ b),
                                             "iou": round(len(a & b) / max(1, len(a | b)), 6)}
    m["shoulder_region_silhouette_before_vs_after_base"] = {}
    for v, box in SHOULDER_BOXES.items():
        a = load("after_" + v).crop(box)
        b = load("before_" + v).crop(box)
        pa, pb = a.load(), b.load()
        w, h = a.size
        ma = {(x, y) for y in range(h) for x in range(w) if max(pa[x, y]) > 3}
        mb = {(x, y) for y in range(h) for x in range(w) if max(pb[x, y]) > 3}
        m["shoulder_region_silhouette_before_vs_after_base"][v] = {
            "box": list(box), "after_px": len(ma), "before_px": len(mb), "xor_px": len(ma ^ mb),
            "iou": round(len(ma & mb) / max(1, len(ma | mb)), 6)}
    m["defect_origin"] = origin_metrics()
    m["sheets"] = sheets
    (OUT / "image_metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
