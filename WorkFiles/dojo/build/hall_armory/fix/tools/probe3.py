"""FIX round probe 3 (read-only -game run, after the rev-2 build): DJ_ThresholdFill strength from the courtyard, and the
interior look as built. usage: py -3 -B probe3.py <out dir>"""
import json, sys
d = sys.argv[1]
outs = [("CAM_Ref2Match", 1920, 1440), ("CAM_DoorwayIn", 1920, 1080), ("CAM_HallVeranda", 1920, 1080)]
shots = []
for tag, mult in (("t1", 1.0), ("t0", 0.0), ("t2", 2.0), ("t4", 4.0), ("t8", 8.0)):
    for k, (c, w, h) in enumerate(outs):
        s = {"name": c, "w": w, "h": h, "out": f"{tag}_{c}"}
        if k == 0:
            s["lamps"] = {"DJ_ThresholdFill": {"mult": mult}}
        shots.append(s)
shots[-3]["lamps"]  # noqa
shots.append({"name": "CAM_Ref2Match", "w": 1920, "h": 1440, "out": "r_CAM_Ref2Match",
              "lamps": {"DJ_ThresholdFill": {"mult": 1.0}}})
for c in ["CAM_AK_C10_Hero", "CAM_AK_C4_ShurikenTray", "CAM_AK_CW_WestAisle", "CAM_AK_C2_Case1", "CAM_AK_CX_FromPlatform",
          "CAM_AK_C3_Case3", "CAM_AK_C5_CloakCase", "CAM_ArmoryEntry", "CAM_ArmoryCeiling"]:
    shots.append({"name": c, "w": 1600, "h": 900, "out": f"n_{c}"})
cfg = {"out_dir": d, "report": d + "/game_capture.json", "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 12,
       "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"],
       "shots": shots}
json.dump(cfg, open(d + "/cfg.json", "w"), indent=1)
print(len(shots), "shots")
