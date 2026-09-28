import bpy, numpy as np, json, math, os
BASE = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo"
PHOTO = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Happo.JPG"

def load_rgb():
    im = bpy.data.images.load(PHOTO)
    w,h = im.size
    buf = np.empty(w*h*4, dtype=np.float32)
    im.pixels.foreach_get(buf)
    a = buf.reshape(h,w,4)[:,:,:3]
    a = a[::-1].copy()          # row 0 = TOP
    return a, w, h

def lum(rgb):
    return 0.2126*rgb[:,:,0] + 0.7152*rgb[:,:,1] + 0.0722*rgb[:,:,2]

def bilinear(img, x, y):
    h,w = img.shape[:2]
    x = np.clip(x, 0, w-1.001); y = np.clip(y, 0, h-1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x-x0; fy = y-y0
    if img.ndim==2:
        return (img[y0,x0]*(1-fx)*(1-fy) + img[y0,x0+1]*fx*(1-fy)
                + img[y0+1,x0]*(1-fx)*fy + img[y0+1,x0+1]*fx*fy)
    out = np.zeros(x.shape+(img.shape[2],), dtype=np.float32)
    for c in range(img.shape[2]):
        ch = img[:,:,c]
        out[...,c] = (ch[y0,x0]*(1-fx)*(1-fy) + ch[y0,x0+1]*fx*(1-fy)
                      + ch[y0+1,x0]*(1-fx)*fy + ch[y0+1,x0+1]*fx*fy)
    return out

def save_png(arr, path):
    """arr: (h,w,3) float 0..1, row0=TOP"""
    h,w = arr.shape[:2]
    out = np.ones((h,w,4), dtype=np.float32); out[:,:,:3] = np.clip(arr,0,1)
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=True)
    img.pixels.foreach_set(out[::-1].reshape(-1))
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()

MAP = {'N_NE-T_NNE':'T1-N0','N_S-T_SSW':'T5-N5','N_E-T_ENE':'T0-N7','N_SW-T_WSW':'T4-N4',
       'N_SE-T_ESE':'T7-N6','N_W-T_WNW':'T3-N3','N_S-T_SSE':'T6-N5','N_NW-T_NNW':'T2-N2',
       'N_SW-T_SSW':'T5-N4','N_N-T_NNE':'T1-N1','N_W-T_WSW':'T4-N3','N_NE-T_ENE':'T0-N0',
       'N_NW-T_WNW':'T3-N2','N_E-T_ESE':'T7-N7','N_N-T_NNW':'T2-N1','N_SE-T_SSE':'T6-N6'}

def load_lines():
    A = json.load(open(BASE+"/radial/geom.json"))
    B = json.load(open(BASE+"/contour/b7_results.json"))
    la = {MAP[e['name']]: (np.array(e['c']), np.array(e['d']), e['rms'], e['name']) for e in A['edges']}
    lb = {k: (np.array(e['sil_line'][0]), np.array(e['sil_line'][1]), e['rms_px'], e['sil_kind'])
          for k,e in B['edges'].items()}
    return A,B,la,lb

def intersect(L1,L2):
    p1,d1 = L1[0],L1[1]; p2,d2 = L2[0],L2[1]
    M = np.array([[d1[0],-d2[0]],[d1[1],-d2[1]]])
    t = np.linalg.solve(M, p2-p1)
    return p1 + t[0]*d1

def edge_frame(p, d, C):
    """unit dir d, outward normal n"""
    d = d/np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    if n @ (p - C) < 0: n = -n
    return d, n
