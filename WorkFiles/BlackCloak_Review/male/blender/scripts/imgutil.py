import bpy, numpy as np
def load(p):
    im=bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name='Non-Color'
    w,h=im.size; a=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,im.channels)[::-1]
    # pixels are linear for sRGB images? bpy returns values in image colorspace float -> for 8-bit png they are sRGB-encoded 0..1
    bpy.data.images.remove(im)
    if a.shape[2]==3: a=np.concatenate([a,np.ones_like(a[...,:1])],2)
    return a
def save(a,p):
    h,w=a.shape[:2]
    if a.ndim==2: a=np.stack([a,a,a],2)
    if a.shape[2]==3: a=np.concatenate([a,np.ones((h,w,1),np.float32)],2)
    im=bpy.data.images.new("tmp_out",w,h,alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(a[::-1]).astype(np.float32).ravel())
    im.filepath_raw=p; im.file_format='PNG'; im.save()
    bpy.data.images.remove(im)
def lum(a): return 0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]
