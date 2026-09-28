"""Pass 2: a SECOND fresh process re-reads the SAVED asset and gates it.

Gates 1-8 are in bhu_common.gates; this adds
    9   the four maps' flags persisted (BC, Detail, ORM, N; every one FROM_TEXTURE_GROUP mips) (re-read here from the saved packages)
    10  lightmap UV generation configured on every LOD
    11  the collision hull contains LOD0, measured in ENGINE space on the engine's own
        hull points (supporting planes rebuilt from its 32 points)
    12  the bytes verified are the bytes the build reported (SHA-256)
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealCheck")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import bhu_common as C                                          # noqa: E402

OUT = C.HERE / "pass2.json"
MIPS = str(unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
#: rewind round 1: FOUR maps (the recolour's full-range Detail joins BC / ORM / N), and EVERY map
#: must carry a mip chain from its texture group (not just "not NoMipmaps")
INTENT = {
    "BC": {"srgb": "True", "compression_settings": str(unreal.TextureCompressionSettings.TC_DEFAULT),
           "mip_gen_settings": MIPS},
    "Detail": {"srgb": "True", "compression_settings": str(unreal.TextureCompressionSettings.TC_GRAYSCALE),
               "mip_gen_settings": MIPS},
    "ORM": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_MASKS),
            "mip_gen_settings": MIPS},
    "N": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_NORMALMAP),
          "flip_green_channel": "False", "mip_gen_settings": MIPS},
}
EXPECTED_SIZES = {"BC": 2048, "Detail": 2048, "ORM": 2048, "N": 2048}
STEMS = ("T_BlackHat_Straw", "T_BlackHat_Cloth")


def mip_probe(tex, path):
    """Round 2: round 1's num_mips came back null (no get_num_mips on Texture2D in 5.8's Python).
    Every way this engine offers to COUNT the mip chain is tried and recorded: callables and
    properties with 'mip' in the name, and the asset registry's tags."""
    out = {"attrs": [a for a in dir(tex) if "mip" in a.lower()]}
    for a in out["attrs"]:
        v = getattr(tex, a, None)
        if callable(v) and a.lower().startswith(("get", "blueprint_get", "is_", "has_")):
            r = C.safe(lambda v=v: v())
            if not str(r).startswith("ERROR"):
                out["call:" + a] = str(r)[:200]
    for prop in ("num_cinematic_mip_levels", "mip_load_options", "mip_gen_settings", "lod_bias",
                 "never_stream", "max_texture_size", "downscale"):
        out["prop:" + prop] = str(C.safe(lambda p=prop: tex.get_editor_property(p)))[:200]
    # (the asset registry's tags were probed in run 0925a: "NumMips"/"MipCount" do not exist on a
    # Texture2D in 5.8, and the call used is deprecated - it logged a warning - so it is gone)
    size = C.safe(lambda: int(tex.blueprint_get_size_x()))
    if isinstance(size, int) and size > 0:
        import math
        out["full_chain_would_be"] = int(math.log2(size)) + 1
    return out


