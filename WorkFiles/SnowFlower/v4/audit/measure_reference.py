"""Measure silhouettes in an image: per-row left/right extents of 'not background' pixels
inside given column windows. Runs in Blender (numpy). Read-only on inputs.
blender -b --factory-startup --python measure_reference.py -- <image> <out.json> <name:x0:x1:y0:y1> ...
Rows are reported top-down (y=0 is the top of the image).
"""
import bpy, sys, json
import numpy as np

a = sys.argv[sys.argv.index('--') + 1:]
img_path, out = a[0], a[1]
wins = a[2:]
im = bpy.data.images.load(img_path)
w, h = im.size
px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1]  # top-down
rgb = px[..., :3]
# background: bright and unsaturated. Use luminance below 0.86 OR strong local darkness.
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
bg = np.median(lum[:20, :20])
mask = lum < (bg - 0.10)
res = {'image': img_path, 'size': [w, h], 'bg_lum': float(bg), 'windows': {}}
for spec in wins:
    name, x0, x1, y0, y1 = spec.split(':'); x0, x1, y0, y1 = map(int, (x0, x1, y0, y1))
    sub = mask[y0:y1, x0:x1]
    rows = []
    for r in range(sub.shape[0]):
        idx = np.nonzero(sub[r])[0]
        if len(idx):
            rows.append([y0 + r, int(x0 + idx[0]), int(x0 + idx[-1]), int(len(idx))])
    cols_any = np.nonzero(sub.any(axis=0))[0]
    rows_any = np.nonzero(sub.any(axis=1))[0]
    res['windows'][name] = {'rows': rows,
                            'bbox': [int(x0 + cols_any[0]), int(y0 + rows_any[0]), int(x0 + cols_any[-1]), int(y0 + rows_any[-1])] if len(rows_any) else None}
json.dump(res, open(out, 'w'))
print('WROTE', out)
