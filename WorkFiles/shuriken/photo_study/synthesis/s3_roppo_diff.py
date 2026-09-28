import bpy, numpy as np, sys, math
sys.argv=[sys.argv[0]]
exec(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/synthesis/s2_synthesis.py").read().split("# ================================================================== JUJI")[0])
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
im = load_rgb(IMG+"Roppo.JPG"); H,W,_=im.shape
Ra=49.0; Sref=Ra/0.514; Rhub=0.2440*Sref; Rbore=0.1140*Sref; ha=math.radians(25.1/2)
tt=Ra*math.cos(ha)-math.sqrt(Rhub**2-(Ra*math.sin(ha))**2); xr,yr=Ra-tt*math.cos(ha),tt*math.sin(ha); beta=math.degrees(math.atan2(yr,xr))
ro=[]
for k in range(6):
    ph=60*k; ro.append(rot(np.array([[xr,-yr],[Ra,0.0],[xr,yr]]),ph))
    a=np.radians(np.linspace(ph+beta,ph+60-beta,90))[1:-1]; ro.append(np.stack([Rhub*np.cos(a),Rhub*np.sin(a)],1))
ro=np.vstack(ro)
cen=np.array([629.0,528.3]); sc=604.978/Ra
M=raster([place(ro,cen,sc,1.595),place(circle(0,0,Rbore),cen,sc,0)],W,H)
for nm,path in (("B",P+"roppo/contour/roppo_mask.png"),("A65",P+"roppo/radial/mask_T65.png"),("A50",P+"roppo/radial/mask_T50.png")):
    mk=load_rgb(path)[...,0]>0.75
    print(nm, "IoU", iou(M,mk), "model px", M.sum(), "mask px", mk.sum(), "model-only", (M&~mk).sum(), "mask-only", (mk&~M).sum())
mk=load_rgb(P+"roppo/contour/roppo_mask.png")[...,0]>0.75
o=im*0.5+0.25
o[M&~mk]=(1,0,0); o[mk&~M]=(0,1,0)
save_png(o,P+"synthesis/roppo_diff_check.png")
