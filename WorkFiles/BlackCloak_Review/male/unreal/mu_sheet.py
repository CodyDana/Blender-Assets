"""Blender-python: review sheet. Row 1 (417x674 each): reference | engine cloak-only | engine with body (rest) | engine settled cloth.
Row 2 (556x556 each): reference collar/clasp crop | engine collar/clasp | reference hem crop | engine hem.  White gutters.
"""
import bpy, sys
a = sys.argv[sys.argv.index("--") + 1:]
REF, SH, OUT = a[0], a[1], a[2]


def load(p):
    im = bpy.data.images.load(p)
    return im


def crop_scale(im, x0, y0, x1, y1, W, H):
    """x0,y0,x1,y1 top-down pixel box -> new image W x H."""
    w, h = im.size
    c = im.channels
    px = im.pixels[:]
    cw, ch = x1 - x0, y1 - y0
    new = bpy.data.images.new("c", cw, ch, alpha=False)
    flat = []
    for j in range(ch):
        row = h - 1 - (y1 - 1 - j)      # bottom-up
        for i in range(cw):
            k = (row * w + x0 + i) * c
            flat += [px[k], px[k + 1], px[k + 2], 1.0]
    new.pixels[:] = flat
    new.scale(W, H)
    return new


def full(im, W, H):
    w, h = im.size
    return crop_scale(im, 0, 0, w, h, W, H)


ref = load(REF)
panels1 = [full(ref, 417, 674)]
for n in ("front_cloak_only_yaw+0", "front_with_body", "front_with_body_cloth_SIE_settled"):
    panels1.append(full(load("%s/%s.png" % (SH, n)), 417, 674))
S2 = 556
ref_collar = crop_scale(ref, 60, 0, 330, 270, S2, S2)            # reference collar + clasp + mantle start
ours_collar = full(load(SH + "/close_collar_clasp_region.png"), S2, S2)
ref_hem = crop_scale(ref, 60, 470, 360, 674, S2, int(S2 * 204 / 300))
ours_hem = full(load(SH + "/close_hem.png"), S2, int(S2 * 1000 / 1400))
panels2 = [ref_collar, ours_collar, ref_hem, ours_hem]
G = 12
W = max(sum(p.size[0] for p in panels1) + G * 5, sum(p.size[0] for p in panels2) + G * 5)
H = G + 674 + G + S2 + G
sheet = [1.0] * (W * H * 4)


def paste(im, x0, ytop):
    w, h = im.size
    px = im.pixels[:]
    for j in range(h):
        row_dst = H - 1 - (ytop + (h - 1 - j))
        for i in range(w):
            ks = (j * w + i) * 4
            kd = (row_dst * W + x0 + i) * 4
            sheet[kd:kd + 3] = px[ks:ks + 3]


x = G
for p in panels1:
    paste(p, x, G); x += p.size[0] + G
x = G
for p in panels2:
    paste(p, x, G + 674 + G); x += p.size[0] + G
out = bpy.data.images.new("sheet", W, H, alpha=False)
out.pixels[:] = sheet
out.filepath_raw = OUT
out.file_format = "PNG"
out.save()
print("SHEET_OK", OUT, W, H)
