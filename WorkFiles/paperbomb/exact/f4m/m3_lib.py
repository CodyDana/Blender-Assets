# m3 independent (copied from m1, own code) measurer helpers (imports nothing from props_lib)
import bpy, numpy as np
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
REF = ROOT + "References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"
BC = ROOT + "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
FRONT = ROOT + "Renders/PaperBomb/paperbomb_front.png"
SCAN = ROOT + "Renders/PaperBomb/paperbomb_front_scan.png"
OUT = ROOT + "WorkFiles/paperbomb/exact/f4m/"

def load(path):
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = 'Non-Color'   # raw stored values
    w, h = im.size; c = im.channels
    a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1, :, :3].copy()
    bpy.data.images.remove(im)
    return a

def save(arr, path):
    arr = np.clip(arr, 0, 1).astype(np.float32)
    h, w = arr.shape[:2]
    if arr.ndim == 2: arr = np.stack([arr]*3, -1)
    rgba = np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)[::-1]
    im = bpy.data.images.new("o", w, h, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

def srgb2lin(c):
    return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)

def lab(rgb):
    l = srgb2lin(np.clip(rgb, 0, 1))
    M = np.array([[0.4124564, 0.3575761, 0.1804375],[0.2126729, 0.7151522, 0.0721750],[0.0193339, 0.1191920, 0.9503041]])
    xyz = l @ M.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216/24389, np.cbrt(xyz), (24389/27*xyz + 16)/116)
    L = 116*f[..., 1] - 16; a = 500*(f[..., 0]-f[..., 1]); b = 200*(f[..., 1]-f[..., 2])
    return np.stack([L, a, b], -1)

def de2000(l1, l2):
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2); Cb = (C1+C2)/2
    G = 0.5*(1-np.sqrt(Cb**7/(Cb**7+25.0**7)))
    a1p = (1+G)*a1; a2p = (1+G)*a2
    C1p = np.hypot(a1p, b1); C2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360; h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2-L1; dCp = C2p-C1p
    dh = h2p-h1p
    dh = np.where(C1p*C2p == 0, 0, np.where(dh > 180, dh-360, np.where(dh < -180, dh+360, dh)))
    dHp = 2*np.sqrt(C1p*C2p)*np.sin(np.radians(dh/2))
    Lbp = (L1+L2)/2; Cbp = (C1p+C2p)/2
    hs = h1p+h2p
    hbp = np.where(C1p*C2p == 0, hs, np.where(np.abs(h1p-h2p) <= 180, hs/2, np.where(hs < 360, (hs+360)/2, (hs-360)/2)))
    T = 1-0.17*np.cos(np.radians(hbp-30))+0.24*np.cos(np.radians(2*hbp))+0.32*np.cos(np.radians(3*hbp+6))-0.20*np.cos(np.radians(4*hbp-63))
    dth = 30*np.exp(-((hbp-275)/25)**2)
    Rc = 2*np.sqrt(Cbp**7/(Cbp**7+25.0**7))
    Sl = 1+0.015*(Lbp-50)**2/np.sqrt(20+(Lbp-50)**2)
    Sc = 1+0.045*Cbp; Sh = 1+0.015*Cbp*T
    Rt = -np.sin(np.radians(2*dth))*Rc
    return np.sqrt((dLp/Sl)**2+(dCp/Sc)**2+(dHp/Sh)**2+Rt*(dCp/Sc)*(dHp/Sh))

def bilinear(img, xs, ys):
    h, w = img.shape[:2]
    xs = np.clip(xs, 0, w-1.001); ys = np.clip(ys, 0, h-1.001)
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = xs-x0; fy = ys-y0
    if img.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return (img[y0, x0]*(1-fx)*(1-fy)+img[y0, x0+1]*fx*(1-fy)+img[y0+1, x0]*(1-fx)*fy+img[y0+1, x0+1]*fx*fy)

def box_blur(img, r):
    # separable box via cumulative sums, radius float -> integer window
    k = max(1, int(round(r)))
    if k <= 1: return img
    out = img
    for ax in (0, 1):
        pad = [(0, 0)]*img.ndim; pad[ax] = (k//2, k-1-k//2)
        p = np.pad(out, pad, mode='edge')
        c = np.cumsum(p, axis=ax, dtype=np.float64)
        c = np.concatenate([np.zeros_like(np.take(c, [0], axis=ax)), c], axis=ax)
        n = out.shape[ax]
        out = ((np.take(c, np.arange(k, k+n), axis=ax)-np.take(c, np.arange(0, n), axis=ax))/k).astype(np.float32)
    return out

def gauss_blur(img, s):
    if s <= 0.05: return img
    r = int(np.ceil(3*s)); x = np.arange(-r, r+1); k = np.exp(-x**2/(2*s*s)); k /= k.sum()
    out = img.astype(np.float32)
    for ax in (0, 1):
        pad = [(0, 0)]*img.ndim; pad[ax] = (r, r)
        p = np.pad(out, pad, mode='edge'); acc = np.zeros_like(out)
        for i, kv in enumerate(k):
            sl = [slice(None)]*img.ndim; sl[ax] = slice(i, i+out.shape[ax]); acc += kv*p[tuple(sl)]
        out = acc
    return out

def upscale_nn(a, f):
    return np.repeat(np.repeat(a, f, 0), f, 1)
