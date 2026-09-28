import bpy, numpy as np, time
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.render.engine='CYCLES'
try:
    pr=bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type='OPTIX'; pr.get_devices()
    for d in pr.devices: d.use=(d.type=='OPTIX')
    sc.cycles.device='GPU'
except Exception as e: print('GPU fail',e)
bpy.ops.mesh.primitive_plane_add(size=1); low=bpy.context.object; low.name='low'
bpy.ops.uv.smart_project() if False else None
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2,location=(0,0,-0.1)); hs=bpy.context.object; hs.name='high_sphere'
bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,-0.001)); hp=bpy.context.object; hp.name='high_plane'
m=bpy.data.materials.new('hm'); m.use_nodes=True; nt=m.node_tree
bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
wave=nt.nodes.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value=20
bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=1
nt.links.new(wave.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
hp.data.materials.append(m); hs.data.materials.append(m)
img=bpy.data.images.new('t',256,256,is_data=True)
lm=bpy.data.materials.new('lm'); lm.use_nodes=True; tn=lm.node_tree.nodes.new('ShaderNodeTexImage'); tn.image=img; lm.node_tree.nodes.active=tn
low.data.materials.append(lm)
for o in bpy.data.objects: o.select_set(False)
hs.select_set(True); hp.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active=low
sc.cycles.samples=4
t=time.time()
r=bpy.ops.object.bake(type='NORMAL',use_selected_to_active=True,cage_extrusion=0.15,max_ray_distance=0.3,margin=4,margin_type='EXTEND',use_clear=True)
print('bake',r,time.time()-t)
a=np.array(img.pixels[:]).reshape(256,256,4)
print('center',a[128,128,:3],'edge',a[128,10,:3],'std edge rows',a[100:110,5:40,0].std())
# AO with low invisible
low.visible_diffuse=False; low.visible_glossy=False; low.visible_shadow=False; low.visible_transmission=False
sc.world=bpy.data.worlds.new('w'); sc.world.light_settings.distance=0.05
r=bpy.ops.object.bake(type='AO',use_selected_to_active=True,cage_extrusion=0.15,max_ray_distance=0.3,margin=4,use_clear=True)
a=np.array(img.pixels[:]).reshape(256,256,4)
print('AO flat',a[128,10,:3],'near sphere foot', a[128,60,:3])
sc.world.light_settings.distance=0.1; sc.cycles.samples=64
for vis in (False,True):
    low.visible_diffuse=vis; low.visible_glossy=vis; low.visible_shadow=vis; low.visible_transmission=vis
    r=bpy.ops.object.bake(type='AO',use_selected_to_active=True,cage_extrusion=0.15,max_ray_distance=0.3,margin=4,use_clear=True)
    a=np.array(img.pixels[:]).reshape(256,256,4)
    print('vis',vis,'AO row128 px', [round(float(a[128,i,0]),3) for i in (10,60,80,84,88,92,120)])
