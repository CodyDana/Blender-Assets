"""Trace pilot stage 4: game throat (LOD0) + bake from the traced high poly.

    blender -b work/tp_high.blend --factory-startup --python tp_lowbake.py -- [target_tris]

LOW  = voxel remesh of the high poly (one closed shell, hidden layers fused) -> collapse decimate to the budget ->
       smooth by angle -> smart UV + pack.
Maps (2048): BaseColor (antiqued silver / enamel / pearl / lacquer colours SAMPLED from the reference, grime in the
       recesses from a local AO, polished edges from an inside-AO), Roughness, Metallic, Normal (tangent), AO.
Colours: work/tones.json (tp_tones.py) - sampled reference tones, optionally scaled by the calibration factor."""
import bpy, bmesh, sys, os, json, math, time
import numpy as np

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
TEX = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/Textures"
os.makedirs(TEX, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TARGET = int(argv[0]) if argv else 6500
RES = 2048
t0 = time.time()
def log(*a): print("[TP-LOW]", f"{time.time() - t0:6.1f}s", *a, flush=True)

tones = json.load(open(WORK + "/tones.json"))
hp = bpy.data.objects["TP_Throat_HIGH"]
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'

# ------------------------------------------------------------------ LOW
MODE = os.environ.get("TP_LOWMODE", "geo")
if MODE == "geo":
    # the game mesh built by the same traced construction at game resolution (tp_build.py with TP_LOWRES=1)
    with bpy.data.libraries.load(WORK + "/tp_lowgeo.blend") as (src, dst):
        dst.objects = ["TP_Throat_LOWGEO"]
    low = dst.objects[0]; sc.collection.objects.link(low)
    low.name = "SM_SnowFlower_Throat_TP_LOD0"; low.data.name = low.name
    n0 = sum(len(p.vertices) - 2 for p in low.data.polygons)
else:
    low = hp.copy(); low.data = hp.data.copy(); low.name = "SM_SnowFlower_Throat_TP_LOD0"; low.data.name = low.name
    sc.collection.objects.link(low)
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = low; low.select_set(True)
if MODE != "geo":
    m = low.modifiers.new("rm", 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = 0.00032; m.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier="rm")
    n0 = sum(len(p.vertices) - 2 for p in low.data.polygons)
log("start tris", n0, "mode", MODE)
for _ in range(3):
    ntri = sum(len(p.vertices) - 2 for p in low.data.polygons)
    if ntri <= TARGET * 1.005:
        break
    m = low.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = TARGET / ntri
    m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="dec")
ntri = sum(len(p.vertices) - 2 for p in low.data.polygons)
log("LOD0 tris", ntri, "verts", len(low.data.vertices))
low.data.materials.clear()
mat = bpy.data.materials.new("M_SnowFlower_Throat_TP"); low.data.materials.append(mat)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
# UV: unwrap a Laplacian-smoothed PROXY (same topology) so the islands follow the crown's large forms instead of the
# decimation noise (1764 islands / 26 % coverage when unwrapped directly), then copy the UVs back.
prox = low.copy(); prox.data = low.data.copy(); sc.collection.objects.link(prox)
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = prox; prox.select_set(True)
if MODE != "geo":
    m = prox.modifiers.new("sm", 'SMOOTH'); m.factor = 1.0; m.iterations = 20
    bpy.ops.object.modifier_apply(modifier="sm")
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004, rotate=True, scale=True)
bpy.ops.object.mode_set(mode='OBJECT')
if not low.data.uv_layers:
    low.data.uv_layers.new(name="UV0")
src_uv = prox.data.uv_layers[0].data; dst_uv = low.data.uv_layers[0].data
for i in range(len(src_uv)):
    dst_uv[i].uv = src_uv[i].uv
bpy.data.objects.remove(prox)
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = low; low.select_set(True)
low.data.uv_layers[0].name = "UV0"
# texel density: sum of 3D area vs UV area
me = low.data
A3 = sum(p.area for p in me.polygons) * 1e6          # mm^2
uv = me.uv_layers[0].data
Auv = 0.0
for p in me.polygons:
    pts = [uv[li].uv for li in p.loop_indices]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[0], pts[i], pts[i + 1]
        Auv += abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2
tdens = math.sqrt(Auv * RES * RES / A3)
log(f"surface {A3:.0f} mm2, uv coverage {Auv:.3f}, texel density {tdens:.2f} px/mm at {RES}")

