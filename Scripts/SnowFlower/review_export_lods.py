"""Render each actual self-contained GLB and compare dimensions to export report."""
from pathlib import Path
import bpy,json,math,os,hashlib
from mathutils import Vector,Quaternion
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Renders/SnowFlower'
expected=json.loads((ROOT/'Exports/SnowFlower/export_report.json').read_text())
report_path=ROOT/'WorkFiles/SnowFlower/lod_visual_report.json'
report=json.loads(report_path.read_text()) if report_path.exists() else {'source':'Self-contained exported GLB files; no manual material substitution','lods':{}}
assert expected['source_sha256']==hashlib.sha256((ROOT/'Assets/SnowFlower/SnowFlower_Master.blend').read_bytes()).hexdigest()
if report.get('source_sha256')!=expected['source_sha256']:
    report['lods']={}
report['source_sha256']=expected['source_sha256']
for lod in ([int(os.environ['SF_REVIEW_LOD'])] if 'SF_REVIEW_LOD' in os.environ else range(3)):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/SnowFlower/SnowFlower_Game.blend'))
    scene=bpy.context.scene;cam=scene.camera
    for o in list(bpy.data.objects):
        if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
    old=set(bpy.data.objects);suffix=f'_LOD{lod}' if lod else ''
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'Exports/SnowFlower/SM_SnowFlower{suffix}.glb'))
    objects=[o for o in set(bpy.data.objects)-old if o.type=='MESH'];points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
    error=max(abs(v-e) for a,b in ((low,expected['lods'][str(lod)]['min']),(high,expected['lods'][str(lod)]['max'])) for v,e in zip(a,b))
    assert error<1e-6,f'LOD{lod} bounds changed: {error}'
    scene.cycles.samples=48
    report['lods'][str(lod)]={'bounds_error_m':error,'materials':[m.name for o in objects for m in o.data.materials],
        'all_images_loaded':all(all(n.image.size) for o in objects for m in o.data.materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image)}
    def take(name,loc,target,scale,w,h):
        cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.location=loc
        cam.rotation_euler=((Vector(target)-cam.location).to_track_quat('-Z','Y')@Quaternion((0,0,1),math.pi)).to_euler()
        scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
        scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    take(f'SnowFlower_ExportLOD{lod}_Front',(0,-3,.458),(0,0,.458),1.39,900,1600)
    take(f'SnowFlower_ExportLOD{lod}_Guard',(.065,-.60,.090),(0,0,.128),.166,1100,950)
    (ROOT/'WorkFiles/SnowFlower/lod_visual_report.json').write_text(json.dumps(report,indent=2))
print('SF_LOD_REVIEW_RENDERED',flush=True)
