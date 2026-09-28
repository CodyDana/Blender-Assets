"""SUPERSEDED by s6_contact.py (corrected captions, roppo spec at apex span). Kept for the record.
Compose the contact sheet: per form, reconciler's built/spec overlay (left) next to the synthesis
photo-matched overlay (right). Headless Blender numpy only.
Run: blender -b --factory-startup --python s4_contact.py"""
import bpy, numpy as np, os, json

P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
S = P + "synthesis/"
N = json.load(open(S + "synthesis_numbers.json"))

def load_rgb(path):
    img = bpy.data.images.load(path); W, H = img.size
    buf = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(buf)
    a = buf.reshape(H, W, 4)[::-1, :, :3].copy(); bpy.data.images.remove(img); return a

def save_png(a, path):
    h, w, _ = a.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    buf = np.ones((h, w, 4), np.float32); buf[..., :3] = np.clip(a, 0, 1)
    img.pixels.foreach_set(buf[::-1].ravel()); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); print("wrote", path)

def box_resize(a, nh, nw):
    """area-average resize (downscale) via cumulative sums"""
    h, w, _ = a.shape
    def axis(arr, n, L, ax):
        cs = np.concatenate([np.zeros_like(np.take(arr, [0], axis=ax)), np.cumsum(arr, axis=ax)], axis=ax)
        e = np.linspace(0, L, n + 1)
        i0 = np.floor(e[:-1]).astype(int); i1 = np.maximum(np.floor(e[1:]).astype(int), i0 + 1)
        i1 = np.minimum(i1, L)
        return (np.take(cs, i1, axis=ax) - np.take(cs, i0, axis=ax)) / (i1 - i0).reshape([-1 if k == ax else 1 for k in range(3)])
    return axis(axis(a, nh, h, 0), nw, w, 1)

F = {
 'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#", 'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
 'C': ".###.|#...#|#....|#....|#....|#...#|.###.", 'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
 'E': "#####|#....|#....|####.|#....|#....|#####", 'F': "#####|#....|#....|####.|#....|#....|#....",
 'G': ".###.|#...#|#....|#.###|#...#|#...#|.####", 'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
 'I': ".###.|..#..|..#..|..#..|..#..|..#..|.###.", 'J': "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
 'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", 'L': "#....|#....|#....|#....|#....|#....|#####",
 'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", 'N': "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
 'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.", 'P': "####.|#...#|#...#|####.|#....|#....|#....",
 'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#", 'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
 'S': ".####|#....|#....|.###.|....#|....#|####.", 'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..",
 'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.", 'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
 'W': "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.", 'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
 'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", 'Z': "#####|....#|...#.|..#..|.#...|#....|#####",
 '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", '1': "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
 '2': ".###.|#...#|....#|...#.|..#..|.#...|#####", '3': "####.|....#|....#|.###.|....#|....#|####.",
 '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", '5': "#####|#....|####.|....#|....#|#...#|.###.",
 '6': "..##.|.#...|#....|####.|#...#|#...#|.###.", '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
 '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.", '9': ".###.|#...#|#...#|.####|....#|...#.|.##..",
 '.': ".....|.....|.....|.....|.....|.##..|.##..", ',': ".....|.....|.....|.....|.##..|..#..|.#...",
 ':': ".....|.##..|.##..|.....|.##..|.##..|.....", '-': ".....|.....|.....|#####|.....|.....|.....",
 '(': "...#.|..#..|.#...|.#...|.#...|..#..|...#.", ')': ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
 '/': ".....|....#|...#.|..#..|.#...|#....|.....", '=': ".....|.....|#####|.....|#####|.....|.....",
 '+': ".....|..#..|..#..|#####|..#..|..#..|.....", '%': "##...|##..#|...#.|..#..|.#...|#..##|...##",
 ' ': ".....|.....|.....|.....|.....|.....|.....", '_': ".....|.....|.....|.....|.....|.....|#####",
}
GL = {k: np.array([[c == '#' for c in row] for row in v.split('|')]) for k, v in F.items()}

def text(im, x, y, s, col, sc=2):
    for ch in s.upper():
        g = GL.get(ch, GL[' '])
        m = np.kron(g, np.ones((sc, sc), bool))
        h, w = m.shape
        if y + h <= im.shape[0] and x + w <= im.shape[1]:
            reg = im[y:y + h, x:x + w]; reg[m] = col
        x += 6 * sc
    return x

