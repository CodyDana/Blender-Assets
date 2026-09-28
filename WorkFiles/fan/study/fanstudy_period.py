import bpy, numpy as np
def load(p):
    im = bpy.data.images.load(p); w,h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h,w,4)[::-1]
R="C:/Users/Cody/Desktop/Blender_Projects/References/Fan/"
for name,(cx,cy) in {"fan2":(398,546),"fan1":(391,600)}.items():
    a = load(R+name+".png"); L = a[...,:3].mean(-1)
    th = np.linspace(np.pi, 0, 3600)
    print("==", name)
    # extent of dark (fan) along the arc at each radius
    for r in range(40, 400, 20):
        X = np.clip((cx + r*np.cos(th)).round().astype(int),0,799); Y=np.clip((cy - r*np.sin(th)).round().astype(int),0,799)
        p = L[Y,X]; dark = p < 0.6
        if dark.sum()<10: print(r,"none"); continue
        idx = np.where(dark)[0]; a0,a1 = np.degrees(np.pi - th[idx[0]]), np.degrees(np.pi - th[idx[-1]])
        seg = p[idx[0]:idx[-1]]
        s = seg - np.convolve(seg, np.ones(61)/61, 'same')
        s = s[40:-40]
        f = np.abs(np.fft.rfft(s*np.hanning(len(s))))
        n = len(s); freqs = np.arange(len(f))
        # restrict cycles to 10..80 across the span
        span_deg = (a1-a0)*(len(s)/len(seg))
        lo,hi = 10,90
        k = lo + np.argmax(f[lo:hi]); top = sorted(range(lo,hi), key=lambda i:-f[i])[:3]
        print(f"r={r:3d} dark {a0:6.1f}..{a1:6.1f} deg (span {a1-a0:5.1f}) cycles over span: {[round(t*(a1-a0)/span_deg,1) for t in top]}")