def texture_gate():
    out, ok = {}, True
    for stem, (suffix, intent) in [(st, it) for st in STEMS for it in INTENT.items()]:
        path = f"{C.TEXTURE_DEST}/{stem}_{suffix}"
        tex = unreal.load_asset(path)
        if tex is None:
            out[f"{stem}_{suffix}"] = {"error": f"{path} did not load"}
            ok = False
            continue
        read = {k: str(C.safe(lambda k=k, t=tex: t.get_editor_property(k)))
                for k in ("srgb", "compression_settings", "flip_green_channel", "mip_gen_settings",
                          "lod_group", "power_of_two_mode")}
        read["size"] = C.safe(lambda t=tex: [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())])
        matches = {k: read.get(k) == v for k, v in intent.items()}
        matches["has_mips"] = "NO_MIPMAPS" not in str(read.get("mip_gen_settings", "")).upper()
        matches["power_of_two"] = bool(isinstance(read["size"], list)
                                       and all(s > 0 and (s & (s - 1)) == 0 for s in read["size"]))
        matches["size_as_shipped"] = read["size"] == [EXPECTED_SIZES[suffix]] * 2
        read["num_mips"] = C.safe(lambda t=tex: int(t.get_num_mips()) if hasattr(t, "get_num_mips") else None)
        # final pass: the asset registry's built-texture tags (the only place a nullrhi commandlet sees
        # the source format and the alpha channel: ORM now carries the baked specular mask in A)
        ad = unreal.EditorAssetLibrary.find_asset_data(path)
        tags = {}
        for tg in ("Format", "SourceFormat", "HasAlphaChannel", "SRGB", "CompressionSettings", "Dimensions", "MaxTextureSize"):
            tags[tg] = str(C.safe(lambda tg=tg: ad.get_tag_value(tg)))
        read["registry_tags"] = tags
        read["compression_no_alpha"] = str(C.safe(lambda t=tex: t.get_editor_property("compression_no_alpha")))
        if suffix == "ORM":
            # the registry's HasAlphaChannel / Format tags are filled by a PLATFORM build, which a
            # -nullrhi commandlet does not run (Format reads "unknown", measured 0925a); the source
            # itself is read instead: its alpha must span a range (the baked specular mask), and
            # compression_no_alpha must be off so the compressor keeps it (TC_Masks -> AutoDXT)
            mm = C.safe(lambda t=tex: t.compute_texture_source_channel_min_max())
            try:
                lo, hi = mm
                read["source_alpha_min_max"] = [round(float(lo.a), 6), round(float(hi.a), 6)]
                # final pass: the source alpha must be the SHIPPED specular mask's range (the build's
                # report, clipped to 0..1, 8-bit tolerance); round 1 asked for a > 0.5 spread, which the
                # matte cloth's 0.50 - 0.70 mask no longer has
                part = 'straw' if 'Straw' in stem else 'cloth'
                want = [min(max(v, 0.0), 1.0) for v in C.REPORT['textures']['spec_mask_min_max'][part]]
                read['shipped_spec_mask_min_max'] = want
                alpha_range = (abs(float(lo.a) - want[0]) <= 0.006 and abs(float(hi.a) - want[1]) <= 0.006
                               and float(hi.a) - float(lo.a) > 0.1)
            except Exception:  # noqa: BLE001
                read["source_alpha_min_max"] = str(mm)[:160]
                alpha_range = False
            matches["orm_alpha_kept"] = bool(alpha_range and read["compression_no_alpha"] == "False"
                                             and "BGRA8" in tags.get("SourceFormat", "BGRA8"))
        read["mip_probe"] = mip_probe(tex, path)
        if suffix == "ORM":
            # final pass: the ORM names its part's N as Composite Texture (normal variance -> roughness
            # per mip, CTM_NormalRoughnessToGreen), set by bhu_tex_composite.py and re-read here
            ct = C.safe(lambda t=tex: t.get_editor_property("composite_texture"))
            read["composite_texture"] = ct.get_path_name() if hasattr(ct, "get_path_name") else str(ct)
            read["composite_texture_mode"] = str(C.safe(lambda t=tex: t.get_editor_property("composite_texture_mode")))
            read["composite_power"] = str(C.safe(lambda t=tex: t.get_editor_property("composite_power")))
            matches["orm_composite_is_its_normal_map_to_green"] = bool(
                str(read["composite_texture"]).startswith(f"{C.TEXTURE_DEST}/{stem}_N")
                and "NORMAL_ROUGHNESS_TO_GREEN" in read["composite_texture_mode"].upper())
        out[f"{stem}_{suffix}"] = {"read": read, "matches": matches, "passed": all(matches.values())}
        ok = ok and out[f"{stem}_{suffix}"]["passed"]
    return ok, out


def hull_gate(mesh):
    body = mesh.get_editor_property("body_setup")
    elems = body.get_editor_property("agg_geom").get_editor_property("convex_elems")
    if len(elems) != C.EXPECTED_HULLS:
        return {"passed": False, "reason": f"{len(elems)} convex elements"}
    pts = C.safe(lambda: [(p.x, p.y, p.z) for p in elems[0].get_editor_property("vertex_data")])
    if not isinstance(pts, list):
        return {"passed": None, "reason": f"hull vertex_data unavailable: {pts}"}
    lod0 = C.safe(lambda: C.lod0_positions_cm(mesh))
    if not isinstance(lod0, list):
        return {"passed": None, "reason": f"LOD0 positions unavailable: {lod0}", "hull_vertices": len(pts)}
    planes = C.hull_planes(pts)
    worst = max(max(n[0] * v[0] + n[1] * v[1] + n[2] * v[2] - d for n, d in planes) for v in lod0)
    return {"passed": bool(worst <= 1e-4), "hull_vertices": len(pts), "hull_planes": len(planes),
            "lod0_vertices": len(lod0), "max_outside_cm": round(float(worst), 8),
            "method": "supporting planes of the engine's own hull points; every LOD0 vertex tested"}


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR),
              "report_fbx_sha256": C.REPORT["export"]["sha256"]["fbx"]}
    try:
        mesh = unreal.load_asset(C.ASSET)
        if mesh is None:
            report["error"] = f"{C.ASSET} did not load in a fresh process"
        else:
            info = C.inspect(mesh)
            report["asset_info"] = info
            passed, detail = C.gates(info)
            report["gate_detail"] = detail
            tex_ok, tex = texture_gate()
            passed["9_texture_flags_persisted"] = tex_ok
            report["textures"] = tex
            builds = info["lod_build_settings"]
            passed["10_lightmap_uv_configured_on_every_lod"] = bool(
                info["light_map_coordinate_index"] == 1 and all(
                    isinstance(b, dict) and b.get("generate_lightmap_u_vs") for b in builds))
            hull = hull_gate(mesh)
            report["hull"] = hull
            passed["11_hull_contains_lod0_in_engine_space"] = bool(hull.get("passed"))
            passed["12_exact_bytes"] = report["fbx_sha256"] == report["report_fbx_sha256"]
            report["gates"] = passed
            report["passed_all"] = all(passed.values())
            for k in ("lod_triangles", "lod_screen_sizes", "sockets", "size_cm", "convex_hulls",
                      "bounds_sphere_radius_cm"):
                report[k] = info.get(k)
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("BHU_PASS2_DONE " + str(OUT))


main()
