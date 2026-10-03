"""DojoLab-only look of the armory interior in the hall (per level, NEVER synced: SYNC.md 6). Read by dj_armory_sync.py.

Exposure parity (measured, 2026-10-01): both projects use manual exposure without the physical camera, so a pixel is
L x 2^bias. ArmoryLab's PostProcess_Armory bias is -2.68 (its level.json); DojoLab's PostProcess_Dojo bias is +1.20
(look_r3 ENV exposure, the round-9 UDS sunset; showcase level.json). The armory's Unreal candela (lights_design.json
ue_armorylab_night) and its emissive instances therefore read 2^(1.20 + 2.68) = 14.7x brighter in DojoLab; the
parity scale is 2^-3.88 = 0.0679. (The survey's starting value 10.295 used the analytic -6.04 EV, which is not the
exposure the DojoLab PPV runs at; rejected after measuring the PPV.)
"""
DOJOLAB_BIAS_EV = 1.20
ARMORYLAB_BIAS_EV = -2.68
PARITY = 2.0 ** (ARMORYLAB_BIAS_EV - DOJOLAB_BIAS_EV)     # 0.0679

LIGHT_SCALE = PARITY          # x ue_armorylab_night candela (the level_scale for DojoLab in lights_design.json)
ROLE_SCALE = {}               # per role trim on top (relight stage)
EMISSIVE_SCALE = PARITY       # x the armory instance's Emissive Intensity (MI_DJA_* children)
EMISSIVE_ROLE = {}            # per slot trim
SHADOW_OFF_ROLES = {"alcove"} # as ArmoryLab (the alcove spots light an empty rack against its own board)
SHADOW_BUDGET = 14            # ArmoryLab's 12 case lights + headroom; perf pass may lower it
ATTENUATION_CM = 2000.0
BACKER_CD = 6.0               # the shell's 10 window-backer rects (3.5 x 1.45 m, 3200 K), DojoLab units
NO_SHADOW_PIECES = set()
PPV = None                    # an interior post-process volume (None = the level's PPV owns exposure)
# look1 (2026-10-01, measured on CAM_AK_CW_WestAisle / CAM_AK_C10_Hero against the armory's own r20 stills): the
# interior read 2.2x the armory's mean and its darks were lifted (p50 34 vs 4.7): the level PPV's Lumen sky-light
# leaking 0.06 (the landscape fix round's shade fill for the open courtyard) adds a flat ambient everywhere, also in
# the closed interior. A bounded PPV over the interior (envelope + 0.3 m, priority over PostProcess_Dojo) sets ONLY the
# leaking back to 0; exposure stays with the one owner (PostProcess_Dojo), so the courtyard look is unchanged.
PPV = {"centre_hl": (0.0, 10.15, 2.5), "size_m": (12.6, 20.6, 5.2), "priority": 20.0, "blend_radius_cm": 60.0,
       "settings": {"lumen_skylight_leaking": 0.0}}
# look2: the ten window backers read as the brightest, most saturated thing in the room (orange lattices on both long
# walls; the armory's own windows are dark at night). Sunset borrowed light, not a fire: the backer paper's emission
# x 0.4 (a DojoLab child MI on the backer actors only) and the backer rects 6 -> 3 cd.
BACKER_EMISSIVE = 0.4
BACKER_CD = 3.0
# perf pass (2026-10-01, ha_game_perf at 1920x1080 / configured %): with the armory's 20 m attenuation on all 124
# lights the deferred 'Lights' pass cost 9.4 ms in the interior (GPU 19.8 ms, over the 16.7 budget) and 3.1 ms even
# from the courtyard (the 20 m spheres reach the sand). Per-role radii ~3x each light's throw to the surface it lights:
# the inverse-square window (1 - (d/r)^4)^2 then keeps >= 0.95 of the light on its target, so the look holds.
ATTEN_ROLE_CM = {"case": 250.0, "glow": 200.0, "panel": 400.0, "down": 1200.0, "alcove": 600.0, "rack": 600.0,
                 "banner": 700.0, "sill": 600.0, "wash": 700.0, "lantern": 300.0, "window_backer": 800.0}
