"""Trace pilot v2 stage R4: bake the traced HIGH onto the game LOW and assemble the throat LOD0.

    blender -b work/tp_high.blend --factory-startup --python tp_rbake.py

Bake source  TP_Throat_HIGH_F (front relief grid + mouth ring): relief-domain maps (tp_rmaps: sampled reference
             tones, grime / polished edges from the traced relief) as emission, ring = sampled silver.
Bake target  TP_Throat_LOW_F (front half + front ring half, UV0).  Maps 2048: BaseColor, Roughness, Metallic,
             Normal (tangent, OpenGL/Blender convention), AO.
LOD0         = LOW_F + its mirror (the back half SHARES the front UVs; mirrored tangent frames are standard in UE),
             seam welded, material from the BAKED maps only.  -> work/tp_low.blend (SM_SnowFlower_Throat_TP_LOD0)."""
import bpy, bmesh, sys, os, json, math, time
import numpy as np

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
TEX = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/Textures"
os.makedirs(TEX, exist_ok=True)
RES = 2048
t0 = time.time()
def log(*a): print("[TP-BAKE]", f"{time.time() - t0:6.1f}s", *a, flush=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
tones = json.load(open(WORK + "/tones.json"))["albedo_linear"]
hp = bpy.data.objects["TP_Throat_HIGH_F"]
high_tris = sum(len(p.vertices) - 2 for p in bpy.data.objects["TP_Throat_HIGH"].data.polygons)
for o in list(sc.objects):
    if o is not hp:
        bpy.data.objects.remove(o)
with bpy.data.libraries.load(WORK + "/tp_lowgeo.blend") as (src, dst):
    dst.objects = ["TP_Throat_LOW_F"]
low = dst.objects[0]; sc.collection.objects.link(low)
low.data.materials.clear()
mat = bpy.data.materials.new("M_SnowFlower_Throat_TP"); low.data.materials.append(mat)

# ------------------------------------------------------------------ bake-source materials (emission)
def img(name, noncolor):
    im = bpy.data.images.load(WORK + f"/relief_{name}.png", check_existing=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im
IMS = {"BC": img("BC", False), "R": img("R", True), "M": img("M", True)}
CH = {}
m = bpy.data.materials["TP_Relief"]; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(em.outputs[0], out.inputs["Surface"])
uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "REF"
src = {}
for k, im in IMS.items():
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = im; t.interpolation = 'Cubic'
    nt.links.new(uvn.outputs[0], t.inputs[0]); src[k] = t.outputs["Color"]
CH["TP_Relief"] = (nt, em, src)
m2 = bpy.data.materials["TP_RingSilver"]; m2.use_nodes = True; nt2 = m2.node_tree; nt2.nodes.clear()
out2 = nt2.nodes.new("ShaderNodeOutputMaterial"); em2 = nt2.nodes.new("ShaderNodeEmission")
nt2.links.new(em2.outputs[0], out2.inputs["Surface"])
sil = tones["silver"]
src2 = {}
for k, val in (("BC", (sil[0] * 1.3, sil[1] * 1.3, sil[2] * 1.3)), ("R", (0.44,) * 3), ("M", (1.0,) * 3)):
    n = nt2.nodes.new("ShaderNodeRGB"); n.outputs[0].default_value = (*val, 1); src2[k] = n.outputs[0]
CH["TP_RingSilver"] = (nt2, em2, src2)
def set_channel(k):
    for nm, (nt_, em_, s_) in CH.items():
        nt_.links.new(s_[k], em_.inputs["Color"])

# ------------------------------------------------------------------ bake
def new_img(name, noncolor):
    im = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im
IM = {"BC": new_img("T_Throat_TP_BC", False), "R": new_img("T_Throat_TP_Rough", True), "M": new_img("T_Throat_TP_Metal", True),
      "N": new_img("T_Throat_TP_N", True), "AO": new_img("T_Throat_TP_AO", True)}
mat.use_nodes = True
lnt = mat.node_tree
tex = lnt.nodes.new("ShaderNodeTexImage"); lnt.nodes.active = tex
for o in sc.objects: o.select_set(False)
hp.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
for attr in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
    setattr(low, attr, False)
bk = sc.render.bake
bk.use_selected_to_active = True; bk.use_cage = False
bk.cage_extrusion = float(os.environ.get("TP_CAGE", "0.004")); bk.max_ray_distance = float(os.environ.get("TP_RAY", "0.009"))
bk.margin = 16; bk.margin_type = 'EXTEND'
sc.cycles.use_denoising = False
def bake(key, btype, **kw):
    tex.image = IM[key]
    bpy.ops.object.bake(type=btype, **kw)
    IM[key].filepath_raw = TEX + f"/{IM[key].name}.png"; IM[key].file_format = 'PNG'; IM[key].save()
    log("baked", key)
sc.cycles.samples = 4
for key in ("BC", "R", "M"):
    set_channel(key); bake(key, 'EMIT')
sc.cycles.samples = 64
bake("AO", 'AO')
sc.cycles.samples = 8
bake("N", 'NORMAL', normal_space='TANGENT')
for attr in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
    setattr(low, attr, True)

# ------------------------------------------------------------------ LOD0 = front + mirrored back (shared UVs)
me = low.data.copy(); me.name = "back"
V = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3); V[:, 1] *= -1
me.vertices.foreach_set("co", V.ravel())
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
back = bpy.data.objects.new("back", me); sc.collection.objects.link(back)
for o in sc.objects: o.select_set(False)
low.select_set(True); back.select_set(True); bpy.context.view_layer.objects.active = low
bpy.ops.object.join()
bm = bmesh.new(); bm.from_mesh(low.data)
nv0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if abs(v.co.y) < 1e-6], dist=1e-6)
log("seam welded verts", nv0 - len(bm.verts))
bm.to_mesh(low.data); bm.free()
low.name = low.data.name = "SM_SnowFlower_Throat_TP_LOD0"
bpy.data.objects.remove(hp)
for o in sc.objects: o.select_set(False)
low.select_set(True); bpy.context.view_layer.objects.active = low
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(55))
ntri = sum(len(p.vertices) - 2 for p in low.data.polygons)
# texel density: 3D area of the FRONT half vs its UV area (the back reuses it)
me = low.data
A3 = 0.0; Auv = 0.0
uv = me.uv_layers["UV0"].data
for p in me.polygons:
    if p.center.y > 0:
        continue
    A3 += p.area * 1e6
    pts = [uv[li].uv for li in p.loop_indices]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[0], pts[i], pts[i + 1]
        Auv += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
