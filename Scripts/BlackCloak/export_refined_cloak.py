"""Export reference revision through shared FBX settings, then verify round trips.
UV0 remains tiled; this is not full Fab/Unreal pipeline approval.
"""
from pathlib import Path
import bpy,bmesh,json,sys,shutil,hashlib,csv,math
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/BlackCloak';WORK=ROOT/'WorkFiles/BlackCloak'
sys.path.insert(0,str(ROOT/'Scripts/pipeline'));from lock import assert_owner
assert_owner('BlackCloak','codex')
sys.path.insert(0,str(ROOT/'Scripts/JinMuWon/v2'));from export_modules import skeleton_info,reset_pose
SOURCE=WORK/'BlackCloak_candidate.blend';FINAL=ROOT/'Assets/BlackCloak.blend'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):activate(o);bpy.ops.object.modifier_apply(modifier=m.name)
def stats(objects):
    result={}
    for o in objects:
        o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data)
        result[o.name]={'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),
                       'uv_sets':len(o.data.uv_layers),'loose_vertices':sum(not v.link_faces for v in bm.verts),
                       'degenerate_triangles':sum(t.area<1e-12 for t in o.data.loop_triangles),
                       'boundary_edges':sum(e.is_boundary for e in bm.edges),
                       'nonmanifold_nonboundary_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
                       'materials':[m.name for m in o.data.materials],
                       'max_influences':max((len(v.groups) for v in o.data.vertices),default=0)}
        bm.free()
    return result

bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
original=[o for o in bpy.data.collections['BLACK_CLOAK'].all_objects if o.type=='MESH']
report={'status':'in_progress','reference_sha256':digest(ROOT/'References/BlackCloak/blackcloak.png'),
        'authoring_meshes':stats(original),'lods':{},'roundtrips':{},'limits':['Cloth physics and collision are not configured in Unreal.','The optional skeletal version has attachment weights, not authored cloth animation.']}
assert all(v['loose_vertices']==0 and v['degenerate_triangles']==0 and v['uv_sets'] for v in report['authoring_meshes'].values())
with (OUT/'authoring_pin_weights.csv').open('w',newline='') as file:
    w=csv.writer(file);w.writerow(['blender_object','blender_vertex','pin_weight'])
    for o in original:
        group=o.vertex_groups.get('CLOTH_Pin')
        if group:
            for v in o.data.vertices:
                weight=next((g.weight for g in v.groups if g.group==group.index),0)
                w.writerow([o.name,v.index,round(weight,6)])
if FINAL.exists():shutil.copy2(FINAL,WORK/'BlackCloak_before_export.blend')
scene['export_notes']='Static FBX/GLB and optional JinMuWon skeleton attachment FBX are in Exports/BlackCloak. Cloth simulation remains to be configured.'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(FINAL))
report['editable_blend_sha256']=digest(FINAL)
(OUT/'Textures').mkdir(exist_ok=True)
for p in (ROOT/'Textures/BlackCloak').glob('*.png'):shutil.copy2(p,OUT/'Textures'/p.name)

def portable_materials():
    # Portable nodes + baked UV tiling for glTF and normal FBX importers.
    fabric=bpy.data.materials['M_BlackCloak_WovenWool'];nt=fabric.node_tree
    p=nt.nodes.get('Principled BSDF');tc=nt.nodes.get('Texture Coordinate')
    # This glTF exporter writes white sheenColorFactor without multiplying
    # Blender's fractional Sheen Weight. Disable that optional lobe in the
    # portable material so the black cloth cannot reimport as white velvet.
    p.inputs['Sheen Weight'].default_value=0
    for node in nt.nodes:
        if node.type=='TEX_IMAGE':
            nt.links.new(tc.outputs['UV'],node.inputs['Vector'])
            if node.image:
                path=OUT/'Textures'/Path(node.image.filepath).name
                fresh=bpy.data.images.load(str(path),check_existing=False)
                fresh.colorspace_settings.name='sRGB' if 'BaseColor' in path.name else 'Non-Color'
                node.image=fresh
    return fabric

def export_fbx(path,objects,rig=None):
    sys.path.insert(0,str(ROOT/'Scripts'))
    from pipeline.export_fbx import export_fbx as shared_export
    prefixed=path.with_name(('SK_' if rig else 'SM_')+path.name)
    shared_export(str(prefixed),objects+([rig] if rig else []),
                  kind='skeletal' if rig else 'static',use_armature_deform_only=False,
                  sidecar=False)
    prefixed.replace(path)

def decimation_ratio(o,level):
    if o.get('component')=='clasp':return (1,.72,.45)[level]
    name=o.name
    if 'Cowl' in name:return (.155,.073,.028)[level]
    if 'Mantle' in name or 'Shawl' in name:return (.16,.085,.035)[level]
    if 'Gathered' in name:return (.16,.080,.030)[level]
    if 'LongDrape' in name:return (.115,.054,.021)[level]
    return (.13,.062,.025)[level]

def reduce_surface(o,level):
    # Reduce the open cloth before adding thickness; the rim stays coherent.
    solid=[]
    for m in list(o.modifiers):
        if m.type=='SUBSURF':o.modifiers.remove(m)
        elif m.type=='SOLIDIFY':solid.append(m)
        else:apply(o,m)
    factor=decimation_ratio(o,level)
    if factor<1:
        o.vertex_groups.clear()
        bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
        inside=[v.index for v in bm.verts if not v.is_boundary]
        bm.free()
        group=o.vertex_groups.new(name='Reduction_Interior')
        if inside:group.add(inside,1,'REPLACE')
        d=o.modifiers.new('Per-part interior reduction','DECIMATE');d.ratio=factor
        d.use_collapse_triangulate=True;d.vertex_group=group.name;d.vertex_group_factor=1000
        # The reduction modifier must evaluate before Solidify.
        activate(o);bpy.ops.object.modifier_move_to_index(modifier=d.name,index=0)
        apply(o,d)
    for m in solid:apply(o,m)
    o.vertex_groups.clear()
    tri=o.modifiers.new('Portable triangulation','TRIANGULATE');apply(o,tri)

