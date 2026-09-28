# Blender-python image stats: silhouette bbox (non-white), luminance percentiles of the dark (garment) pixels in sRGB 0-255.
import bpy, sys, json
args = sys.argv[sys.argv.index("--") + 1:]
res = {}
for path in args:
    img = bpy.data.images.load(path)
    w, h = img.size
    px = list(img.pixels[:])
    ch = img.channels
    lum = []
    xs = []; ys = []
    bg = []
    for j in range(h):
        for i in range(w):
            k = (j * w + i) * ch
            # blender stores float linear for 8-bit? pixels are in the image colour space as floats 0-1 (sRGB bytes/255)
            r, g, b = px[k], px[k + 1], px[k + 2]
            L = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if L < 0.55:
                lum.append(L * 255); xs.append(i); ys.append(h - 1 - j)
            elif L > 0.9:
                bg.append(L * 255)
    lum.sort(); bg.sort()
    pc = lambda a, q: round(a[int(q * (len(a) - 1))], 1) if a else None
    res[path] = {"size": [w, h], "garment_px": len(lum), "bbox_xy": [min(xs), min(ys), max(xs), max(ys)] if xs else None,
                 "garment_L_p10_p50_p90_p99": [pc(lum, .1), pc(lum, .5), pc(lum, .9), pc(lum, .99)],
                 "bg_L_p50": pc(bg, .5)}
    bpy.data.images.remove(img)
print("IMGSTATS " + json.dumps(res))