tdens = math.sqrt(Auv * RES * RES / A3)
log(f"LOD0 tris {ntri} verts {len(me.vertices)}; front surface {A3:.0f} mm2 uv cov {Auv:.3f} texel {tdens:.2f} px/mm")
# material from the baked maps only
lnt.nodes.clear()
out = lnt.nodes.new("ShaderNodeOutputMaterial"); bs = lnt.nodes.new("ShaderNodeBsdfPrincipled")
lnt.links.new(bs.outputs[0], out.inputs["Surface"])
def img_node(key):
    n = lnt.nodes.new("ShaderNodeTexImage"); n.image = IM[key]; return n
lnt.links.new(img_node("BC").outputs["Color"], bs.inputs["Base Color"])
lnt.links.new(img_node("R").outputs["Color"], bs.inputs["Roughness"])
lnt.links.new(img_node("M").outputs["Color"], bs.inputs["Metallic"])
nm_ = lnt.nodes.new("ShaderNodeNormalMap"); nm_.uv_map = "UV0"
lnt.links.new(img_node("N").outputs["Color"], nm_.inputs["Color"]); lnt.links.new(nm_.outputs[0], bs.inputs["Normal"])
for k, im in IM.items():
    im.filepath = TEX + f"/{im.name}.png"; im.source = 'FILE'
json.dump({"lod0_tris": ntri, "lod0_verts": len(me.vertices), "texel_px_per_mm": tdens, "texture_res": RES,
           "front_surface_mm2": A3, "uv_coverage_front": Auv, "uv_shared_front_back": True,
           "high_tris": high_tris}, open(WORK + "/low_report.json", "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=WORK + "/tp_low.blend")
log("saved tp_low.blend")
