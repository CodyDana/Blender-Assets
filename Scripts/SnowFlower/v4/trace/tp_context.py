"""Trace pilot stage 5: assemble the PILOT blend - the traced game throat (LOD0, baked maps) on a COPY of the round-1
sheath body (snapshot r1_snapshot_interrupted/SnowFlower_Sheath.blend, LOD0), with the round-1 throat removed.

    blender -b --factory-startup --python tp_context.py

Body edits (copy only): Fittings-material faces above ref row 168 (the r1 throat, collar, sleeve, drips) are deleted;
the r1 lacquer core under the throat stays (hidden) and its top is lowered under the traced saddle-shaped mouth ring
where the ring dips (|x| > ~22 mm), so the core does not stick up above the ring.  Output:
trace_pilot/SnowFlower_Sheath_TracePilot.blend."""
import bpy, bmesh, json, os, sys, math
import numpy as np

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
SNAP = ROOT + "/WorkFiles/SnowFlower/v4/lookmatch/r1_snapshot_interrupted"
PILOT = ROOT + "/WorkFiles/SnowFlower/v4/trace_pilot"
WORK = PILOT + "/work"
K = 0.687
def zr(row): return (row - 304.0) * K

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
c_throat = bpy.data.collections.new("TP_Throat_LOD0"); sc.collection.children.link(c_throat)
c_ctx = bpy.data.collections.new("TP_Context_r1_body_copy"); sc.collection.children.link(c_ctx)
with bpy.data.libraries.load(WORK + "/tp_low.blend") as (src, dst):
    dst.objects = ["SM_SnowFlower_Throat_TP_LOD0"]
low = dst.objects[0]; c_throat.objects.link(low)
with bpy.data.libraries.load(SNAP + "/SnowFlower_Sheath.blend") as (src, dst):
    dst.objects = ["SM_SnowFlower_Sheath_LOD0"]
body = dst.objects[0]; c_ctx.objects.link(body)
body.name = "r1_Sheath_LOD0_body_copy"; body.parent = None
body.matrix_world = body.matrix_world  # already identity in the r1 file
# relink the body textures to the snapshot copies (never the live Exports folder)
for im in bpy.data.images:
    fn = os.path.basename(im.filepath)
    if fn.startswith("T_SnowFlower_Sheath_"):
        im.filepath = SNAP + "/Exports_v4/Textures/" + fn
        im.reload()
# --- remove the r1 throat
me = body.data
mats = [m.name for m in me.materials]
fit_idx = mats.index("M_SnowFlower_Sheath_Fittings")
bm = bmesh.new(); bm.from_mesh(me)
zcut = zr(168.0) / 1000.0
dele = [f for f in bm.faces if f.material_index == fit_idx and f.calc_center_median().z < zcut]
bmesh.ops.delete(bm, geom=dele, context='FACES')
# --- lower the core top under the saddle ring
rp = json.load(open(WORK + "/ring_profile.json"))
xs = np.array(rp["xs_mm"]); zt = np.array(rp["ztop_mm"])
moved = 0
for v in bm.verts:
    x, y, z = v.co.x * 1000, v.co.y * 1000, v.co.z * 1000
    if z < rp["z_ring_bottom_mm"]:
        zmin = float(np.interp(abs(x), xs, zt)) + 0.8
        if z < zmin:
            v.co.z = zmin / 1000.0; moved += 1
bm.to_mesh(me); bm.free()
print("[TP-CTX] deleted r1 throat faces:", len(dele), "core verts lowered under the ring:", moved)
ntri = sum(len(p.vertices) - 2 for p in me.polygons)
print("[TP-CTX] body copy tris", ntri, "throat LOD0 tris", sum(len(p.vertices) - 2 for p in low.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=PILOT + "/SnowFlower_Sheath_TracePilot.blend")
