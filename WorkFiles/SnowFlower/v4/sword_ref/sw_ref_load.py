"""Dump the sword reference sheet as a numpy array (top-down rows) for fast analysis outside Blender."""
import bpy, numpy as np
im=bpy.data.images.load(r'C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower/SnowFlower_user_reference.png')
w,h=im.size
a=np.array(im.pixels[:],np.float32).reshape(h,w,im.channels)[::-1].copy()
np.save(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_ref/sw_ref.npy',a)
print('SAVED',a.shape)
