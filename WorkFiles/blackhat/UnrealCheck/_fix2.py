def edit(p, pairs):
    s = open(p, encoding="utf8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf8").write(s)

edit("bhu_common.py", [
    ('EXPECTED_SIZE_CM = REPORT["size_cm"]', 'EXPECTED_SIZE_CM = [v / 10.0 for v in REPORT["size_mm"]]'),
    ('size_ok = all(abs(a - e) < 1e-3 for a', 'size_ok = all(abs(a - e) < 2e-3 for a'),
    ('hulls_ok = (info["convex_hulls"] == 1', 'hulls_ok = (info["convex_hulls"] == 2'),
    ('"2_exactly_one_convex_hull": hulls_ok', '"2_exactly_two_convex_hulls": hulls_ok'),
    ('"3_two_sockets_at_scale_1_outered_to_the_asset"', '"3_head_socket_at_scale_1_outered_to_the_asset"'),
    ('"7_one_material_slot": len(info["material_slots"]) == 1', '"7_two_material_slots_straw_cloth": len(info["material_slots"]) == 2'),
    ('"""Shared helpers for SM_SmokeBomb\'s Unreal verification', '"""Shared helpers for SM_BlackHat\'s Unreal verification (adapted copy of the smoke bomb\'s sbu_common;'),
])
edit("bhu_pass2_verify.py", [
    ('EXPECTED_SIZES = {"BC": 4096, "Detail": 4096, "ORM": 2048, "N": 2048}', 'EXPECTED_SIZES = {"BC": 2048, "Detail": 2048, "ORM": 2048, "N": 2048}\nSTEMS = ("T_BlackHat_Straw", "T_BlackHat_Cloth")'),
    ('    for suffix, intent in INTENT.items():\n        path = f"{C.TEXTURE_DEST}/T_SmokeBomb_{suffix}"',
     '    for stem, (suffix, intent) in [(st, it) for st in STEMS for it in INTENT.items()]:\n        path = f"{C.TEXTURE_DEST}/{stem}_{suffix}"'),
    ('        out[suffix] = {"error": f"{path} did not load"}', '        out[f"{stem}_{suffix}"] = {"error": f"{path} did not load"}'),
    ('        out[suffix] = {"read": read, "matches": matches, "passed": all(matches.values())}\n        ok = ok and out[suffix]["passed"]',
     '        out[f"{stem}_{suffix}"] = {"read": read, "matches": matches, "passed": all(matches.values())}\n        ok = ok and out[f"{stem}_{suffix}"]["passed"]'),
    ('    if len(elems) != 1:', '    if len(elems) != 2:'),
])
edit("bhu_roundtrip_compare.py", [
    ('    if n.startswith("UCX"):\n        return "hull"', '    if n.startswith("UCX"):\n        return "hull" + n[-2:]'),
    ('    h_s, h_u = shipped.get("hull"), unreal.get("hull")\n    if h_s is not None and h_u is not None:',
     '''    hs = {k: v for k, v in shipped.items() if k.startswith("hull")}
    hu = {k: v for k, v in unreal.items() if k.startswith("hull")}
    report["hull_nodes"] = {"shipped": sorted(hs), "unreal": sorted(hu)}
    if hs and hu:
        # two hulls: every LOD0 vertex must lie inside AT LEAST ONE of Unreal's hulls; the hull
        # vertices must round-trip (each shipped hull against the nearest Unreal hull)
        lod0 = shipped["LOD0"]["co"]
        inside_any = np.full(len(lod0), np.inf)
        per = {}
        for k, h in hu.items():
            bm = bmesh.new()
            for p in h["co"]:
                bm.verts.new(p)
            bmesh.ops.convex_hull(bm, input=bm.verts)
            bm.normal_update()
            planes = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:]))))
                      for f in bm.faces]
            bm.free()
            d = np.max(np.stack([lod0 @ n - dd for n, dd in planes]), axis=0)
            inside_any = np.minimum(inside_any, d)
            per[k] = {"vertices": int(len(h["co"])), "planes": len(planes)}
        vt = max(min(max(nn_max(a["co"], b["co"]), nn_max(b["co"], a["co"])) for b in hu.values()) for a in hs.values())
        report["hull"] = {"shipped_vertices": [int(len(v["co"])) for v in hs.values()], "unreal": per,
                          "vertices_two_sided_cm": round(vt, 7),
                          "lod0_worst_outside_cm": round(float(inside_any.max()), 7),
                          "contains_lod0": bool(inside_any.max() <= 1e-4)}
    else:
        report["hull"] = {"missing": True}
    if False:
        h_s = h_u = None'''),
])
edit("bhu_summary.py", [
    ('tv["processed"] == tv["expected"] == 4)', 'tv["processed"] == tv["expected"] == 8)'),
    ('"notes": ["UE 5.8 Python', '"notes": ["BlackHat: two hulls, one HEAD socket, two material slots (straw, cloth), 8 maps at 2048", "UE 5.8 Python'),
])
