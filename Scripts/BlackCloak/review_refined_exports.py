"""Verify the actual revised GLB and FBX LOD appearance in a shared camera."""
from pathlib import Path
import bpy,sys,json
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/BlackCloak';REND=ROOT/'Renders/BlackCloak/ReferenceRevision'
sys.path.insert(0,str(ROOT/'Scripts/pipeline'));from lock import assert_owner
assert_owner('BlackCloak','codex')

def studio():
    with bpy.data.libraries.load(str(ROOT/'Assets/BlackCloak.blend'),link=False) as (a,b):
        b.collections=['STUDIO_ExcludeFromExport'];b.worlds=['StudioWorld']
    for c in b.collections:bpy.context.scene.collection.children.link(c)
    s=bpy.context.scene;s.world=b.worlds[0];s.camera=bpy.data.objects['Camera']
    s.view_settings.view_transform='Standard';s.view_settings.look='None'

def render(name):
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.cycles.device='GPU'
    p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    s.render.resolution_x=834;s.render.resolution_y=1348;s.render.resolution_percentage=100
    c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=674*(1.72/654)
    c.location=(6.5*(1.72/654),-4,(665-337)*(1.72/654));c.rotation_euler=(Vector((c.location.x,0,c.location.z))-c.location).to_track_quat('-Z','Y').to_euler()
    s.render.image_settings.file_format='PNG';s.render.filepath=str(REND/(name+'.png'));bpy.ops.render.render(write_still=True)

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'BlackCloak.glb'));studio();render('Reimported_GLB_Front')
for level in (1,2):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'WorkFiles/BlackCloak/BlackCloak_export_LOD0.blend'))
    mats={m.name:m for m in bpy.data.materials}
    for o in list(bpy.data.collections['BLACK_CLOAK'].all_objects):bpy.data.objects.remove(o,do_unlink=True)
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(OUT/f'BlackCloak_LOD{level}.fbx'),use_anim=False)
    for o in set(bpy.data.objects)-before:
        if o.type=='MESH':
            for i,mat in enumerate(o.data.materials):
                match=next((v for k,v in mats.items() if mat.name==k or mat.name.startswith(k+'.')),None)
                if match:o.data.materials[i]=match
    render(f'Reimported_LOD{level}_Front')
print('REFINED_EXPORT_PREVIEWS_COMPLETE',flush=True)
