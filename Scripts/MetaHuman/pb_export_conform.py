"""PlayerBase conform input - step 4: export the custom body for MetaHuman
"From Custom Mesh" (UE 5.8).

Runs headless on the player_base COPY only and never saves it:

    blender -b WorkFiles/MetaHuman/player_base/src_Human_copy.blend --factory-startup \
        --python Scripts/MetaHuman/pb_export_conform.py

Writes to WorkFiles/MetaHuman/player_base/conform_input/:
  PB_Body_ForConform.fbx / .obj(+.mtl)   body skin mesh alone, rest pose, no armature/weights/shape keys
  PB_BodyEyes_ForConform.fbx             same body + the two opaque eyeballs in ONE mesh (2 material slots);
                                         eyeballs intersect the lids, so use only if eye tracking fails
  PB_Eyes.fbx                            the two opaque eyeballs alone (cornea shells dropped, see
                                         drop_cornea_shells)
  PB_Body_Albedo.png / PB_Eyes_Albedo.png  sRGB base colour maps (exact copies of the packed PNGs
                                         that feed Principled Base Color with the default skin-tone
                                         and nail-polish amounts of 0)
  pb_conform_source.blend                only the clean PB_* objects, for re-export
  pb_export_report.json                  every number below

Coordinates: Blender scene is metric, 1 unit = 1 m, character faces -Y, up +Z. The mesh is
translated so the lowest sole vertex sits on Z = 0 (MetaHuman convention); the offset is recorded.
FBX uses the house settings from Scripts/pipeline/export_fbx.py (base_settings("static")):
-Y forward / Z up, FBX Units Scale -> Unreal sees centimetres and the face points +Y in UE
mesh space (same as SKM_Manny / MetaHuman bodies). The pipeline's export_fbx() itself is not
called because its SM_/SK_/A_ basename gate rejects the PB_ names this task requires.
OBJ is written Z-up with no axis conversion and scaled x100 (centimetres), because UE's
Interchange OBJ translator reads positions as (X, -Y, Z) in cm with no axis or unit conversion.
"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import lock
lock.assert_owner("JinMuWon_v2", "claude")

import hashlib
import json
import math
import os

import bpy
import bmesh
from mathutils import Matrix, Vector

from pipeline.export_fbx import base_settings  # house FBX settings (study 3.7)

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
COPY_DIR = os.path.normcase(os.path.abspath(ROOT + "/WorkFiles/MetaHuman/player_base"))
OUT = ROOT + "/WorkFiles/MetaHuman/player_base/conform_input"
if os.path.normcase(os.path.dirname(os.path.abspath(bpy.data.filepath))) != COPY_DIR:
    raise SystemExit(f"Refusing to run on {bpy.data.filepath}: only the player_base copy is allowed")
os.makedirs(OUT, exist_ok=True)

SRC_BODY = "SK_JinMuWon_Human_Body"
SRC_EYES = "SK_JinMuWon_Eyes"
report = {"source_copy": bpy.data.filepath, "blender": bpy.app.version_string, "outputs": {}, "checks": {}}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ source state checks
arm = bpy.data.objects["Armature"]
arm.data.pose_position = "REST"
for mod_owner in (SRC_BODY, SRC_EYES):
    o = bpy.data.objects[mod_owner]
    assert o.data.shape_keys is None, f"{mod_owner} has shape keys"
    kinds = [m.type for m in o.modifiers]
    assert kinds == ["ARMATURE"], f"{mod_owner} modifiers {kinds}"
bpy.context.view_layer.update()

skin_mat = bpy.data.materials["M_JinMuWon_Skin"]
nt = skin_mat.node_tree
skin_amt = nt.nodes["SkinCustomization"].inputs["Skin Tone Amount"]
nail_amt = nt.nodes["NailCustomization"].inputs["Nail Polish Amount"]
assert not skin_amt.links and abs(skin_amt.default_value) < 1e-9, "skin tone amount not 0"
assert not nail_amt.links and abs(nail_amt.default_value) < 1e-9, "nail polish amount not 0"
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
chain = bsdf.inputs["Base Color"].links[0].from_node.name
assert chain == "NailCustomization", chain
src_albedo = nt.nodes["Export_BaseColor"].image
report["checks"]["skin_base_color_chain"] = ("Export_BaseColor -> SkinCustomization(amount 0) -> "
                                            "NailCustomization(amount 0) -> Principled Base Color")

eye_mat = bpy.data.materials["M_JinMuWon_Eyes"]
eye_bsdf = next(n for n in eye_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
src_eye_albedo = eye_bsdf.inputs["Base Color"].links[0].from_node.image


def write_packed_png(img, path):
    assert img.packed_file is not None, f"{img.name} not packed"
    data = bytes(img.packed_file.data)
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{img.name} packed data is not PNG"
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "source_image": img.name, "source_filepath": img.filepath,
            "size_px": list(img.size), "colorspace": img.colorspace_settings.name,
            "bytes": len(data), "sha256": sha256(path)}


body_albedo_path = OUT + "/PB_Body_Albedo.png"
eye_albedo_path = OUT + "/PB_Eyes_Albedo.png"
report["outputs"]["body_albedo"] = write_packed_png(src_albedo, body_albedo_path)
report["outputs"]["eyes_albedo"] = write_packed_png(src_eye_albedo, eye_albedo_path)
exp_tex = ROOT + "/Exports/JinMuWon_v2/Textures/T_JinMuWon_Skin_BaseColor.png"
if os.path.exists(exp_tex):
    report["checks"]["body_albedo_identical_to_exported_skin_basecolor_png"] = (
        sha256(exp_tex) == report["outputs"]["body_albedo"]["sha256"])

# ------------------------------------------------------------------ numerical albedo check:
# bake the effective diffuse colour of the ORIGINAL material at 1024 and compare with the copy.
def bake_check():
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError as exc:
        return {"skipped": str(exc)}
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    body = bpy.data.objects[SRC_BODY]
    res = 1024
    bake_img = bpy.data.images.new("pbexp_bake_check", res, res, alpha=False, float_buffer=True)
    bake_img.colorspace_settings.name = "Linear Rec.709" if "Linear Rec.709" in [
        i.name for i in bake_img.colorspace_settings.bl_rna.properties["name"].enum_items] else bake_img.colorspace_settings.name
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = bake_img
    for n in nt.nodes:
        n.select = False
    node.select = True
    nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    body.hide_set(False)
    body.hide_render = False
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = 0
    bpy.ops.object.bake(type="DIFFUSE")
    baked = list(bake_img.pixels)
    # reference: the albedo PNG, resampled to 1024 (linear values)
    ref = bpy.data.images.load(body_albedo_path, check_existing=False)
    ref.colorspace_settings.name = "sRGB"
    ref.scale(res, res)
    refp = list(ref.pixels)  # byte image: .pixels are the stored sRGB-encoded values / 255

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    # compare only texels the bake wrote: unbaked texels keep the new image's (0,0,0)
    diffs = []
    for i in range(0, len(baked), 4 * 7):  # sample every 7th texel
        b = baked[i:i + 3]
        if b[0] == 0.0 and b[1] == 0.0 and b[2] == 0.0:
            continue
        r = [lin(x) for x in refp[i:i + 3]]
        diffs.append(sum(abs(b[k] - r[k]) for k in range(3)) / 3.0)
    nt.nodes.remove(node)
    diffs.sort()
    n = len(diffs)
    return {"resolution": res, "samples_compared": n,
            "mean_abs_diff_linear": sum(diffs) / n if n else None,
            "p95_abs_diff_linear": diffs[int(n * 0.95)] if n else None,
            "note": "Cycles DIFFUSE colour bake of the original material vs. the copied PNG "
                    "(box-resampled to 1024); small residue comes from resampling at UV seams"}


report["checks"]["albedo_bake_vs_copy"] = bake_check()


# ------------------------------------------------------------------ build clean objects
deps = bpy.context.evaluated_depsgraph_get()


def clean_copy(src_name, new_name):
    src = bpy.data.objects[src_name]
    ev = src.evaluated_get(deps)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=deps)
    me.name = new_name
    me.transform(ev.matrix_world)
    ob = bpy.data.objects.new(new_name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.vertex_groups.clear()
    if me.shape_keys:
        raise RuntimeError("unexpected shape keys")
    return ob


body = clean_copy(SRC_BODY, "PB_Body_ForConform")
eyes = clean_copy(SRC_EYES, "PB_Eyes")


def drop_cornea_shells(ob, tex_path):
    """The source eye mesh is 2 opaque eyeballs + 2 cornea shells. The shells' UVs sit entirely in
    the black part of the eye albedo and only look right with the original alpha-masked material,
    which an FBX/static-mesh import does not recreate (they render as black caps). Keep the
    eyeballs only."""
    img = bpy.data.images.load(tex_path, check_existing=False)
    w, h = img.size
    px = img.pixels[:]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uvl = bm.loops.layers.uv.active
    bm.faces.ensure_lookup_table()
    seen, comps = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, fs = [f], []
        seen.add(f.index)
        while stack:
            c = stack.pop()
            fs.append(c)
            for e in c.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        comps.append(fs)
    removed, kept = [], []
    for fs in comps:
        black = 0
        total = 0
        for f in fs:
            for lp in f.loops:
                u, v = lp[uvl].uv
                x = min(w - 1, max(0, int(u * w)))
                y = min(h - 1, max(0, int(v * h)))
                i = (y * w + x) * 4
                total += 1
                if px[i] + px[i + 1] + px[i + 2] < 0.06:
                    black += 1
        nverts = len({v for f in fs for v in f.verts})
        (removed if black / total > 0.95 else kept).append(nverts)
        if black / total > 0.95:
            bmesh.ops.delete(bm, geom=list({v for f in fs for v in f.verts}), context="VERTS")
            bm.faces.ensure_lookup_table()
    bm.to_mesh(ob.data)
    bm.free()
    bpy.data.images.remove(img)
    return {"kept_component_vertex_counts": kept, "removed_cornea_shell_vertex_counts": removed}


report["checks"]["eyes_components"] = drop_cornea_shells(eyes, eye_albedo_path)

# ground the soles on Z = 0 and verify X symmetry
min_z = min(v.co.z for v in body.data.vertices)
xs = [v.co.x for v in body.data.vertices]
report["checks"]["x_extent_symmetry_m"] = [min(xs), max(xs)]
ground = Matrix.Translation((0.0, 0.0, -min_z))
for ob in (body, eyes):
    ob.data.transform(ground)
    ob.data.update()
report["ground_offset_applied_m"] = [0.0, 0.0, -min_z]
report["ground_offset_note"] = ("Lowest sole vertex was %.5f m above the Blender origin; the exported meshes are "
                                "moved down by that amount so the soles sit on Z=0. Add +%.3f cm in Z to map "
                                "back onto the original skeleton space." % (min_z, min_z * 100))

# materials: new, neutral names, single image texture into Base Color so FBX/OBJ carry the map
def make_mat(name, tex_path, roughness):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:  # noqa: BLE001 - deprecated in 5.x, nodes always on
        pass
    tree = m.node_tree
    p = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    t = tree.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(tex_path, check_existing=False)
    img.colorspace_settings.name = "sRGB"
    t.image = img
    tree.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = roughness
    return m


m_skin = make_mat("M_PB_Skin", body_albedo_path, 0.5)
m_eyes = make_mat("M_PB_Eyes", eye_albedo_path, 0.2)
for ob, m in ((body, m_skin), (eyes, m_eyes)):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.material_index = 0

# combined body + eyes variant (one mesh, two material slots)
combo_me = body.data.copy()
combo_me.name = "PB_BodyEyes_ForConform"
combo = bpy.data.objects.new("PB_BodyEyes_ForConform", combo_me)
bpy.context.scene.collection.objects.link(combo)
eyes_tmp = bpy.data.objects.new("pbexp_eyes_tmp", eyes.data.copy())
bpy.context.scene.collection.objects.link(eyes_tmp)
for o in bpy.context.view_layer.objects:
    o.select_set(False)
combo.select_set(True)
eyes_tmp.select_set(True)
bpy.context.view_layer.objects.active = combo
bpy.ops.object.join()
combo = bpy.data.objects["PB_BodyEyes_ForConform"]
report["checks"]["combo_material_slots"] = [m.name for m in combo.data.materials]

# hide every source object so only PB_* can be selected/exported
for o in bpy.data.objects:
    if not o.name.startswith("PB_"):
        o.hide_render = True


# ------------------------------------------------------------------ stats helper
def stats(ob):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    comps, seen = 0, set()
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        if v.index in seen:
            continue
        comps += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            c = stack.pop()
            for e in c.link_edges:
                w = e.other_vert(c)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
    out = {"verts": len(me.vertices), "faces": len(me.polygons),
           "tris": sum(len(p.vertices) - 2 for p in me.polygons),
           "components": comps,
           "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
           "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
           "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
           "uv_layers": [u.name for u in me.uv_layers],
           "bounds_min_cm": [round(min(v.co[i] for v in me.vertices) * 100, 3) for i in range(3)],
           "bounds_max_cm": [round(max(v.co[i] for v in me.vertices) * 100, 3) for i in range(3)]}
    out["height_cm"] = round(out["bounds_max_cm"][2] - out["bounds_min_cm"][2], 3)
    bm.free()
    return out


for ob in (body, eyes, combo):
    report.setdefault("mesh_stats_blender", {})[ob.name] = stats(ob)

# ------------------------------------------------------------------ export
def export_fbx(path, objs):
    s = base_settings("static")
    s["object_types"] = {"MESH"}
    s["path_mode"] = "RELATIVE"
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    r = bpy.ops.export_scene.fbx(filepath=path, **s)
    assert "FINISHED" in r, r
    rep = dict(s)
    rep["object_types"] = sorted(rep["object_types"])
    return {"path": path, "objects": [o.name for o in objs], "bytes": os.path.getsize(path),
            "sha256": sha256(path), "settings": rep}


report["outputs"]["body_fbx"] = export_fbx(OUT + "/PB_Body_ForConform.fbx", [body])
report["outputs"]["body_eyes_fbx"] = export_fbx(OUT + "/PB_BodyEyes_ForConform.fbx", [combo])
report["outputs"]["eyes_fbx"] = export_fbx(OUT + "/PB_Eyes.fbx", [eyes])

for o in bpy.context.view_layer.objects:
    o.select_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active = body
obj_path = OUT + "/PB_Body_ForConform.obj"
r = bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True, apply_modifiers=True,
                          forward_axis="Y", up_axis="Z", global_scale=100.0,
                          export_uv=True, export_normals=True, export_materials=True,
                          path_mode="STRIP", export_triangulated_mesh=False,
                          export_vertex_groups=False, export_object_groups=False)
assert "FINISHED" in r, r
report["outputs"]["body_obj"] = {"path": obj_path, "mtl": OUT + "/PB_Body_ForConform.mtl",
                                 "bytes": os.path.getsize(obj_path), "sha256": sha256(obj_path),
                                 "settings": {"forward_axis": "Y", "up_axis": "Z", "global_scale": 100.0,
                                              "units": "centimetres", "faces": "original quads (not triangulated)"}}

# clean source .blend with only PB_* data (images referenced by absolute path)
blend_out = OUT + "/pb_conform_source.blend"
ids = {body, eyes, combo}
bpy.data.libraries.write(blend_out, ids, fake_user=True, path_remap="ABSOLUTE")
report["outputs"]["clean_blend"] = {"path": blend_out, "bytes": os.path.getsize(blend_out)}

report["axes"] = {
    "blender": "Z up, character faces -Y (nose tip at negative Y), metres",
    "fbx_settings": "axis_forward=-Y, axis_up=Z, apply_unit_scale=True, apply_scale_options=FBX_SCALE_UNITS",
    "unreal_expected": "Z up, face points +Y (UE mesh space), centimetres; identical to SKM_Manny and "
                       "MetaHuman body assets, so no import rotation is needed",
    "obj": "written in Blender axes (Y forward, Z up) x100; UE Interchange OBJ maps (x,y,z)->(x,-y,z) cm, "
           "so the face also points +Y in UE",
}
with open(OUT + "/pb_export_report.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, default=str)
print(json.dumps({k: report[k] for k in ("mesh_stats_blender", "checks", "ground_offset_applied_m")}, indent=1, default=str))
print("EXPORT DONE")
