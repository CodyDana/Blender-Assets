from pathlib import Path
import bpy
from mathutils import Vector
root=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(root/'Assets/SnowFlower/SnowFlower_Master.blend'))
s=bpy.context.scene;c=s.camera;c.data.clip_start=.001;c.data.type='ORTHO';c.data.ortho_scale=.080;c.location=(.057,-.065,-.235)
c.rotation_euler=(Vector((0,0,-.152))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1200;s.render.resolution_y=1100;s.render.filepath=str(root/'Renders/SnowFlower/SnowFlower_Pommel_ClipCheck.png')
bpy.ops.render.render(write_still=True)
