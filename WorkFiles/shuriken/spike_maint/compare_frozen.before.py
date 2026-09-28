"""Regression gate: every FROZEN form must be bitwise unchanged against a snapshot of the pack.

Written for the senban build (library 3.3), generic on purpose: the snapshot directory is
the pack as it stood when the previous form's fix step completed, and ``--forms`` names the
forms that must not move.  The next form's build points it at the snapshot taken after this
one (post_senban_snapshot/, all three forms).

Current baseline (2026-09-18, after the spike build, library 3.8.0): post_spike/ - all five forms frozen
(four_point, eight_point, square_plate, six_point, spike).  The next form runs
  --snapshot post_spike --forms four_point,eight_point,square_plate,six_point,spike
The spike build itself passed --snapshot post_six_point (four forms) and --snapshot post_restyle2 (three forms);
its maps were additionally proven bit-identical on the CPU (spike/material_noop_check.json).

Previous baseline (2026-09-18, after the six-point maintenance pass, library 3.7.1):
post_six_point/ - four_point, eight_point, square_plate AND six_point, all frozen.  The spike
(and every later form) runs  --snapshot post_six_point --forms four_point,eight_point,square_plate,six_point.
Maps are expected to differ only by the GPU bake's run-to-run noise (1/255 on a few dozen pixels;
six_point_maint/texdiff_*.json), which this script reports as informational.

Headless:
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python-exit-code 3 \
        --python WorkFiles/shuriken/regression/compare_frozen.py -- \
        --snapshot pre_senban_snapshot --forms four_point,eight_point [--root DIR] [--out NAME.json]

Snapshot layout (see pre_senban_snapshot/): Shuriken.blend, export/<mesh>.fbx + .sockets.json,
textures/T_*.png, renders/*.png, <form>_report.json.  ``--root`` points at a build tree with the
same layout (a scratch build); without it the project's Assets / Exports / Renders / WorkFiles
are compared.

Per frozen form, and all of it must be IDENTICAL (bitwise for arrays):
  * every LOD mesh in the .blend: vertex positions, face loops, edges, sharp_edge / sharp_face,
    every UV layer (UV0 of all LODs, not only LOD0), material slots, object custom properties
    (the material's wear tags), identity transforms;
  * the UCX hull mesh; both SOCKET_ Empties (matrix_basis and their ue_socket* properties);
    the LOD group Empty and its children;
  * the FBX re-imported: node set, per mesh triangles / vertices / UV layer names, sorted vertex
    positions and the (position, UV0) loop set;
  * the .sockets.json sidecar, every key;
  * M_Shuriken_Master's FBX export scalars (Principled base colour, metallic, roughness);
  * the report's measured figures, LOD triangles, hull, socket records, screen sizes, qa.
Informational (allowed to differ): the baked textures' SHA-256 (reported; identical when the bake
is deterministic) and every gallery PNG (the rig renders; expected to differ run to run).
Writes <out> (default regression_frozen.json) next to this file or into --root.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


SNAP = Path(arg("--snapshot", "pre_senban_snapshot"))
SNAP = SNAP if SNAP.is_absolute() else HERE / SNAP
FORMS = [f.strip() for f in arg("--forms", "four_point,eight_point").split(",") if f.strip()]
ROOT = Path(arg("--root")) if arg("--root") else None
if ROOT:
    NEW_BLEND, EXPORTS, TEXTURES, RENDERS, REPORTS = (ROOT / "Shuriken.blend", ROOT / "export", ROOT / "tex",
                                                      ROOT / "renders", ROOT / "reports")
    OUT = ROOT / arg("--out", "regression_frozen.json")
else:
    NEW_BLEND = PROJECT / "Assets" / "Shuriken.blend"
    EXPORTS = PROJECT / "Exports" / "Shuriken"
    TEXTURES, RENDERS, REPORTS = EXPORTS / "Textures", PROJECT / "Renders" / "Shuriken", PROJECT / "WorkFiles" / "shuriken"
    OUT = HERE / arg("--out", "regression_frozen.json")
GEOMETRY_KEYS = ("verts", "loops", "loop_start", "loop_total", "edges", "sharp_edge", "sharp_face")
REPORT_KEYS = ("lod_triangles", "hull", "socket_records", "lod_screen_sizes", "measured", "lod_measured",
               "lod_bands_ok", "symmetry")


def arr(data, prop, width, dtype=np.float32):
    out = np.empty(len(data) * width, dtype=dtype)
    data.foreach_get(prop, out)
    return out.reshape(-1, width) if width > 1 else out


def attr(mesh, name):
    a = mesh.attributes.get(name)
    if a is None:
        return None
    out = np.empty(len(a.data), dtype=bool)
    a.data.foreach_get("value", out)
    return out


def props(obj):
    return {k: (list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v)
            for k, v in obj.items() if not k.startswith("_")}


def mesh_record(obj):
    mesh = obj.data
    return {
        "verts": arr(mesh.vertices, "co", 3),
        "loops": arr(mesh.loops, "vertex_index", 1, np.int64),
        "loop_start": arr(mesh.polygons, "loop_start", 1, np.int64),
        "loop_total": arr(mesh.polygons, "loop_total", 1, np.int64),
        "edges": arr(mesh.edges, "vertices", 2, np.int64),
        "sharp_edge": attr(mesh, "sharp_edge"),
        "sharp_face": attr(mesh, "sharp_face"),
        "uv": {uv.name: arr(uv.data, "uv", 2) for uv in mesh.uv_layers},
        "materials": [m.name.split(".")[0] if m else None for m in mesh.materials],
        "props": props(obj),
        "identity": bool(np.allclose(np.array(obj.matrix_world), np.eye(4), atol=0.0)),
    }


def same(a, b):
    if a is None or b is None:
        return {"identical": a is None and b is None}
    if a.shape != b.shape:
        return {"identical": False, "shape": [list(a.shape), list(b.shape)]}
    if a.dtype == bool or np.issubdtype(a.dtype, np.integer):
        return {"identical": bool(np.array_equal(a, b)), "mismatches": int(np.count_nonzero(a != b))}
    return {"identical": bool(np.array_equal(a, b)),
            "max_abs_diff": float(np.abs(a.astype(np.float64) - b.astype(np.float64)).max()) if a.size else 0.0}


def compare_mesh(a, b):
    out = {k: same(a[k], b[k]) for k in GEOMETRY_KEYS}
    names = sorted(set(a["uv"]) | set(b["uv"]))
    out["uv_layers"] = {"identical": list(a["uv"]) == list(b["uv"]), "names": [list(a["uv"]), list(b["uv"])]}
    for name in names:
        out[f"uv:{name}"] = same(a["uv"].get(name), b["uv"].get(name))
    out["materials"] = {"identical": a["materials"] == b["materials"], "values": [a["materials"], b["materials"]]}
    out["props"] = {"identical": a["props"] == b["props"]}
    if a["props"] != b["props"]:
        out["props"]["values"] = [a["props"], b["props"]]
    out["identity"] = {"identical": a["identity"] and b["identity"]}
    return out


def principled(mat):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    return {"base_color": [float(v) for v in bsdf.inputs["Base Color"].default_value],
            "metallic": float(bsdf.inputs["Metallic"].default_value),
            "roughness": float(bsdf.inputs["Roughness"].default_value),
            "nodes": len(mat.node_tree.nodes)}


def fbx_record(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for obj in bpy.data.objects:
        entry = {"type": obj.type, "parent": obj.parent.name if obj.parent else None, "props": props(obj)}
        if obj.type == "MESH":
            mesh = obj.data
            mesh.calc_loop_triangles()
            mw = obj.matrix_world
            co = np.array([(mw @ v.co)[:] for v in mesh.vertices], dtype=np.float64)
            uv0 = mesh.uv_layers[0].data if mesh.uv_layers else None
            loops = sorted((tuple(np.round(co[l.vertex_index], 12)), tuple(round(c, 7) for c in uv0[l.index].uv))
                           for l in mesh.loops) if uv0 is not None else []
            entry.update({"triangles": len(mesh.loop_triangles), "vertices": len(mesh.vertices), "co": co,
                          "uv_layers": [uv.name for uv in mesh.uv_layers], "loops": loops})
        out[obj.name] = entry
    return out


def sorted_rows(co):
    return co[np.lexsort((co[:, 2], co[:, 1], co[:, 0]))]


def load_png(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(h, w, 4)


def png_diff(a_path, b_path):
    if not Path(a_path).exists() or not Path(b_path).exists():
        return {"missing": [str(p) for p in (a_path, b_path) if not Path(p).exists()]}
    a, b = load_png(a_path), load_png(b_path)
    if a.shape != b.shape:
        return {"shape": [list(a.shape), list(b.shape)]}
    d = np.abs(a[..., :3].astype(np.float64) - b[..., :3].astype(np.float64)).max(axis=-1)
    return {"identical": bool(d.max() == 0.0), "mean_abs": round(float(d.mean()), 5),
            "pixels_over_8_of_255": round(float((d > 8.5 / 255).mean()), 4)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None


def all_identical(tree):
    if isinstance(tree, dict):
        if "identical" in tree and not isinstance(tree["identical"], dict):
            return bool(tree["identical"])
        return all(all_identical(v) for v in tree.values())
    return True


result = {"snapshot": str(SNAP), "root": str(ROOT) if ROOT else "project", "forms": FORMS, "per_form": {}}
snap_reports = {f: json.loads((SNAP / f"{f}_report.json").read_text(encoding="utf-8")) for f in FORMS}
new_reports = {f: json.loads((REPORTS / f"{f}_report.json").read_text(encoding="utf-8")) for f in FORMS}

# ------------------------------------------------------------------ .blend
names = {}
for form in FORMS:
    rep = snap_reports[form]
    lods = list(rep["objects"])
    names[form] = {"mesh": rep["asset"], "lods": lods, "hull": rep["hull"]["name"], "sockets": list(rep["sockets"]),
                   "group": rep["lod_group"]}
bpy.ops.wm.open_mainfile(filepath=str(NEW_BLEND))
new_blend = {}
for form, n in names.items():
    new_blend[form] = {
        "lods": {name: mesh_record(bpy.data.objects[name]) for name in n["lods"]},
        "hull": mesh_record(bpy.data.objects[n["hull"]]),
        "hull_parent": bpy.data.objects[n["hull"]].parent.name,
        "sockets": {name: {"matrix": np.array(bpy.data.objects[name].matrix_basis, dtype=np.float64),
                           "type": bpy.data.objects[name].type, "parent": bpy.data.objects[name].parent.name,
                           "props": props(bpy.data.objects[name])} for name in n["sockets"]},
        "group": {"props": props(bpy.data.objects[n["group"]]),
                  "children": sorted(c.name for c in bpy.data.objects[n["group"]].children)},
    }
new_material = principled(bpy.data.materials["M_Shuriken_Master"])
result["new_blend_collections"] = {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections}

bpy.ops.wm.read_factory_settings(use_empty=True)
wanted = [nm for n in names.values() for nm in n["lods"] + [n["hull"]] + n["sockets"] + [n["group"]]]
with bpy.data.libraries.load(str(SNAP / "Shuriken.blend"), link=False) as (src, dst):
    dst.objects = [nm for nm in wanted if nm in src.objects]
    dst.materials = ["M_Shuriken_Master"]
snap_objs = {o.name: o for o in dst.objects}
snap_material = principled(bpy.data.materials["M_Shuriken_Master"])
for form, n in names.items():
    new = new_blend[form]
    rec = {"lods": {}, "sockets": {}}
    for name in n["lods"]:
        rec["lods"][name] = compare_mesh(mesh_record(snap_objs[name]), new["lods"][name])
    rec["hull"] = compare_mesh(mesh_record(snap_objs[n["hull"]]), new["hull"])
    rec["hull"]["parent"] = {"identical": snap_objs[n["hull"]].parent.name == new["hull_parent"]}
    for name in n["sockets"]:
        s_obj = snap_objs[name]
        m = np.array(s_obj.matrix_basis, dtype=np.float64)
        rec["sockets"][name] = {
            "matrix": {"identical": bool(np.array_equal(m, new["sockets"][name]["matrix"])),
                       "max_abs_diff": float(np.abs(m - new["sockets"][name]["matrix"]).max())},
            "type": {"identical": s_obj.type == new["sockets"][name]["type"] == "EMPTY"},
            "parent": {"identical": s_obj.parent.name == new["sockets"][name]["parent"]},
            "props": {"identical": props(s_obj) == new["sockets"][name]["props"]},
        }
    s_group = snap_objs[n["group"]]
    rec["lod_group"] = {"props": {"identical": props(s_group) == new["group"]["props"]},
                        "children": {"identical": sorted(c.name for c in s_group.children) == new["group"]["children"],
                                     "names": new["group"]["children"]}}
    result["per_form"][form] = {"blend": rec}
result["material_export_scalars"] = {
    "snapshot": snap_material, "now": new_material,
    **{k: {"identical": snap_material[k] == new_material[k]} for k in ("base_color", "metallic", "roughness")},
    "nodes_identical": snap_material["nodes"] == new_material["nodes"],
}

# ------------------------------------------------------------------ FBX, sidecar, textures, report, renders
for form, n in names.items():
    mesh = n["mesh"]
    a, b = fbx_record(SNAP / "export" / f"{mesh}.fbx"), fbx_record(EXPORTS / f"{mesh}.fbx")
    fbx = {"nodes": {"identical": sorted(a) == sorted(b), "names": [sorted(a), sorted(b)]},
           "node_types_parents": {"identical": {k: (v["type"], v["parent"]) for k, v in a.items()}
                                  == {k: (v["type"], v["parent"]) for k, v in b.items()}},
           "meshes": {}}
    for name in sorted(set(a) & set(b)):
        if a[name]["type"] != "MESH":
            continue
        ca, cb = a[name]["co"], b[name]["co"]
        fbx["meshes"][name] = {
            "triangles": {"identical": a[name]["triangles"] == b[name]["triangles"], "value": b[name]["triangles"]},
            "vertices": {"identical": a[name]["vertices"] == b[name]["vertices"]},
            "uv_layers": {"identical": a[name]["uv_layers"] == b[name]["uv_layers"]},
            "sorted_positions": {"identical": bool(ca.shape == cb.shape and np.array_equal(sorted_rows(ca), sorted_rows(cb))),
                                 "max_abs_diff_m": float(np.abs(sorted_rows(ca) - sorted_rows(cb)).max())
                                 if ca.shape == cb.shape else None},
            "position_uv0_loops": {"identical": a[name]["loops"] == b[name]["loops"]},
        }
    side_a = json.loads((SNAP / "export" / f"{mesh}.sockets.json").read_text(encoding="utf-8"))
    side_b = json.loads((EXPORTS / f"{mesh}.sockets.json").read_text(encoding="utf-8"))
    sidecar = {"all_keys": {"identical": side_a == side_b},
               "sockets": {"identical": side_a.get("sockets") == side_b.get("sockets")},
               "lod_screen_sizes": {"identical": side_a.get("lod_screen_sizes") == side_b.get("lod_screen_sizes"),
                                    "value": side_b.get("lod_screen_sizes")}}
    stem = "T_" + mesh[len("SM_"):]
    textures = {s: {"snapshot": sha(SNAP / "textures" / f"{stem}_{s}.png"), "now": sha(TEXTURES / f"{stem}_{s}.png")}
                for s in ("BC", "ORM", "N")}
    for v in textures.values():
        v["identical"] = v["snapshot"] is not None and v["snapshot"] == v["now"]
    rs, rn = snap_reports[form], new_reports[form]
    report = {k: {"identical": rs.get(k) == rn.get(k)} for k in REPORT_KEYS}
    report["qa"] = {"identical": (rs["qa"]["passed"], len(rs["qa"]["checks"])) == (rn["qa"]["passed"], len(rn["qa"]["checks"])),
                    "now": [rn["qa"]["passed"], len(rn["qa"]["checks"])]}
    report["measured_keys_changed"] = sorted(k for k in set(rs["measured"]) | set(rn["measured"])
                                             if rs["measured"].get(k) != rn["measured"].get(k))
    renders = {shot: png_diff(SNAP / "renders" / f"{form}_{shot}.png", RENDERS / f"{form}_{shot}.png")
               for shot in ("persp", "top", "wire", "lods")}
    per = result["per_form"][form]
    per.update({"fbx": fbx, "sidecar": sidecar, "report": report})
    per["informational"] = {"textures_sha256": textures, "renders": renders,
                            "fbx_sha256": {"snapshot": sha(SNAP / "export" / f"{mesh}.fbx"),
                                           "now": sha(EXPORTS / f"{mesh}.fbx"),
                                           "note": "FBX bytes change on every export (header time, UIDs)"}}
    per["gated_identical"] = {k: all_identical(per[k]) for k in ("blend", "fbx", "sidecar", "report")}

result["summary"] = {
    form: {**result["per_form"][form]["gated_identical"],
           "textures_identical": all(v["identical"] for v in result["per_form"][form]["informational"]["textures_sha256"].values())}
    for form in FORMS}
result["summary"]["material_export_scalars_identical"] = all(
    result["material_export_scalars"][k]["identical"] for k in ("base_color", "metallic", "roughness"))
result["allowed_differences"] = ["gallery renders (informational)", "FBX file bytes (header time, UIDs; content compared)",
                                 "report timestamps, seconds, library_version and new report keys"]
result["passed"] = bool(all(all(v for k, v in s.items() if k != "textures_identical")
                            for f, s in result["summary"].items() if isinstance(s, dict))
                        and result["summary"]["material_export_scalars_identical"])


def _jsonable(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return str(o)


OUT.write_text(json.dumps(result, indent=2, default=_jsonable), encoding="utf-8")
print("FROZEN_REGRESSION " + json.dumps(result["summary"]) + " passed=" + str(result["passed"]))
