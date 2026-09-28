import numpy as np
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
a=np.load(P+"contour/juji_rgb.npy", mmap_mode='r')
print("rgb shape",a.shape,a.dtype,float(a.min()),float(a.max()))
m=np.load(P+"radial/mask_final.npy", mmap_mode='r')
print("maskA",m.shape,m.dtype, m.sum())
mb=np.load(P+"contour/mask_refined.npy", mmap_mode='r')
print("maskB",mb.shape,mb.dtype, np.asarray(mb).sum())
# orientation: top row of mask A should have ~34 px
A=np.asarray(m).astype(bool); B=np.asarray(mb).astype(bool)
print("A row0 sum",A[0].sum(),"A last row",A[-1].sum())
print("B row0 sum",B[0].sum(),"B last row",B[-1].sum())
# sample corner colour
r=np.asarray(a[0,0]),np.asarray(a[-1,-1])
print("rgb[0,0]",r[0],"rgb[-1,-1]",r[1])
print("IoU A,B", (A&B).sum()/ (A|B).sum())
print("areaA",A.sum(),"areaB",B.sum())