# ------------------------------------------------------------------ HIGH bake materials
def lin(c): return [((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c]
CH = {}
def bake_mat(name, bc, rough, metal, grime=0.0, edge=0.0, rough_grime=0.6, rough_edge=None):
    mt = bpy.data.materials[name]; mt.use_nodes = True; nt = mt.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    col = nt.nodes.new("ShaderNodeRGB"); col.outputs[0].default_value = (*bc, 1)
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.only_local = True
    ao.inputs["Distance"].default_value = 0.0016
    aoi = nt.nodes.new("ShaderNodeAmbientOcclusion"); aoi.samples = 16; aoi.only_local = True; aoi.inside = True
    aoi.inputs["Distance"].default_value = 0.0006
    # grime mask g = clamp((0.9 - ao) / 0.55)
    g = nt.nodes.new("ShaderNodeMapRange"); g.inputs["From Min"].default_value = 0.9; g.inputs["From Max"].default_value = 0.35
    nt.links.new(ao.outputs["AO"], g.inputs["Value"])
    # edge mask e = clamp((0.75 - aoi) / 0.5)
    e = nt.nodes.new("ShaderNodeMapRange"); e.inputs["From Min"].default_value = 0.8; e.inputs["From Max"].default_value = 0.3
    nt.links.new(aoi.outputs["AO"], e.inputs["Value"])
    gm = nt.nodes.new("ShaderNodeMath"); gm.operation = 'MULTIPLY'; gm.inputs[1].default_value = grime
    nt.links.new(g.outputs[0], gm.inputs[0])
    emk = nt.nodes.new("ShaderNodeMath"); emk.operation = 'MULTIPLY'; emk.inputs[1].default_value = edge
    nt.links.new(e.outputs[0], emk.inputs[0])
    dark = nt.nodes.new("ShaderNodeRGB"); dark.outputs[0].default_value = (bc[0] * 0.22, bc[1] * 0.22, bc[2] * 0.24, 1)
    bright = nt.nodes.new("ShaderNodeRGB"); bright.outputs[0].default_value = (min(bc[0] * 1.35, 1), min(bc[1] * 1.35, 1), min(bc[2] * 1.35, 1), 1)
    m1 = nt.nodes.new("ShaderNodeMix"); m1.data_type = 'RGBA'
    nt.links.new(gm.outputs[0], m1.inputs["Factor"]); nt.links.new(col.outputs[0], m1.inputs["A"]); nt.links.new(dark.outputs[0], m1.inputs["B"])
    m2 = nt.nodes.new("ShaderNodeMix"); m2.data_type = 'RGBA'
    nt.links.new(emk.outputs[0], m2.inputs["Factor"]); nt.links.new(m1.outputs["Result"], m2.inputs["A"]); nt.links.new(bright.outputs[0], m2.inputs["B"])
    # roughness = rough + grime*(rough_grime - rough) + edge*(rough_edge - rough)
    r0 = nt.nodes.new("ShaderNodeValue"); r0.outputs[0].default_value = rough
    rg = nt.nodes.new("ShaderNodeMapRange"); rg.inputs["To Min"].default_value = rough; rg.inputs["To Max"].default_value = rough_grime
    nt.links.new(gm.outputs[0], rg.inputs["Value"])
    re_ = nt.nodes.new("ShaderNodeMapRange"); re_.inputs["To Min"].default_value = 0.0
    re_.inputs["To Max"].default_value = ((rough_edge if rough_edge is not None else rough) - rough)
    nt.links.new(emk.outputs[0], re_.inputs["Value"])
    radd = nt.nodes.new("ShaderNodeMath"); radd.operation = 'ADD'
    nt.links.new(rg.outputs[0], radd.inputs[0]); nt.links.new(re_.outputs[0], radd.inputs[1])
    mv = nt.nodes.new("ShaderNodeValue"); mv.outputs[0].default_value = metal
    CH[name] = {"bc": m2.outputs["Result"], "rough": radd.outputs[0], "metal": mv.outputs[0], "em": em, "nt": nt}

T = tones["albedo_linear"]
bake_mat("TP_Silver", T["silver"], 0.45, 1.0, grime=1.0, edge=0.8, rough_grime=0.7, rough_edge=0.28)
bake_mat("TP_Enamel", T["enamel"], 0.2, 0.0, grime=0.3, edge=0.0, rough_grime=0.45)
bake_mat("TP_Pearl", T["pearl"], 0.26, 0.0, grime=0.35, edge=0.0, rough_grime=0.4)
bake_mat("TP_Lacquer", T["lacquer"], 0.28, 0.0, grime=0.2, edge=0.0, rough_grime=0.5)

def set_channel(ch):
    for nm, d in CH.items():
        d["nt"].links.new(d[ch], d["em"].inputs["Color"])

# ------------------------------------------------------------------ bake
def new_img(name, noncolor):
    im = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im
IM = {"BC": new_img("T_Throat_TP_BC", False), "R": new_img("T_Throat_TP_Rough", True), "M": new_img("T_Throat_TP_Metal", True),
      "N": new_img("T_Throat_TP_N", True), "AO": new_img("T_Throat_TP_AO", True)}
mat.use_nodes = True
lnt = mat.node_tree
tex = lnt.nodes.new("ShaderNodeTexImage")
lnt.nodes.active = tex
for o in sc.objects: o.select_set(False)
hp.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
# the LOW must not occlude / shadow the HIGH during the bake (it sits within 0.3 mm of it)
for attr in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
    setattr(low, attr, False)
bk = sc.render.bake
bk.use_selected_to_active = True; bk.use_cage = False; bk.cage_extrusion = 0.002; bk.max_ray_distance = 0.005
bk.margin = 12; bk.margin_type = 'EXTEND'
sc.cycles.samples = 24
sc.cycles.use_denoising = False
def bake(key, btype, **kw):
    tex.image = IM[key]
    bpy.ops.object.bake(type=btype, **kw)
    IM[key].filepath_raw = TEX + f"/{IM[key].name}.png"; IM[key].file_format = 'PNG'; IM[key].save()
    log("baked", key)
for key, ch in (("BC", "bc"), ("R", "rough"), ("M", "metal")):
    set_channel(ch)
    bake(key, 'EMIT')
sc.cycles.samples = 64
bake("AO", 'AO')
sc.cycles.samples = 8
bake("N", 'NORMAL', normal_space='TANGENT')

# ------------------------------------------------------------------ LOW material from the baked maps only
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
json.dump({"lod0_tris": ntri, "lod0_verts": len(low.data.vertices), "remesh_tris": n0, "texel_px_per_mm": tdens,
           "texture_res": RES, "surface_mm2": A3, "uv_coverage": Auv, "high_tris": sum(len(p.vertices) - 2 for p in hp.data.polygons)},
          open(WORK + "/low_report.json", "w"), indent=1)
bpy.data.objects.remove(hp)
for attr in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
    setattr(low, attr, True)
bpy.ops.wm.save_as_mainfile(filepath=WORK + "/tp_low.blend")
log("saved tp_low.blend")
