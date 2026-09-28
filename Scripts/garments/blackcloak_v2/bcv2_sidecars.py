"""BlackCloak_MH_v2: write the export sidecars that build_garment.py does not (system Python or Blender, stdlib only).

    py Scripts/garments/blackcloak_v2/bcv2_sidecars.py [--tag r1]

* Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.material_params.json - the TARGET_SPEC 4.6 contract: per slot the
  textures, UV map, UV scale and shading numbers, so a measurer can rebuild the shipped material (v2m_common reads the
  keys base_color_tex / orm_tex / normal_tex / uv_map / uv_scale / roughness_mult / specular / sheen_* / normal_strength;
  the fray alpha keys are extra: the wool is Masked through UV1 in Unreal).
* Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.cloth.json - the cloth section's per-vertex pin weight (the
  PinMask red) and the proposed Unreal MaxDistance / AnimDrive per vertex (keyed by rest position, cm, Unreal axes too),
  plus the proposed Chaos settings. Copied from the assemble step's record.
"""
import argparse
import hashlib
import json
import os
import shutil

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = ROOT + "/Exports/Garments/BlackCloak_MH_v2"
WORK = ROOT + "/WorkFiles/BlackCloak_MH_v2/build"

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="r1")
A = ap.parse_args()

P = json.load(open(os.path.join(HERE, "material_params.json")))
S_UV = 5.85
TILE = P["tile_m"]
cb = P["cloth"]["blender"]
fbx = os.path.join(EXPORT, "SK_BlackCloak_MH_v2.fbx")
sha = hashlib.sha256(open(fbx, "rb").read()).hexdigest()
wool = {
    "base_color_tex": P["textures"]["cloth_bc"],
    "orm_tex": P["textures"]["cloth_orm"],
    "normal_tex": P["textures"]["cloth_n"],
    "normal_convention": "DirectX (green down) on disk; flip green in Blender, not in Unreal",
    "uv_map": "UVMap",
    "uv_scale": round(S_UV / TILE, 6),
    "uv_note": "UV0 = flat-pattern metres / %.2f (unique, non-overlapping atlas); the 0.45 m slub tile repeats %.1f times per UV unit" % (S_UV, S_UV / TILE),
    "base_tint_linear": [1.0, 1.0, 1.0],
    "roughness_mult": 1.0,
    "roughness_note": "roughness = ORM.G (x 1.0; the stage-1 kit's 'ORM.G + 0.0' is the same)",
    "metallic": 0.0,
    "specular": cb["specular_ior_level"],
    "sheen_weight": cb["sheen_weight"],
    "sheen_tint": cb["sheen_tint"],
    "sheen_roughness": cb["sheen_roughness"],
    "normal_strength": cb["normal_strength"],
    "two_sided": True,
    "ao_tex_channel": "ORM.R (Unreal indirect only; Cycles computes its own occlusion)",
    "fray_opacity_tex": P["textures"]["fray_bca"],
    "fray_opacity_uv_map": "UV1_Fray",
    "fray_opacity_channel": "A",
    "fray_opacity_uv_scale": 1.0,
    "fray_note": "the fringe rows along every cut edge (and every non-fringe vertex at V 0.97, opaque) sample the fray strip's alpha "
                 "through UV1 (U = edge metres / 0.45, V = 1 at the cloth side). Unreal: Blend Mode Masked, clip 0.5, dithered, "
                 "alpha-coverage preservation on the fray texture. A measurer that ignores these keys renders the fringe as solid cloth.",
    "unreal": {"shading_model": P["cloth"]["unreal"]["shading_model"], "fuzz_colour": P["cloth"]["unreal"]["fuzz_colour"],
               "cloth": P["cloth"]["unreal"]["cloth"], "specular": P["cloth"]["unreal"]["specular"], "blend_mode": "Masked",
               "opacity_mask": "T_BlackCloakV2_Fray_BCA.A via UV1_Fray", "opacity_mask_clip": 0.5, "two_sided": True,
               "uv_scale": round(S_UV / TILE, 6), "fallback": P["cloth"]["unreal"]["fallback_default_lit"],
               "status": "not verified in Unreal"},
}
cl = P["clasp"]
clasp = {"base_tint_linear": cl["blender"]["base_colour_linear"], "metallic": cl["blender"]["metallic"],
         "roughness": cl["blender"]["roughness"], "specular": cl["blender"]["specular_ior_level"], "normal_strength": 1.0,
         "two_sided": False, "unreal": cl["unreal"], "note": "no textures: a dark glossy lacquer / horn dielectric"}
out = {"version": "BlackCloak_MH_v2 round build (%s)" % A.tag, "fbx": os.path.basename(fbx), "fbx_sha256": sha,
       "texture_dir": "Textures", "view_transform_for_tone_checks": "Standard, look None, exposure 0 (white card 0.90 linear)",
       "slots": {"M_BlackCloakV2_Wool": wool, "M_BlackCloakV2_Wool_Sim": dict(wool, note="the build's cloth-section copy of M_BlackCloakV2_Wool"),
                 "M_BlackCloakV2_Clasp": clasp}}
json.dump(out, open(os.path.join(EXPORT, "SK_BlackCloak_MH_v2.material_params.json"), "w"), indent=1)
src = os.path.join(WORK, "cloth_pins_%s.json" % A.tag)
if os.path.exists(src):
    d = json.load(open(src))
    d["fbx_sha256"] = sha
    json.dump(d, open(os.path.join(EXPORT, "SK_BlackCloak_MH_v2.cloth.json"), "w"), indent=0)
print("SIDECARS_OK", sha[:12])
