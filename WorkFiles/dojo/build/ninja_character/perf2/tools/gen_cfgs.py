"""perf2: write the run configs (cfg/*.json) for dj_ninja_perf2.py.
main_<pawn>_<n>: the clean profile, views PlayerEyeSand / WestAisle / RiverRapids / PAWN, 1 window each per process
(processes alternate ninja, GASP x3 = 3 windows per view per pawn, the same view order in every session).
lever_<n>: the scratch lever session (ninja pawn): every lever A/B against an adjacent base window at the same view."""
import json
import sys
from pathlib import Path

P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/perf2"
CFGD = Path(P) / "cfg"
DIST = {"CAM_PlayerEyeSand": 450, "CAM_AK_CW_WestAisle": 350, "CAM_RiverRapids": 525}
VIEWS = ["CAM_PlayerEyeSand", "CAM_AK_CW_WestAisle", "CAM_RiverRapids", "PAWN"]


def main_cfg(tag, warm_s):
    steps = [{"view": v, "label": f"{v}", "settle_s": 8, "sample_s": 10} for v in VIEWS]
    return {"out": f"{P}/main/{tag}.json", "shots": f"{P}/main/shots", "warm_s": warm_s,
            "warm_views": ["CAM_PlayerEyeSand"] + VIEWS, "warm_per_s": 6, "dist": DIST, "steps": steps}


def lever_cfg(tag, shots, levers):
    """levers: [(view, [toggles], label)]; each lever window is followed by a base window at the same view"""
    steps, k = [], 0
    for view, tgs, label in levers:
        b = {"view": view, "label": f"base_{label}", "settle_s": 6, "sample_s": 8}
        lv = {"view": view, "label": label, "toggles": tgs, "settle_s": 6, "sample_s": 8}
        if shots:
            b["shot"] = f"{tag}_{k:02d}_base_{label}.png"
            lv["shot"] = f"{tag}_{k:02d}_{label}.png"
        steps += [b, lv]
        k += 1
    return {"out": f"{P}/levers/{tag}.json", "shots": f"{P}/levers/shots", "warm_s": 45,
            "warm_views": ["CAM_PlayerEyeSand"] + VIEWS, "warm_per_s": 6, "dist": DIST, "steps": steps,
            "light_dist_cm": 2500, "light_fade_cm": 500}


if __name__ == "__main__":
    warm = float(sys.argv[1]) if len(sys.argv) > 1 else 45
    for n in (1, 2, 3):
        for pawn in ("ninja", "gasp"):
            (CFGD / f"main_{pawn}_{n}.json").write_text(json.dumps(main_cfg(f"main_{pawn}_{n}", warm), indent=1))
    print("written")


PES, WA, RR = "CAM_PlayerEyeSand", "CAM_AK_CW_WestAisle", "CAM_RiverRapids"
LEVERS = [
    (PES, ["pawn_hidden"], "PES_pawn_hidden"),
    (PES, ["cloth_suspended"], "PES_cloth_off"),
    (PES, ["groom_hidden"], "PES_groom_hidden"),
    (PES, ["groom_lod2"], "PES_groom_lod2"),
    (PES, ["groom_sim_off"], "PES_groom_sim_off"),
    (PES, ["mh_lod3"], "PES_mh_lod3"),
    (PES, ["skin_cache_off"], "PES_skin_cache_off"),
    (PES, ["interior_light_dist2500"], "PES_light_dist25m"),
    (PES, ["interior_shadows_off"], "PES_interior_shadows_off"),
    (PES, ["interior_lights_off"], "PES_interior_lights_off"),
    (PES, ["winpaper_noshadow"], "PES_winpaper_noshadow"),
    (PES, ["winpaper_hidden"], "PES_winpaper_hidden"),
    (PES, ["niagara_rt_cvars_off"], "PES_niagara_rt_off"),
    (PES, ["niagara_hidden_all"], "PES_niagara_hidden"),
    (PES, ["rt_cull3000"], "PES_rt_cull30m"),
    (WA, ["pawn_hidden"], "WA_pawn_hidden"),
    (WA, ["cloth_suspended"], "WA_cloth_off"),
    (WA, ["groom_hidden"], "WA_groom_hidden"),
    (WA, ["interior_light_dist2500"], "WA_light_dist25m"),
    (WA, ["interior_shadows_off"], "WA_interior_shadows_off"),
    (WA, ["winpaper_noshadow"], "WA_winpaper_noshadow"),
    (WA, ["winpaper_hidden"], "WA_winpaper_hidden"),
    (WA, ["niagara_rt_cvars_off"], "WA_niagara_rt_off"),
    (RR, ["pawn_hidden"], "RR_pawn_hidden"),
    (RR, ["interior_light_dist2500"], "RR_light_dist25m"),
    (RR, ["niagara_rt_cvars_off"], "RR_niagara_rt_off"),
    ("PAWN", ["cloth_suspended"], "PAWN_cloth_off"),
    ("PAWN", ["groom_hidden"], "PAWN_groom_hidden"),
    ("PAWN", ["groom_lod2"], "PAWN_groom_lod2"),
    ("PAWN", ["mh_lod3"], "PAWN_mh_lod3"),
]


def casts(tag):
    out = []
    for key, name in (("Four", "Chidori"), ("Two", "Fireball"), ("F", "ShadowClone")):
        for tg, lab in (([], "base"), (["niagara_rt_cvars_off"], "rt_off")):
            if name == "ShadowClone" and lab == "rt_off":
                continue
            out.append({"view": PES, "label": f"cast_{name}_{lab}", "toggles": tg, "cast": key, "settle_s": 3,
                        "cast_delay_s": 1.3 if name != "ShadowClone" else 1.0, "sample_s": 2.5 if name == "Fireball" else 3.0,
                        "post_s": 7.0})
    return out


def write_levers():
    for n, shots in ((1, True), (2, False)):
        c = lever_cfg(f"lever_{n}", shots, LEVERS if n == 1 else list(reversed(LEVERS)))
        c["steps"] += casts(f"lever_{n}") + casts(f"lever_{n}")
        c["steps"].append({"view": PES, "label": "profilegpu_PES", "settle_s": 6, "sample_s": 6, "profilegpu": True,
                           "post_s": 5})
        c["groom_lod"] = 2
        (CFGD / f"lever_{n}.json").write_text(json.dumps(c, indent=1))
    print("levers written", len(LEVERS))
