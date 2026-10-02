"""Build v10_ue_verify.py from verify_r9/v9_ue_verify.py with the landscape-round adaptations (text patches, each asserted)."""
from pathlib import Path
src = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r9\v9_ue_verify.py").read_text(encoding="utf-8")


def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:80], src.count(old))
    src = src.replace(old, new)


rep('VD = ROOT / "WorkFiles" / "dojo" / "build" / "verify_r9"', 'VD = ROOT / "WorkFiles" / "dojo" / "build" / "landscape" / "verify"')
rep('"""VERIFY r8 (independent verifier), Unreal side.', '"""VERIFY LANDSCAPE ROUND (independent verifier; the verify_r9 script with landscape adaptations), Unreal side.')
# ---- level: removed instances must be absent, hide_landscape ones hidden
rep('''    for n, inst in enumerate(L["instances"]):
        lab = f"{inst['piece']}__{n:04d}"
        want_labels.add(lab)
        if labels.get(lab, 0) == 0:''', '''    removed_present, hide_bad = [], []
    for n, inst in enumerate(L["instances"]):
        lab = f"{inst['piece']}__{n:04d}"
        if inst.get("removed"):
            if labels.get(lab, 0):
                removed_present.append(lab)
            continue
        want_labels.add(lab)
        if inst.get("hide_landscape") and labels.get(lab, 0) and not bool(by_label[lab].get_editor_property("hidden")):
            hide_bad.append(lab)
        if labels.get(lab, 0) == 0:''')
rep('''    per_piece_ok = Counter(i["piece"] for i in L["instances"]) == Counter(''',
    '''    per_piece_ok = Counter(i["piece"] for i in L["instances"] if not i.get("removed")) == Counter(''')
rep('''                "n_instances": len(L["instances"])})''', '''                "n_instances": len(L["instances"]), "n_removed": sum(1 for i in L["instances"] if i.get("removed")),
                "removed_but_present": removed_present, "hide_landscape_not_hidden": hide_bad})''')
rep('''                     and not col_err and not bounds_fail and not extra and per_piece_ok and not visible_eng)''',
    '''                     and not col_err and not bounds_fail and not extra and per_piece_ok and not visible_eng
                     and not removed_present and not hide_bad)''')
# ---- lamps: landscape lights (stair lanterns) separate; street lamps removed with the town
rep('''    lay_lights = {l["name"]: l for l in L["lights"]}
    got = {li["label"]: li for li in lights}''', '''    lay_lights = {l["name"]: l for l in L["lights"]}
    WL = json.loads((ROOT / "WorkFiles/dojo/build/landscape/fix/json/world_layout.json").read_text(encoding="utf-8"))
    land_lights = {l["name"]: l for l in WL["lights"]}
    got_land = {li["label"]: li for li in lights if li["label"] in land_lights}
    lights = [li for li in lights if li["label"] not in land_lights]
    got = {li["label"]: li for li in lights}''')
rep('''    res["passed"] = bool(not bad and not orphan and not miss and not extra and not loc_err and street''',
    '''    land_err = {k: (round(max(abs(got_land[k]["loc_bl_m"][i] - l["loc"][i]) for i in range(3)), 4) if k in got_land else "missing")
                for k, l in land_lights.items()}
    res["landscape_lights"] = {"rows": got_land, "loc_err_m": land_err,
                               "ok": all(isinstance(v, float) and v <= 0.02 for v in land_err.values())
                               and all(v.get("on_mesh") for v in got_land.values())}
    res["orphan_lights"] = orphan = [o for o in orphan if o not in land_lights]
    res["street_lamps_removed_with_town"] = not street
    res["passed"] = bool(not bad and not orphan and not miss and not extra and not loc_err and res["landscape_lights"]["ok"]''')
# ---- group: the terrace B-lines join the 1v1 group
rep('''    want_inst = {f"{i['piece']}__{n:04d}" for n, i in enumerate(L["instances"]) if i["piece"] in want_vis | want_inv}''',
    '''    want_inst = {f"{i['piece']}__{n:04d}" for n, i in enumerate(L["instances"]) if i["piece"] in want_vis | want_inv}
    WL = json.loads((ROOT / "WorkFiles/dojo/build/landscape/fix/json/world_layout.json").read_text(encoding="utf-8"))
    blines = {a["label"] for a in WL["actors"] if a["group"] == "boundary"}
    want_inst |= blines''')
