"""Blender-python (headless) comparison of Unreal captures against the user's reference photo.
args: -- <ref.png> <out_dir> <shot.png> [<shot.png> ...]
For each full-frame shot (834x1348 = 2x the reference): box-downsample 2x to 417x674, silhouette masks (garment = luminance
< T), IoU vs the reference, bbox, garment luminance percentiles (sRGB 0-255), and a side-by-side PNG (ref | ours | overlay).
Overlay colours: grey = both, red = reference only, blue = ours only.
"""
import bpy, sys, json, os

a = sys.argv[sys.argv.index("--") + 1:]
REF, OUTD, SHOTS = a[0], a[1], a[2:]
T = 0.45   # garment threshold (sRGB luminance fraction); backgrounds are > 0.8, the cloth < 0.35


def load(p):
    im = bpy.data.images.load(p)
    w, h = im.size
    px = list(im.pixels[:])
    c = im.channels
    rgb = [(px[k], px[k + 1], px[k + 2]) for k in range(0, w * h * c, c)]
    bpy.data.images.remove(im)
    return w, h, rgb   # rows bottom-up


def down2(w, h, rgb):
    W, H = w // 2, h // 2
    out = []
    for j in range(H):
        for i in range(W):
            s = [0.0, 0.0, 0.0]
            for dj in (0, 1):
                for di in (0, 1):
                    p = rgb[(2 * j + dj) * w + 2 * i + di]
                    s[0] += p[0]; s[1] += p[1]; s[2] += p[2]
            out.append((s[0] / 4, s[1] / 4, s[2] / 4))
    return W, H, out


def lum(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def stats(w, h, rgb):
    m = [lum(p) < T for p in rgb]
    xs = [i % w for i, v in enumerate(m) if v]
    ys = [h - 1 - i // w for i, v in enumerate(m) if v]
    L = sorted(lum(p) * 255 for p, v in zip(rgb, m) if v)
    pc = lambda q: round(L[int(q * (len(L) - 1))], 1) if L else None
    return m, {"garment_px": len(L), "bbox_x0y0x1y1_topdown": [min(xs), min(ys), max(xs), max(ys)] if xs else None,
               "L_p10_p50_p90_p99": [pc(.1), pc(.5), pc(.9), pc(.99)]}


def save(w, h, rgb, path):
    im = bpy.data.images.new("o", w, h, alpha=False)
    flat = []
    for p in rgb:
        flat += [p[0], p[1], p[2], 1.0]
    im.pixels[:] = flat
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


rw, rh, rref = load(REF)
rmask, rst = stats(rw, rh, rref)
res = {"reference": dict(rst, path=REF), "threshold": T, "shots": {}}
for s in SHOTS:
    w, h, rgb = load(s)
    if (w, h) == (2 * rw, 2 * rh):
        w, h, rgb = down2(w, h, rgb)
    if (w, h) != (rw, rh):
        res["shots"][s] = {"skipped": "size %dx%d" % (w, h)}
        continue
    m, st = stats(w, h, rgb)
    inter = sum(1 for x, y in zip(m, rmask) if x and y)
    union = sum(1 for x, y in zip(m, rmask) if x or y)
    st["iou_vs_reference"] = round(inter / union, 4) if union else None
    st["ref_only_px"] = sum(1 for x, y in zip(m, rmask) if y and not x)
    st["ours_only_px"] = sum(1 for x, y in zip(m, rmask) if x and not y)
    ov = []
    for x, y in zip(m, rmask):
        ov.append((0.45, 0.45, 0.45) if x and y else (0.9, 0.15, 0.1) if y else (0.1, 0.3, 0.95) if x else (1, 1, 1))
    sep = [(1, 1, 1)] * (8)
    W3 = rw * 3 + 16
    comp = []
    for j in range(rh):
        comp += rref[j * rw:(j + 1) * rw] + sep + rgb[j * rw:(j + 1) * rw] + sep + ov[j * rw:(j + 1) * rw]
    base = os.path.splitext(os.path.basename(s))[0]
    out = os.path.join(OUTD, "sbs_" + base + ".png")
    save(W3, rh, comp, out)
    st["side_by_side"] = out
    res["shots"][s] = st
print("MUCMP " + json.dumps(res))
json.dump(res, open(os.path.join(OUTD, "mu_compare.json"), "w"), indent=1)
