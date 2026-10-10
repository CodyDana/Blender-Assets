"""Fresh-process check of the EXPORTED SM_Casing_762x39 bytes (headless Blender 5.2):

    blender.exe -b --factory-startup --python Scripts/guns/casing/verify_casing.py

Re-imports Exports/Guns/Casing/SM_Casing_762x39.fbx in a new process and re-measures: node names and LOD order,
triangle counts, the C.I.P. dimension gate (casing_measure) on the imported LOD0 with the base taken from the
sidecar's Base socket, UD1/UD2 (gunlib.ud.check_np on the imported triangles), UV0 present, the material slot,
the textures (power of two, present) and the sha256 of every shipped file against casing_build.json.
Writes WorkFiles/guns/casing/casing_verify.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(HERE), str(ROOT / "Scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import casing_spec as CS  # noqa: E402
from casing_measure import measure  # noqa: E402
from guns.gunlib import ud  # noqa: E402

NAME = "SM_Casing_762x39"
EXP = ROOT / "Exports" / "Guns" / "Casing"
WORK = ROOT / "WorkFiles" / "guns" / "casing"


def tris_mm(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    V = np.array([ob.matrix_world @ v.co for v in me.vertices]) * 1000.0
    T = np.array([t.vertices[:] for t in me.loop_triangles])
    info = {"uv_layers": [u.name for u in me.uv_layers], "materials": [m.name if m else None for m in ob.data.materials],
            "has_custom_normals": bool(ob.data.has_custom_normals)}
    ev.to_mesh_clear()
    return V, T, info


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fbx = EXP / f"{NAME}.fbx"
    build = json.loads((WORK / "casing_build.json").read_text())
    sidecar = json.loads((EXP / f"{NAME}.sockets.json").read_text())
    rep = {"fbx": str(fbx.relative_to(ROOT)).replace("\\", "/")}
    sha = {}
    for rel, h in build["sha256"].items():
        now = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        sha[rel] = {"build": h, "now": now, "same": now == h}
    rep["sha256"] = sha
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    names = sorted(o.name for o in bpy.data.objects)
    rep["nodes"] = names
    lods = [bpy.data.objects.get(f"{NAME}_LOD{i}") for i in range(3)]
    rep["lod_nodes_present"] = all(o is not None and o.type == "MESH" for o in lods)
    grp = bpy.data.objects.get(f"{NAME}_LodGroup")
    rep["lod_group_present"] = grp is not None
    rep["no_socket_nodes_in_fbx"] = not any(n.startswith("SOCKET_") for n in names)
    rows = {}
    V0 = None
    for o in lods:
        V, T, info = tris_mm(o)
        r = ud.check_np(V, T, o.name)
        r.update(info)
        rows[o.name] = r
        if o.name.endswith("LOD0"):
            V0 = V
    rep["lods"] = rows
    tri = [rows[o.name]["triangles"] for o in lods]
    rep["triangles"] = tri
    rep["tri_budget_pass"] = all(t <= CS.TRI_BUDGET[f"LOD{i}"] for i, t in enumerate(tri)) and tri[0] > tri[1] > tri[2]
    base = next(s for s in sidecar["sockets"] if s["socket"] == "Base")
    mouth = next(s for s in sidecar["sockets"] if s["socket"] == "Mouth")
    base_x_mm = base["location_cm"][0] * 10.0
    rep["sidecar"] = {"base_cm": base["location_cm"], "mouth_cm": mouth["location_cm"],
                      "mouth_minus_base_mm": round((mouth["location_cm"][0] - base["location_cm"][0]) * 10.0, 4),
                      "lod_screen_sizes": sidecar.get("lod_screen_sizes")}
    # Blender's FBX import of a -Y forward / Z up file: the case axis comes back on +X (as authored)
    Vc = V0.copy()
    rep["axis_extent_mm"] = {"x": [round(float(Vc[:, 0].min()), 4), round(float(Vc[:, 0].max()), 4)],
                             "y": [round(float(Vc[:, 1].min()), 4), round(float(Vc[:, 1].max()), 4)],
                             "z": [round(float(Vc[:, 2].min()), 4), round(float(Vc[:, 2].max()), 4)]}
    Vc[:, 0] -= base_x_mm
    rep["dimensions"] = measure(Vc, 24)
    rep["base_from_sidecar_matches_mesh_base_plane_mm"] = round(rep["dimensions"]["base_plane_x_mm"], 5)
    tex = {}
    for p in sorted((EXP / "Textures").glob("T_*.png")):
        img = bpy.data.images.load(str(p))
        w, h = img.size
        tex[p.name] = {"size": [w, h], "pow2": w > 0 and h > 0 and (w & (w - 1)) == 0 and (h & (h - 1)) == 0}
    rep["textures"] = tex
    gates = {
        "sha_unchanged": all(v["same"] for v in sha.values()),
        "nodes": rep["lod_nodes_present"] and rep["lod_group_present"] and rep["no_socket_nodes_in_fbx"],
        "tri_budget": rep["tri_budget_pass"],
        "dimensions": rep["dimensions"]["pass"] and abs(rep["base_from_sidecar_matches_mesh_base_plane_mm"]) < 1e-3
        and abs(rep["sidecar"]["mouth_minus_base_mm"] - CS.CIP["L3"]) < 1e-3,
        "ud1": all(r["pass_ud1"] for r in rows.values()),
        "ud2": all(r["pass_ud2"] for r in rows.values()),
        "uv0": all(r["uv_layers"] for r in rows.values()),
        "material": all(r["materials"] == ["M_Casing_762x39"] for r in rows.values()),
        "textures": len(tex) == 3 and all(t["pow2"] for t in tex.values()),
    }
    rep["gates"] = gates
    rep["pass"] = all(gates.values())
    (WORK / "casing_verify.json").write_text(json.dumps(rep, indent=1, default=str))
    print("[casing-verify]", "PASS" if rep["pass"] else "FAIL", gates, flush=True)


main()
