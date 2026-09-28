"""Store useful portrait framing in the editable file; update its hash."""
from pathlib import Path
import bpy,json,hashlib
from mathutils import Vector
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');path=ROOT/'Assets/BlackCloak.blend'
bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
s.render.resolution_x=1000;s.render.resolution_y=1350;s.render.resolution_percentage=100
c=s.camera;c.data.type='ORTHO';c.data.ortho_scale=1.93;c.location=(.12,-4,1.9);c.rotation_euler=(Vector((0,0,.89))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(ROOT/'Renders/BlackCloak/BlackCloak_Front.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=str(path))
p=ROOT/'Exports/BlackCloak/asset_report.json';r=json.loads(p.read_text());r['editable_blend_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();p.write_text(json.dumps(r,indent=2))
print('CLOAK_PORTRAIT_VIEW_SAVED',flush=True)
