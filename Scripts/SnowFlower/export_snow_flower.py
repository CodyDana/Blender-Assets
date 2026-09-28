"""Bake portable PBR maps and export isolated static-mesh deliverables."""
from pathlib import Path
import bpy,bmesh,json,hashlib,math,numpy as np,sys
from mathutils import Vector,Quaternion
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/SnowFlower';TEX=OUT/'Textures';WORK=ROOT/'WorkFiles/SnowFlower'
TEX.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'Assets/SnowFlower/SnowFlower_Master.blend'
sys.path.insert(0,str(ROOT/'Scripts/SnowFlower'))
from lod_helpers import thin_tassel
from uv_helpers import repair_collapsed_uv
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
source=[o for o in scene.objects if o.type=='MESH' and o.get('sf_export')]
col=bpy.data.collections.new('EXPORT_SnowFlower');scene.collection.children.link(col)
groups={}
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.hide_render=False;o.select_set(True);bpy.context.view_layer.objects.active=o
for ob in source:
    ob.hide_render=True
    for index,material in enumerate(ob.data.materials):
        if not any(p.material_index==index for p in ob.data.polygons):continue
        cp=ob.copy();cp.data=ob.data.copy();cp.name='BAKE_'+ob.name;cp.parent=None;cp.matrix_world=ob.matrix_world.copy();col.objects.link(cp);cp.hide_render=False
        if len(ob.data.materials)>1:
            bm=bmesh.new();bm.from_mesh(cp.data)
            bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=index],context='FACES')
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(cp.data);bm.free()
        cp.data.materials.clear();cp.data.materials.append(material)
        for p in cp.data.polygons:p.material_index=0
        groups.setdefault(material.name,[]).append(cp)
meshes=[]
for name,objects in groups.items():
    activate(objects[0])
    for ob in objects:ob.select_set(True)
    bpy.ops.object.join();ob=bpy.context.object;ob.name='BAKE_'+name.removeprefix('M_SnowFlower_')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.006);bpy.ops.object.mode_set(mode='OBJECT')
    repair_collapsed_uv(ob.data)
    meshes.append(ob)
scene.cycles.samples=4;scene.render.bake.margin=6;scene.render.bake.use_clear=False;scene.render.bake.use_selected_to_active=False
manifest={'asset':'Snow Flower','source_sha256':source_hash,'normal_convention':'OpenGL (+Y); flip green for DirectX/Unreal when importing textures.','materials':{}}