J, H_, Ro, Se, M = N["juji"], N["happo"], N["roppo"], N["senban"], N["manji"]
rows = [
 ("FOUR-POINT JUJI  (JUJI.JPG, STUDY 2.1)",
  P + "juji/juji_overlay_built_vs_photo.png",
  ["BUILT SM_SHURIKEN_FOURPOINT = MAGENTA", "GREEN = MEASURED PHOTO EDGE"],
  S + "juji_photo_matched.png",
  ["PHOTO-MATCHED AT 97 MM = CYAN", "LEAF ON NECK, NO HUB, NO HOLE. IOU %.3f" % J["iou_vs_reconciled_mask"]]),
 ("EIGHT-POINT HAPPO  (HAPPO.JPG, STUDY 2.2)",
  P + "happo/happo_overlay_built.png",
  ["BUILT SM_SHURIKEN_EIGHTPOINT = MAGENTA", "22 MM HUB R, 10 MM ARMS, 9.5 MM HOLE"],
  S + "happo_photo_matched.png",
  ["PHOTO-MATCHED STAR, V NOTCHES = CYAN", "YELLOW DASH = SOURCED 9.5 MM HOLE. IOU %.3f" % H_["iou_vs_reconciled_mask_no_hole"]]),
 ("SIX-POINT ROPPO  (ROPPO.JPG, STUDY 2.4)",
  P + "roppo/roppo_overlay_spec.png",
  ["STUDY SPEC, NOT BUILT = RED (HOLE ORANGE)", "18 MM HUB R, 11 MM ARMS, 38 DEG, 8 MM HOLE"],
  S + "roppo_photo_matched.png",
  ["PHOTO-MATCHED AT 98 MM = CYAN", "25.1 DEG POINTS, 46.5 HUB, 21.7 BORE. IOU %.3f" % Ro["iou_vs_radial_mask_A_T65"]]),
 ("SENBAN SQUARE PLATE  (SENBAN.JPG, STUDY 2.3)",
  P + "senban/senban_spec_outline.png",
  ["STUDY SPEC = MAGENTA", "6 MM SAGITTA (ESTIMATE), 12.7 MM HOLE"],
  S + "senban_photo_matched.png",
  ["PHOTO-MATCHED 4.7 MM SAGITTA = CYAN", "YELLOW 12.7 MM HOLE KEPT, DASH = PHOTO 20.1"]),
 ("MANJI HOOKED CROSS  (MANJIKEN.JPG, STUDY 2.6)",
  P + "manji/manji_spec_overlay_half.png",
  ["STUDY PLACEHOLDER = CYAN (NOT BUILT)", "RED = MEASURED OUTLINE"],
  S + "manji_photo_matched_half.png",
  ["PHOTO-MATCHED AT 100 MM = CYAN", "TAPERED ARMS, SWEPT HOOKS. IOU %.3f" % M["iou_vs_contour_mask"]]),
]

BOX_W, BOX_H, GUT, HEAD, CAP, TOP = 700, 660, 20, 40, 52, 70
Wd = 2 * BOX_W + 3 * GUT
Ht = TOP + len(rows) * (HEAD + BOX_H + CAP + 12)
sheet = np.full((Ht, Wd, 3), 0.11, np.float32)
text(sheet, GUT, 16, "SHURIKEN PHOTO STUDY  CONTACT SHEET  2026-09-18", (1, 1, 1), 3)
text(sheet, GUT, 46, "LEFT: BUILT OR STUDY-SPEC OUTLINE ON THE PHOTO    RIGHT: PHOTO-MATCHED SET AT THE SOURCED SIZE", (0.8, 0.8, 0.8), 2)
y = TOP
for title, lp, lcap, rp, rcap in rows:
    sheet[y:y + HEAD - 6, GUT:Wd - GUT] = (0.2, 0.2, 0.22)
    text(sheet, GUT + 10, y + 10, title, (1.0, 0.9, 0.5), 2)
    y0 = y + HEAD
    for j, (path, cap) in enumerate(((lp, lcap), (rp, rcap))):
        a = load_rgb(path); h, w, _ = a.shape
        f = min(BOX_W / w, BOX_H / h)
        nh, nw = int(round(h * f)), int(round(w * f))
        r = box_resize(a, nh, nw)
        x0 = GUT + j * (BOX_W + GUT) + (BOX_W - nw) // 2
        yy = y0 + (BOX_H - nh) // 2
        sheet[yy:yy + nh, x0:x0 + nw] = r
        cx = GUT + j * (BOX_W + GUT)
        text(sheet, cx + 4, y0 + BOX_H + 8, cap[0], (0.95, 0.95, 0.95), 2)
        text(sheet, cx + 4, y0 + BOX_H + 28, cap[1], (0.75, 0.75, 0.75), 2)
    y = y0 + BOX_H + CAP + 12
save_png(sheet, P + "contact_sheet.png")
