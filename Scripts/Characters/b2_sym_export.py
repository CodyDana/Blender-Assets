"""b2_sym_export.py - PRIVATE / DO NOT SHIP. Symmetry step: copy of b2_rig_export.py writing export_sym/ (never export/).

  blender -b WorkFiles/Characters/2B_private/2B_private_rig_sym.blend -P Scripts/Characters/b2_sym_export.py -- export
  blender -b --factory-startup -P Scripts/Characters/b2_sym_export.py -- verify

verify additionally parses the raw FBX and checks that every texture FileName / RelativeFilename resolves to a file
(RelativeFilename relative to the FBX folder).

export: textures written from the packed images to export/textures/T_2B_*.jpg, then the FBX through the shared
        pipeline (Scripts/pipeline/export_fbx.py, kind="skeletal", units="cm": the same centimetre path the garments
        use, which UE 5.8 imports with root scale 1). Only the armature "root" and the three SK_2B_* meshes are
        written; the Render_Rig collection is not.
verify: imports the FBX into an empty scene and measures height, bones, meshes, influences and names.
"""
import bpy, os, sys, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Scripts/ (pipeline package)
from b2_rig_common import log, argv, world_bbox, MH_BLEND  # noqa
from b2_sym_lib import EXPORT_DIR, FBX, TEX_DIR, CHECKS, SYM_BLEND, save_json  # noqa
assert FBX.replace("\\", "/").endswith("/2B_private/export_sym/SK_2B_Private.fbx"), FBX

MESHES = ["SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"]
EXPORT_INFO = CHECKS + "/sym_export_info.json"
VERIFY_INFO = CHECKS + "/sym_verify_info.json"


def safe(n):
    return "".join(c if c.isalnum() else "_" for c in n).strip("_")


def export():
    assert bpy.data.filepath.replace("\\", "/") == SYM_BLEND, bpy.data.filepath
    os.makedirs(TEX_DIR, exist_ok=True)
    info = {"textures": {}, "materials": {}}
    written = {}
    for mn in MESHES:
        o = bpy.data.objects[mn]
        for m in o.data.materials:
            ent = {"base_color_texture": None}
            if m.node_tree:
                b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
                if tex:
                    im = tex.image
                    if im.name not in written:
                        ext = ".jpg" if (im.file_format or "").upper() in ("JPEG", "JPG") else ".png"
                        path = f"{TEX_DIR}/T_2B_{safe(im.name)}_D{ext}"
                        if im.packed_file:
                            with open(path, "wb") as fh:
                                fh.write(im.packed_file.data)
                        else:
                            im.save_render(path)
                        written[im.name] = path
                        info["textures"][os.path.basename(path)] = {"source_image": im.name, "size": list(im.size)}
                    ent["base_color_texture"] = os.path.basename(written[im.name])
                if b:
                    ent["base_color"] = [round(x, 4) for x in b.inputs["Base Color"].default_value]
                    ent["alpha"] = round(b.inputs["Alpha"].default_value, 3)
                    ent["roughness"] = round(b.inputs["Roughness"].default_value, 3)
            info["materials"][m.name] = ent
    # the FBX must point at the written JPEGs, not at the packed originals (those have no file on disk, so the FBX got
    # extension-less '..\textures\packed\<name>' paths): every image node of the export materials is re-pointed at its
    # export/textures file for the export only. The blend is opened read-only here (never saved), so the rig blend's
    # packed images are untouched; they are also restored below.
    repointed = []
    restore = []
    loaded = {}
    for mn in MESHES:
        for m in bpy.data.objects[mn].data.materials:
            if not m.node_tree:
                continue
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.name in written:
                    path = written[n.image.name]
                    if path not in loaded:
                        loaded[path] = bpy.data.images.load(path, check_existing=True)
                    restore.append((n, n.image))
                    n.image = loaded[path]
                    repointed.append([m.name, os.path.basename(path)])
    info["fbx_texture_nodes_repointed"] = repointed
    from pipeline.export_fbx import export_fbx
    try:
        res = export_fbx(FBX, ["root"] + MESHES, kind="skeletal", units="cm")
    finally:
        for n, im in restore:
            n.image = im
    info["fbx"] = res
    # A-pose measurements in the blend (metres)
    mn, mx = world_bbox([bpy.data.objects[n] for n in MESHES])
    sk_mn, sk_mx = world_bbox([bpy.data.objects["SK_2B_Body"]])
    info["apose_bbox_m"] = {"min": list(mn), "max": list(mx)}
    info["apose_skin_height_m"] = sk_mx.z - sk_mn.z
    arm = bpy.data.objects["root"]
    info["bones"] = [b.name for b in arm.data.bones]
    save_json(EXPORT_INFO, info)
    log("exported", FBX, "skin height", round(sk_mx.z - sk_mn.z, 4), "warnings", res["warnings"])


