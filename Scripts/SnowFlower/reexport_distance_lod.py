"""Revise only LOD2 from the saved baked mesh; do not repeat texture bakes."""
from pathlib import Path
import bpy,bmesh,json,sys,hashlib
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/SnowFlower'
sys.path.insert(0,str(ROOT/'Scripts/SnowFlower'))
from lod_helpers import thin_tassel
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/SnowFlower/SnowFlower_Game.blend'))
o=bpy.data.objects['SM_SnowFlower'];o.name='SM_SnowFlower_LOD2'
reduction=thin_tassel(o)
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
m=o.modifiers.new('Distance reduction','DECIMATE');m.ratio=.28;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
o.data.validate(verbose=True,clean_customdata=False)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
bad=[f for f in bm.faces if f.calc_area()<1e-15]
if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(o.data);bm.free();o.data.validate(verbose=True,clean_customdata=False);o.data.calc_loop_triangles()
points=[o.matrix_world@v.co for v in o.data.vertices]
stats={'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'uv_sets':len(o.data.uv_layers),'materials':[m.name for m in o.data.materials],
       'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
fbx=OUT/'SM_SnowFlower_LOD2.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS',use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='RELATIVE',bake_anim=False)
stats['fbx_sha256']=hashlib.sha256(fbx.read_bytes()).hexdigest()
bpy.ops.export_scene.gltf(filepath=str(OUT/'SM_SnowFlower_LOD2.glb'),export_format='GLB',use_selection=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_extras=True)
report=json.loads((OUT/'export_report.json').read_text());report['lods']['2']=stats;report['lod2_tassel_reduction']=reduction
for ext in ('fbx','glb'):
    bpy.ops.wm.read_factory_settings(use_empty=True);path=OUT/('SM_SnowFlower_LOD2.'+ext)
    if ext=='fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    else:bpy.ops.import_scene.gltf(filepath=str(path))
    meshes=[ob for ob in bpy.data.objects if ob.type=='MESH'];count=0
    for ob in meshes:
        ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
        bm=bmesh.new();bm.from_mesh(ob.data)
        assert not any(f.calc_area()<1e-14 for f in bm.faces),'Degenerate imported face'
        assert not any(not v.link_faces for v in bm.verts),'Loose imported vertex';bm.free()
        assert len(ob.data.uv_layers)>0
    assert count==stats['triangles'],'Triangle mismatch'
    report['roundtrips'][path.name]={'triangles':count,'mesh_count':len(meshes),'uvs_present':True,'no_degenerate_faces_or_loose_vertices':True,'file_bytes':path.stat().st_size}
(OUT/'export_report.json').write_text(json.dumps(report,indent=2))
print('SF_DISTANCE_LOD_REVISED',stats['triangles'],reduction,flush=True)
