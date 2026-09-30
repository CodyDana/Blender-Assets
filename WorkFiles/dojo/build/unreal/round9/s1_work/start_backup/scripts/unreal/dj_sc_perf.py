"""DojoLab SHOWCASE performance report (pythonscript commandlet, -nullrhi, READ-ONLY: never saves anything). Round 5.

Loads the saved L_Dojo and counts, from the assets themselves:
  actors        by class (mesh actors, decals, lights, markers, cameras, the rest)
  draw calls    an ESTIMATE for the raster passes: non-Nanite = mesh sections (actor x material slot, LOD0), and the
                unique (mesh, material) pairs those collapse to with UE's dynamic instancing of identical mesh draw
                commands; Nanite = the unique materials in the Nanite raster / shading bins; decals = one per decal actor
                (DBuffer pass); both counted per pass family, shadows not included
  triangles     LOD0 (non-Nanite) and full-detail source triangles (Nanite; the rendered count is view dependent), per
                piece and placed (x instances), split Nanite / non-Nanite
  textures      every Texture2D the level's materials use: size, format (compression settings), mips, and an estimated
                GPU memory (bytes per texel by the compressed format, x 4/3 for the mip chain, never-stream noted)
  settings      the renderer cvars that matter (Lumen, VSM, Nanite, TSR, DBuffer) as the project runs them
Result: WorkFiles/dojo/build/unreal/showcase/perf.json
"""
import json
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402
import dj_sc_common as S  # noqa: E402

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L = S.load()
# bytes per texel of the compressed GPU format (DX12 desktop): TC_Default = BC1 (no alpha) / BC3 (alpha); TC_Masks =
# BC1 / BC3; TC_Normalmap = BC5; TC_VectorDisplacementmap = B8G8R8A8; TC_HDR = RGBA16F; TC_BC7 = BC7; TC_Grayscale = G8
BPP = {"TC_DEFAULT": (0.5, 1.0), "TC_MASKS": (0.5, 1.0), "TC_NORMALMAP": (1.0, 1.0),
       "TC_VECTOR_DISPLACEMENTMAP": (4.0, 4.0), "TC_HDR": (8.0, 8.0), "TC_BC7": (1.0, 1.0), "TC_GRAYSCALE": (1.0, 1.0),
       "TC_ALPHA": (1.0, 1.0), "TC_EDITOR_ICON": (4.0, 4.0), "TC_HDR_COMPRESSED": (1.0, 1.0)}
CVARS = ("r.DynamicGlobalIlluminationMethod", "r.ReflectionMethod", "r.Shadow.Virtual.Enable", "r.Nanite",
         "r.AntiAliasingMethod", "r.Lumen.HardwareRayTracing", "r.DBuffer", "r.Lumen.TraceMeshSDFs",
         "r.DistanceFields", "r.GenerateMeshDistanceFields", "r.ScreenPercentage", "r.Shadow.Virtual.ResolutionLodBiasDirectional",
         "r.Lumen.ScreenProbeGather.DownsampleFactor", "r.VolumetricFog", "r.SkyAtmosphere")


def enum_name(v):
    return str(v).split(".")[-1].split(":")[0].strip("<> ")


def cvar(name):
    try:
        return unreal.SystemLibrary.get_console_variable_float_value(name)
    except Exception:  # noqa: BLE001
        try:
            return unreal.SystemLibrary.get_console_variable_int_value(name)
        except Exception as exc:  # noqa: BLE001
            return f"n/a ({str(exc)[:60]})"


