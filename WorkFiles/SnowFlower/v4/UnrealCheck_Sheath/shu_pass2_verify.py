"""Pass 2: a SECOND fresh process re-reads the SAVED asset and gates it (adapted from the black hat's pass 2).

Gates 1-8 are in shu_common.gates; this adds
    9   every map's flags persisted: Sheath BC/ORM/N (4096) + Lacquer Detail (2048), mips from the
        texture group, N flip-green OFF (DirectX on disk), ORM composite = its N (normal -> roughness)
    10  lightmap UV generation configured on every LOD
    12  the bytes verified are the bytes the build reported (SHA-256)
(the hull-contains-LOD0 gate is carried by the Unreal FBX round trip: UE 5.8 Python cannot read hull points)
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck_Sheath")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import shu_common as C                                          # noqa: E402

OUT = C.HERE / "pass2.json"
MIPS = str(unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
INTENT = {
    "BC": {"srgb": "True", "compression_settings": str(unreal.TextureCompressionSettings.TC_DEFAULT)},
    "Detail": {"srgb": "True", "compression_settings": str(unreal.TextureCompressionSettings.TC_GRAYSCALE),
               "mip_gen_settings": MIPS},
    "ORM": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_MASKS),
            "mip_gen_settings": MIPS},
    "N": {"srgb": "False", "compression_settings": str(unreal.TextureCompressionSettings.TC_NORMALMAP),
          "flip_green_channel": "False"},
}
MAPS = {("T_SnowFlower_Sheath", k): 4096 for k in ("BC", "ORM", "N")}
MAPS[("T_SnowFlower_Sheath_Lacquer", "Detail")] = 2048   # final pass 2026-09-27: shipped at half the atlas
NORMAL_OF = {"T_SnowFlower_Sheath": "T_SnowFlower_Sheath_N"}


def texture_gate():
    out, ok = {}, True
    for (stem, suffix), size in MAPS.items():
        path = f"{C.TEXTURE_DEST}/{stem}_{suffix}"
        tex = unreal.load_asset(path)
        if tex is None:
            out[f"{stem}_{suffix}"] = {"error": f"{path} did not load"}
            ok = False
            continue
        read = {k: str(C.safe(lambda k=k, t=tex: t.get_editor_property(k)))
                for k in ("srgb", "compression_settings", "flip_green_channel", "mip_gen_settings", "lod_group")}
        read["size"] = C.safe(lambda t=tex: [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())])
        m = {k: read.get(k) == v for k, v in INTENT[suffix].items()}
        m["has_mips"] = "NO_MIPMAPS" not in read["mip_gen_settings"].upper()
        m["size_as_shipped"] = read["size"] == [size, size]
        if suffix == "ORM":
            ct = C.safe(lambda t=tex: t.get_editor_property("composite_texture"))
            read["composite_texture"] = ct.get_path_name() if hasattr(ct, "get_path_name") else str(ct)
            read["composite_texture_mode"] = str(C.safe(lambda t=tex: t.get_editor_property("composite_texture_mode")))
            m["orm_composite_is_its_normal_map"] = (read["composite_texture"].startswith(f"{C.TEXTURE_DEST}/{NORMAL_OF[stem]}")
                                                   and "NORMAL_ROUGHNESS_TO_GREEN" in read["composite_texture_mode"].upper())
        out[f"{stem}_{suffix}"] = {"read": read, "matches": m, "passed": all(m.values())}
        ok = ok and out[f"{stem}_{suffix}"]["passed"]
    return ok, out


def holster_gate():
    """In-engine: the sword's own sockets carried through the sheath's Holster socket land where the Blender
    containment gates placed them (sheath_report.json holster_expected_ue_cm, 0.01 cm)."""
    sheath = unreal.load_asset(C.ASSET)
    sword = unreal.load_asset(C.SWORD_ASSET)
    if sheath is None or sword is None:
        return False, {"error": "sheath or sword did not load"}
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(sheath)
    th = comp.get_socket_transform("Holster", unreal.RelativeTransformSpace.RTS_COMPONENT)
    sc = unreal.new_object(unreal.StaticMeshComponent)
    sc.set_static_mesh(sword)
    exp = C.REPORT["holster_expected_ue_cm"]
    out, ok = {}, True
    for name, want in exp.items():
        t = sc.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        p = th.transform_location(t)
        got = [round(p.x, 4), round(p.y, 4), round(p.z, 4)]
        d = max(abs(a - b) for a, b in zip(got, want))
        out[name] = {"engine_cm": got, "blender_cm": want, "max_abs_diff_cm": round(d, 5)}
        ok = ok and d <= 0.01
    e = th.rotation.euler()
    out["holster_rpy"] = [round(e.x, 4), round(e.y, 4), round(e.z, 4)]
    return ok, out


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
            passed["12_exact_bytes"] = report["fbx_sha256"] == report["report_fbx_sha256"]
            h_ok, h = holster_gate()
            passed["20_holster_places_the_sword_as_in_blender"] = h_ok
            report["holster"] = h
            report["gates"] = passed
            report["passed_all"] = all(passed.values())
            for k in ("lod_triangles", "lod_screen_sizes", "sockets", "size_cm", "convex_hulls",
                      "bounds_sphere_radius_cm", "material_slots", "nanite_enabled"):
                report[k] = info.get(k)
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SHU_PASS2_DONE " + str(OUT))


main()
