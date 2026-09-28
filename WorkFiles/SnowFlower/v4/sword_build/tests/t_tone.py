import bpy, numpy as np, glob, os, json
def load(p):
    im=bpy.data.images.load(p); w,h=im.size
    a=np.array(im.pixels[:],np.float32).reshape(h,w,im.channels)[::-1].copy(); bpy.data.images.remove(im); return a
ref=load(r'C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower/SnowFlower_user_reference.png')
L=lambda a:a[...,:3]@np.array([.2126,.7152,.0722])
# regions relative to the front-view axis col (sheet 287.5 / render 150): rows, dx range
R={'grip':(70,240,-15,0),'guard':(285,315,-50,50),'blade_up':(380,650,-22,28),'blade_low':(700,1000,-20,20),'pommel':(15,40,-18,18)}
def stats(img,ax,mask=None):
    out={}
    for k,(r0,r1,d0,d1) in R.items():
        reg=img[r0:r1,int(ax+d0):int(ax+d1)]
        l=L(reg)
        if reg.shape[2]==4: l=l[reg[...,3]>0.5]
        else: l=l[l<0.93]
        out[k]=[round(float(np.percentile(l,q)),3) for q in (10,50,90)]
    return out
print('SHEET',stats(ref,287.5))
for d in sorted(glob.glob(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_build/expo/*')):
    print(os.path.basename(d),stats(load(d+'/ref_front.png'),150))
