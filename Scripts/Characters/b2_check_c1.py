"""Independent numbers check for step C1 (PRIVATE / DO NOT SHIP 2B rig export).

Run headless in a FRESH Blender:
  blender -b --factory-startup -P b2_check_c1.py
Reads only; writes checks_c1/check_c1.json.
"""
import bpy, os, json, hashlib, math, sys
from collections import Counter
from mathutils import Vector

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
WD = ROOT + "/WorkFiles/Characters/2B_private"
FBX = WD + "/export/SK_2B_Private.fbx"
TEX = WD + "/export/textures"
OUT = WD + "/checks_c1"
MH = ROOT + "/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend"
GLB = ROOT + "/References/Characters/2B_kimono_private/source/28.glb"
GLB_SHA = "8d8143d12c8cf7f0d147fd29a3a5175b10f2b3ffd8fd850b3bde457207057135"
BASE = WD + "/2B_private_base.blend"
RIG = WD + "/2B_private_rig.blend"
os.makedirs(OUT, exist_ok=True)
R = {}

# ---------- raw FBX header ----------
from io_scene_fbx import parse_fbx
root_el, ver = parse_fbx.parse(FBX)
def find(el, name):
    return [e for e in el.elems if e.id == name.encode()]
gs = {}
for g in find(root_el, "GlobalSettings"):
    for p70 in find(g, "Properties70"):
        for p in p70.elems:
            gs[p.props[0].decode()] = [x.decode() if isinstance(x, bytes) else x for x in p.props[4:]]
R["fbx_version"] = ver
R["fbx_global_settings"] = {k: gs.get(k) for k in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign",
                                                  "CoordAxis", "CoordAxisSign", "UnitScaleFactor",
                                                  "OriginalUnitScaleFactor")}
# texture filenames referenced in the file
tex_refs = set()
objs = find(root_el, "Objects")
for o in objs:
    for e in o.elems:
        if e.id in (b"Texture", b"Video"):
            for sub in e.elems:
                if sub.id in (b"FileName", b"RelativeFilename", b"Filename"):
                    tex_refs.add(sub.props[0].decode(errors="replace"))
R["fbx_texture_refs"] = sorted(tex_refs)

# ---------- import ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)  # defaults; importer reads axes/units from file
bpy.context.view_layer.update()
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
R["objects"] = [(o.name, o.type, o.parent.name if o.parent else None,
                 [round(v, 4) for v in o.scale], [round(math.degrees(v), 2) for v in o.rotation_euler])
                for o in bpy.data.objects]
arm = arms[0]
R["armature_count"] = len(arms)
R["unit_note"] = ("Blender importer converts file units to metres; object scale shown above. "
                  "UnitScaleFactor=1 means 1 FBX unit = 1 cm.")

# bounds in world space (rest pose)
dg = bpy.context.evaluated_depsgraph_get()
allz, per = [], {}
for m in meshes:
    me = m.evaluated_get(dg).to_mesh()
    mw = m.matrix_world
    co = [mw @ v.co for v in me.vertices]
    per[m.name] = {"min": [round(min(c[i] for c in co), 4) for i in range(3)],
                   "max": [round(max(c[i] for c in co), 4) for i in range(3)]}
    allz += [c.z for c in co]
    m.evaluated_get(dg).to_mesh_clear()
R["mesh_bounds_m"] = per
zmin = min(allz); zmax = max(allz)
R["height_cm"] = round((zmax - zmin) * 100, 2)
R["zmin_cm"] = round(zmin * 100, 3)
# feet: lowest points left/right
body = next((m for m in meshes if "Body" in m.name), meshes[0])
bco = [body.matrix_world @ v.co for v in body.data.vertices]
R["foot_min_z_cm"] = {"x>0": round(min(c.z for c in bco if c.x > 0.02) * 100, 3),
                      "x<0": round(min(c.z for c in bco if c.x < -0.02) * 100, 3)}

# facing: head bone and face (nose tip = most extreme y among head-height verts near x=0)
aw = arm.matrix_world
bw = {b.name: (aw @ b.head_local, aw @ b.tail_local) for b in arm.data.bones}
head_h = bw.get("head", (Vector(), Vector()))[0]
face = [c for c in bco if c.z > head_h.z and abs(c.x) < 0.01]
ymin = min(c.y for c in face); ymax = max(c.y for c in face)
cy = sum(c.y for c in face) / len(face)
R["head_y_extent_m"] = [round(ymin, 4), round(ymax, 4), round(cy, 4)]
# toes: foot_l ball vs ankle
fl = bw.get("foot_l"); bl = bw.get("ball_l")
R["foot_l_head"] = [round(v, 4) for v in fl[0]] if fl else None
R["ball_l_head"] = [round(v, 4) for v in bl[0]] if bl else None
toes_y = (bl[0].y - fl[0].y) if (fl and bl) else None
R["toe_direction_blender"] = ("-Y" if toes_y < 0 else "+Y") if toes_y is not None else None
# nose sticks out further than back of head? use eye bones or eye meshes
hp = next((m for m in meshes if "HeadParts" in m.name), None)
if hp:
    hco = [hp.matrix_world @ v.co for v in hp.data.vertices]
    R["headparts_center_y"] = round(sum(c.y for c in hco) / len(hco), 4)
    R["head_bone_y"] = round(head_h.y, 4)