def lightmap_uvs(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
        if 'LightmapUV' not in o.data.uv_layers:o.data.uv_layers.new(name='LightmapUV')
        o.data.uv_layers.active_index=1
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.008,area_weight=.3,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objects:
        o.data.uv_layers.active_index=0
        o.data.uv_layers[0].active_render=True
        assert all(-1e-6<=uv.uv.x<=1.000001 and -1e-6<=uv.uv.y<=1.000001 for uv in o.data.uv_layers[1].data)

for level,ratio in [(0,.52),(1,.23),(2,.075)]:
    bpy.ops.wm.open_mainfile(filepath=str(FINAL));scene=bpy.context.scene
    objects=[o for o in bpy.data.collections['BLACK_CLOAK'].all_objects if o.type=='MESH']
    portable_materials()
    for o in objects:
        reduce_surface(o,level)
        if o.data.materials[0].name=='M_BlackCloak_WovenWool':
            for uv in o.data.uv_layers[0].data:uv.uv*=1/.128
    lightmap_uvs(objects)
    record=stats(objects);total=sum(v['triangles'] for v in record.values())
    assert all(v['loose_vertices']==0 and v['degenerate_triangles']==0 and v['uv_sets'] for v in record.values())
    suffix='' if level==0 else f'_LOD{level}'
    path=OUT/f'BlackCloak{suffix}.fbx';export_fbx(path,objects)
    report['lods'][str(level)]={'reduction':'Per-part interior weighted reduction before cloth thickness','static_fbx':str(path),'sha256':digest(path),'triangles':total,'meshes':record}
    if level==0:
        bpy.ops.export_scene.gltf(filepath=str(OUT/'BlackCloak.glb'),export_format='GLB',use_selection=True,
                                  export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
        # Save the same export geometry for deterministic round-trip comparison.
        bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'BlackCloak_export_LOD0.blend'))
    # Rig attachment is optional and never modifies the original character.
    with bpy.data.libraries.load(str(ROOT/'Assets/JinMuWon_v2/JinMuWon_Human.blend'),link=False) as (src,dst):dst.objects=['Armature']
    rig=dst.objects[0];scene.collection.objects.link(rig);reset_pose(rig)
    report['skeleton']=skeleton_info(rig)
    for o in objects:
        o.vertex_groups.clear()
        bone='neck01' if any(k in o.name for k in ['Cowl','Scarf']) else 'clavicle.R' if o.get('component')=='clasp' else 'spine01'
        group=o.vertex_groups.new(name=bone);group.add(list(range(len(o.data.vertices))),1,'REPLACE')
        o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted();mod=o.modifiers.new('Attachment skin','ARMATURE');mod.object=rig
    path=OUT/f'BlackCloak_Skeletal{suffix}.fbx';export_fbx(path,objects,rig)
    report['lods'][str(level)]['skeletal_fbx']=str(path);report['lods'][str(level)]['skeletal_sha256']=digest(path)
    (OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
    print('CLOAK_LOD_EXPORTED',level,total,flush=True)

for level in range(3):
    suffix='' if level==0 else f'_LOD{level}'
    for skeletal in (False,True):
        path=OUT/('BlackCloak'+('_Skeletal' if skeletal else '')+suffix+'.fbx')
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];meshes=stats(objects)
        rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
        triangles=sum(v['triangles'] for v in meshes.values())
        checks={'triangle_count_matches':triangles==report['lods'][str(level)]['triangles'],
                'uvs_present':all(v['uv_sets']>=2 for v in meshes.values()),
                'no_loose_or_degenerate_geometry':all(v['loose_vertices']==0 and v['degenerate_triangles']==0 for v in meshes.values()),
                'rig_matches_type':len(rigs)==(1 if skeletal else 0)}
        if skeletal:
            checks['full_152_bone_skeleton']=len(rigs[0].data.bones)==152
            checks['all_vertices_attached']=all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for o in objects for v in o.data.vertices)
        assert all(checks.values()),(path,checks)
        report['roundtrips'][path.name]=checks
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'BlackCloak.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];glbstats=stats(objects)
report['roundtrips']['BlackCloak.glb']={'triangle_count_matches':sum(v['triangles'] for v in glbstats.values())==report['lods']['0']['triangles'],
                                      'uvs_present':all(v['uv_sets']>0 for v in glbstats.values()),'embedded_images':len(bpy.data.images)}
assert report['roundtrips']['BlackCloak.glb']['triangle_count_matches'] and len(bpy.data.images)>=3
report['limits'] += ['UV0 is intentionally tiled, not a unique bake atlas.','AO/ORM is not baked; standalone roughness and normal maps are provided.','UV1 was smart-projected and bounded; engine lightmap validation is pending.','Visible front landmarks were reconstructed; hidden surfaces remain interpretation.','Shared 152-bone compatibility preserves existing bone names and rigid attachment only.']; report['status']='roundtrip_passed';report['dimensions_m']=[max((o.matrix_world@v.co)[i] for o in objects for v in o.data.vertices)-min((o.matrix_world@v.co)[i] for o in objects for v in o.data.vertices) for i in range(3)]
assert report['lods']['0']['triangles']>report['lods']['1']['triangles']>report['lods']['2']['triangles']
report['files']={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.suffix.lower() in {'.fbx','.glb','.png'}}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
print('CLOAK_EXPORT_VALIDATION_PASSED',flush=True)
