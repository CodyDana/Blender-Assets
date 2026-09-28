from pathlib import Path
H = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/UnrealCheck")


def patch(name, pairs):
    p = H / name
    s = p.read_text(encoding="utf8")
    for a, b in pairs:
        assert s.count(a) == 1, (name, a[:70], s.count(a))
        s = s.replace(a, b)
    p.write_text(s, encoding="utf8")


patch("bhu_common.py", [
    ('''EXPECTED_RADIUS_CM = REPORT["bounds_radius_mm"] / 10.0''',
     '''EXPECTED_RADIUS_CM = REPORT["bounds_radius_mm"] / 10.0
#: final pass: ONE hull round the body (the hanging tails have no collision by design)
EXPECTED_HULLS = len(REPORT["collision"]["hulls"])'''),
    ('''    hulls_ok = (info["convex_hulls"] == 2''', '''    hulls_ok = (info["convex_hulls"] == EXPECTED_HULLS'''),
    ('''        "2_exactly_two_convex_hulls": hulls_ok,''', '''        "2_convex_hull_count_as_shipped": hulls_ok,'''),
])

patch("bhu_pass2_verify.py", [
    ('''    if len(elems) != 2:''', '''    if len(elems) != C.EXPECTED_HULLS:'''),
    ('''        read["mip_probe"] = mip_probe(tex, path)''', '''        read["mip_probe"] = mip_probe(tex, path)
        if suffix == "ORM":
            # final pass: the ORM names its part's N as Composite Texture (normal variance -> roughness
            # per mip, CTM_NormalRoughnessToGreen), set by bhu_tex_composite.py and re-read here
            ct = C.safe(lambda t=tex: t.get_editor_property("composite_texture"))
            read["composite_texture"] = ct.get_path_name() if hasattr(ct, "get_path_name") else str(ct)
            read["composite_texture_mode"] = str(C.safe(lambda t=tex: t.get_editor_property("composite_texture_mode")))
            read["composite_power"] = str(C.safe(lambda t=tex: t.get_editor_property("composite_power")))
            matches["orm_composite_is_its_normal_map_to_green"] = bool(
                str(read["composite_texture"]).startswith(f"{C.TEXTURE_DEST}/{stem}_N")
                and "NORMAL_ROUGHNESS_TO_GREEN" in read["composite_texture_mode"].upper())'''),
])

patch("bhu_roundtrip_compare.py", [
    ('''        tris = np.array([t.vertices[:] for t in me.loop_triangles], np.int64).reshape(-1, 3)
        out[obj.name] = {"co": co, "tris": tris}''',
     '''        tris = np.array([t.vertices[:] for t in me.loop_triangles], np.int64).reshape(-1, 3)
        mats = np.array([t.material_index for t in me.loop_triangles], np.int64)
        slots = [(s.material.name if s.material else "") for s in obj.material_slots]
        out[obj.name] = {"co": co, "tris": tris, "mat": mats, "slots": slots}'''),
    ('''        # two hulls: every LOD0 vertex must lie inside AT LEAST ONE of Unreal's hulls, and every
        # shipped hull's vertices must round-trip onto one of Unreal's
        lod0 = shipped["LOD0"]["co"]''',
     '''        # every LOD0 BODY vertex must lie inside AT LEAST ONE of Unreal's hulls, and every shipped
        # hull's vertices must round-trip onto one of Unreal's.  Final pass: the hanging tails have
        # no collision by design; they are the cloth slot's vertices below the rim bottom (z < 0)
        # or outside the rim tube's centre circle (the build's own rule, blackhat_report collision)
        L0 = shipped["LOD0"]
        cloth = [i for i, n in enumerate(L0["slots"]) if "cloth" in n.lower()]
        cv = np.unique(L0["tris"][np.isin(L0["mat"], cloth)])
        rc_cm = float(REPORT["geometry"]["frame"]["tube_centre_mm"][0]) / 10.0
        co0 = L0["co"]
        hang = np.zeros(len(co0), bool)
        hang[cv] = True
        hang &= (co0[:, 2] < -0.05) | (np.hypot(co0[:, 0], co0[:, 1]) > rc_cm)
        lod0 = co0[~hang]'''),
    ('''                          "lod0_worst_outside_cm": round(float(inside_any.max()), 7),
                          "contains_lod0": bool(inside_any.max() <= 1e-4)}''',
     '''                          "lod0_body_vertices_tested": int(len(lod0)), "hanging_tail_vertices_excluded": int(hang.sum()),
                          "lod0_worst_outside_cm": round(float(inside_any.max()), 7),
                          "contains_lod0_body": bool(inside_any.max() <= 1e-4)}'''),
    ('''OUT = HERE / "roundtrip_compare.json"''', '''OUT = HERE / "roundtrip_compare.json"
REPORT = json.loads((PROJ / "WorkFiles" / "blackhat" / "blackhat_report.json").read_text(encoding="utf-8"))'''),
])

