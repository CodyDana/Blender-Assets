# shared helpers for sheath metrology (run inside Blender's Python; numpy only)
import numpy as np, os, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
DBG = os.path.join(HERE, "debug")
os.makedirs(DBG, exist_ok=True)


def load(key):
    return np.load(os.path.join(HERE, f"sm_{key}.npy"))


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def sat(a):
    mx = a[..., :3].max(-1); mn = a[..., :3].min(-1)
    return np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)


def save_png(arr, name, scale=1):
    """arr: HxWx3/4 float, row0 = top. nearest-neighbour upscale."""
    a = np.asarray(arr, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, -1)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones(a.shape[:2] + (1,), np.float32)], -1)
    if scale != 1:
        a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w = a.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.ascontiguousarray(a[::-1]).ravel())
    p = os.path.join(DBG, name if name.endswith(".png") else name + ".png")
    img.filepath_raw = p
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return p


def flood_bg(near_white):
    """background = near-white pixels 4-connected to the image border (numpy propagation)."""
    bg = np.zeros_like(near_white)
    bg[0, :] = near_white[0, :]; bg[-1, :] = near_white[-1, :]
    bg[:, 0] = near_white[:, 0]; bg[:, -1] = near_white[:, -1]
    for _ in range(5000):
        g = bg.copy()
        g[1:, :] |= bg[:-1, :]; g[:-1, :] |= bg[1:, :]
        g[:, 1:] |= bg[:, :-1]; g[:, :-1] |= bg[:, 1:]
        g &= near_white
        if (g == bg).all():
            break
        bg = g
    return bg


def runs(mask1d):
    """list of (start, end_inclusive) runs of True."""
    m = np.concatenate([[False], mask1d, [False]]).astype(np.int8)
    d = np.diff(m)
    s = np.where(d == 1)[0]; e = np.where(d == -1)[0] - 1
    return list(zip(s.tolist(), e.tolist()))


def body_half_table(profile):
    """outer half-width of the lacquered BODY per image row: the throat (rows < 169) and mid band (287-321)
    are fittings wrapped around the body, so the body width under them is taken as the adjacent body width (97 px)."""
    import numpy as _np
    t = {int(r[0]): (r[2] - r[1] + 1) / 2 for r in profile}
    for y in list(t):
        if y < 169 or 287 <= y <= 321:
            t[y] = 48.5
    return t