def verify():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX, use_anim=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             automatic_bone_orientation=False, ignore_leaf_bones=False)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    out = {"objects": [(o.name, o.type, [round(x, 5) for x in o.scale]) for o in bpy.data.objects]}
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    rows = []
    maxinf = 0
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        for v in me.vertices:
            c = o.matrix_world @ v.co
            for k in range(3):
                mn[k] = min(mn[k], c[k]); mx[k] = max(mx[k], c[k])
        ev.to_mesh_clear()
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        inf = max((sum(1 for g in v.groups if g.weight > 0) for v in o.data.vertices), default=0)
        maxinf = max(maxinf, inf)
        rows.append({"name": o.name, "tris": tris, "material_slots": len(o.data.materials),
                     "materials": [m.name for m in o.data.materials], "vertex_groups": len(o.vertex_groups),
                     "max_influences": inf, "armature_modifier": any(m.type == 'ARMATURE' for m in o.modifiers)})
    a = arms[0]
    # raw file units: the imported armature carries the unit conversion as its object scale
    out.update({"armatures": [x.name for x in arms], "bone_count": len(a.data.bones), "bones": [b.name for b in a.data.bones],
                "armature_object_scale": list(a.scale), "meshes": rows, "max_influences": maxinf,
                "height_blender_m": mx.z - mn.z, "height_cm": round((mx.z - mn.z) * 100, 2),
                "bbox_min_m": list(mn), "bbox_max_m": list(mx)})
    with bpy.data.libraries.load(MH_BLEND, link=False) as (src, dst):
        dst.armatures = ["metahuman_base_skel"]
    mh = {b.name: (b.parent.name if b.parent else None) for b in dst.armatures[0].bones}
    names = [b.name for b in a.data.bones]
    out["bone_names_all_in_mh"] = all(n in mh for n in names)
    out["parents_match_mh"] = all((a.data.bones[n].parent.name if a.data.bones[n].parent else None) == mh[n] for n in names)
    out["total_tris"] = sum(r["tris"] for r in rows)
    # raw FBX texture references must resolve (RelativeFilename relative to the FBX folder)
    from io_scene_fbx import parse_fbx
    root_el, ver = parse_fbx.parse(FBX)
    refs = {"FileName": set(), "RelativeFilename": set()}
    for ob in [e for e in root_el.elems if e.id == b"Objects"]:
        for e in ob.elems:
            if e.id in (b"Texture", b"Video"):
                for sub in e.elems:
                    k = sub.id.decode()
                    if k in ("FileName", "Filename"):
                        refs["FileName"].add(sub.props[0].decode(errors="replace"))
                    elif k == "RelativeFilename":
                        refs["RelativeFilename"].add(sub.props[0].decode(errors="replace"))
    fdir = os.path.dirname(FBX)
    out["fbx_texture_refs"] = {k: sorted(v) for k, v in refs.items()}
    out["fbx_relative_refs_resolve"] = {r: os.path.isfile(os.path.normpath(os.path.join(fdir, r.replace("\\", "/"))))
                                        for r in refs["RelativeFilename"]}
    out["fbx_absolute_refs_exist"] = {r: os.path.isfile(r) for r in refs["FileName"]}
    out["fbx_refs_point_into_export_sym"] = all("export_sym" in r.replace("\\", "/") for r in refs["FileName"])
    out["all_texture_refs_ok"] = bool(refs["RelativeFilename"]) and all(out["fbx_relative_refs_resolve"].values()) and         all(out["fbx_absolute_refs_exist"].values()) and out["fbx_refs_point_into_export_sym"]
    # imported materials: image file paths resolve
    imgs = {}
    for im in bpy.data.images:
        if im.filepath:
            imgs[im.name] = [im.filepath, os.path.isfile(bpy.path.abspath(im.filepath))]
    out["imported_images"] = imgs
    save_json(VERIFY_INFO, out)
    log("verify", json.dumps({k: v for k, v in out.items() if k not in ("bones",)})[:3000])


if __name__ == "__main__":
    a = argv()
    {"export": export, "verify": verify}[a[0] if a else "export"]()
