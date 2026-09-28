"""b2_sym_sheet.py - PRIVATE / DO NOT SHIP. Midline overlays, mirror-half comparisons and the labelled symmetry sheet.

  py -3 b2_sym_sheet.py

Reads sym_renders/{before,after}_*.png (b2_sym_render.py) and sym_renders/poses/*.png (b2_sym_posetest.py); writes
  sym_renders/{before,after}_{front,face}_mid.png      textured ortho front + thin vertical midline (x = 0)
  sym_renders/{before,after}_{front,face}_mirror.png   clay ortho: [her right half + its mirror | her left half + its
                                                       mirror | |image - mirrored image| x4], midline drawn
  sym_renders/sym_sheet.png                            everything, labelled (incl. the b2_sym_detail.py girth views
                                                       {prev_chord,before,after}_det_*.png when present)
The ortho cameras sit on x = 0, so the image centre column is the character's midline.
"""
import os, json
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

R = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/sym_renders"
P = R + "/poses"
CHK = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/checks_sym"


def font(sz):
    for f in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def label(im, text, sz=20, pos=(8, 6), fill=(20, 20, 24)):
    d = ImageDraw.Draw(im)
    f = font(sz)
    bb = d.textbbox(pos, text, font=f)
    d.rectangle((bb[0] - 5, bb[1] - 3, bb[2] + 5, bb[3] + 3), fill=fill)
    d.text(pos, text, font=f, fill=(255, 255, 255))


def midline(im, color=(255, 40, 40), width=1):
    im = im.copy()
    d = ImageDraw.Draw(im)
    x = im.size[0] / 2.0 - 0.5
    d.line([(x, 0), (x, im.size[1])], fill=color, width=width)
    return im


def mirror_panel(im):
    """[her right side (image left) + its mirror | her left side (image right) + its mirror | diff x4]"""
    w, h = im.size
    hw = w // 2
    left = im.crop((0, 0, hw, h)); right = im.crop((w - hw, 0, w, h))
    a = Image.new("RGB", (2 * hw, h)); a.paste(left, (0, 0)); a.paste(ImageOps.mirror(left), (hw, 0))
    b = Image.new("RGB", (2 * hw, h)); b.paste(ImageOps.mirror(right), (0, 0)); b.paste(right, (hw, 0))
    diff = ImageChops.difference(im, ImageOps.mirror(im)).point(lambda v: min(255, v * 4))
    out = Image.new("RGB", (3 * 2 * hw + 20, h), (30, 30, 34))
    for k, (img, t) in enumerate(((a, "her RIGHT half + mirror"), (b, "her LEFT half + mirror"), (diff, "|img - mirror| x4"))):
        img = midline(img, (255, 60, 60))
        label(img, t, 18, (6, h - 30))
        out.paste(img, (k * (2 * hw + 10), 0))
    return out, diff


