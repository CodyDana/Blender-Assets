from pathlib import Path
import bpy, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Scripts'))
from pipeline.lock import assert_owner
assert_owner('BlackNunchucks','codex')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/BlackNunchucks.blend'))
names={'blacknunchucks_basecolor.png':'T_BlackNunchucks_BaseColor','blacknunchucks_orm.png':'T_BlackNunchucks_ORM','blacknunchucks_normal_opengl.png':'T_BlackNunchucks_NormalGL'}
for im in bpy.data.images:
    if im.name in names: im.name=names[im.name]
    filename=Path(bpy.path.abspath(im.filepath)).name if im.filepath else ''
    if filename.startswith('blacknunchucks_') and (ROOT/'Textures/BlackNunchucks'/filename).is_file():
        im.filepath='//../Textures/BlackNunchucks/'+filename
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Assets/BlackNunchucks.blend'))