def bake(ob,mat,channel):
    label=mat.name.removeprefix('M_SnowFlower_');size=2048 if label in ('BlackenedSteel','Leather') and channel!='Roughness' else 1024
    image=bpy.data.images.new('T_SnowFlower_'+label+'_'+channel,width=size,height=size,alpha=False)
    image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
    nt=mat.node_tree;n=nt.nodes;l=nt.links;bs=n.get('Principled BSDF');out=n.get('Material Output')
    # Tiny raised ornaments can have subpixel UV islands. A physically valid
    # fallback outside the baked islands avoids black color/normal seams.
    if channel=='BaseColor':fill=list(bs.inputs['Base Color'].default_value)
    elif channel=='Normal':fill=[.5,.5,1,1]
    else:fill=[bs.inputs['Roughness'].default_value]*3+[1]
    pixels=np.empty((size*size,4),dtype=np.float32);pixels[:]=fill;image.pixels.foreach_set(pixels.ravel());image.update()
    target=n.new('ShaderNodeTexImage');target.image=image
    for node in n:node.select=False
    target.select=True;n.active=target
    em=None
    if channel!='Normal':
        em=n.new('ShaderNodeEmission');socket=bs.inputs['Base Color' if channel=='BaseColor' else 'Roughness']
        if socket.is_linked:l.new(socket.links[0].from_socket,em.inputs['Color'])
        else:
            value=socket.default_value;em.inputs['Color'].default_value=tuple(value) if channel=='BaseColor' else (value,value,value,1)
        em.inputs['Strength'].default_value=1;l.new(em.outputs[0],out.inputs['Surface'])
    activate(ob);bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
    if em:n.remove(em);l.new(bs.outputs[0],out.inputs['Surface'])
    n.remove(target);image.filepath_raw=str(TEX/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
    print('SF_BAKED',label,channel,flush=True);return image

for ob in meshes:
    mat=ob.data.materials[0];bs=mat.node_tree.nodes.get('Principled BSDF')
    metal=float(bs.inputs['Metallic'].default_value);spec=float(bs.inputs['Specular IOR Level'].default_value)
    images={channel:bake(ob,mat,channel) for channel in ('BaseColor','Roughness','Normal')}
    # Pack AO=1, roughness, metalness for common runtime material workflows.
    rough=images['Roughness'];w,h=rough.size;rgba=np.empty(w*h*4,dtype=np.float32);rough.pixels.foreach_get(rgba);rgba=rgba.reshape(-1,4)
    packed=np.ones((w*h,4),dtype=np.float32);packed[:,1]=rgba[:,0];packed[:,2]=metal
    orm=bpy.data.images.new('T_SnowFlower_'+mat.name.removeprefix('M_SnowFlower_')+'_ORM',width=w,height=h,alpha=False)
    orm.colorspace_settings.name='Non-Color';orm.pixels.foreach_set(packed.ravel());orm.filepath_raw=str(TEX/(orm.name+'.png'));orm.file_format='PNG';orm.save();orm.pack()
    nt=mat.node_tree;nt.nodes.clear();bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bs.name='Principled BSDF';out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Specular IOR Level'].default_value=spec
    for channel,img in images.items():
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img;tex.name='Export_'+channel;tex.interpolation='Linear'
        if channel=='Normal':
            normal=nt.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1;nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:nt.links.new(tex.outputs['Color'],bs.inputs['Base Color' if channel=='BaseColor' else 'Roughness'])
    manifest['materials'][mat.name]={
        'base_color':'Textures/'+Path(images['BaseColor'].filepath_raw).name,
        'normal':'Textures/'+Path(images['Normal'].filepath_raw).name,
        'roughness':'Textures/'+Path(images['Roughness'].filepath_raw).name,
        'orm':'Textures/'+Path(orm.filepath_raw).name,'metallic_value':metal,'specular_value':spec,'flip_normal_green':True}
(OUT/'material_manifest.json').write_text(json.dumps(manifest,indent=2))

for ob in source:bpy.data.objects.remove(ob,do_unlink=True)
activate(meshes[0])
for ob in meshes:ob.select_set(True)
bpy.ops.object.join();sword=bpy.context.object;sword.name='SM_SnowFlower';sword.parent=None;sword['sf_export']=True
for ob in list(bpy.data.objects):
    if ob.type=='EMPTY':bpy.data.objects.remove(ob,do_unlink=True)
report={'status':'building','source_sha256':source_hash,'lods':{},'roundtrips':{},'gameplay_tested':False}
def stats(ob):
    ob.data.calc_loop_triangles();points=[ob.matrix_world@v.co for v in ob.data.vertices]
    return {'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'uv_sets':len(ob.data.uv_layers),'materials':[m.name for m in ob.data.materials],
            'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def fbx(path,objects):
    select(objects);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='RELATIVE',bake_anim=False)

# Simple separate convex collision pieces for the rigid sword, excluding tassel.
collision=bpy.data.collections.new('COLLISION_UE');scene.collection.children.link(collision);colliders=[]
blade_source=sword.data.copy();temp=bpy.data.objects.new('TEMP_Collision',blade_source);collision.objects.link(temp)
bm=bmesh.new();bm.from_mesh(temp.data)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<.19 or abs(v.co.y)>.0033],context='VERTS')
bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
interior=[f for f in bm.faces if any(not e.is_manifold for e in f.edges)]
# Use Blender's evaluated convex hull via a clean vertex-only hull instead.
coords=[v.co.copy() for v in bm.verts];bm.free();bpy.data.objects.remove(temp,do_unlink=True)
def convex(name,coords):
    bm=bmesh.new()
    for co in coords:bm.verts.new(co)
    result=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    if result.get('geom_interior'):bmesh.ops.delete(bm,geom=result['geom_interior'],context='VERTS')
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);collision.objects.link(o);o.hide_render=True;o.display_type='WIRE';colliders.append(o);return o
convex('UCX_SM_SnowFlower_00',coords)
convex('UCX_SM_SnowFlower_01',[(x,y,z) for x in (-.065,.065) for y in (-.0205,.0205) for z in (.103,.171)])
convex('UCX_SM_SnowFlower_02',[(.022*math.cos(math.tau*i/12),.022*math.sin(math.tau*i/12),z) for z in (-.172,.104) for i in range(12)])
for level,ratio in [(0,1),(1,.40),(2,.28)]:
    if level:
        ob=sword.copy();ob.data=sword.data.copy();ob.name=f'SM_SnowFlower_LOD{level}';col.objects.link(ob)
        if level==2:report['lod2_tassel_reduction']=thin_tassel(ob)
        dec=ob.modifiers.new('Distance LOD reduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True
        activate(ob);bpy.ops.object.modifier_apply(modifier=dec.name)
    else:ob=sword
    ob.data.validate(verbose=True,clean_customdata=False)
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    collapsed=[f for f in bm.faces if f.calc_area()<1e-15]
    if collapsed:bmesh.ops.delete(bm,geom=collapsed,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(ob.data);bm.free();ob.data.update();ob.data.validate(verbose=True,clean_customdata=False)
    report['lods'][str(level)]=stats(ob);suffix='' if level==0 else f'_LOD{level}'
    path=OUT/f'SM_SnowFlower{suffix}.fbx';fbx(path,[ob]+(colliders if level==0 else []));report['lods'][str(level)]['fbx_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    select([ob]);bpy.ops.export_scene.gltf(filepath=str(OUT/f'SM_SnowFlower{suffix}.glb'),export_format='GLB',use_selection=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_extras=True)
    if level:bpy.data.objects.remove(ob,do_unlink=True)
for c in colliders:c.hide_set(True)
activate(sword);bpy.ops.file.pack_all();scene.cycles.samples=48
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Assets/SnowFlower/SnowFlower_Game.blend'))
# The preview is rendered from the actual baked, portable material graphs.
cam=scene.camera;cam.data.type='ORTHO';cam.data.ortho_scale=.166;cam.location=(.065,-.60,.090)
cam.rotation_euler=((Vector((0,0,.128))-cam.location).to_track_quat('-Z','Y')@Quaternion((0,0,1),math.pi)).to_euler()
scene.render.resolution_x=1300;scene.render.resolution_y=1100;scene.render.filepath=str(ROOT/'Renders/SnowFlower/SnowFlower_ExportGuard.png');bpy.ops.render.render(write_still=True)

for level in range(3):
    suffix='' if level==0 else f'_LOD{level}'
    for extension in ('fbx','glb'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path=OUT/f'SM_SnowFlower{suffix}.{extension}'
        if extension=='fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
        else:bpy.ops.import_scene.gltf(filepath=str(path))
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
        data=[stats(o) for o in objects];triangles=sum(o['triangles'] for o in data)
        assert triangles==report['lods'][str(level)]['triangles'],f'{path.name}: triangle mismatch'
        assert all(o['uv_sets']>0 for o in data),f'{path.name}: UVs missing'
        bm_errors=[]
        for o in objects:
            bm=bmesh.new();bm.from_mesh(o.data)
            deg=sum(f.calc_area()<1e-14 for f in bm.faces);loose=sum(not v.link_faces for v in bm.verts);bm.free()
            if deg or loose:bm_errors.append({'object':o.name,'degenerate_faces':deg,'loose_vertices':loose})
        assert not bm_errors,f'{path.name}: {bm_errors}'
        report['roundtrips'][path.name]={'triangles':triangles,'mesh_count':len(objects),'uvs_present':True,'no_degenerate_faces_or_loose_vertices':True,'file_bytes':path.stat().st_size}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash,'Master was modified during export'
report['status']='passed';report['master_unchanged']=True
(OUT/'export_report.json').write_text(json.dumps(report,indent=2))
print('SNOW_FLOWER_EXPORT_PASSED',flush=True)
