"""Write WorkFiles/shared/armory_hall/shell_materials.json: everything ArmoryLab needs to rebuild the hall SHELL
(SM_DKH_*) with its materials WITHOUT DojoLab (finish stage of the hall + armory round, 2026-10-01). Plain Python 3.

Source of truth (dojo chat): WorkFiles/dojo/build/showcase/layout_showcase.json (pieces, slots, material recipes,
textures, Nanite flags) and Scripts/dojo/unreal/dj_sc_common.py (EMISSIVE_SCALE: the DojoLab emissive level value);
the Unreal recipes it describes are dj_sc_import.py (meshes / textures) and dj_sc_materials.py (masters as graph code,
the instances' parameters). Every number is copied, not re-derived; the readback check compares the recipe with
DojoLab's own build report (WorkFiles/dojo/build/unreal/showcase/materials.json readback) and fails on any mismatch.

Run from the repo root under the ArmoryHall lock:  py -3 -B Scripts/dojo/hall/make_shell_materials.py [--write]
(the caller then runs tools/check_sync.py and tools/bump_manifest.py)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "unreal"))
sys.path.insert(0, str(ROOT / "WorkFiles" / "shared" / "armory_hall" / "tools"))
import ahcommon as A  # noqa: E402
import dj_sc_common as S  # noqa: E402

ARMORYLAB_BIAS_EV, DOJOLAB_BIAS_EV = -2.68, 1.20      # the two levels' manual exposure biases (dj_armory_look.py)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    L = A.jload(ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json")
    H = A.jload(A.SH / "hall_shell_layout.json")
    RB = A.jload(ROOT / "WorkFiles/dojo/build/unreal/showcase/materials.json")["instances"]
    placed = A.placed_shell(H)
    pieces = sorted({i["piece"] for i in placed})
    out_p, slots_all = {}, set()
    for p in pieces:
        e = L["pieces"][p]
        fbx = A.EXPORTS_HALL / f"{p}.fbx"
        sc = fbx.with_suffix(".sockets.json")
        slots_all |= set(e["slots"])
        out_p[p] = {"fbx": A.rel(fbx), "sha256": A.sha256(fbx), "ue_mesh": f"{e['ue_dir']}/{p}",
                    "sidecar": A.rel(sc) if sc.exists() else None, "sidecar_sha256": A.sha256(sc) if sc.exists() else None,
                    "nanite": bool(e["nanite"]), "lods": e.get("lods"), "ucx": e.get("n_ucx"), "vertex_colours": e.get("vcol"),
                    "collision_class": next(i["collision_class"] for i in placed if i["piece"] == p),
                    "slots": {s: f"{L['materials'][s]['ue_dir']}/{s}" for s in e["slots"]},
                    "instances": sum(1 for i in placed if i["piece"] == p)}
    mats, tex_names, masters, readback_bad = {}, set(), set(), []
    for s in sorted(slots_all):
        r = L["materials"][s]
        scal = {}
        for k, v in r["scalars"].items():
            scal[k] = round(float(v) * (S.EMISSIVE_SCALE if k in ("EmissiveIntensity", "Emissive Intensity") else 1.0), 6)
        rb = RB.get(s, {}).get("readback", {})
        for k, v in scal.items():
            if k in rb and abs(rb[k] - v) > 1e-3:
                readback_bad.append({"mi": s, "param": k, "recipe": v, "dojolab": rb[k]})
        mats[s] = {"ue_path": f"{r['ue_dir']}/{s}", "parent": f"{S.MASTER_DIR}/{r['master']}",
                   "scalars": scal, "vectors_linear_rgba": {k: [float(x) for x in (list(v) + [1.0] * (4 - len(v)))[:4]]
                                                            for k, v in r["vectors"].items()},
                   "static_switches": dict(r.get("switches", {})), "textures": dict(r["textures"])}
        tex_names |= set(r["textures"].values())
        masters.add(r["master"])
    kinds = {"BC": {"srgb": True, "compression": "TC_DEFAULT"}, "ORM": {"srgb": False, "compression": "TC_MASKS"},
             "M": {"srgb": False, "compression": "TC_MASKS"},
             "N": {"srgb": False, "compression": "TC_NORMALMAP", "flip_green_channel": False}}
    tex = {}
    for t in sorted(tex_names):
        r = L["textures"][t]
        png = Path(r["png"])
        tex[t] = {"png": A.rel(png), "sha256": A.sha256(png), "ue_path": f"{r['ue_dir']}/{t}", "kind": r["kind"],
                  **kinds[r["kind"]]}
    parity = 2.0 ** (DOJOLAB_BIAS_EV - ARMORYLAB_BIAS_EV)
    doc = {
        "revision": None, "date": A.today(), "owner": "dojo chat (shell)",
        "written_by": "Scripts/dojo/hall/make_shell_materials.py",
        "purpose": "ArmoryLab rebuilds the hall shell (every SM_DKH_* placed by hall_shell_layout.json) with its materials "
                   "without DojoLab: import the FBX + PNG listed here, build the two masters, create one material instance "
                   "per slot with these exact parameters, assign slot -> instance by slot name. "
                   "tools/ue_armorylab_shell.py does all of it in one commandlet (SYNC.md section 11).",
        "ue_paths": {"meshes": "/Game/DojoKit/Hall/Meshes", "masters": S.MASTER_DIR,
                     "instances": "/Game/DojoKit/Materials/Materials/Library", "textures": "/Game/DojoKit/Materials/Textures",
                     "note": "the same package paths as DojoLab; nothing of the armory's own /Game/ArmoryKit is touched"},
        "import_recipe": {
            "source": "Scripts/dojo/unreal/dj_sc_import.py mesh_options() / TEX_INTENT",
            "mesh": {"importer": "legacy FBX (console: Interchange.FeatureFlags.Import.FBX 0)", "import_mesh_lods": True,
                     "auto_generate_collision": False, "one_convex_hull_per_ucx": True, "combine_meshes": False,
                     "generate_lightmap_uvs": False, "normal_import_method": "FBXNIM_IMPORT_NORMALS",
                     "normal_generation_method": "MIKK_T_SPACE", "vertex_color_import_option": "REPLACE",
                     "convert_scene": True, "convert_scene_unit": True, "force_front_x_axis": False,
                     "import_uniform_scale": 1.0, "import_materials": False, "import_textures": False,
                     "build_nanite": "per piece (pieces[*].nanite)",
                     "nanite_fallback": "fallback_target RELATIVE_ERROR, fallback_relative_error 0.0, "
                                        "fallback_percent_triangles 1.0 (full detail: the bounds stay exact)",
                     "sidecar": "Scripts/pipeline/ue_import_sockets.py apply_sidecar(<sidecar>, <ue_mesh>) when listed"},
            "texture": {"BC": kinds["BC"], "ORM": kinds["ORM"], "M": kinds["M"], "N": kinds["N"],
                        "maps": "power-of-two PNG with full mips; normal maps are DirectX (no green flip)"},
        },
        "masters": {m: {"ue_path": f"{S.MASTER_DIR}/{m}",
                        "recipe": "Scripts/dojo/unreal/dj_sc_materials.py :: " + {"M_DJ_Lib_Opaque": "build_lib_opaque",
                                                                                  "M_DJ_Lib_Emissive": "build_lib_emissive"}[m]
                                  + " (the node graph as code; MEL.layout_material_expressions + recompile after)",
                        "usage": "used_with_nanite True (reset()); opaque, default lit, one-sided"} for m in sorted(masters)},
        "pieces": out_p,
        "materials": mats,
        "textures": tex,
        "level_values": {
            "EmissiveIntensity": {
                "DojoLab_scale_applied": round(S.EMISSIVE_SCALE, 6),
                "ArmoryLab_parity_scale": round(parity, 4),
                "note": "materials[*].scalars carry DojoLab's value (layout recipe x DojoLab's EMISSIVE_SCALE). Emission "
                        "is a per-level value (SYNC.md 6): at ArmoryLab's manual exposure (bias %.2f against DojoLab's "
                        "+%.2f) the same look needs x %.2f; ArmoryLab chooses (the only emissive shell slot is "
                        "M_DJ_ShojiPaper)." % (ARMORYLAB_BIAS_EV, DOJOLAB_BIAS_EV, parity)},
            "per_actor_overrides_dojolab": {
                "SM_DKH_DoorLeaf_Parked": {"slot": "M_DJ_ShojiPaper", "child_mi": "MI_DJA_ParkedLeafPaper",
                                           "scalars": {"EmissiveIntensity": 0.0, "BaseMult": 1.0},
                                           "why": "the six parked leaves stand against plaster inside the hall: reflective "
                                                  "paper, not a lamp"},
                "SM_DKH_Rear_WindowBacker": {"slot": "M_DJ_ShojiPaper", "child_mi": "MI_DJA_BackerPaper",
                                             "scalars": {"EmissiveIntensity": "x 0.02 of M_DJ_ShojiPaper"},
                                             "why": "the windows read dark like the armory's own night stills; the "
                                                    "backer rects are off"},
                "note": "recommended for ArmoryLab too (the interior faces these); per level, never synced"},
        },
        "counts": {"pieces": len(out_p), "instances": len(placed), "materials": len(mats), "textures": len(tex),
                   "masters": len(masters)},
        "readback_check": {"against": "WorkFiles/dojo/build/unreal/showcase/materials.json (DojoLab readback)",
                           "mismatches": readback_bad},
    }
    print(json.dumps(doc["counts"]), "readback mismatches:", readback_bad)
    if readback_bad:
        print("STOP: the recipe does not equal DojoLab's built instances")
        return 1
    cur = A.SH / "shell_materials.json"
    old = A.jload(cur) if cur.exists() else None
    strip = lambda d: {k: v for k, v in (d or {}).items() if k not in ("revision", "date")}  # noqa: E731
    if old is not None and strip(old) == strip(doc):
        print("shell_materials.json: unchanged")
        return 0
    if not a.write:
        print("dry run: shell_materials.json would change (run with --write under the ArmoryHall lock)")
        return 4
    if not A.lock_held():
        return 1
    M = A.jload(A.SH / "manifest.json")
    doc["revision"] = int(M["revision"]) + 1
    A.jdump(cur, doc)
    print(f"shell_materials.json WRITTEN as revision {doc['revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
