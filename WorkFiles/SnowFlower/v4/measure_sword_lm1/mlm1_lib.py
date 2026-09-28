import bpy, numpy as np, zlib, struct
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1/"
BG = 0.996
def load(path):
    im = bpy.data.images.load(path); w,h = im.size
    a = np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4)[::-1]
    bpy.data.images.remove(im); return a
def over(a, bgc=(BG,BG,BG)):
    return a[...,:3]*a[...,3:4] + np.array(bgc,np.float32)*(1-a[...,3:4])
def savepng(path, arr):
    arr = (np.clip(arr[...,:3],0,1)*255+0.5).astype(np.uint8)
    h,w,c = arr.shape
    raw = b''.join(b'\x00'+arr[y].tobytes() for y in range(h))
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def _box(x, k, axis):
    if k <= 1: return x
    x = np.moveaxis(x, axis, 0)
    pad = np.concatenate([np.repeat(x[:1], k//2, 0), x, np.repeat(x[-1:], k - k//2, 0)], 0)
    c = np.cumsum(pad, 0, dtype=np.float64)
    c = np.concatenate([np.zeros_like(c[:1]), c], 0)
    y = (c[k:k+x.shape[0]] - c[:x.shape[0]]) / k
    return np.moveaxis(y.astype(np.float32), 0, axis)
def resize(a, nh, nw):
    def ax(x, n, axis):
        m = x.shape[axis]
        if n < m: x = _box(x, int(round(m/n)), axis)
        src = (np.arange(n)+0.5)*m/n-0.5
        i0 = np.clip(np.floor(src).astype(int),0,m-1); i1 = np.clip(i0+1,0,m-1); t = np.clip(src-np.floor(src),0,1)
        t[src<0]=0
        shp = [1]*x.ndim; shp[axis]=n; t = t.reshape(shp).astype(np.float32)
        return np.take(x,i0,axis)*(1-t)+np.take(x,i1,axis)*t
    return ax(ax(a,nh,0),nw,1)