# ---- FIX round (2026-10-01, shared rev 2; the judge's deltas checked against the armory chat's own r20 stills first)
# - Windows (delta 2, 'outside and inside of the shell disagree'): the armory's long-wall lattice windows read DARK in
#   its own night stills (CX_FromPlatform, CW_WestAisle), and the hall shell has no openings behind them (plaster side
#   walls and the extension's plaster bays, measured in hall_shell_layout.json), so the borrowed-light backers go dark:
#   backer paper x BACKER_EMISSIVE of the facade's shoji paper, the 10 backer rects off (kept, visible = False).
BACKER_EMISSIVE = 0.02
BACKER_CD = 0.0
# - Parked door leaves (delta 5): they stand against the inside of the plaster bays X 17-19 / 25-27, nothing lights them
#   from behind, so their paper is reflective paper, not a lamp: a DojoLab child MI on those six actors only.
PARKED_LEAF_PAPER = {"EmissiveIntensity": 0.0, "BaseMult": 1.0}
# - The shuriken tray's reflect card (delta 9: the hottest point of CAM_DoorwayIn, clipped white): it exists in the
#   armory's own C1 as a dim card; trimmed on top of the parity scale.
EMISSIVE_ROLE = {"M_AK_ReflectCard": 0.3}
# - DJ_ThresholdFill (delta 6, checked against reference 2: every front bay of the hall glows warm; the open centre
#   bays read as a dark slot): a warm wash just inside the open doors onto the entry floor, the mat and the parked
#   leaves. Level-only (like the armory's own Sun_WindowFill), lighting channel 1 (interior only), no shadows, no
#   specular (no rect highlight in the glossy floor). Hall-local metres; Unreal pitch / yaw (yaw -90 = north).
LEVEL_LIGHTS = [{"name": "DJ_ThresholdFill", "type": "rect", "role": "threshold_fill", "loc_m": [0.0, 0.9, 2.3],
                 "pitch_deg": -55.0, "yaw_ue_deg": -90.0, "size_m": [5.6, 1.0], "kelvin": 2700, "cd": 30.0}]
ATTEN_ROLE_CM["threshold_fill"] = 700.0
# - Interior exposure (delta 4; measured, fix/probe/p1 + p2, 7 CAM_AK_* views against the armory's r20 stills, display
#   luma mean / p50 as log2(ours / armory)): as built 0.62 / 0.83 (p10 up to 15 against ~0-1). NOT the fog (r.Fog 0:
#   no change), NOT the GI (indirect_lighting_intensity 0.5 / 0.25: no change), barely the sky light (UDS x0.25: 0.57 /
#   0.71); the armory's film toe 0.4 lifted our darks (p10 5 -> 24): rejected. Exposure -0.6 EV (bias 1.2 -> 0.6): 0.25
#   / 0.17; + local exposure contrast 1.0 / 1.0 (the level's 0.8 highlight / 0.9 shadow compress toward mid-grey):
#   0.14 / -0.24 with p10 0-2.8 (the armory 0-1.4): the deep blacks back. -1.0 EV went too dark (p50 -0.83). Chosen:
#   -0.6 EV (the judge's 0.5-0.7) + local exposure 1.0 / 1.0, plus the armory's own bloom 0.3 (the level's 0.5 widened
#   the halo round the gold panel) and shadow saturation 1.0 (the armory grades at saturation 1.0). Only inside the
#   bounded interior PPV: the courtyard, CAM_DoorwayIn and CAM_Ref2Match keep PostProcess_Dojo (cameras outside it).
INTERIOR_EXPOSURE_OFFSET_EV = -0.6
PPV = {"centre_hl": (0.0, 10.15, 2.5), "size_m": (12.6, 20.6, 5.2), "priority": 20.0, "blend_radius_cm": 60.0,
       "settings": {"lumen_skylight_leaking": 0.0,
                    "auto_exposure_bias": round(DOJOLAB_BIAS_EV + INTERIOR_EXPOSURE_OFFSET_EV, 4),
                    "local_exposure_highlight_contrast_scale": 1.0, "local_exposure_shadow_contrast_scale": 1.0,
                    "bloom_intensity": 0.3, "color_saturation_shadows": (1.0, 1.0, 1.0, 1.0)}}
