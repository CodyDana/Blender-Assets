import bpy, numpy as np, os
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float32); H,W,_=rgb.shape
def save(a,path):
    h,w,_=a.shape
    img=bpy.data.images.new(os.path.basename(path),width=w,height=h,alpha=False)
    buf=np.zeros((h,w,4),np.float32); buf[...,:3]=np.clip(a,0,1); buf[...,3]=1
    img.pixels.foreach_set(buf[::-1].ravel()); img.filepath_raw=path; img.file_format='PNG'; img.save()
    bpy.data.images.remove(img); print("wrote",path)
def line(im,p0,p1,col,r=1.2):
    n=int(max(abs(p1[0]-p0[0]),abs(p1[1]-p0[1]))*2)+2
    for t in np.linspace(0,1,n):
        x=p0[0]+(p1[0]-p0[0])*t; y=p0[1]+(p1[1]-p0[1])*t
        x0=int(round(x)); y0=int(round(y)); k=int(np.ceil(r))
        for dy in range(-k,k+1):
            for dx in range(-k,k+1):
                if dx*dx+dy*dy>r*r+0.3: continue
                xi,yi=x0+dx,y0+dy
                if 0<=xi<W and 0<=yi<H: im[yi,xi]=col
def poly(im,pts,col,r=1.2,close=True):
    n=len(pts)
    for i in range(n-(0 if close else 1)):
        line(im,pts[i],pts[(i+1)%n],col,r)
def marker(im,p,col,s=7):
    x0,y0=int(round(p[0])),int(round(p[1]))
    for dy in range(-s,s+1):
        for dx in range(-s,s+1):
            if abs(dx)+abs(dy)<=s and 0<=x0+dx<W and 0<=y0+dy<H: im[y0+dy,x0+dx]=col

C=np.array([694.10,651.11]); SPAN=1325.0
recon=np.load(P+"contour/contour_refined.npy")   # (N,2) x,y  validated by reconcile chr50

# ---------- overlay 1: reconciled outline ----------
im=rgb.copy()*0.78+0.11
poly(im,recon,(0.0,1.0,0.25),1.6)
arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
Rt={'right':660.3,'top':663.0,'left':664.5,'bottom':662.0}     # reconciled tip radii (see notes)
neckS={'right':183.,'top':197.,'left':198.,'bottom':218.}
neckW={'right':83.9,'top':82.1,'left':83.2,'bottom':79.2}
maxS={'right':447.,'top':435.,'left':446.,'bottom':483.}
maxW={'right':178.1,'top':173.9,'left':181.5,'bottom':171.3}
for k,th in arms.items():
    t=np.radians(th); d=np.array([np.cos(t),-np.sin(t)]); n=np.array([-d[1],d[0]])
    line(im,C,C+Rt[k]*d,(1,1,1),0.7)
    marker(im,C+Rt[k]*d,(1,0.1,0.1),6)
    p=C+neckS[k]*d; line(im,p-n*neckW[k]/2,p+n*neckW[k]/2,(0.1,0.7,1.0),1.6)
    p=C+maxS[k]*d;  line(im,p-n*maxW[k]/2,p+n*maxW[k]/2,(1.0,0.55,0.0),1.6)
for th in (53.4,135.8,227.6,315.0):
    t=np.radians(th); marker(im,C+103.7*np.array([np.cos(t),-np.sin(t)]),(1.0,1.0,0.0),5)
marker(im,C,(1,0,1),7)
save(im,OUT+"juji_overlay_reconciled.png")

# ---------- overlay 2: built outline, spans matched ----------
outer=np.load("built_loop0.npy"); hole=np.load("built_loop1.npy")
# close the outer loop ordering: sort is already a traversal
sc=SPAN/0.097          # px per metre, tip-to-tip 97 mm -> SPAN px
rot=np.radians(1.70)   # piece sits 1.70 deg CCW (math convention) in the scan
def place(pts):
    q=pts*sc
    ca,sa=np.cos(rot),np.sin(rot)
    x= ca*q[:,0]-sa*q[:,1]; y= sa*q[:,0]+ca*q[:,1]
    return np.stack([C[0]+x, C[1]-y],1)     # flip y for image coords
bo=place(outer); bh=place(hole)
im2=rgb.copy()*0.72+0.14
poly(im2,recon,(0.0,0.95,0.25),1.5)
poly(im2,bo,(1.0,0.15,0.9),2.0)
poly(im2,bh,(1.0,0.15,0.9),2.0)
save(im2,OUT+"juji_overlay_built_vs_photo.png")
# zoom of the junction for overlay 2
z=im2[380:930,420:980]; z=np.repeat(np.repeat(z,2,0),2,1)
save(z,OUT+"juji_overlay_built_junction_zoom.png")
