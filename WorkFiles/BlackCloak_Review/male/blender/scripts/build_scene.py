"""Builds the lean review scene: MH_PlayerDefault fit body (copy) + the exact in-game cloak FBX (copy, sha fb8d35a2), bound to the
SAME skeleton (the body's 'root' = metahuman_base_skel) the way the game's Leader Pose follower does it, with the game's materials
reproduced (M_BlackCloak two-sided, UV0 untiled, OpenGL normal; MI_BlackCloak_Steel / _Leather) and a second, labelled, TILED
wool material (UV x 7.8125 = the source sculpt's 'Meter UV to 128 mm tile'). Writes male_cloak_scene.blend + align json.
Run on the COPY: blender -b copies/FitBody_copy.blend --factory-startup --python build_scene.py
"""
import bpy, bmesh, json, math, hashlib
import mathutils
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blender/"
FBX = D + "copies/SKM_BlackCloak_MH.fbx"
TEX = D + "copies/tex/"
rep = {}
rep["fbx_sha256"] = hashlib.sha256(open(FBX, "rb").read()).hexdigest()
assert rep["fbx_sha256"].startswith("fb8d35a2"), rep["fbx_sha256"]

arm = bpy.data.objects["root"]
body = bpy.data.objects["FIT_MH_PlayerDefault_Body"]
head = bpy.data.objects["FIT_MH_PlayerDefault_Head"]
parts = bpy.data.objects["FIT_MH_PlayerDefault_HeadParts"]
hairp = bpy.data.objects["FIT_MH_PlayerDefault_HairProxy"]
# lean: drop the 46k-vert hair cards (the helmet proxy stands in for the hair, as in the fit)
bpy.data.objects.remove(bpy.data.objects["FIT_MH_PlayerDefault_HairCards"], do_unlink=True)
for o in list(bpy.data.objects):
    if o.type in {"CAMERA", "LIGHT"} or (o.type == "MESH" and o not in (body, head, parts, hairp)):
        print("removing extra", o.name); bpy.data.objects.remove(o, do_unlink=True)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=FBX, automatic_bone_orientation=False)
new = set(bpy.data.objects) - before
farm = next(o for o in new if o.type == "ARMATURE")
cloak = next(o for o in new if o.type == "MESH")
bpy.context.view_layer.update()

# --- bind-pose agreement between the cloak's own skeleton (FBX) and the body's (the game uses the body's bones)
used = [g.name for g in cloak.vertex_groups]
diffs = {}
for b in farm.data.bones:
    if b.name in arm.data.bones:
        m1 = farm.matrix_world @ b.matrix_local
        m2 = arm.matrix_world @ arm.data.bones[b.name].matrix_local
        dp = (m1.translation - m2.translation).length
        q1 = m1.to_quaternion(); q2 = m2.to_quaternion()
        da = math.degrees(q1.rotation_difference(q2).angle)
        diffs[b.name] = (dp, da)
rep["bind_pose_compare"] = {
    "bones_compared": len(diffs),
    "max_pos_diff_m_all": max(v[0] for v in diffs.values()),
    "max_rot_diff_deg_all": max(v[1] for v in diffs.values()),
    "used_bones": {n: {"pos_diff_m": diffs[n][0], "rot_diff_deg": diffs[n][1]} for n in used},
}
# world position of the cloak verts before re-binding (the FBX's own skeleton at rest)
dg = bpy.context.evaluated_depsgraph_get()
ev = cloak.evaluated_get(dg); me0 = ev.to_mesh()
pre = [cloak.matrix_world @ v.co for v in me0.vertices]
ev.to_mesh_clear()

mw = cloak.matrix_world.copy()
cloak.parent = arm
cloak.matrix_world = mw
for m in cloak.modifiers:
    if m.type == "ARMATURE":
        m.object = arm
bpy.data.objects.remove(farm, do_unlink=True)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = cloak.evaluated_get(dg); me1 = ev.to_mesh()
post = [cloak.matrix_world @ v.co for v in me1.vertices]
ev.to_mesh_clear()
rep["rebind_vertex_shift_max_m"] = max((a - b).length for a, b in zip(pre, post))
cloak.name = "SKM_BlackCloak_MH"

