import numpy as np, sys, os
sys.path.insert(0,'.')
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64)
H,W,_=rgb.shape
A=np.load(P+"radial/mask_final.npy"); B=np.load(P+"contour/mask_refined.npy")
def boundary(M):
    b=np.zeros_like(M)
    b[1:-1,1:-1]=M[1:-1,1:-1]&~(M[:-2,1:-1]&M[2:,1:-1]&M[1:-1,:-2]&M[1:-1,2:])
    return b
bA=boundary(A); bB=boundary(B)
import bpy
def save(arr,path):
    h,w,_=arr.shape
    img=bpy.data.images.new(os.path.basename(path),width=w,height=h,alpha=False)
    buf=np.zeros((h,w,4),np.float32); buf[...,:3]=arr; buf[...,3]=1.0
    img.pixels.foreach_set(buf[::-1].ravel())
    img.filepath_raw=path; img.file_format='PNG'; img.save()
    bpy.data.images.remove(img)
def crop(name,x0,y0,x1,y1,zoom=4,boost=True):
    sub=rgb[y0:y1,x0:x1].copy()
    if boost:
        lo=np.percentile(sub,1); hi=np.percentile(sub,99)
        sub=np.clip((sub-lo)/(hi-lo+1e-9),0,1)
    ba=bA[y0:y1,x0:x1]; bb=bB[y0:y1,x0:x1]
    sub[ba]=[0,1,0]; sub[bb&~ba]=[1,0,1]
    out=np.repeat(np.repeat(sub,zoom,0),zoom,1)
    save(out.astype(np.float32),os.path.abspath(name))
    print(name,out.shape)
crop("z_rightneck.png",840,540,980,760,4)
crop("z_topneck.png",600,400,800,540,4)
crop("z_leftneck.png",410,560,550,770,4)
crop("z_botneck.png",620,790,800,930,4)
