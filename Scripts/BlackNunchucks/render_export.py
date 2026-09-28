"""Render the actual GLB in the saved studio; never save over the source."""
from pathlib import Path
import bpy, json, hashlib, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Scripts'))
from pipeline.lock import assert_owner
assert_owner('BlackNunchucks','codex')
source=ROOT/'Assets/BlackNunchucks.blend'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
for ob in list(bpy.data.collections['BLACK_NUNCHUCKS'].objects): bpy.data.objects.remove(ob,do_unlink=True)
# Drop source-only material compatibility groups before importing in this
# existing studio; a fresh import should create its own complete group schema.
for group in list(bpy.data.node_groups):
    if group.name.startswith('glTF Material Output'): bpy.data.node_groups.remove(group,do_unlink=True)
glb=ROOT/'Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.glb'
bpy.ops.import_scene.gltf(filepath=str(glb),disable_bone_shape=True)
s=bpy.context.scene;s.cycles.samples=96
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU';s.render.filepath=str(ROOT/'Renders/BlackNunchucks/BlackNunchucks_ExportCheck.png')
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
(ROOT/'WorkFiles/BlackNunchucks/export_render.json').write_text(json.dumps({'glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'source_sha256':sha,'source_unchanged':True,'render':'BlackNunchucks_ExportCheck.png'},indent=2))