patch("bhu_summary.py", [
    ('''ti = json.loads((H / "props_textures_import.json").read_text()); tv = json.loads((H / "props_textures_verify.json").read_text())''',
     '''ti = json.loads((H / "props_textures_import.json").read_text()); tv = json.loads((H / "props_textures_verify.json").read_text())
tc = json.loads((H / "tex_composite.json").read_text())'''),
    ('''        for n in ("pass1", "tex_import", "tex_verify", "pass2", "pass3")}''',
     '''        for n in ("pass1", "tex_import", "tex_composite", "tex_verify", "pass2", "pass3")}'''),
    ('''g["11_hull_contains_lod0_in_engine_space"] = bool(rt["hull"].get("contains_lod0"))''',
     '''g["11_hull_contains_lod0_body_in_engine_space"] = bool(rt["hull"].get("contains_lod0_body"))
g.pop("11_hull_contains_lod0_in_engine_space", None)
g["19_orm_composite_normal_roughness_set_and_persisted"] = bool(tc.get("passed")) and all(
    v.get("matches", {}).get("orm_composite_is_its_normal_map_to_green") for k, v in (p2.get("textures") or {}).items()
    if k.endswith("_ORM"))'''),
    ('''       "processes": ["pass1 import + sidecar (one save)", "tex_import (props importer)", "tex_verify (fresh)",''',
     '''       "processes": ["pass1 import + sidecar (one save)", "tex_import (props importer)",
                     "tex_composite (ORM composite = N, NormalRoughnessToGreen; fresh)", "tex_verify (fresh)",'''),
    ('''       "notes": ["BlackHat: two hulls, one HEAD socket, two material slots (straw, cloth), 8 maps at 2048",''',
     '''       "notes": ["BlackHat final pass (2026-09-26): ONE hull round the body (hanging tails: no collision by design), one HEAD socket, two material slots (straw, cloth), 8 maps at 2048; ORM composite = N (Toksvig roughness per mip)",
                 "mip count: a -nullrhi commandlet does not build platform data (ListTextures reads 1x1 / 0 mips), so the 12-mip chain is INFERRED from 2048^2 power-of-two sources, TMGS_FROM_TEXTURE_GROUP (World / WorldNormalMap: SimpleAverage), LOD bias 0, max size 0",'''),
    ('''"verified": all(g.values()),''', '''"verified": all(g.values()), "tex_composite": tc,'''),
])

p = H / "run_unreal_checks.sh"
s = p.read_text(encoding="utf8")
a = '''PROPS_TEXTURE_MODE=import PROPS_TEXTURE_OUT="$HERE/props_textures_import.json" run tex_import "$IMPORTER"
'''
b = '''PROPS_TEXTURE_MODE=import PROPS_TEXTURE_OUT="$HERE/props_textures_import.json" run tex_import "$IMPORTER"
run tex_composite "$HERE/bhu_tex_composite.py"
'''
assert s.count(a) == 1
s = s.replace(a, b).replace('''"$HERE"/uv1_overlap.json "$HERE"/verification_summary.json''',
                            '''"$HERE"/uv1_overlap.json "$HERE"/tex_composite.json "$HERE"/verification_summary.json''')
p.write_text(s, encoding="utf8")
print("ok")
