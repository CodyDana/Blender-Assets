"""Bake the procedural nunchucks into a portable 4K PBR asset."""
from pathlib import Path
import bpy, bmesh, sys, json, time
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'WorkFiles/BlackNunchucks'
TEX = ROOT/'Textures/BlackNunchucks'
REND = ROOT/'Renders/BlackNunchucks'
sys.path[:0] = [str(ROOT/'Scripts'), str(ROOT/'Scripts/BlackNunchucks')]
from pipeline.lock import assert_owner
from pipeline.textures import image_pixels, write_png, load_data_image
from materials import create_materials
assert_owner('BlackNunchucks', 'codex')
source = WORK/'BlackNunchucks_resolved.blend'
if not source.is_file(): source = WORK/'BlackNunchucks_procedural.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
create_materials()
s = bpy.context.scene
asset = bpy.data.collections['BLACK_NUNCHUCKS']
parts = [o for o in asset.objects if o.type == 'MESH']
lod0 = [o for o in parts if o['lod_level'] == 0]
rig = bpy.data.objects['Nunchucks_Rig']
size = 4096

def select(objects, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[0]

def triangulate(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='FIXED')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()

# Lock metric procedural coordinates to the original component axes before join.
temp = bpy.data.collections.new('__BAKE_TEMP'); s.collection.children.link(temp)
highparts = []
for source in lod0:
    ob = source.copy(); ob.data = source.data.copy(); temp.objects.link(ob)
    ob.name = '__HIGH_' + source['part_id']; ob.hide_set(False); ob.hide_render = False
    ob.modifiers.clear(); triangulate(ob)
    coords = bpy.data.objects.new('__COORD_' + source['part_id'], None)
    temp.objects.link(coords); coords.matrix_world = source.matrix_world.copy()
    mat = source.data.materials[0].copy(); mat.name = '__SOURCE_' + source['part_id']
    mat.node_tree.nodes['Metric Object Coordinates'].object = coords
    ob.data.materials.clear(); ob.data.materials.append(mat)
    highparts.append(ob)
select(highparts)
bpy.ops.object.join(); high = bpy.context.object; high.name = '__BAKE_HIGH'
select([high]); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
target = high.copy(); target.data = high.data.copy(); temp.objects.link(target)
target.name = '__BAKE_TARGET'; target.hide_render = False
target.data.materials.clear()
targetmat = bpy.data.materials.new('__BAKE_TARGET_MATERIAL'); targetmat.use_nodes = True
target.data.materials.append(targetmat)
for p in target.data.polygons: p.material_index = 0
for o in list(s.objects):
    if o not in (high, target): o.hide_render = True
node = targetmat.node_tree.nodes.new('ShaderNodeTexImage')
targetmat.node_tree.nodes.active = node
target.data.uv_layers.active_index = 0
target.data.uv_layers[0].active_render = True

s.render.engine = 'CYCLES'; s.cycles.samples = 32
s.render.bake.target = 'IMAGE_TEXTURES'; s.render.bake.margin = 32
s.render.bake.margin_type = 'EXTEND'; s.render.bake.use_selected_to_active = True
s.render.bake.use_cage = True; s.render.bake.cage_extrusion = .00004
s.render.bake.max_ray_distance = .00012
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for d in prefs.devices: d.use = d.type != 'CPU'
s.cycles.device = 'GPU'
stats = {'resolution': size, 'margin_px':32, 'method':'Cycles selected-to-active with extruded cage',
         'cage_extrusion_m':.00004, 'ao_samples':32, 'maps':{}}

def source_pass(channel=None):
    for m in high.data.materials:
        nt=m.node_tree; shader=nt.nodes['PBR Source']; out=nt.nodes['Material Output']
        if channel is None:
            nt.links.new(shader.outputs['BSDF'], out.inputs['Surface']); continue
        em = nt.nodes.get('__BAKE_EMISSION') or nt.nodes.new('ShaderNodeEmission')
        em.name='__BAKE_EMISSION'
        for link in list(em.inputs['Color'].links): nt.links.remove(link)
        inp=shader.inputs[channel]
        if inp.is_linked: nt.links.new(inp.links[0].from_socket,em.inputs['Color'])
        else:
            val=inp.default_value
            em.inputs['Color'].default_value = tuple(val) if hasattr(val,'__len__') else (val,val,val,1)
        nt.links.new(em.outputs[0],out.inputs['Surface'])

def bake(name, bake_type, channel=None):
    print('BAKE_START',name,flush=True); begin=time.time()
    source_pass(channel)
    im=bpy.data.images.new('__WORK_'+name,width=size,height=size,alpha=False,float_buffer=True,is_data=True)
    im.colorspace_settings.name='Non-Color'; node.image=im
    select([high,target],target)
    bpy.ops.object.bake(type=bake_type,margin=32,margin_type='EXTEND',use_selected_to_active=True,
                        use_clear=True,use_cage=True,cage_extrusion=.00004,max_ray_distance=.00012,
                        normal_space='TANGENT')
    arr=image_pixels(im); arr[:,:,3]=1
    bpy.data.images.remove(im)
    stats['maps'][name]={'seconds':round(time.time()-begin,2),'min':float(arr[:,:,:3].min()),'max':float(arr[:,:,:3].max())}
    print('BAKE_FINISHED',name,stats['maps'][name],flush=True)
    return arr

base=bake('basecolor','EMIT','Base Color')
rgb=base[:,:,:3]
base[:,:,:3]=np.where(rgb<=.0031308,12.92*rgb,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
write_png(base,TEX/'blacknunchucks_basecolor.png'); del base,rgb
normal=bake('normal','NORMAL')
# Unused texels are neutral normals; covered regions and extended margins keep the bake.
unused=np.all(normal[:,:,:3] == 0,axis=2); normal[unused,:3]=(.5,.5,1)
write_png(normal,TEX/'blacknunchucks_normal_opengl.png')
normal[:,:,1]=1-normal[:,:,1]
write_png(normal,TEX/'blacknunchucks_normal.png'); del normal,unused
rough=bake('roughness','EMIT','Roughness')[:,:,0].copy()
metal=bake('metallic','EMIT','Metallic')[:,:,0].copy()
ao=bake('ao','AO')
covered=rough>0
stats['ao_covered_range']=[float(ao[:,:,0][covered].min()),float(ao[:,:,0][covered].max())]
assert stats['ao_covered_range'][1]-stats['ao_covered_range'][0]>.01, 'AO must contain real occlusion'
write_png(ao,TEX/'blacknunchucks_ao.png')
ao[:,:,1]=rough; ao[:,:,2]=metal
write_png(ao,TEX/'blacknunchucks_orm.png'); del ao,rough,metal,covered

# Remove temporary baking meshes and coordinate anchors; preserve original rig.
for o in list(temp.objects): bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(temp)
mat=bpy.data.materials.new('M_BlackNunchucks_Baked'); mat.use_nodes=True
nt=mat.node_tree; nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputMaterial'); out.location=(740,0)
p=nt.nodes.new('ShaderNodeBsdfPrincipled'); p.location=(460,0)
nt.links.new(p.outputs['BSDF'],out.inputs['Surface'])
def texture(suffix,loc,data=True):
    path=TEX/('blacknunchucks_'+suffix+'.png')
    im=load_data_image(path) if data else bpy.data.images.load(str(path),check_existing=True)
    im.colorspace_settings.name='Non-Color' if data else 'sRGB'
    im.name='T_BlackNunchucks_'+{'basecolor':'BaseColor','orm':'ORM','normal_opengl':'NormalGL'}[suffix]
    im.pack()
    im.filepath=str(path)
    n=nt.nodes.new('ShaderNodeTexImage'); n.image=im; n.location=loc; n.label=suffix
    return n
bc=texture('basecolor',(-800,350),False); nt.links.new(bc.outputs['Color'],p.inputs['Base Color'])
orm=texture('orm',(-800,-50)); sep=nt.nodes.new('ShaderNodeSeparateColor'); sep.location=(-500,-50)
nt.links.new(orm.outputs['Color'],sep.inputs[0]); nt.links.new(sep.outputs['Green'],p.inputs['Roughness']); nt.links.new(sep.outputs['Blue'],p.inputs['Metallic'])
normal=texture('normal_opengl',(-800,-400)); nm=nt.nodes.new('ShaderNodeNormalMap');nm.location=(-200,-350)
nt.links.new(normal.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
# glTF's exporter reads this named auxiliary occlusion socket.
from io_scene_gltf2.blender.com.material_helpers import create_settings_group
group=create_settings_group('glTF Material Output')
gn=nt.nodes.new('ShaderNodeGroup');gn.node_tree=group;gn.location=(80,-180)
nt.links.new(sep.outputs['Red'],gn.inputs['Occlusion'])
mat['normal_convention']='OpenGL in Blender/glTF; DirectX companion blacknunchucks_normal.png for Unreal'
mat['ao_source']='Cycles baked geometry occlusion in ORM red'
for ob in parts:
    select([ob]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    triangulate(ob); ob.data.materials.clear(); ob.data.materials.append(mat)
    for face in ob.data.polygons: face.material_index=0
    ob.hide_render=ob['lod_level']!=0; ob.hide_set(ob['lod_level']!=0)
for o in bpy.data.collections['STUDIO_ExcludeFromExport'].objects: o.hide_render=False
rig.hide_set(True);rig.hide_render=True
# Broad reflection bands and neutral fill reproduce the photographed satin finish.
bpy.data.lights['Key_Softbox'].size=.26; bpy.data.lights['Key_Softbox'].energy=1.10
bpy.data.lights['Right_Softbox'].size=.19; bpy.data.lights['Right_Softbox'].energy=.75
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.28
floor=bpy.data.objects['StudioFloor']
floor.data.materials[0].node_tree.nodes.get('Ambient Occlusion').inputs['Distance'].default_value=.010
s.cycles.samples=96; s.cycles.use_denoising=True
s.render.bake.use_selected_to_active=False
s.render.filepath=str(REND/'BlackNunchucks_Front.png')
s['bake_info']='4K BaseColor, DirectX normal + OpenGL companion, real baked AO, ORM. See bake_report.json.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.overlay.show_overlays=False
select(lod0); bpy.context.view_layer.objects.active=lod0[0]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Assets/BlackNunchucks.blend'))
(WORK/'bake_report.json').write_text(json.dumps(stats,indent=2))
bpy.ops.render.render(write_still=True)
cam=s.camera
def render(name,loc,target,scale,width,height):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale;s.render.resolution_x=width;s.render.resolution_y=height
    s.render.filepath=str(REND/name);bpy.ops.render.render(write_still=True)
render('BlackNunchucks_Chain.png',(0,-1,.354),(0,0,.325),.143,1400,900)
render('BlackNunchucks_Grip.png',(-.078,-.5,.16),(-.078,0,.16),.068,1000,1250)
render('BlackNunchucks_ThreeQuarter.png',(.28,-.8,.32),(0,0,.17),.405,1254,1254)
print('BAKED_SAVED_AND_RENDERED',flush=True)
