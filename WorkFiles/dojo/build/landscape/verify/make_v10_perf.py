"""Build v10_game_perf.py from verify_r9/v9_game_perf.py (asserted text patches): landscape views, 4 configs, A/B toggles."""
from pathlib import Path

s = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r9\v9_game_perf.py").read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)


rep(r'WorkFiles\dojo\build\verify_r9\game_perf.json', r'WorkFiles\dojo\build\landscape\verify\game_perf.json')
rep('WARM_S, WARM_PER_S, SETTLE_S, SAMPLE_S, PROF_S = 35.0, 6.0, 9.0, 9.0, 4.0',
    'WARM_S, WARM_PER_S, SETTLE_S, SAMPLE_S, PROF_S = 40.0, 6.0, 9.0, 10.0, 4.0')
rep('VIEWS = ["CAM_PlayerEyeSand", "CAM_Overview", "PAWN"]',
    'VIEWS = ["CAM_PlayerEyeSand", "CAM_Overview", "CAM_LandscapeRef", "PAWN", "CAM_RiverRapids", "CAM_StairPath"]')
rep('CONFIGS = [(1920, 1080, 0), (2560, 1440, 0), (2560, 1440, 100)]',
    'CONFIGS = [(1920, 1080, 0), (2560, 1440, 0), (2560, 1440, 100), (1920, 1080, 100)]')
rep('PLAN = [(v, c) for v in VIEWS for c in CONFIGS]', '''PLAN = [(v, c, None) for v in VIEWS for c in CONFIGS]
# landscape verify: A/B cost of the new content, same session, 1920x1080 configured %: baseline, then each group hidden
for _v in ("CAM_LandscapeRef", "CAM_PlayerEyeSand", "CAM_RiverRapids"):
    for _tg in ("base", "no_foliage", "no_niagara", "no_water"):
        PLAN.append((_v, (1920, 1080, 0), _tg))
TOGGLED = []


def set_toggle(tg):
    """hide one content group at runtime (nothing is saved): foliage = every instanced (H)ISM component (forest, grass,
    bushes, pebbles) + the pine / cypress actors' mesh components; niagara = every NiagaraComponent; water = the water
    body and zone actors."""
    for c, kind in TOGGLED:
        try:
            if kind == "actor":
                c.set_actor_hidden_in_game(False)
            else:
                c.set_visibility(True, True)
        except Exception:  # noqa: BLE001
            pass
    TOGGLED.clear()
    if tg in (None, "base"):
        return 0
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
        cls = a.get_class().get_name()
        if tg == "no_water" and cls in ("WaterBodyRiver", "WaterZone"):
            a.set_actor_hidden_in_game(True)
            TOGGLED.append((a, "actor"))
            n += 1
            continue
        comps = []
        if tg == "no_niagara":
            comps = list(a.get_components_by_class(unreal.NiagaraComponent))
        elif tg == "no_foliage":
            comps = list(a.get_components_by_class(unreal.InstancedStaticMeshComponent))
            lab = a.get_name().lower()
            if any(k in lab for k in ("pine", "cypress", "dkn_")):
                comps += [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c not in comps]
        for c in comps:
            if c.is_visible():
                c.set_visibility(False, True)
                TOGGLED.append((c, "comp"))
                n += 1
    return n''')
rep('''            v, (w, h, sp) = PLAN[ST["i"]]
            ok = view(v, w, h, sp)
            log(f"segment {ST['i']} {v} {w}x{h}@{sp} view_ok={ok}")''', '''            v, (w, h, sp), tg = PLAN[ST["i"]]
            ok = view(v, w, h, sp)
            ST["toggled_n"] = set_toggle(tg)
            log(f"segment {ST['i']} {v} {w}x{h}@{sp} {tg} view_ok={ok} toggled={ST['toggled_n']}")''')
rep('''                v, (w, h, sp) = PLAN[ST["i"]]
                ST["dts"] = []''', '''                v, (w, h, sp), tg = PLAN[ST["i"]]
                ST["dts"] = []''')
rep('''                v, (w, h, sp) = PLAN[ST["i"]]
                seg = {"i": ST["i"], "view": v, "res": [w, h], "screen_pct": sp,''',
    '''                v, (w, h, sp), tg = PLAN[ST["i"]]
                seg = {"i": ST["i"], "view": v, "res": [w, h], "screen_pct": sp, "toggle": tg, "toggled_n": ST.get("toggled_n"),''')
rep('''            if ST["i"] >= len(PLAN):
                REP["env_end"] = env_state()''', '''            if ST["i"] >= len(PLAN):
                set_toggle(None)
                REP["env_end"] = env_state()''')
rep('"""VERIFY r9 (independent verifier;', '"""VERIFY LANDSCAPE ROUND (independent verifier; the verify_r9 script + landscape views + A/B content toggles;')
Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\verify\v10_game_perf.py").write_text(s, encoding="utf-8")
print("ok")
