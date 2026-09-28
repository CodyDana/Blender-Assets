import bpy, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from imgutil import load
sc=bpy.context.scene; set_visible(True, False)
make_camera((0,-0.02,1.2),0,0,85,3.0)
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
bg=next(n for n in w.node_tree.nodes if n.type=="BACKGROUND"); bg.inputs[0].default_value=(1,1,1,1); bg.inputs[1].default_value=1.0
sc.render.engine="CYCLES"; sc.cycles.samples=16; prefs=bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type="OPTIX"; prefs.get_devices(); [setattr(d,"use",d.type=="OPTIX") for d in prefs.devices]; sc.cycles.device="GPU"
sc.render.resolution_x=100; sc.render.resolution_y=100
sc.view_settings.view_transform="Standard"
m=bpy.data.materials['GAME_M_BlackCloak_UV0']; bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
print("BSDF inputs", [(i.name, (tuple(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value)) for i in bs.inputs if not i.is_linked and hasattr(i,'default_value')])
def r(tag):
    p=D+"logs/_dbg_%s.png"%tag; sc.render.filepath=p; bpy.ops.render.render(write_still=True)
    a=load(p); print("DBG",tag, a[40:60,40:60,:3].mean(), a[40:60,40:60,3].mean())
r("asis")
L=m.node_tree.links
for l in list(L):
    if l.to_socket == bs.inputs['Base Color']: L.remove(l)
bs.inputs['Base Color'].default_value=(0.01,0.01,0.01,1)
r("const001")
for l in list(L):
    if l.to_socket == bs.inputs['Normal']: L.remove(l)
r("nonormal")
