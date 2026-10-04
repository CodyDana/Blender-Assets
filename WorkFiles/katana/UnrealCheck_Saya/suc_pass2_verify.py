"""Pass 2: a SECOND fresh process re-reads the SAVED asset and gates it (adapted from the black hat's pass 2).

Gates 1-8 are in sfu_common.gates; this adds
    9   every map's flags persisted: Steel BC/ORM/N (4096), Wrap BC/ORM/N (2048) + Detail (1024), mips from the
        texture group, N flip-green OFF (DirectX on disk), ORM composite = its N (normal -> roughness)
    10  lightmap UV generation configured on every LOD
    12  the bytes verified are the bytes the build reported (SHA-256)
(the hull-contains-LOD0 gate is carried by the Unreal FBX round trip: UE 5.8 Python cannot read hull points)
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealCheck_Saya")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import suc_common as C                                          # noqa: E402

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
MAPS = {("T_Katana_Saya", k): 2048 for k in ("BC", "ORM", "N")}
KATANA_SIDECAR = C.PROJ / "Exports" / "Katana" / "SM_Katana.sockets.json"


def holster_gate(info):
    """F13: the katana attached at the saya's Holster (zero relative transform): each katana socket composed through
    the IN-ENGINE Holster transform lands where the Blender fit puts it (saya frame = sword frame - 13.83 cm in Z)."""
    hol = next((s for s in info["sockets"] if s["name"] == "Holster"), None)
    if hol is None:
        return False, {"error": "no Holster socket in engine"}
    kat = json.loads(KATANA_SIDECAR.read_text(encoding="utf-8"))["sockets"]
    rot_ok = all(abs(v) < 1e-3 for v in hol["rpy"])
    out, worst = {}, 0.0
    for s in kat:
        comp = [h + k for h, k in zip(hol["location_cm"], s["location_cm"])]
        exp = [s["location_cm"][0], s["location_cm"][1], s["location_cm"][2] - 13.83]
        err = max(abs(a - b) for a, b in zip(comp, exp))
        worst = max(worst, err)
        out[s["socket"]] = {"composed_cm": [round(v, 4) for v in comp], "expected_cm": exp, "err_cm": round(err, 6)}
    return bool(rot_ok and worst <= 0.001), {"holster_in_engine": hol, "katana_sockets_composed": out,
                                             "worst_err_cm": worst}


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
            m["orm_composite_is_its_normal_map"] = (read["composite_texture"].startswith(f"{C.TEXTURE_DEST}/{stem}_N")
                                                   and "NORMAL_ROUGHNESS_TO_GREEN" in read["composite_texture_mode"].upper())
        out[f"{stem}_{suffix}"] = {"read": read, "matches": m, "passed": all(m.values())}
        ok = ok and out[f"{stem}_{suffix}"]["passed"]
    return ok, out


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR),
              "report_fbx_sha256": C.REPORT["sha256"]["fbx"]}
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
            ok13, d13 = holster_gate(info)
            passed["13_holster_composition_F13"] = ok13
            report["holster_composition"] = d13
            report["gates"] = passed
            report["passed_all"] = all(passed.values())
            for k in ("lod_triangles", "lod_screen_sizes", "sockets", "size_cm", "convex_hulls",
                      "bounds_sphere_radius_cm", "material_slots", "nanite_enabled"):
                report[k] = info.get(k)
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SUC_PASS2_DONE " + str(OUT))


main()
