"""Blade band comparison, reference front view vs rev-3 front render, rows 320-1216, 2x. blender -b --factory-startup --python compare_blade.py"""
import bpy, numpy as np
from pathlib import Path
ROOT=Path(r'C:/Users/Cody/Desktop/Blender_Projects');AUD=ROOT/'WorkFiles/SnowFlower/v4/audit'
def load(p):
    im=bpy.data.images.load(str(p));w,h=im.size;a=np.array(im.pixels[:],np.float32).reshape(h,w,im.channels)[::-1].copy();bpy.data.images.remove(im)
    if a.shape[2]==3:a=np.concatenate([a,np.ones((h,w,1),np.float32)],2)
    return a
def save(a,p):
    h,w=a.shape[:2];im=bpy.data.images.new(p.stem,w,h,alpha=True);im.pixels.foreach_set(a[::-1].ravel());im.filepath_raw=str(p);im.file_format='PNG';im.save();bpy.data.images.remove(im)
ref=load(ROOT/'References/SnowFlower/SnowFlower_user_reference.png');rv=load(AUD/'renders/rev3_front_1x.png')
al=rv[...,3:4];rv=np.concatenate([rv[...,:3]*al+.996*(1-al),np.ones_like(al)],2)
up=lambda a:np.repeat(np.repeat(a,2,0),2,1)
# split blade into two halves side by side for legibility
parts=[]
for r0,r1 in ((320,770),(770,1220)):
    parts+= [up(ref[r0:r1,250:330]), up(rv[r0:r1,110:190]), np.full((900,10,4),1,np.float32)]
save(np.concatenate(parts[:-1],1),AUD/'compare_blade_ref_rev3_2x.png');print('DONE')