rep('''            if nm in want_vis and (r["hidden_in_game"] or r["pawn"] != "block"):''',
    '''            if lab in blines and not (r["hidden_in_game"] and r["pawn"] == "block" and r["camera"] == "ignore"
                                      and r["visibility"] == "ignore" and not r["cast_shadow"]):
                why.append("B-line blocker setup")
            if nm in want_vis and (r["hidden_in_game"] or r["pawn"] != "block"):''')
rep('''    return {"tag": tag, "n_expected": len(want_inst),''', '''    return {"tag": tag, "n_blines": len(blines), "n_expected": len(want_inst),''')
# ---- landscape gate
rep('''def main():
    t0 = time.time()''', '''CHERRY_WORDS = ("cherry", "sakura", "yoshino", "prunus", "blossom")


def check_landscape(actors):
    """landscape round: cherry slots (count, hidden, no collision, tags), no cherry content anywhere in /Game, the
    water body / zone (Water plugin classes load), landscapes."""
    slots = []
    for a in actors:
        tags = [str(t) for t in a.get_editor_property("tags")]
        if "CherrySlot" in tags or a.get_actor_label().startswith("CherrySlot"):
            smc = a.get_component_by_class(unreal.StaticMeshComponent)
            o, e = a.get_actor_bounds(False)
            slots.append({"label": a.get_actor_label(), "tags": tags, "hidden": bool(a.get_editor_property("hidden")),
                          "collision": enum_name(smc.get_collision_enabled()) if smc else None,
                          "cast_shadow": bool(smc.get_editor_property("cast_shadow")) if smc else None,
                          "loc_bl_m": bl_of(a.get_actor_location()),
                          "size_m": [round(2 * e.x / 100, 2), round(2 * e.y / 100, 2), round(2 * e.z / 100, 2)]})
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    cherry_assets = []
    for ad in ar.get_assets_by_path("/Game", recursive=True):
        nm = (str(ad.package_name) + " " + str(ad.asset_name)).lower()
        if any(w in nm for w in CHERRY_WORDS):
            cherry_assets.append(str(ad.package_name))
    cls = Counter(a.get_class().get_name() for a in actors)
    water = {k: v for k, v in cls.items() if "Water" in k}
    lands = [a for a in actors if isinstance(a, unreal.LandscapeProxy)]
    niag = sum(1 for a in actors if a.get_class().get_name() == "NiagaraActor")
    ok_slots = (len(slots) >= 1 and all(s["hidden"] and "no_collision" in (s["collision"] or "") for s in slots))
    return {"cherry_slots": slots, "n_cherry_slots": len(slots), "cherry_assets_in_game": cherry_assets,
            "water_classes": water, "water_plugin_classes": [n for n in ("WaterBodyRiver", "WaterZone") if hasattr(unreal, n)],
            "landscapes": [a.get_actor_label() for a in lands], "niagara_actors": niag,
            "top_classes": dict(cls.most_common(30)),
            "passed": bool(ok_slots and not cherry_assets and water.get("WaterBodyRiver", 0) >= 1
                           and water.get("WaterZone", 0) >= 1 and len(lands) >= 1)}


def main():
    t0 = time.time()''')
rep('''        rep["16_group_1v1"] = check_group(actors)''', '''        rep["16_group_1v1"] = check_group(actors)
        rep["17_landscape"] = check_landscape(actors)''')
rep('''                                                           "10_greybox", "13_alley_ring", "16_group_1v1", "7_env")}''',
    '''                                                           "10_greybox", "13_alley_ring", "16_group_1v1", "7_env", "17_landscape")}''')
rep('"verifier": "independent r9"', '"verifier": "independent landscape round"')
rep('unreal.log(f"V8_VERIFY_DONE', 'unreal.log(f"V10_VERIFY_DONE')
Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\verify\v10_ue_verify.py").write_text(src, encoding="utf-8")
print("ok", len(src))