# - The reflect card: probe p2 at x0.3 still read near-white from CAM_DoorwayIn (clipped share 12.8 -> 7.0 % in its box):
#   x0.1 (it also lit the shuriken bronze in C4 where the armory's read dark)
EMISSIVE_ROLE = {"M_AK_ReflectCard": 0.1}
# - The white card (delta 9) measured (fix/probe/p4, CAM_DoorwayIn, its 90 x 100 px box, cumulative switches): base
#   p95 luma 240 (clipped 5.2 %); reflect card emission 0: 239 (3.6 %); + CaseLight_08 / UnderGlow_08 off: 164 (2.4 %);
#   + sun off: 160. So it is the tray's upright reflect card LIT by its own case light 19 cm above it (the armory's C1
#   shows it pale too). Per level only: CaseLight_08 x 0.5 in DojoLab (the shared design keeps its candela).
LIGHT_TRIM = {"CaseLight_08": 0.5}
# - DJ_ThresholdFill strength (fix/probe/p3, x 0 / 1 / 2 / 4 / 8 on 30 cd, CAM_Ref2Match door box mean 66.6 / 70.8 /
#   76.2 / 82.9 / 90.7, CAM_DoorwayIn 54.4 -> 62.3): x4-x8 reads as a lit room from the courtyard, x8 hot on the
#   threshold boards from the steps: 160 cd.
LEVEL_LIGHTS[0]["cd"] = 160.0
# - Parked leaves, final (fix/caps/final first pass): with their paper unlit they still read as orange lattices from the
#   platform, now LIT by DJ_ThresholdFill (1.3 m from them, in front of its plane) and the entry lanterns. They stand in
#   the doorway band where the light is the courtyard's: lighting channel 0 only (sun / sky / bounce through the open
#   doors), so the paper reads as daylit paper with the lattice dark, as the judge asked; the design lights and the
#   fill (channel 1) no longer touch them.
PARKED_LEAF_CHANNEL1 = False
# - FINISH stage (2026-10-01): one ISM per interior piece where the materials allow it (dj_armory_sync.py checks that
#   every slot's base material carries used_with_instanced_static_meshes; the copied armory masters do not yet, so all
#   pieces stay single actors until the armory chat sets the flag on its masters).
INTERIOR_ISM = True
# ---- voices_paper stage (2026-10-02): the rev-5 window paper behind the upper lattices (SM_AK_Window_Paper_35_W/_E,
# AKI_0618-0627) at the locked sunset. Measured in -game (WorkFiles/dojo/build/ninja_character/voices_paper/paper:
# masks by switching the paper / the neighbouring lit paper off in the same process, 7 views): as synced the paper read
# as a COLD light box: hue 210 deg, saturation 0.04 (the copied ArmoryLab MIs carry its NIGHT moon tint 0.30 / 0.45 / 1.0,
# ak_common NIGHT_EMIT) and 1.24-1.31x the luminance of the transom shoji directly above it (hue 38, sat 0.40-0.55).
# DojoLab is a sunset level, so it takes the armory's own DAY paper colour (tint 1 / 1 / 1 = build_armory_kit's warm
# cream picture as authored) and its DAY west / east balance (emit 0.55 / 0.42 -> the night copies' 0.70 / 0.73 scale is
# undone: E = W x 0.70 / 0.73). Sweep (day tint, x the synced value): 0.15 -> 0.85-0.94x the transom shoji, 0.20 ->
# 0.98-1.06x, 0.25 -> 1.07-1.13x; 0 % clipped at every step. Chosen 0.18 (in family, a touch under the transom strip).
EMISSIVE_ROLE["M_AK_HWinPaperW"] = 0.18
EMISSIVE_ROLE["M_AK_HWinPaperE"] = round(0.18 * 0.70 / 0.73, 6)
EMISSIVE_TINT = {"M_AK_HWinPaperW": (1.0, 1.0, 1.0), "M_AK_HWinPaperE": (1.0, 1.0, 1.0)}
# - Shadows: the armory's rev-5 change line and interior_layout.json (cast_shadow False on AKI_0618-0627) say the paper
#   casts no shadow; DojoLab follows (the perf2 lever test: no measurable cost either way).
NO_SHADOW_PIECES = {"SM_AK_Window_Paper_35_W", "SM_AK_Window_Paper_35_E"}
