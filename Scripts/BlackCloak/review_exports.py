"""Render saved editable mesh and imported exports in the same studio."""
from pathlib import Path
import bpy,json,os
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');REND=ROOT/'Renders/BlackCloak';OUT=ROOT/'Exports/BlackCloak'
def take(name,loc,target,scale,w=1000,h=1350):
    s=bpy.context.scene;c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=scale;c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.device='GPU'
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    s.render.resolution_x=w;s.render.resolution_y=h;s.render.resolution_percentage=100;s.render.filepath=str(REND/(name+'.png'));bpy.ops.render.render(write_still=True)
def loadstudio():
    with bpy.data.libraries.load(str(ROOT/'Assets/BlackCloak.blend'),link=False) as (a,b):b.collections=['STUDIO_ExcludeFromExport'];b.worlds=['StudioWorld']
    for c in b.collections:bpy.context.scene.collection.children.link(c)
    s=bpy.context.scene;s.world=b.worlds[0];s.camera=bpy.data.objects['Camera'];s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'

if os.environ.get('CLOAK_REVIEW_EXPORTS_ONLY')!='1':
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/BlackCloak.blend'))
    take('BlackCloak_Front',(.12,-4,1.9),(0,0,.89),1.93)
    take('BlackCloak_ThreeQuarter',(2.6,-4,2.0),(0,0,.89),1.96)
    take('BlackCloak_Back',(-.2,4,1.95),(0,0,.9),1.94)
    take('BlackCloak_Collar',(.50,-3,2.03),(0,-.03,1.58),.54,1100,1000)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'BlackCloak.glb'));loadstudio()
take('Export_GLB_Front',(.12,-4,1.9),(0,0,.89),1.93)
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
    take(f'Export_LOD{level}_Front',(.12,-4,1.9),(0,0,.89),1.93)
print('CLOAK_REVIEW_RENDERED',flush=True)
