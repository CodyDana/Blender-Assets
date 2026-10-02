"""FIX round probe 2 (read-only -game run): the interior PPV (PostProcess_ArmoryHall) variants: indirect lighting
intensity (Lumen GI incl. the sky through the doors), exposure offset, local exposure; with the planned rev-2 look
(backers off, parked-leaf paper, reflect card trim) applied at runtime. usage: py -3 -B probe2.py <out dir>"""
import json, sys
d = sys.argv[1]
cams = ["CAM_AK_C10_Hero", "CAM_AK_C4_ShurikenTray", "CAM_AK_CW_WestAisle", "CAM_AK_C2_Case1", "CAM_AK_CX_FromPlatform",
        "CAM_AK_C3_Case3", "CAM_AK_C5_CloakCase"]
LOOKS = {"M_DJ_ShojiPaper@SM_DKH_DoorLeaf_Parked": {"s": {"EmissiveIntensity": 0.0, "BaseMult": 1.0}},
         "MI_DJA_AK_ReflectCard": {"s_mul": {"Emissive Intensity": 0.3}},
         "MI_DJA_BackerPaper": {"s": {"EmissiveIntensity": 0.0}}}
P = "PostProcess_ArmoryHall"
sets = [("g", {"mat": LOOKS, "lamps": {"BackerLight": {"mult": 0.0}}}),
        ("h", {"pp": {"__label": P, "indirect_lighting_intensity": 0.5}}),
        ("i", {"pp": {"__label": P, "indirect_lighting_intensity": 0.5, "auto_exposure_bias": 0.6}}),
        ("j", {"pp": {"__label": P, "indirect_lighting_intensity": 0.25, "auto_exposure_bias": 0.6}}),
        ("k", {"pp": {"__label": P, "indirect_lighting_intensity": 0.5, "auto_exposure_bias": 0.6,
                      "local_exposure_shadow_contrast_scale": 1.0, "local_exposure_highlight_contrast_scale": 1.0}}),
        ("l", {"pp": {"__label": P, "indirect_lighting_intensity": 0.25, "auto_exposure_bias": 0.2,
                      "local_exposure_shadow_contrast_scale": 1.0, "local_exposure_highlight_contrast_scale": 1.0}}),
        ("m", {"pp": {"__label": P, "indirect_lighting_intensity": 1.0, "auto_exposure_bias": 1.2,
                      "local_exposure_shadow_contrast_scale": 0.9, "local_exposure_highlight_contrast_scale": 0.8},
               "uds": {"Sky Light Intensity": 0.7}})]
shots = []
for tag, first in sets:
    for k, c in enumerate(cams):
        s = {"name": c, "w": 1600, "h": 900, "out": f"{tag}_{c}"}
        if k == 0:
            s.update(first)
        shots.append(s)
shots.insert(len(cams), {"name": "CAM_DoorwayIn", "w": 1920, "h": 1080, "out": "g_CAM_DoorwayIn"})
cfg = {"out_dir": d, "report": d + "/game_capture.json", "warm_s": 75, "warm_per_cam_s": 6, "settle_s": 12,
       "shot_timeout_s": 120, "hide_pawn": True, "warm_pass": True,
       "cvars": ["scalability 3", "r.ScreenPercentage 100", "r.HighResScreenshotDelay 8", "t.MaxFPS 60"],
       "shots": shots}
json.dump(cfg, open(d + "/cfg.json", "w"), indent=1)
print(len(shots), "shots")
