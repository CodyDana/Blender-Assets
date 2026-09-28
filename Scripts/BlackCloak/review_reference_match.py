"""Read-only reference audit. Render the saved asset; never save over it."""
from pathlib import Path
import bpy,hashlib,json
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');SOURCE=ROOT/'Assets/BlackCloak.blend'
OUT=ROOT/'WorkFiles/BlackCloak/reference_match_review';OUT.mkdir(exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=digest(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));s=bpy.context.scene
# Camera and studio adjustments only, for a closer front-view comparison.
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
floor=bpy.data.objects['StudioFloor'].data.materials[0].node_tree.nodes['Principled BSDF']
floor.inputs['Base Color'].default_value=(.82,.82,.82,1)
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True;s.cycles.device='GPU'
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type!='CPU'
c=s.camera
def take(name,loc,target,scale,w,h):
    c.data.type='ORTHO';c.data.ortho_scale=scale;c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x=w;s.render.resolution_y=h;s.render.resolution_percentage=100;s.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
take('SavedAsset_Front',(0,-4,1.00),(0,0,.88),1.82,760,1240)
take('SavedAsset_CollarClasp',(0,-4,1.71),(-.05,-.015,1.565),.59,1000,850)
take('SavedAsset_FoldsHem',(0,-4,.54),(0,0,.46),1.10,950,1050)
report={'source':str(SOURCE),'sha256':before,'source_unchanged':before==digest(SOURCE),
        'reference':str(ROOT/'References/BlackCloak/blackcloak.png'),
        'reference_sha256':digest(ROOT/'References/BlackCloak/blackcloak.png'),
        'scope':'Saved LOD0 editable model, neutral front camera and lighter studio only. No asset changes.',
        'limits':'Reference is a single 417x674 front image with no physical dimensions or rear/side views. Lighting and hidden surfaces cannot be matched exactly from this image.',
        'renders':['SavedAsset_Front.png','SavedAsset_CollarClasp.png','SavedAsset_FoldsHem.png']}
(OUT/'evidence.json').write_text(json.dumps(report,indent=2));assert report['source_unchanged']
print('REFERENCE_AUDIT_RENDERED_SOURCE_UNCHANGED',flush=True)
