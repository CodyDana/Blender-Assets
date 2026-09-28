import sys; sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import bpy, numpy as np
import sfv4_bake as BK
BK.setup_cycles()
low=bpy.data.objects['SF4_BAKE_grip']
hs=[o for o in bpy.data.collections['HIGH'].objects if o['sf4_part']=='grip']
print('highs',[ (h.name,len(h.data.polygons)) for h in hs])
import mathutils
print('low bbox', [tuple(round(x,4) for x in v) for v in (low.bound_box[0], low.bound_box[6])])
for h in hs: print(h.name,[tuple(round(x,4) for x in v) for v in (h.bound_box[0], h.bound_box[6])], h.hide_render, h.hide_get())
for o in bpy.data.collections['BAKE_LOW'].objects: o.hide_render = o is not low
for c in bpy.data.collections:
    if c.name.startswith('LOD'):
        for o in c.objects: o.hide_render=True
for cage in (1.6, 3.0):
    px=BK.bake_part(low,hs,'NORMAL',2048,cage,4)
    tris=BK.uv_triangles_px(low,2048,1.0); m=BK.rasterize(tris,2048)
    print('cage',cage,'std of normal inside',px[...,:3][m].std(axis=0), 'mean', px[...,:3][m].mean(axis=0))
