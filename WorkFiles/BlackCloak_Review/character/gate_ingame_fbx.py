"""Character-fit review (read-only): run the garment gates (Scripts/pipeline/garment_qa.py, type cloak) on an exported
MetaHuman cloak FBX, against a COPY of the locked fitting body, plus a detailed air-gap histogram.

blender -b <copy of MH_PlayerDefault_FitBody.blend> --factory-startup --python gate_ingame_fbx.py -- <fbx> <out.json>
Never saves the .blend. Writes only <out.json>.
"""
import sys
sys.dont_write_bytecode = True  # never drop __pycache__ into Scripts/
import json
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import garment_qa as gq  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
FBX, OUT = args[0], args[1]
report = {"fbx": FBX, "fbx_sha256": gq.file_sha256(Path(FBX))}

lock = gq.load_base_lock()
fit_root = bpy.data.objects[lock["armature_object"]]
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=FBX, global_scale=1.0, automatic_bone_orientation=False)
new = [o for o in bpy.data.objects if o not in before]
imp_arm = next(o for o in new if o.type == "ARMATURE")
mesh = next(o for o in new if o.type == "MESH")
report["imported"] = {"armature": imp_arm.name, "mesh": mesh.name, "bones": len(imp_arm.data.bones),
                      "armature_matrix_identity": gq._is_identity(imp_arm.matrix_world)}
# skeleton of the file vs the lock, before retargeting
ok, detail, numbers = gq.compare_skeleton(imp_arm, lock["skeleton"])
report["file_skeleton_vs_lock"] = {"ok": ok, "detail": detail}

# bake the mesh's world transform, then drive it by the fitting body's own root (same bone names)
mw = mesh.matrix_world.copy()
mesh.parent = None
mesh.data.transform(mw)
mesh.matrix_world.identity()
for m in mesh.modifiers:
    if m.type == "ARMATURE":
        m.object = fit_root
mesh.parent = fit_root
mesh.matrix_parent_inverse.identity()
mesh.matrix_world.identity()
bpy.data.objects.remove(imp_arm, do_unlink=True)
# make PinMask active if present (the FBX importer names colour layers 'Col'/'Attribute'; record what came in)
report["colour_layers"] = [c.name for c in mesh.data.color_attributes]
report["active_colour"] = mesh.data.color_attributes.active_color.name if mesh.data.color_attributes.active_color else None
if mesh.data.color_attributes and "PinMask" not in [c.name for c in mesh.data.color_attributes]:
    # FBX import loses the attribute name; rename the single layer so the pin gate reads the real data
    mesh.data.color_attributes[0].name = "PinMask"
    mesh.data.color_attributes.active_color = mesh.data.color_attributes[0]
    report["colour_note"] = "single imported colour layer renamed to PinMask for the gate (the FBX carries one colour set)"
# strip Blender's .001 suffixes on imported material names so section checks read the real slot names
for mat in mesh.data.materials:
    if mat and "." in mat.name:
        mat.name = mat.name.split(".")[0]
report["slots"] = [m.name if m else None for m in mesh.data.materials]

result = gq.qa_garment([mesh.name], "cloak")
report["qa_passed"] = result["passed"]
report["qa_failed"] = [c for c in result["checks"] if not c["passed"]]
report["qa_checks"] = result["checks"]
report["qa_metrics"] = result.get("metrics")

# detailed air gap at rest (all regions, and arms ignored), per section
fit = gq._fitbody_objects("MH_PlayerDefault", lock)
skin = [fit["body"], fit["head"]]
collider = gq.Collider(skin, [gq.dominant_regions(o) for o in skin])
coords, _ = gq.evaluated_world(mesh)
dist, found, region = collider.signed(coords, max_distance=0.5)
sim_mask, _ = gq._section_vertices(mesh)
slot_of_vert = np.full(len(coords), -1)
for p in mesh.data.polygons:
    slot_of_vert[list(p.vertices)] = p.material_index


def hist(sel):
    d = dist[sel & found]
    return {"n": int(sel.sum()), "found_within_50cm": int(len(d)),
            "inside_any": int(np.count_nonzero(d < 0)), "inside_gt_1mm": int(np.count_nonzero(d < -0.001)),
            "deepest_cm": round(float(-d.min() * 100) if len(d) and d.min() < 0 else 0.0, 2),
            "gap_0_to_5mm": int(np.count_nonzero((d >= 0) & (d < 0.005))),
            "gap_5_to_10mm": int(np.count_nonzero((d >= 0.005) & (d < 0.010))),
            "gap_10_to_15mm": int(np.count_nonzero((d >= 0.010) & (d < 0.015))),
            "gap_ge_15mm": int(np.count_nonzero(d >= 0.015)),
            "min_gap_cm": round(float(d.min() * 100), 2) if len(d) else None}


arm_mask = region == "arm"
gap = {}
for label, sel in (("all", np.ones(len(coords), bool)), ("sim", sim_mask), ("skinned", ~sim_mask)):
    gap[label] = {"all_regions": hist(sel), "arms_ignored": hist(sel & ~arm_mask),
                  "nearest_is_arm": int(np.count_nonzero(sel & arm_mask & found))}
# nearest region for the close / inside verts, for the non-arm set
close = found & ~arm_mask & (dist < 0.010)
reg, cnt = np.unique(region[close], return_counts=True)
gap["under_1cm_non_arm_by_region"] = {str(r): int(c) for r, c in zip(reg, cnt)}
inside_arm = found & arm_mask & (dist < 0)
gap["inside_arm_vertices"] = int(inside_arm.sum())
gap["inside_arm_deepest_cm"] = round(float(-dist[inside_arm].min() * 100), 2) if inside_arm.any() else 0.0
report["air_gap_rest"] = gap

# weights summary
names = {g.index: g.name for g in mesh.vertex_groups}
used, infl = {}, []
for v in mesh.data.vertices:
    ws = [(names[g.group], g.weight) for g in v.groups if g.weight > 0]
    infl.append(len(ws))
    for n, _w in ws:
        used[n] = used.get(n, 0) + 1
report["weights"] = {"bones_used": used, "max_influences": max(infl), "vertex_groups_total": len(mesh.vertex_groups)}
report["mesh"] = {"vertices": len(mesh.data.vertices), "triangles": gq.triangle_count(mesh),
                  "uv_layers": [u.name for u in mesh.data.uv_layers]}
Path(OUT).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
print("GATE_DONE", report["qa_passed"], [c["name"] for c in report["qa_failed"]])
