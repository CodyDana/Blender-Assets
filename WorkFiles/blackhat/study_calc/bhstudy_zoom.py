"""bhstudy_zoom.py - x4 gain-3 crops for reading details by eye (views/zoom_*.png). Viewing aid only."""
import sys, numpy as np, OpenImageIO as oiio
ROOT="C:/Users/Cody/Desktop/Blender_Projects"; OUT=ROOT+"/WorkFiles/blackhat/study_calc/views/"
px=oiio.ImageBuf(ROOT+"/References/BlackHat/blackhat_guide.png").get_pixels(oiio.FLOAT)[...,:3]
args=sys.argv[sys.argv.index("--")+1:]
name,x0,y0,x1,y1,k,g=args[0],*map(int,args[1:6]),float(args[6])
c=np.clip(px[y0:y1,x0:x1]*g,0,1); c=np.repeat(np.repeat(c,k,0),k,1).astype(np.float32)
# grid every 10 source px
for i in range(0,c.shape[0],10*k): c[i,:]=(1,0,0) if ((i//k+y0)%50==0) else c[i,:]*0.6
for j in range(0,c.shape[1],10*k): c[:,j]=(1,0,0) if ((j//k+x0)%50==0) else c[:,j]*0.6
h,w=c.shape[:2]; o=oiio.ImageBuf(oiio.ImageSpec(w,h,3,oiio.UINT8)); o.set_pixels(oiio.ROI(0,w,0,h,0,1,0,3),c); o.write(OUT+name)
