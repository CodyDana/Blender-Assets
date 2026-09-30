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

NAMES = {"PineA": "small S-curve garden pine (~2.2-2.5 m from the sheet's 1.8 m figure; cloud pads, rounded crown)",
         "PineB": "tall layered pine (~3.4-3.6 m; S trunk, 9 tiers of pads)",
         "PineC": "big leaning pine (~4.3-4.5 m; massive twisted trunk, the long reaching limb, a broken stub)",
         "PineD": "cliff pine on a granite boulder (rock stage: ~3.2 m incl. a ~1.1-1.25 m rock at 0.65 x the "
                  "sheet's relative size, owner; 10 roots over the rock into its clefts)"}
# v2 (owner): heights come from the sheet's 1.8 m figure, not the old 2.5/4.5/7/4 m spec. In-engine the instance
# scale may go to about 1.3x where a bigger tree is wanted (trunk girth, pads and needles scale with it: needles stay
# inside 7-12 cm up to about 1.3x on A/B/D and 1.0x on C, whose needles are already 8.3-11.3 cm).
SCALE_NOTE = ("Heights are measured from the sheet's 1.8 m figure (v2). Instance scale may go to ~1.3x in Unreal for a "
              "bigger tree; needles then reach ~12 cm on A/B/D (C: keep <= 1.05x for needles <= 12 cm). D (rock "
              "stage): the owner shrank the rock to ~0.65 x its sheet size relative to the tree and the tree sits "
              "lower on it, so D stands ~3.2 m instead of the sheet's 3.6-3.9 m; ~1.15-1.2x restores the sheet height "
              "(rock included).")
BUDGET = {"study_8.7": {"trunk_tris": 80000, "foliage_tris": 150000, "foliage_tris_if_judge_needs_density": 250000},
          "note": "Nanite meshes; over-budget items are listed per item (measure in Unreal, G15/G18, before cutting)"}

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
                      "_Rock": "UCX hulls, one per lobe (D1 3, D2 2); BlockAll; no traversal marker: the top is the "
                               "tree's root plate (no flat landing >= 0.49 m free of the trunk; stone study 4.13)",
                      "_Foliage": "NoCollision on the component (no hulls)"},
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
        "MI_DKN_<D1|D2>_Rock (rock slot 0, rock stage v3)": "the stone study's M_ST_RockUnique recipe (4.9.5 a) "
                        "on the shared library granite: M_DJ_Granite (UseWear on, Tint (0.60, 0.565, 0.515)) tiled on "
                        "TexCoord[0] * (S / 4) with S = the rock's metres per UV0 unit (item 'rock.m_per_uv0'), under "
                        "the rock's unique maps on TexCoord[0]: T_DKN_<V>_Rock_N (DirectX; replaces the library's "
                        "3.5 / 9 cm facet normal, study rule 10), T_DKN_<V>_Rock_ORM (baked AO in R, roughness G), "
                        "T_DKN_<V>_Rock_M (linear, Masks: R moss -> lerp to the moss BC tiled at S / 2, G lichen -> "
                        "lerp to ochre (0.30, 0.155, 0.06) / yellow-grey (0.34, 0.32, 0.18) / pale (0.50, 0.49, 0.44) "
                        "picked by a ~30 cm noise, x0.8, B dirt -> lerp to soil (0.075, 0.058, 0.042), x0.55); grain "
                        "micro relief = a 0.1 bump of the albedo (Blender) or the library's detail normal at 0.15-0.3 "
                        "(Unreal). The rock's 'Wear' vertex colours: R grime (clefts, cracks, weathering mottle), "
                        "G edge wear, B foot dirt. Not built in Unreal in this run",
        "MI_DKN_<D1|D2>_RockMoss (rock slot 1)": "the moss cushions on the rock top: M_DKN_Moss on TexCoord[0] * (S / 2)",
        "MI_DKN_PineRock (BaseMound_D stones)": "the v2 tiling granite + T_DKN_RockOverlay_M, kept for the mound's "
                        "small stones only",
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
    ap.add_argument("--renders", default=str(BUILD / "renders" / "v2f"))
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
            "instance_scale_max": 1.05 if v.startswith("PineC") else 1.3,
            "rosettes_per_pad": [p.get("rosettes") for p in info.get("pad_info", [])],
            "over_budget": {k: n for k, n in info["tris"].items()
                            if (k == "trunk" and n > 80000) or (k == "foliage" and n > 150000)},
            "base_mound": f"SM_DKN_BaseMound_{v[4]} (optional, shared by {v[:5]}1/{v[:5]}2, same origin)",
            **({"rock_status": "rock stage (2026-09-30): rebuilt with STONE_BUILDING_STUDY.md 4.9 / 8.3 (SDF corestone "
                               "lobes, per-lobe opening, cracks, unique UV0 + bakes) at 0.65 x the v2 rock (owner); tree "
                               "moved onto it (make_spec d_rock_v3); roots refitted. v2f: ONE fused broad boulder (lobes "
                               "overlap, 5.5 cm SDF closing, domed tops; visible width / height 1.24 / 1.28), trunk "
                               "0.26 / 0.30 m at the rock (about 1/5 of the rock width), 13 roots + forks draping the left "
                               "flank, fern / shrub skirt on BaseMound_D",
                "trunk_base_r_m": s["trunk"].get("d_trunk_r0"),
                "rock": info.get("rock"), "tree_shift_m": s.get("rock", {}).get("tree_shift_m"),
                "height_sheet_m": s.get("height_sheet_m")} if v.startswith("PineD") else {}),
            "files": files,
            "measured_views": {k: {kk: m.get(kk) for kk in ("ref_panel", "iou", "width_err", "crown_w_m", "row_fill")}
                               for k, m in meas.items() if k.startswith(v + "_")},
        })
    shared = {k: e for k, e in exp.items() if k.startswith(("T_DKN_Bark", "T_DKN_Needle", "T_DKN_Moss", "T_DKN_Soil",
                                                           "T_DKN_RockOverlay"))}
    mounds = {k: e for k, e in exp.items() if k.startswith("SM_DKN_BaseMound")}
    cat = {"kit": "DojoKit", "set": "DojoPines", "round": "v2f (fix round on v2 + rock stage)", "prefix": "SM_DKN_ / T_DKN_",
           "species": "Pinus thunbergii (niwaki)", "scale_note": SCALE_NOTE, "budgets": BUDGET,
           "base_mounds": mounds,
           "reference": "References/Dojo/dojo_japanese_pine_ref.png (AI-generated sheet: measured and traced only; "
                        "no pixel of it is in any texture). Record AI-reference use for Fab (ASSET_GUIDELINES 11).",
           "study": "TREE_BUILDING_STUDY.md", "generator": "Scripts/vegetation/ (reusable) + Scripts/dojo/pines/",
           "shared_textures": shared, "unreal": UNREAL, "items": items,
           "qa_notes": qa.get("notes"), "tuft_unit_qa": qa.get("tuft_unit_qa")}
    (BUILD / "pines_catalog.json").write_text(json.dumps(cat, indent=1), encoding="utf-8")
    print("wrote", BUILD / "pines_catalog.json", len(items), "items")


if __name__ == "__main__":
    main()
