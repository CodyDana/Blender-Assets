"""FIX round probe config (read-only -game run): interior exposure / fog / grade / backer / parked-leaf variants on the
armory chat's key cameras. usage: py -3 -B probe.py <out dir>  -> cfg.json"""
import json, sys
d = sys.argv[1]
cams = ["CAM_AK_C10_Hero", "CAM_AK_C4_ShurikenTray", "CAM_AK_CW_WestAisle", "CAM_AK_C2_Case1", "CAM_AK_CX_FromPlatform",
        "CAM_AK_C3_Case3"]
LOOKS = {"M_DJ_ShojiPaper@SM_DKH_DoorLeaf_Parked": {"s": {"EmissiveIntensity": 0.0, "BaseMult": 1.0}},
         "MI_DJA_AK_ReflectCard": {"s_mul": {"Emissive Intensity": 0.3}},
         "MI_DJA_BackerPaper": {"s": {"EmissiveIntensity": 0.0}}}
sets = [("a", {}), ("b", {"cmds": ["r.Fog 0", "r.VolumetricFog 0"]}),
        ("c", {"cmds": ["r.Fog 1", "r.VolumetricFog 1"], "pp": {"bloom_intensity": 0.3, "film_toe": 0.4}}),
        ("d", {"mat": LOOKS, "lamps": {"BackerLight": {"mult": 0.0}}}),
        ("e", {"pp": {"auto_exposure_bias": 0.6}}),
        ("f", {"pp": {"auto_exposure_bias": 0.2}})]
shots = []
for tag, first in sets:
    for k, c in enumerate(cams):
        s = {"name": c, "w": 1600, "h": 900, "out": f"{tag}_{c}"}
        if k == 0:
            s.update(first)
        shots.append(s)
cfg = {"out_dir": d, "report": d + "/game_capture.json", "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 12,
       "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"],
       "shots": shots}
json.dump(cfg, open(d + "/cfg.json", "w"), indent=1)
print(len(shots), "shots")
