"""Write fx_catalog.json (the Unreal import, material and Niagara recipe) from the build results (plain Python 3).

    py -3 -B Scripts/dojo/fx/make_catalog.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402


def rel(p):
    return str(Path(p).relative_to(fx.ROOT)).replace("\\", "/")


def main():
    qa = fx.load_json(fx.WORK / "json/petals_qa.json")
    tq = fx.load_json(fx.WORK / "json/texture_qa.json")
    fb = fx.load_json(fx.WORK / "json/flipbooks.json") if (fx.WORK / "json/flipbooks.json").exists() else {}
    foam = fx.load_json(fx.WORK / "json/foam.json")
    meshes = []
    for name, e in {**qa["petals"], **qa["drifts"]}.items():
        meshes.append({"name": name, "file": qa["exports"][name]["file"].replace("\\", "/"), "triangles": e["triangles"],
                       "size_mm_xyz": qa["dims_mm_xyz"].get(name),
                       "qa": "PASS" if e["passed"] else ("PASS except uv_no_overlap (shared petal UV0 by design)"
                                                          if e.get("passed_except_shared_uv0") else "FAIL"),
                       "collision": "none (FX / decor)",
                       "origin": "area centroid (Niagara mesh particles spin about it)" if "Drift" not in name
                       else "on the ground at the cluster centre (lowest petal 0.3 mm above)"})
    textures = [{"name": k, "file": rel(fx.TEX / k), "size": v["size"], "colour_space": v.get("colour_space"),
                 "ue_compression": v.get("ue_compression"), "qa": "PASS" if v["passed"] else "FAIL"}
                for k, v in tq["textures"].items()]
    cat = {
        "asset": "DojoFX (cherry petals, river mist / spray / haze, water foam)",
        "date": str(date.today()), "units": "metres in the FBX (export_fbx kind=static); Unreal cm on import",
        "provenance": "Our own procedural work (Blender 5.2 headless). The sheets dojo_petals_ref / dojo_mist_ref are "
                      "AI-generated look references: measured and traced (petal outline), no reference pixel is in any "
                      "texture. Colour-neutral FX maps, lit in engine.",
        "meshes": meshes, "textures": textures, "flipbooks": fb, "foam": foam,
        "import": {
            "petal_meshes": "Static Mesh, Import Normals, Nanite OFF (tiny masked two-sided cards: Niagara mesh particles "
                            "and small clusters), Generate Lightmap UVs OFF (UV1 shipped), collision none "
                            "(Collision Complexity: no collision; Niagara uses its own GPU depth-buffer collision), "
                            "Build Scale 1.0. Material slot 0 MI_DKF_Petal, drift slot 1 MI_DKF_PetalOld.",
            "textures": "sRGB ON for *_BC only. *_N: Normalmap, Flip Green OFF (DirectX already). *_ORM / *_M: Masks. "
                        "*_SSS: Grayscale. *_SixWayP / *_SixWayN: Default (BC7), sRGB OFF, Mip Gen FromTextureGroup, "
                        "Texture Group Effects, LOD Bias 1 on Medium/Low scalability (4096 -> 2048). "
                        "T_DKF_Foam_*: Texture Group World, Wrap. Petal and decal textures: Clamp is NOT required (masked).",
            "flipbook_layout": "8 x 8, frame 0 top-left, row-major: Niagara Sub UV 'Sub Image Size' (8, 8), "
                               "linear over Normalized Age, Sub UV Blending ON (renderer) for the 64-frame life cycle.",
        },
        "materials": {
            "M_DKF_Petal (master)": {
                "domain": "Surface", "blend": "Masked (Opacity Mask Clip 0.5)", "two_sided": True,
                "shading": "Two Sided Foliage (or Substrate Slab, Sub-Surface Type Two-Sided Wrap, as the pines)",
                "usage_flags": ["Niagara Mesh Particles", "Static Lighting OFF", "Instanced Static Meshes"],
                "graph": {
                    "BaseColor": "lerp(T_BackBC.rgb, T_BC.rgb, TwoSidedSign * 0.5 + 0.5) * Tint; Tint default (1,1,1); "
                                 "hue jitter: lerp(1, (1.0, 0.97, 0.99), ParticleRandom or PerInstanceRandom) (+-3 %)",
                    "OpacityMask": "T_BC.a (dither-free, masked)",
                    "Normal": "T_N (DirectX)", "Roughness": "T_ORM.g", "AmbientOcclusion": "T_ORM.r", "Metallic": 0,
                    "SubsurfaceColor": "BaseColor * T_SSS.r * TransmissionTint (1.0, 0.80, 0.82) * Transmission (0.8)",
                    "Specular": 0.35,
                    "WPO": "none (Niagara moves the particles; clusters are static)",
                },
                "instances": {
                    "MI_DKF_Petal": "T_DKF_Petal_BC / T_DKF_PetalBack_BC / _N / _ORM / _SSS",
                    "MI_DKF_PetalOld": "T_DKF_PetalOld_BC (also as Back BC), _N, _ORM, _SSS; Transmission 0.35, "
                                       "BackTint (0.8, 0.8, 0.8) (browned, ~1 in 8 on the ground, ~1 in 14 in the air)",
                },
            },
            "M_DKF_PetalScatterDecal": {
                "domain": "Deferred Decal", "blend": "Translucent, Decal Response ColorNormalRoughness (DBuffer)",
                "graph": "Cell (0..3 scalar) picks one 2x2 atlas cell: UV = TexCoord * 0.5 + (fmod(Cell,2), floor(Cell/2)) * 0.5; "
                         "BaseColor = BC.rgb, Opacity = BC.a * Fade, Normal = N, Roughness = ORM.g",
                "decal_actor": "size X/Y 35 cm (one cell = 0.35 m), projection depth 10 cm, random yaw; cells: 0 sparse, "
                               "1 medium, 2 dense drift, 3 strays. Use in stone-paver joints, on moss and on the raked gravel "
                               "where meshes would z-fight; the SM_DKF_PetalDrift_* meshes for hero spots.",
            },
            "M_DKF_SixWaySprite (master)": {
                "domain": "Surface", "blend": "Translucent", "shading": "Unlit (lighting from the six-way maps)",
                "usage": "Niagara Sprites", "flags": "Responsive AA off, Depth Fade 150 cm (soft particles), "
                                                     "Translucency Pass: Before DOF, no velocity output",
                "subuv": "Particle SubUV node (8x8, blend ON) sampling BOTH SixWayP and SixWayN with the same UVs",
                "lighting": {
                    "sprite_basis": "R = CameraRightVector, U = CameraUpVector, F = CameraForwardVector (camera-facing sprites)",
                    "light": "Ls = (dot(L,R), dot(L,U), dot(L,F)); L = direction TO the sun (MPC_DKF_Sky.SunDirection, set "
                             "from the Ultra Dynamic Sky directional light each tick), sun colour MPC_DKF_Sky.SunColor",
                    "formula": "key = max(Ls.x,0)*P.r + max(-Ls.x,0)*N.r + max(Ls.y,0)*P.g + max(-Ls.y,0)*N.g + "
                               "max(Ls.z,0)*P.b + max(-Ls.z,0)*N.b ; P.b is lit from BEHIND the sprite (backlight, "
                               "the sheet's sunset glow), N.b from the camera side",
                    "emissive": "SunColor * key * SunIntensity + SkyColor * (P.g*0.5 + N.b*0.3 + 0.2) * AmbientScale",
                    "opacity": "P.a * ParticleColor.a * DepthFade",
                    "cheap_fallback": "Default Lit translucent, Translucency Lighting Mode Volumetric Per Vertex "
                                      "Directional, BaseColor = lerp(0.4, 1, P.g), Opacity = P.a",
                },
                "instances": {"MI_DKF_MistPuff": "T_DKF_MistPuff_SixWay*", "MI_DKF_MistWisp": "T_DKF_MistWisp_SixWay*",
                              "MI_DKF_SprayBurst": "T_DKF_SprayBurst_SixWay* (AmbientScale 0.6, a little Specular-like "
                                                   "boost: key^0.8)"},
            },
            "M_DKF_Haze": "Translucent unlit sprite / card: Opacity = T_DKF_Haze_M.r * Alpha(0.12-0.2) * DepthFade(300); "
                          "Emissive = SunColor * (0.6*b + 0.4*g) + SkyColor*0.3 (G top-lit, B back-lit). 2:1 card.",
            "MF_DKF_RiverFoam (for the Water plugin river material)": {
                "inputs": "WorldPosition.xy, flow (Water body velocity / flow map), turbulence mask (velocity magnitude, "
                          "rock proximity from the distance field, the rapids spline mask)",
                "graph": "two samples of T_DKF_Foam_M.r panned along the flow with a half-period phase offset (flow-map "
                         "blend), tiling 2.0 m; T_DKF_Foam_M.g at 0.6 m for close lace; B streaks stretched along the "
                         "flow; foam = saturate((cov - (1 - turbulence)) * 3) ; BaseColor = lerp(water, (0.80, 0.82, 0.82), "
                         "foam); Roughness lerp(0.05, 0.6, foam); Normal = BlendAngleCorrected(water N, T_DKF_Foam_N, foam); "
                         "Opacity/refraction reduced under foam",
                "seamless": "built on the torus (FFT noise + periodic Voronoi; the Voronoi half-period shift test is exact "
                        "to 5e-15), so the tile has no seam",
            },
        },
        "niagara": {
            "NS_DKF_PetalFall": {
                "renderer": "Mesh renderer, meshes SM_DKF_Petal_A..F (weight 1 each) + SM_DKF_PetalOld_A (weight 0.45 "
                            "~ 1 in 14 in the air), Facing Mode Default, sort off, GPU sim",
                "spawn": "global: box 60 x 60 m at 8-16 m above the terrace, 25-40 /s; per CherrySlot actor: sphere r 3 m "
                         "centred 4.5 m up, 2-5 /s (canopy fall) + gust burst 40-80 on a wind event",
                "lifetime": "14-20 s", "scale": "mesh is real size (12.5-14.5 mm); uniform scale 1.0-1.4 (gameplay legibility)",
                "forces": "Gravity -980 cm/s2 + Drag 3.0 (terminal ~1 m/s, the real petal fall speed), Curl Noise "
                          "strength 80 cm/s freq 0.015, Wind from MPC (UDS wind dir) 60-160 cm/s",
                "rotation": "initial orientation random; Mesh Rotation Rate random axis 120-420 deg/s (flutter), "
                            "Rotational Drag 1.5",
                "collision": "GPU Depth Buffer collision, Restitution 0, Friction 0.9, Rest after 0.2 s; resting petals "
                             "fade (Scale Color alpha) over the last 4 s",
                "lighting": "the petal material (Two Sided Foliage) gives the back-lit rim glow at the 9 deg sun",
                "scalability": "spawn scale Epic 1.0 / High 0.6 / Medium 0.35 / Low 0.15; cull 70 m; max 6000 GPU particles",
            },
            "NS_DKF_RiverMist": {
                "emitters": {
                    "puff": "MI_DKF_MistPuff sprites at rapids / rock impacts: 2-4 /s, lifetime 4-7 s, size 3-7 m, "
                            "velocity up 20-50 cm/s + downstream 60-150 cm/s, rotation +-15 deg, alpha 0.25-0.45",
                    "wisp": "MI_DKF_MistWisp along the river spline: 4-8 /s, lifetime 6-10 s, size (8-14) x (4-7) m, "
                            "velocity downstream 80-200 cm/s + up 10-30, alpha 0.2-0.35",
                },
                "cell_usage": "measured: MistPuff content spans 0.76 x 0.48 of a cell (median 0.68 x 0.43), MistWisp 0.78 x 0.41: "
                              "the visible mist is ~0.7 of the sprite width, so set Sprite Size ~1.4x the wanted mist width",
                "common": "SubUV 8x8 linear over age, Sub UV Blending ON, camera facing (Face Camera Plane), sort view "
                          "depth, Depth Fade 150-300 cm, local space off, bounds fixed; colour white (lit by the six-way "
                          "material from the UDS sun)",
            },
            "NS_DKF_RapidSpray": {
                "burst": "MI_DKF_SprayBurst (a Mantaflow surge-into-boulder splash: rises up the rock face, the sheet "
                         "tears, falls, fades): 1 sprite every 0.8-1.8 s per boulder the current hits, placed just in front "
                         "of the rock, size 1.5-3 m (the cell spans 1.3 sim m), lifetime 0.64-0.9 s (64 frames at 100 "
                         "fps = 0.64 s real time), sprite pivot offset (0.5, 0.96): the water line is 4 % above the "
                         "cell bottom; mirror (UV flip) half the spawns for variety",
                "droplets": "secondary GPU sprites 1-3 cm, white, Velocity-aligned, 60-150 per burst, cone 35 deg up, "
                            "speed 250-450 cm/s, gravity, lifetime 0.6-0.9 s",
                "mist": "each burst spawns 1 MI_DKF_MistPuff at 40 % alpha (the sheet's spray-into-mist)",
            },
            "NS_DKF_RiverHaze": "T_DKF_Haze_M on 20-40 x 8-12 m camera-facing sprites with the Z axis locked (Custom "
                                "Alignment (0,0,1)), low over the water, lifetime 25-40 s, drift 20-50 cm/s downstream, "
                                "alpha 0.12-0.2, fade with height (Depth Fade 300 cm)",
        },
    }
    fx.write_json(fx.WORK / "fx_catalog.json", cat)
    print("catalog", len(meshes), "meshes", len(textures), "textures")


if __name__ == "__main__":
    main()