# --- cloak vs body clearance at rest (the shape the game's cloth starts from)
def bvh_of(objs):
    bm = bmesh.new()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh()
        tmp = bmesh.new(); tmp.from_mesh(m); tmp.transform(o.matrix_world)
        mm = bpy.data.meshes.new("tmp"); tmp.to_mesh(mm); tmp.free()
        bm.from_mesh(mm); bpy.data.meshes.remove(mm); e.to_mesh_clear()
    bm.normal_update()
    return BVHTree.FromBMesh(bm), bm

skin_bvh, skin_bm = bvh_of([body, head])
inside = 0; near = []
dists = []
for p in post:
    loc, nrm, idx, d = skin_bvh.find_nearest(p, 0.5)
    if loc is None: continue
    s = (p - loc).dot(nrm)
    sd = d if s >= 0 else -d
    dists.append((sd, p))
    if sd < -0.001: inside += 1
dists.sort(key=lambda t: t[0])
rep["clearance_rest"] = {
    "verts_checked_within_50cm": len(dists), "verts_inside_skin_gt_1mm": inside,
    "min_signed_cm": dists[0][0] * 100, "min_at": list(dists[0][1]),
    "verts_under_1cm": sum(1 for d in dists if d[0] < 0.01),
    "verts_under_0p5cm": sum(1 for d in dists if d[0] < 0.005),
    "p1_cm": dists[len(dists) // 100][0] * 100,
}
skin_bm.free()

# --- bounds
def wb(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh()
    pts = [o.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]
rep["bounds_cloak_m"] = wb(cloak); rep["bounds_body_m"] = wb(body); rep["bounds_head_m"] = wb(head)

# --- UV density per material slot of the cloak (UV units per metre, the game's UV0)
me = cloak.data; uvl = me.uv_layers[0].data
dens = {}
for p in me.polygons:
    if len(p.vertices) < 3: continue
    vs = [me.vertices[i].co for i in p.vertices]; uvs = [Vector(uvl[li].uv) for li in p.loop_indices]
    a3 = 0; a2 = 0
    for k in range(1, len(vs) - 1):
        a3 += ((vs[k] - vs[0]).cross(vs[k + 1] - vs[0])).length / 2
        e1 = uvs[k] - uvs[0]; e2 = uvs[k + 1] - uvs[0]; a2 += abs(e1.x * e2.y - e1.y * e2.x) / 2
    a3 *= (cloak.matrix_world.to_scale()[0]) ** 2
    s = dens.setdefault(p.material_index, [0, 0]); s[0] += a3; s[1] += a2
rep["uv_units_per_m_by_slot"] = {me.materials[k].name: math.sqrt(v[1] / v[0]) if v[0] else None for k, v in dens.items()}
rep["weave_repeat_cm_by_slot_untiled"] = {k: (100.0 / v if v else None) for k, v in rep["uv_units_per_m_by_slot"].items()}

# --- materials: exactly what the game draws
def img(name, cs):
    im = bpy.data.images.load(TEX + name, check_existing=True); im.colorspace_settings.name = cs; return im

def wool_mat(name, tile):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    uv = N.new("ShaderNodeUVMap"); uv.uv_map = me.uv_layers[0].name
    vec = uv.outputs[0]
    if tile != 1.0:
        sc = N.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs["Scale"].default_value = tile
        L.new(uv.outputs[0], sc.inputs[0]); vec = sc.outputs[0]
    bc = N.new("ShaderNodeTexImage"); bc.image = img("T_BlackCloak_BaseColor.png", "sRGB")
    rg = N.new("ShaderNodeTexImage"); rg.image = img("T_BlackCloak_Roughness.png", "Non-Color")
    nm = N.new("ShaderNodeTexImage"); nm.image = img("T_BlackCloak_Normal_OpenGL.png", "Non-Color")
    for t in (bc, rg, nm):
        t.interpolation = "Linear"; L.new(vec, t.inputs[0])
    L.new(bc.outputs["Color"], bs.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor"); L.new(rg.outputs["Color"], sep.inputs[0]); L.new(sep.outputs[0], bs.inputs["Roughness"])
    nmap = N.new("ShaderNodeNormalMap"); nmap.space = "TANGENT"; nmap.uv_map = me.uv_layers[0].name
    nmap.inputs["Strength"].default_value = 1.0
    L.new(nm.outputs["Color"], nmap.inputs["Color"]); L.new(nmap.outputs[0], bs.inputs["Normal"])
    bs.inputs["Specular IOR Level"].default_value = 0.065   # UE Specular 0.065 (F0 = 0.08*spec in both)
    bs.inputs["Metallic"].default_value = 0.0
    m.use_backface_culling = False                          # M_BlackCloak two_sided = True
    return m

def solid_mat(name, col, rough, metal):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (*col, 1); bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal; bs.inputs["Specular IOR Level"].default_value = 0.5
    return m

GAME = {"wool": wool_mat("GAME_M_BlackCloak_UV0", 1.0),
        "steel": solid_mat("GAME_MI_BlackCloak_Steel", (0.04, 0.041, 0.038), 0.42, 0.85),
        "leather": solid_mat("GAME_MI_BlackCloak_Leather", (0.014, 0.011, 0.008), 0.66, 0.0)}
TILED = wool_mat("TILED_M_BlackCloak_UVx7.8125_12.8cm", 7.8125)
slot_map = {}
for i, s in enumerate(cloak.material_slots):
    n = s.material.name if s.material else ""
    if "Steel" in n: s.material = GAME["steel"]
    elif "Leather" in n: s.material = GAME["leather"]
    else: s.material = GAME["wool"]
    slot_map[n] = s.material.name
rep["slot_map"] = slot_map
cloak["tiled_material"] = TILED.name
TILED.use_fake_user = True

# neutral body
skin = bpy.data.materials.new("NEUTRAL_Skin"); skin.use_nodes = True
b = next(n for n in skin.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.55, 0.50, 0.46, 1); b.inputs["Roughness"].default_value = 0.6
hairm = bpy.data.materials.new("NEUTRAL_Hair"); hairm.use_nodes = True
b = next(n for n in hairm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.03, 0.028, 0.026, 1); b.inputs["Roughness"].default_value = 0.7
eye = bpy.data.materials.new("NEUTRAL_Eye"); eye.use_nodes = True
b = next(n for n in eye.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.35, 0.34, 0.33, 1); b.inputs["Roughness"].default_value = 0.2
hide = bpy.data.materials.new("NEUTRAL_Hidden"); hide.use_nodes = True
nt = hide.node_tree
for n in list(nt.nodes):
    if n.type == "BSDF_PRINCIPLED": nt.nodes.remove(n)
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); nt.links.new(tr.outputs[0], out.inputs["Surface"])
for o in (body, head):
    for s in o.material_slots: s.material = skin
for s in hairp.material_slots: s.material = hairm
for s in parts.material_slots:
    n = s.material.name if s.material else ""
    if "Eye" in n and "Shell" not in n and "lash" not in n.lower(): s.material = eye
    elif "Skin" in n: s.material = skin
    else: s.material = hide

# collections for render toggles
def coll(name, objs):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    for o in objs:
        for u in list(o.users_collection): u.objects.unlink(o)
        c.objects.link(o)
coll("REV_Cloak", [cloak])
coll("REV_Body", [body, head, parts, hairp])
coll("REV_Rig", [arm])
for c in list(bpy.data.collections):
    if c.name not in ("REV_Cloak", "REV_Body", "REV_Rig") and not c.all_objects:
        bpy.data.collections.remove(c)

json.dump(rep, open(D + "logs/scene_build_report.json", "w"), indent=1, default=str)
bpy.ops.wm.save_as_mainfile(filepath=D + "male_cloak_scene.blend", compress=True)
print("REPORT", json.dumps(rep, default=str)[:4000])