def fit(im, W, H, bg=(40, 40, 44)):
    im = im.copy()
    im.thumbnail((W, H), Image.LANCZOS)
    tile = Image.new("RGB", (W, H), bg)
    tile.paste(im, ((W - im.size[0]) // 2, (H - im.size[1]) // 2))
    return tile


def main():
    made = {}
    stats = {}
    for pre in ("before", "after"):
        for shot in ("front", "face"):
            im = Image.open(f"{R}/{pre}_{shot}_ortho.png").convert("RGB")
            p = f"{R}/{pre}_{shot}_mid.png"
            midline(im, width=2 if shot == "front" else 2).save(p); made[f"{pre}_{shot}_mid"] = p
            clay = Image.open(f"{R}/{pre}_{shot}_clay.png").convert("RGB")
            panel, diff = mirror_panel(clay)
            p = f"{R}/{pre}_{shot}_mirror.png"
            panel.save(p); made[f"{pre}_{shot}_mirror"] = p
            # mean abs difference image vs mirror (raw, 0..255) of the clay render: a pixel measure of the asymmetry
            raw = ImageChops.difference(clay, ImageOps.mirror(clay)).convert("L")
            hist = raw.histogram()
            n = sum(hist)
            stats[f"{pre}_{shot}_clay_mirror_diff_mean"] = round(sum(i * c for i, c in enumerate(hist)) / n, 3)
            stats[f"{pre}_{shot}_clay_mirror_diff_px_over_32"] = sum(hist[33:])
    # ------------------------------------------------------------------ sheet
    W = 1900
    rows = []

    def row(title, tiles, h):
        n = len(tiles)
        tw = (W - 20 - (n - 1) * 8) // n
        r = Image.new("RGB", (W, h + 40), (30, 30, 34))
        label(r, title, 22, (10, 8), fill=(60, 30, 30))
        for k, (t, im) in enumerate(tiles):
            tile = fit(im, tw, h)
            label(tile, t, 17, (6, 6))
            r.paste(tile, (10 + k * (tw + 8), 38))
        rows.append(r)
    o = lambda p: Image.open(p).convert("RGB")  # noqa
    row("1. Orthographic front, textured, symmetric light - red line = midline x = 0",
        [("BEFORE", o(made["before_front_mid"])), ("AFTER", o(made["after_front_mid"])),
         ("BEFORE face", o(made["before_face_mid"])), ("AFTER face", o(made["after_face_mid"]))], 760)
    row("2. Mirror-half comparison BEFORE (clay): right half mirrored | left half mirrored | difference",
        [("BEFORE body", o(made["before_front_mirror"])), ("BEFORE face", o(made["before_face_mirror"]))], 520)
    row("3. Mirror-half comparison AFTER (clay): identical halves, difference image black",
        [("AFTER body", o(made["after_front_mirror"])), ("AFTER face", o(made["after_face_mirror"]))], 520)
    row("4. A-pose, step C1 render rig",
        [("BEFORE 3/4", o(f"{R}/before_apose_tq.png")), ("AFTER 3/4", o(f"{R}/after_apose_tq.png")),
         ("BEFORE front", o(f"{R}/before_apose_front.png")), ("AFTER front", o(f"{R}/after_apose_front.png"))], 620)
    det = [(t, f"{R}/{pre}_det_{v}.png") for v, vt in (("front", "front"), ("back", "back"), ("tq", "3/4"))
           for pre, t in (("prev_chord", f"PLAIN AVG {vt}"), ("before", f"BEFORE {vt}"), ("after", f"AFTER {vt}"))]
    det = [(t, o(f)) for t, f in det if os.path.exists(f)]
    for k in range(0, len(det), 3):
        row("4b. Girth (clay, upper body): plain topological average (first build, upper arms pinched) | BEFORE | AFTER "
            "(twist-aware average)" if k == 0 else "4b. (cont.)", det[k:k + 3], 600)
    poses = ["walk", "run", "squat", "arms_up", "tpose", "twist45", "head_turn60", "fist", "arms_forward"]
    cells = []
    for p in poses:
        for v in ("front", "side"):
            f = f"{P}/{p}_{v}.png"
            if os.path.exists(f):
                cells.append((f"{p} {v if not (p == 'fist' and v == 'side') else '3/4'}", o(f)))
    for s in ("l", "r"):
        f = f"{P}/fist_close_{s}.png"
        if os.path.exists(f):
            cells.append((f"fist close {s}", o(f)))
    for k in range(0, len(cells), 7):
        row("5. AFTER - deformation test poses (b2_rig_posetest logic)" if k == 0 else "5. (cont.)", cells[k:k + 7], 400)
    H = sum(r.size[1] for r in rows) + 70
    sheet = Image.new("RGB", (W, H), (22, 22, 26))
    label(sheet, "2B private - symmetry fix BEFORE / AFTER (PRIVATE / DO NOT SHIP)", 28, (14, 14))
    y = 60
    for r in rows:
        sheet.paste(r, (0, y)); y += r.size[1]
    out = R + "/sym_sheet.png"
    sheet.save(out)
    made["sheet"] = out
    json.dump({"files": made, "pixel_stats": stats}, open(CHK + "/sym_sheet_info.json", "w"), indent=1)
    print("sheet", out, sheet.size, json.dumps(stats))


main()
