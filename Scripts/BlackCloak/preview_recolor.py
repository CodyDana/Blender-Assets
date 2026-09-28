"""Render the Unreal recolor math in Blender; never modify source geometry.

These are Blender previews, not Unreal screenshots. The engine material and
saved-instance checks are created separately by unreal_recolor_setup.py.
"""
from pathlib import Path
import bpy,sys,json,hashlib
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Renders/BlackCloak/Recolor';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Scripts/pipeline'));from lock import assert_owner
assert_owner('BlackCloak','codex')
SOURCE=ROOT/'Assets/BlackCloak.blend'
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Exports/BlackCloak/BlackCloak.glb'))
with bpy.data.libraries.load(str(SOURCE),link=False) as (a,b):
    b.collections=['STUDIO_ExcludeFromExport'];b.worlds=['StudioWorld']
for c in b.collections:bpy.context.scene.collection.children.link(c)
s=bpy.context.scene;s.world=b.worlds[0];s.camera=bpy.data.objects['Camera']
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.cycles.device='GPU'
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
mat=bpy.data.materials['M_BlackCloak_WovenWool'];nt=mat.node_tree;p=nt.nodes.get('Principled BSDF')
base_link=list(p.inputs['Base Color'].links)[0];tex=base_link.from_node;nt.links.remove(base_link)
split=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs['Color'],split.inputs['Color'])
norm=nt.nodes.new('ShaderNodeMath');norm.operation='DIVIDE';norm.inputs[1].default_value=.013702083;norm.use_clamp=True
nt.links.new(split.outputs['Red'],norm.inputs[0])
color=nt.nodes.new('ShaderNodeRGB');color.label='CloakColor (linear RGB)'
mul=nt.nodes.new('ShaderNodeVectorMath');mul.operation='MULTIPLY'
nt.links.new(color.outputs[0],mul.inputs[0]);nt.links.new(norm.outputs[0],mul.inputs[1]);nt.links.new(mul.outputs[0],p.inputs['Base Color'])
presets={'Black':(.013702083,.01355,.0134),'Crimson':(.32,.012,.018),'Navy':(.016,.035,.12),'Ivory':(.80,.73,.57)}
report={'renderer':'Blender Cycles preview of the same recoloring math, not an Unreal screenshot','formula':'CloakColor * saturate(BaseColorTexture.R / 0.013702083)','fabric_detail':1,'source_sha256':before,'presets':presets}
for name,rgb in presets.items():
    color.outputs[0].default_value=(*rgb,1)
    c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=674*(1.72/654)
    c.location=(6.5*(1.72/654),-4,(665-337)*(1.72/654));c.rotation_euler=(Vector((c.location.x,0,c.location.z))-c.location).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x=625;s.render.resolution_y=1011;s.render.resolution_percentage=100
    s.render.filepath=str(OUT/f'Cloak_{name}.png');bpy.ops.render.render(write_still=True)
report['source_unchanged']=before==hashlib.sha256(SOURCE.read_bytes()).hexdigest();assert report['source_unchanged']
(OUT/'preview_report.json').write_text(json.dumps(report,indent=2))
print('RECOLOR_PREVIEWS_COMPLETE_SOURCE_UNCHANGED',flush=True)