R["left_side_x_sign"] = None
cl = bw.get("clavicle_l");
if cl: R["left_side_x_sign"] = "+X" if cl[1].x > 0 else "-X"

# ---------- bones vs MetaHuman ----------
names_fbx = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
with bpy.data.libraries.load(MH, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n == "root"]
mho = dst.objects[0]
mh = {b.name: (b.parent.name if b.parent else None) for b in mho.data.bones}
R["mh_armature_bones"] = len(mh)
R["fbx_bones"] = len(names_fbx)
R["fbx_root_bones"] = [n for n, p in names_fbx.items() if p is None]
R["extra_bones_not_in_mh"] = sorted(n for n in names_fbx if n not in mh)
R["parent_mismatch"] = sorted((n, p, mh[n]) for n, p in names_fbx.items() if n in mh and mh[n] != p)
R["armature_object_name"] = arm.name
# rest orientation deviation vs MH (local, in armature space)
dev = {}
for b in arm.data.bones:
    if b.name in mho.data.bones:
        mb = mho.data.bones[b.name]
        q1 = (arm.matrix_world.to_3x3() @ b.matrix_local.to_3x3()).to_quaternion()
        q2 = (mho.matrix_world.to_3x3() @ mb.matrix_local.to_3x3()).to_quaternion()
        dev[b.name] = round(math.degrees(q1.rotation_difference(q2).angle), 2)
R["rest_rot_dev_vs_mh_deg_max"] = max(dev.values()) if dev else None
R["rest_rot_dev_top"] = sorted(dev.items(), key=lambda kv: -kv[1])[:8]
bpy.data.objects.remove(mho)

# ---------- weights / tris ----------
bone_set = set(names_fbx)
W = {}
tot_tris = 0
for m in meshes:
    me = m.data
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    tot_tris += tris
    gi = {g.index: g.name for g in m.vertex_groups}
    nonbone = [g.name for g in m.vertex_groups if g.name not in bone_set]
    bad_sum = 0; no_w = 0; maxinf = 0; inf_hist = Counter(); worst = 0.0
    bone_usage = Counter()
    for v in me.vertices:
        ws = [(gi[g.group], g.weight) for g in v.groups if gi.get(g.group) in bone_set and g.weight > 0]
        n = len(ws)
        inf_hist[n] += 1
        maxinf = max(maxinf, n)
        if n == 0:
            no_w += 1; continue
        s = sum(w for _, w in ws)
        if abs(s - 1) > 0.01:
            bad_sum += 1; worst = max(worst, abs(s - 1))
        for b, w in ws:
            bone_usage[b] += w
    mods = [(md.type, getattr(md, "object", None) and md.object.name) for md in m.modifiers]
    W[m.name] = {"verts": len(me.vertices), "tris": tris, "materials": [s.material.name if s.material else None for s in m.material_slots],
                 "weight_sum_bad": bad_sum, "worst_sum_dev": round(worst, 4), "no_weight_verts": no_w,
                 "max_influences": maxinf, "influence_hist": dict(sorted(inf_hist.items())),
                 "nonbone_groups": nonbone, "modifiers": mods, "parent": m.parent.name if m.parent else None,
                 "top_bones": bone_usage.most_common(6)}
    if "HeadParts" in m.name:
        # rigid: every vertex 100% head
        nonhead = 0
        for v in me.vertices:
            ws = {gi[g.group]: g.weight for g in v.groups if gi.get(g.group) in bone_set and g.weight > 0}
            if abs(ws.get("head", 0) - 1) > 0.01:
                nonhead += 1
        W[m.name]["verts_not_100pct_head"] = nonhead
R["meshes"] = W
R["total_tris"] = tot_tris

# ---------- textures ----------
img = []
for mat in bpy.data.materials:
    if not mat.node_tree: continue
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            p = bpy.path.abspath(n.image.filepath)
            img.append((mat.name, os.path.basename(p), os.path.normpath(os.path.dirname(p)) == os.path.normpath(TEX),
                        os.path.isfile(os.path.join(TEX, os.path.basename(p)))))
R["material_images"] = img
R["fbx_tex_refs_exist_in_textures_dir"] = {os.path.basename(t.replace("\\", "/")): os.path.isfile(os.path.join(TEX, os.path.basename(t.replace("\\", "/")))) for t in tex_refs}
R["mats_without_image"] = [m.name for m in bpy.data.materials if not any(n.type == "TEX_IMAGE" for n in (m.node_tree.nodes if m.node_tree else []))]
R["textures_dir_files"] = sorted(os.listdir(TEX))

# ---------- source integrity ----------
h = hashlib.sha256()
with open(GLB, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
R["glb_sha256"] = h.hexdigest()
R["glb_sha_ok"] = h.hexdigest() == GLB_SHA
R["base_mtime"] = os.path.getmtime(BASE); R["rig_mtime"] = os.path.getmtime(RIG)
R["fbx_mtime"] = os.path.getmtime(FBX)
R["base_older_than_rig"] = R["base_mtime"] < R["rig_mtime"]

with open(OUT + "/check_c1.json", "w") as f:
    json.dump(R, f, indent=1, default=str)
print("CHECK_C1_DONE")
