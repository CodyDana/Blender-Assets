"""pines_catalog.json: every shipped pine with its files, numbers, the Unreal import / material / wind recipe.

    py -3 -B Scripts/dojo/pines/make_catalog.py --renders WorkFiles/dojo/build/pines/renders/r0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "pines"
EXPORT = ROOT / "Exports" / "DojoKit" / "Pines"

NAMES = {"PineA": "small garden pine (~2.5 m, curved trunk, cloud pads)",
         "PineB": "medium S-curved pine (~4.5 m, layered pads)",
         "PineC": "large leaning pine (~7 m, long reaching limb, wide flat pads)",
         "PineD": "cliff pine on a granite boulder (~4 m incl. the rock; roots gripping the rock)"}

UNREAL = {
    "route": "A: static Nanite meshes + Pivot Painter 2 WPO wind (study 5.1); no Unreal step was run in this build",
    "import": {
        "importer": "legacy FBX (house setting)",
        "normals": "Import Normals + MikkTSpace", "convert_scene": True, "convert_scene_unit": True,
        "uniform_scale": 1.0, "materials": "Do Not Create Material", "auto_generate_collision": False,
        "one_convex_hull_per_ucx": True, "import_mesh_lods": True, "generate_lightmap_uvs": False,
        "vertex_color_import_option": "Replace (the static default Ignore drops every mask)",
        "build_nanite": True,
        "nanite": {"_Trunk": {"shape_preservation": "None", "lerp_uvs": True},
                   "_Rock": {"shape_preservation": "None", "lerp_uvs": True},
                   "_Foliage": {"shape_preservation": "Voxelize", "lerp_uvs": False,
                                "why": "UV2 carries the PP2 element index; lerping it tears triangles (study 4.13)"}},
        "textures": {"_BC": "sRGB, Default", "_N": "Normalmap, no green flip (maps are DirectX)",
                     "_ORM": "linear, Masks", "_SSS": "linear, Grayscale, full mips",
                     "_PivotPos.exr": "HDR 16-bit, sRGB off, NoMipMaps, Filter Nearest",
                     "_XVector.png": "sRGB off, NoMipMaps, Filter Nearest, VectorDisplacementmap (uncompressed)"},
        "collision": {"_Trunk": "UCX hulls (2-4 per trunk); BlockAll base; Visibility/Camera per study 5.7",
                      "_Rock": "UCX hulls (3); BlockAll", "_Foliage": "NoCollision on the component (no hulls)"},
    },
    "materials": {
        "M_DKN_Bark (master; MI_DKN_<Variant>_Bark per tree)": {
            "model": "Substrate Slab, opaque",
            "inputs": "TexCoord[0]: T_DKN_Bark_BC/_N/_ORM (1 m tiles, 10.24 px/cm); TexCoord[2]: "
                      "T_DKN_<Variant>_Trunk_ORM (unique AO bake, R channel) multiplied into AO; VertexColor.R junction "
                      "weight (fade the unique AO into the tiling bark), .G moss mask (lerp to MossTint 0.10/0.12/0.03 "
                      "linear), .B branch AO (multiply AO)",
            "params": ["Tint", "MossTint", "MossAmount", "NormalStrength (1.0)", "RoughMult (1.0)"],
            "wpo": "none (niwaki are stiff; trunk shadows stay cached)"},
        "M_DKN_Needle": {
            "model": "Substrate Slab, Sub-Surface Type = Two-Sided Wrap (one closure), two-sided, opaque",
            "inputs": "TexCoord[0]: T_DKN_Needle_BC/_N/_ORM/_SSS (every needle has its own cell of the tiling "
                      "needle image); TexCoord[3].x = canopy AO (multiply base colour and subsurface, remap 0.8-1 as "
                      "in Blender or tune); SubsurfaceTint = BC * (1.0, 1.15, 0.55); translucency = SSS * "
                      "TranslucencyStrength (0.3 in Blender, where 0.5 darkened front-lit pads; the Unreal Two-Sided Wrap adds back-light without that loss, so tune it at the sunset camera)",
            "params": ["HueJitter", "ValueJitter (PerInstanceRandom, HZD formula)", "SubsurfaceTint",
                       "TranslucencyStrength", "WindStrength", "PadSwayAmp", "TuftFlutterAmp", "MaxWPO",
                       "PP2_UVIndex = 2"]},
        "MI_DKN_PineRock (rock slot 0)": "instance of the shared dojo library's M_DJ_Granite (Scripts/dojo/materials; "
                        "Opaque master, UseWear on, TileM (4, 4)) with Tint (0.40, 0.385, 0.36); plus the pines' rock "
                        "overlay: T_DKN_RockOverlay_M (linear, Masks) on TexCoord[0] * 4 (1 m tile): lerp(BC, "
                        "(0.075, 0.055, 0.035), 0.55 * G) for the stain streaks, then lerp(BC, (0.30, 0.27, 0.12), "
                        "0.75 * R) for lichen. The overlay needs a small material function in the kit master (not in "
                        "the shared library); the rock carries the library's 'Wear' vertex colours",
        "MI_DKN_Groundcover (foliage slot 1)": "instance of M_DKN_Needle with a Tint multiply (1.25, 1.12, 0.62): "
                        "the grass / fern tufts at the tree bases use the needle texture set",
        "M_DKN_Moss": "Opaque: T_DKN_Moss_BC/_N/_ORM on TexCoord[0] * 2 (2 m moss tile on the granite's 4 m box UVs)",
    },
    "wind": {
        "method": "PivotPainter2FoliageShader on the foliage mesh only",
        "hierarchy": "trunk (0) -> scaffold limb (1) -> sub-limb (2) -> pad; per-tuft flutter from vertex colour B",
        "data": "UV2 = pad element texel; T_DKN_<Variant>_PivotPos.exr (RGB pivot in UE cm, A parent index as Int "
                "as float) + T_DKN_<Variant>_XVector.png (RGB axis, A extent/2048 cm); SM_DKN_<Variant>.wind.json",
        "character": "gentle pad bob about each pad pivot, weighted by vertex colour R (0 at the pivot, 1 at the "
                     "needle tips), phase = G per pad; needle shimmer phase = B per tuft; never whole-tree rocking",
        "suggested": {"PadSwayAmp_cm": 2.0, "PadSwayFreq_hz": 0.35, "TuftFlutterAmp_cm": 0.6,
                      "TuftFlutterFreq_hz": 2.2, "MaxWPO_cm": 6},
        "component": {"wpo_disable_distance_cm": "4000-6000, capped at the measured voxel takeover (study 5.2)",
                      "shadow_cache_invalidation": "Rigid", "vsm_lodbias_test": [3, 4, 5],
                      "per_instance": "PerInstanceRandom hue/value and wind phase"},
        "unverified": ["PP2 Int-as-float decode default in 5.8", "Y flip with a one-vertex test mesh",
                       "XVector extent scale", "voxel takeover distance per tree"],
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", default=str(BUILD / "renders" / "r0"))
    a = ap.parse_args()
    spec = json.loads((HERE / "pines_spec.json").read_text(encoding="utf-8"))
    rep = json.loads((BUILD / "build_report.json").read_text(encoding="utf-8"))
    exp = json.loads((BUILD / "export_report.json").read_text(encoding="utf-8"))["files"]
    qa = json.loads((BUILD / "qa_report.json").read_text(encoding="utf-8"))
    rdir = Path(a.renders)
    meas = json.loads((rdir / "measure.json").read_text(encoding="utf-8")) if (rdir / "measure.json").exists() else {}
    items = []
    for v, s in spec.items():
        info = rep["variants"][v]
        files = {k: e for k, e in exp.items() if f"_{v}_" in k or k.startswith(f"SM_DKN_{v}") or f"T_DKN_{v}" in k}
        items.append({
            "variant": v, "pine": NAMES[v[:-1]], "variant_of_two": int(v[-1]),
            "traced_from": s["ref"], "height_m": s["height_m"],
            "meshes": {k: {"tris": info["tris"][k]} for k in info["tris"]},
            "tufts": info["tufts"], "pads": info["pads"], "wind_elements": info["elements"],
            "flare_ratio": info["flare_ratio"], "fork_exponents": info["fork_exponents"],
            "needle_len_cm": info["needle_len_cm"], "min_twig_r_mm": info["min_twig_r_mm"],
            "u_texel_px_per_cm_by_order": info["u_texel_px_per_cm_by_order"],
            "qa_passed": rep.get("qa_passed", {}).get(v), "pp2_roundtrip_ok": info.get("pp2_roundtrip_ok"),
            "files": files,
            "measured_views": {k: {kk: m[kk] for kk in ("ref_panel", "iou", "width_err", "crown_w_m", "row_fill")}
                               for k, m in meas.items() if k.startswith(v + "_")},
        })
    shared = {k: e for k, e in exp.items() if k.startswith(("T_DKN_Bark", "T_DKN_Needle", "T_DKN_Moss"))}
    cat = {"kit": "DojoKit", "set": "DojoPines", "prefix": "SM_DKN_ / T_DKN_", "species": "Pinus thunbergii (niwaki)",
           "reference": "References/Dojo/dojo_japanese_pine_ref.png (AI-generated sheet: measured and traced only; "
                        "no pixel of it is in any texture). Record AI-reference use for Fab (ASSET_GUIDELINES 11).",
           "study": "TREE_BUILDING_STUDY.md", "generator": "Scripts/vegetation/ (reusable) + Scripts/dojo/pines/",
           "shared_textures": shared, "unreal": UNREAL, "items": items,
           "qa_notes": qa.get("notes"), "tuft_unit_qa": qa.get("tuft_unit_qa")}
    (BUILD / "pines_catalog.json").write_text(json.dumps(cat, indent=1), encoding="utf-8")
    print("wrote", BUILD / "pines_catalog.json", len(items), "items")


if __name__ == "__main__":
    main()
