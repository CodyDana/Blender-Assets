"""One-off patch of the showcase runner / level / verify for the landscape round (idempotent: asserts each hunk once)."""
from pathlib import Path

D = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal")
BS = chr(92)


def patch(name, pairs):
    p = D / name
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s:
            continue
        assert s.count(old) == 1, (name, old[:80])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8", newline="")


patch("run_showcase_unreal.sh", [(
    '''      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/showcase/apply_look_r3.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      grep -q "^ROUND2 " "$OUT/logs/prep.log" && grep -q "^LOOK_R3 " "$OUT/logs/prep.log" || { [ $code -eq 0 ] && code=8; } ;;''',
    '''      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/showcase/apply_look_r3.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      # landscape round (2026-09-30): the town removal / hidden grey-box trees / new cameras (idempotent)
      [ $code -eq 0 ] && { py -3 -B "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/landscape/apply_landscape.py" >> "$OUT/logs/prep.log" 2>&1; code=$?; }
      grep -q "^ROUND2 " "$OUT/logs/prep.log" && grep -q "^LOOK_R3 " "$OUT/logs/prep.log" && grep -q "^LANDSCAPE_PREP " "$OUT/logs/prep.log" || { [ $code -eq 0 ] && code=8; } ;;''')])

patch("dj_sc_level.py", [
    ('''    for n, inst in enumerate(L["instances"]):
        piece = inst["piece"]
        if piece not in meshes:''',
     '''    for n, inst in enumerate(L["instances"]):
        piece = inst["piece"]
        if inst.get("removed"):   # landscape round: the town / outside v1 pieces leave the level (assets stay on disk)
            continue
        if piece not in meshes:'''),
    ('''        if L["collision_classes"][inst["collision_class"]].get("hidden_in_game"):
            a.set_actor_hidden_in_game(True)''',
     '''        if L["collision_classes"][inst["collision_class"]].get("hidden_in_game") or inst.get("hide_landscape"):
            # landscape round: hide_landscape = the grey-box trees, hidden with their trunk collision kept (CS01/CS02)
            a.set_actor_hidden_in_game(True)'''),
    ('''    return {"tolerance_cm": TOL_CM, "n_checked": len(rows), "n_layout": len(L["instances"]),''',
     '''    n_active = sum(1 for i in L["instances"] if not i.get("removed"))   # landscape round: removed = not placed
    return {"tolerance_cm": TOL_CM, "n_checked": len(rows), "n_layout": len(L["instances"]), "n_active": n_active,'''),
    ('''            "failures": fails, "passed": len(rows) == len(L["instances"]) and not fails}''',
     '''            "failures": fails, "passed": len(rows) == n_active and not fails}'''),
])

patch("dj_sc_verify.py", [
    ('''    for n, inst in enumerate(L["instances"]):
        lab = S.label(inst, n)
        a = by_label.get(lab)
        if a is None:
            missing.append(lab)
            continue''',
     '''    removed_present = []
    for n, inst in enumerate(L["instances"]):
        lab = S.label(inst, n)
        a = by_label.get(lab)
        if inst.get("removed"):   # landscape round: must NOT be in the level
            if a is not None:
                removed_present.append(lab)
            continue
        if a is None:
            missing.append(lab)
            continue'''),
    ('''        if (any(got[k] != want[k] for k in got) or hidden != bool(want.get("hidden_in_game", False))''',
     '''        if (any(got[k] != want[k] for k in got)
                or hidden != (bool(want.get("hidden_in_game", False)) or bool(inst.get("hide_landscape")))'''),
    ('''    mesh_actors = [a for a in actors if a.get_class().get_name() == "StaticMeshActor" and a not in dome]''',
     '''    # landscape round: the world build's actors (tag DJ_Landscape) are gated by dj_ls_verify.py, not here
    mesh_actors = [a for a in actors if a.get_class().get_name() == "StaticMeshActor" and a not in dome
                   and unreal.Name("DJ_Landscape") not in list(a.tags)]
    n_active = sum(1 for i in L["instances"] if not i.get("removed"))'''),
    ('''                "n_instances": len(L["instances"]), "bounds_max_err_cm": round(worst, 4),''',
     '''                "n_instances": len(L["instances"]), "n_active_instances": n_active,
                "removed_but_present": removed_present, "bounds_max_err_cm": round(worst, 4),'''),
    ('''                "n_nanite_actors": sum(1 for i in L["instances"] if L["pieces"][i["piece"]]["nanite"]),''',
     '''                "n_nanite_actors": sum(1 for i in L["instances"] if L["pieces"][i["piece"]]["nanite"]
                                       and not i.get("removed")),'''),
    ('''                     and not res["bounds_failures"] and len(mesh_actors) == len(L["instances"]) and not stand_ins''',
     '''                     and not res["bounds_failures"] and len(mesh_actors) == n_active and not stand_ins
                     and not removed_present'''),
    ('''    for a in actors:
        cls = a.get_class().get_name()
        if cls in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog", "VolumetricCloud") or ''' + BS,
     '''    for a in actors:
        cls = a.get_class().get_name()
        if unreal.Name("DJ_Landscape") in list(a.tags) and cls not in ("DirectionalLight", "SkyAtmosphere", "SkyLight",
                                                                         "ExponentialHeightFog", "VolumetricCloud"):
            env["landscape_actors_skipped"] = env.get("landscape_actors_skipped", 0) + 1   # gated by dj_ls_verify.py
            continue
        if cls in ("DirectionalLight", "SkyAtmosphere", "SkyLight", "ExponentialHeightFog", "VolumetricCloud") or ''' + BS),
])
print("PATCHED")
