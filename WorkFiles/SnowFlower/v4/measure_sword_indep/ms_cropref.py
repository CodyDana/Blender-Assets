import bpy, numpy as np, zlib, struct, sys
a = np.load("ref_rgb.npy")
def savepng(path, arr):
    arr = (np.clip(arr,0,1)*255+0.5).astype(np.uint8)
    h,w,c = arr.shape
    raw = b''.join(b'\x00'+arr[y].tobytes() for y in range(h))
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    ct = {3:2,4:6}[c]
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,ct,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def up(x,k): return np.repeat(np.repeat(x,k,0),k,1)
savepng("look_ref_guard.png", up(a[0:530,800:1222],2))
savepng("look_ref_blade.png", up(a[560:870,800:1222],2))
savepng("look_ref_pommel.png", up(a[870:1230,800:1222],2))
savepng("look_ref_hilt_front.png", up(a[0:360,200:400],3))
