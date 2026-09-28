"""Crop a region of the reference, upscale (nearest) and overlay a labelled coordinate grid.
usage: python metro_crop.py x0 y0 x1 y1 scale step out.png [overlay.json]
Grid lines every <step> ref px (cyan), every 5th step red and labelled with its REFERENCE pixel coordinate.
Optional overlay json: {"polylines": [{"pts": [[x,y],...], "color": [r,g,b], "closed": bool}], "points": [[x,y],...]}"""
import sys, json, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlowerHeels")
import metro_png as png
SP = r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad"
REF_NPY = SP + "/metro_ref.npy"
FONT = {'0':"111101101101111",'1':"010110010010111",'2':"111001111100111",'3':"111001111001111",'4':"101101111001001",
        '5':"111100111001111",'6':"111100111101111",'7':"111001010010010",'8':"111101111101111",'9':"111101111001111"}
def text(img, s, x, y, col, k=2):
    H, W = img.shape[:2]
    for i, ch in enumerate(s):
        g = FONT[ch]
        for r in range(5):
            for c in range(3):
                if g[r*3+c] == '1':
                    yy, xx = y + r*k, x + (i*4 + c)*k
                    if 0 <= yy and yy+k <= H and 0 <= xx and xx+k <= W:
                        img[yy:yy+k, xx:xx+k] = col
def crop(x0, y0, x1, y1, s, step, out, a=None, overlay=None):
    if a is None: a = np.load(REF_NPY)
    c = a[y0:y1, x0:x1].copy()
    c = np.repeat(np.repeat(c, s, 0), s, 1)
    for gx in range((x0//step+1)*step, x1, step):
        major = gx % (step*5) == 0; col = np.array((1, 0, 0) if major else (0, 0.7, 1))
        X = (gx-x0)*s; c[:, X] = c[:, X]*0.4 + col*0.6
        if major:
            for yy in range(2, c.shape[0], 400): 
                c[yy:yy+12, X+2:X+2+len(str(gx))*8] = 1; text(c, str(gx), X+2, yy+1, (1, 0, 0))
    for gy in range((y0//step+1)*step, y1, step):
        major = gy % (step*5) == 0; col = np.array((1, 0, 0) if major else (0, 0.7, 1))
        Y = (gy-y0)*s; c[Y, :] = c[Y, :]*0.4 + col*0.6
        if major:
            for xx in range(2, c.shape[1], 400):
                c[Y+2:Y+14, xx:xx+len(str(gy))*8] = 1; text(c, str(gy), xx, Y+3, (0, 0, 1))
    if overlay:
        for pl in overlay.get("polylines", []):
            pts = [((p[0]-x0+0.5)*s, (p[1]-y0+0.5)*s) for p in pl["pts"]]
            col = pl.get("color", [1, 0, 1]); P = pts + ([pts[0]] if pl.get("closed") else [])
            for (px, py), (qx, qy) in zip(P[:-1], P[1:]):
                n = int(max(abs(qx-px), abs(qy-py))) + 1
                for t in np.linspace(0, 1, n):
                    xx, yy = int(px + (qx-px)*t), int(py + (qy-py)*t)
                    if 0 <= yy < c.shape[0] and 0 <= xx < c.shape[1]: c[yy, xx] = col
        for p in overlay.get("points", []):
            X, Y = int((p[0]-x0+0.5)*s), int((p[1]-y0+0.5)*s)
            if 3 <= X < c.shape[1]-4 and 3 <= Y < c.shape[0]-4:
                c[Y-3:Y+4, X-3:X+4] = (1, 1, 0)
    png.write(out, c)
if __name__ == "__main__":
    x0, y0, x1, y1, s, step = map(int, sys.argv[1:7])
    ov = json.load(open(sys.argv[8])) if len(sys.argv) > 8 else None
    crop(x0, y0, x1, y1, s, step, sys.argv[7], overlay=ov)
