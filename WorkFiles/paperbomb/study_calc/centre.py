import bpy, numpy as np, os
REF=r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
for tag,fn in (("v1","paperbomb_guide.png"),("v2","paperbomb_guide_v2_real_glyphs.png")):
    img=bpy.data.images.load(os.path.join(REF,fn)); img.colorspace_settings.name="Non-Color"
    w,h=img.size; buf=np.empty(w*h*4,dtype=np.float32); img.pixels.foreach_get(buf)
    a=buf.reshape(h,w,4)[::-1].astype(np.float64); bpy.data.images.remove(img)
    rgb=a[:,:,:3]; L=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
    sat=rgb.max(axis=2)-rgb.min(axis=2)
    card=(sat>0.06)|(L<0.70)
    cx=np.nonzero(card.sum(axis=0)>0.05*h)[0]; ry=np.nonzero(card.sum(axis=1)>0.05*w)[0]
    x0,x1,y0,y1=int(cx.min()),int(cx.max()),int(ry.min()),int(ry.max()); CW,CH=x1-x0+1,y1-y0+1
    BK=((L<0.32)&(sat<0.14))[y0:y1+1,x0:x1+1]
    sub=BK[int(0.30*CH):int(0.70*CH), int(0.10*CW):int(0.92*CW)]
    colp=sub.sum(axis=0)/sub.shape[0]; rowp=sub.sum(axis=1)/sub.shape[1]
    print("==",tag,"CW",CW,"CH",CH)
    sig=[i for i,v in enumerate(colp) if v>0.02]
    print("  cols>2%%: x %.3f .. %.3f"%((0.10*CW+sig[0])/CW,(0.10*CW+sig[-1]+1)/CW))
    sig5=[i for i,v in enumerate(colp) if v>0.05]
    print("  cols>5%%: x %.3f .. %.3f"%((0.10*CW+sig5[0])/CW,(0.10*CW+sig5[-1]+1)/CW))
    sr=[i for i,v in enumerate(rowp) if v>0.02]
    print("  rows>2%%: y %.3f .. %.3f"%((0.30*CH+sr[0])/CH,(0.30*CH+sr[-1]+1)/CH))
    sr5=[i for i,v in enumerate(rowp) if v>0.05]
    print("  rows>5%%: y %.3f .. %.3f"%((0.30*CH+sr5[0])/CH,(0.30*CH+sr5[-1]+1)/CH))
    print("  ink frac of window %.3f"%(sub.mean()))
    # weighted centroid
    ys,xs=np.nonzero(sub)
    print("  centroid x %.3f y %.3f"%(((0.10*CW+xs.mean())/CW),((0.30*CH+ys.mean())/CH)))