def textures_of(mat, seen):
    out = set()
    if mat is None:
        return out
    try:
        for t in unreal.MaterialEditingLibrary.get_used_textures(mat):
            out.add(t)
    except Exception:  # noqa: BLE001
        pass
    return out


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": []}
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        rep["loaded"] = bool(les.load_level(C.LEVEL))
        actors = EAS.get_all_level_actors()
        rep["actors"] = {"total": len(actors), "by_class": dict(Counter(a.get_class().get_name() for a in actors))}
        sm_actors = [a for a in actors if isinstance(a, unreal.StaticMeshActor)]
        visible = [a for a in sm_actors if not a.get_editor_property("hidden")]
        pieces = defaultdict(int)
        nn_sections, nn_pairs, nan_mats, nan_pairs, all_mats = 0, set(), set(), set(), set()
        tris = {"nanite_source": 0, "non_nanite_lod0": 0}
        per_piece = {}
        shadow_casters = 0
        for a in visible:
            smc = a.static_mesh_component
            m = smc.get_editor_property("static_mesh")
            if m is None:
                continue
            name = m.get_name()
            pieces[name] += 1
            nanite = bool(m.get_editor_property("nanite_settings").get_editor_property("enabled"))
            if name not in per_piece:
                per_piece[name] = {"nanite": nanite, "lod0_tris": int(m.get_num_triangles(0)), "lods": int(m.get_num_lods()),
                                   "slots": len(m.get_editor_property("static_materials"))}
            mats = [smc.get_material(i) for i in range(smc.get_num_materials())]
            for mi in mats:
                all_mats.add(mi.get_path_name() if mi else "None")
            if smc.get_editor_property("cast_shadow"):
                shadow_casters += 1
            if nanite:
                tris["nanite_source"] += per_piece[name]["lod0_tris"]
                for mi in mats:
                    nan_mats.add(mi.get_path_name() if mi else "None")
                    nan_pairs.add((name, mi.get_path_name() if mi else "None"))
            else:
                tris["non_nanite_lod0"] += per_piece[name]["lod0_tris"]
                nn_sections += len(mats)
                for mi in mats:
                    nn_pairs.add((name, mi.get_path_name() if mi else "None"))
        decals = [a for a in actors if a.get_class().get_name() == "DecalActor"]
        dmats = {a.get_editor_property("decal").get_decal_material().get_path_name() for a in decals
                 if a.get_editor_property("decal").get_decal_material()}
        lights = [a for a in actors if a.get_class().get_name() in ("PointLight", "SpotLight", "DirectionalLight", "SkyLight")]
        rep["meshes"] = {"visible_mesh_actors": len(visible), "hidden_mesh_actors": len(sm_actors) - len(visible),
                         "unique_meshes": len(pieces),
                         "nanite_actors": sum(n for p, n in pieces.items() if per_piece[p]["nanite"]),
                         "non_nanite_actors": sum(n for p, n in pieces.items() if not per_piece[p]["nanite"]),
                         "nanite_unique_meshes": sum(1 for p in pieces if per_piece[p]["nanite"]),
                         "non_nanite_unique_meshes": sum(1 for p in pieces if not per_piece[p]["nanite"]),
                         "shadow_casting_mesh_actors": shadow_casters}
        rep["draw_calls_estimate"] = {
            "non_nanite_sections_actor_x_slot": nn_sections,
            "non_nanite_unique_mesh_material_pairs": len(nn_pairs),
            "nanite_unique_materials_shading_bins": len(nan_mats),
            "nanite_unique_mesh_material_pairs": len(nan_pairs),
            "decal_draws": len(decals), "decal_materials": len(dmats),
            "unique_materials_in_level": len(all_mats),
            "per_pass_estimate_after_instancing": len(nn_pairs) + len(nan_mats) + len(decals),
            "note": "base pass only; shadow depth (VSM) re-draws the casters, Lumen card capture is cached"}
        rep["triangles"] = {"nanite_full_detail_source_placed": tris["nanite_source"],
                            "non_nanite_lod0_placed": tris["non_nanite_lod0"],
                            "total_placed": tris["nanite_source"] + tris["non_nanite_lod0"],
                            "unique_mesh_tris": sum(v["lod0_tris"] for v in per_piece.values()),
                            "top_placed": sorted(([p, per_piece[p]["lod0_tris"] * n, n, per_piece[p]["nanite"]]
                                                  for p, n in pieces.items()), key=lambda r: -r[1])[:15]}
        rep["lights"] = {"count": len(lights), "by_class": dict(Counter(a.get_class().get_name() for a in lights))}
        # textures used by every material on the visible meshes + decals + the sky dome
        texs = {}
        mats_all = set()
        for a in visible:
            smc = a.static_mesh_component
            for i in range(smc.get_num_materials()):
                mats_all.add(smc.get_material(i))
        for a in decals:
            mats_all.add(a.get_editor_property("decal").get_decal_material())
        for mat in mats_all:
            for t in textures_of(mat, texs):
                texs[t.get_path_name()] = t
        # MaterialEditingLibrary.get_used_textures returns nothing in a -nullrhi commandlet: every layout texture (the
        # instances' maps, all of them used) plus the sky dome's cloud texture
        for name in L["textures"]:
            t = unreal.load_asset(S.tex_path(L, name))
            if t is not None:
                texs[t.get_path_name()] = t
        sky = unreal.load_asset("/Game/DojoKit/Showcase/Textures/T_DJS_SunsetClouds")
        if sky is not None:
            texs[sky.get_path_name()] = sky
        rows, total = [], 0.0
        for path, t in sorted(texs.items()):
            try:
                w, h = int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())
                comp = enum_name(t.get_editor_property("compression_settings"))
                alpha = False
                try:
                    alpha = not bool(t.get_editor_property("compression_no_alpha"))
                except Exception:  # noqa: BLE001
                    pass
                bpp = BPP.get(comp, (1.0, 1.0))[1 if alpha else 0]
                mb = w * h * bpp * 4.0 / 3.0 / 2 ** 20
                total += mb
                rows.append({"texture": path.split(".")[0], "size": [w, h], "compression": comp,
                             "never_stream": bool(t.get_editor_property("never_stream")), "est_mb": round(mb, 3)})
            except Exception as exc:  # noqa: BLE001
                rep["notes"].append(f"{path}: {str(exc)[:120]}")
        rep["textures"] = {"count": len(rows), "est_total_mb_full_mips": round(total, 1),
                           "by_size": dict(Counter(f"{r['size'][0]}x{r['size'][1]}" for r in rows)),
                           "by_compression": dict(Counter(r["compression"] for r in rows)),
                           "largest": sorted(rows, key=lambda r: -r["est_mb"])[:12],
                           "note": "estimate; the texture streamer keeps only the mips the views need resident"}
        rep["cvars"] = {k: cvar(k) for k in CVARS}
        rep["per_piece"] = per_piece
        rep["passed"] = True
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    S.write_json(S.SC_OUT / "perf.json", rep)
    unreal.log(f"DJ_STEP_DONE sc_perf passed={rep['passed']}")


main()
