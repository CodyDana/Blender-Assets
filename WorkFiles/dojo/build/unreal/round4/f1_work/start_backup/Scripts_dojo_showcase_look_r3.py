"""Showcase ROUND 3 (2026-09-28): the Unreal look pass, in one place (plain Python, no bpy / unreal imports).

Used by compose_showcase.py (Blender) and by apply_look_r3.py (patches an existing layout_showcase.json in place, so a
look iteration needs no Blender re-compose). Holds:
  LOOK            per material slot: extra instance scalars / vectors on top of the library recipe. The masters'
                  round-3 parameters (dj_sc_materials.py): Saturation (lerp luminance -> colour, after the wear maths),
                  ValueMult, TopBleach (+ TopBleachColour: sun-bleached upward faces, world normal Z), RoughMult;
                  ground masters: Saturation, ValueMult, NormalFade*; emissive: EmissiveTint.
                  Every value was set by measuring the DojoLab captures (WorkFiles/dojo/build/unreal/round3/).
  CLOSEUPS        the round-3 judge close-up cameras (Blender frame, metres)
  RETIRED_MESHES  meshes a round retired: the level step deletes them from DojoLab once no actor uses them
  check_no_invented_lamps  the user's 2026-09-28 decision: no street lamps inside the courtyard, no short lanterns
"""
import copy

# ---- look values (instance parameters). Filled from the r3 capture measurements; see the ROUND 3 notes.
# Why ValueMult on the dark sets: the colour probe's unlit grey cards show the filmic tonemapper's toe (radiance x4 ->
# sRGB 10 -> 55): dark albedos in shade sit in the toe, which crushes G and B harder than R, so a (74, 62, 54) timber
# under a near-neutral light (veranda grey card R/B 1.3) came out (26, 9, 4) s 0.85. Lifting the dark sets out of the
# toe and pulling their saturation is the material-side fix (probe3 V1 / V2, round3/probe3).
_TIMBER = {"scalars": {"ValueMult": 1.8, "Saturation": 0.6}, "vectors": {"Tint": [0.82, 1.0, 0.96]}}
_GRANITE_MEAN = (0.171, 0.159, 0.145)          # T_DJ_Granite_BC median, linear


def _granite(tint, flat=0.7, sat=0.55, nstr=0.55, ao=0.3):
    # AOStrength: the granite ORM's cavity AO (5th percentile 122 / 255) speckles every shaded face (dalmatian spots)
    return {"scalars": {"FlattenToMean": flat, "Saturation": sat, "NormalStrength": nstr, "AOStrength": ao},
            "vectors": {"Tint": list(tint), "MeanColour": [round(a * b, 5) for a, b in zip(_GRANITE_MEAN, tint)]}}


LOOK = {
    "M_DJ_TimberDark": _TIMBER, "M_DJ_TimberDarkEnd": _TIMBER, "M_DJ_TimberAged": _TIMBER,
    "M_DJ_TimberAgedEnd": _TIMBER,
    "M_DJ_RoofTile": {"scalars": {"ValueMult": 2.3, "Saturation": 0.3, "RoughMult": 1.25}, "vectors": {"Tint": [0.96, 1.0, 1.03]}},
    "M_DJ_PlasterCream": {"scalars": {"ValueMult": 1.35, "Saturation": 0.78}, "vectors": {"Tint": [0.95, 1.0, 0.97]}},
    "M_DK_FootingStone": {"scalars": {"ValueMult": 2.6, "Saturation": 0.55, "FlattenToMean": 0.5,
                                     "NormalStrength": 0.7, "AOStrength": 0.45}, "vectors": {"Tint": [0.52, 0.55, 0.57]}},
    "M_DJ_Granite": _granite((1.0, 1.04, 0.92)),
    "M_DJ_Granite_Tri": _granite((1.0, 1.04, 0.92)),
    "M_DJ_GraniteRubble": {"scalars": {"AOStrength": 0.45, "NormalStrength": 0.7}},
    "M_DKG_Granite": _granite((1.52, 1.44, 1.10), flat=0.5, sat=1.0, nstr=0.7),
    "M_DKG_Gravel": {"vectors": {"Tint": [1.10, 1.08, 0.82]}},
    "M_DKG_GravelCoarse": {"vectors": {"Tint": [1.10, 1.08, 0.82]}},
    "M_DKG_SandRaked": {"scalars": {"ValueMult": 0.9}, "vectors": {"Tint": [1.0, 1.0, 0.95]}},
    "M_DKG_SandEdge": {"scalars": {"ValueMult": 0.9}, "vectors": {"Tint": [1.0, 1.0, 0.95]}},
    "M_DJ_GlassAmber": {"scalars": {"EmissiveIntensity": 120.0, "Saturation": 0.85}},
    "M_DKP_Taiko_Lacquer": {"scalars": {"ValueMult": 1.4, "Saturation": 0.45}, "vectors": {"Tint": [0.9, 1.0, 1.0]}},
}

CLOSEUPS = [   # name, loc, look_at, hfov, (w, h), note
    ("CU_SandEye", (15.2, 6.2, 1.65), (17.6, 11.5, 0.0), 58.0, (1920, 1080),
     "round 3 close-up: the raked sand at player eye (rake lines, grain, moire check)"),
    ("CU_PathStepBand", (22.9, 15.2, 1.7), (22.0, 21.6, 0.35), 58.0, (1920, 1080),
     "round 3 close-up: the paver path running into the granite step band and central stair"),
    ("CU_WallFooting", (31.6, 3.1, 1.25), (29.0, 0.0, 1.0), 56.0, (1920, 1080),
     "round 3 close-up: the south wall's courtyard face east of the gate: pillow-rubble footing, dressed course, "
     "plaster, cap tiles"),
    ("CU_GateFront", (22.0, -7.6, 1.7), (22.0, -1.0, 2.5), 62.0, (1920, 1080),
     "round 3 close-up: the gate front from the street (lamps, plinths, sill step, leaves)"),
    ("CU_HallUpperRoof", (12.6, 17.0, 9.2), (17.6, 25.0, 7.2), 60.0, (1920, 1080),
     "round 3 close-up: the hall's upper roof, the raised centre plane, diagonal ridges, ridge and ridge ends"),
    ("CU_Lantern", (17.4, 17.35, 1.55), (19.0, 19.75, 1.05), 44.0, (1920, 1080),   # f1: the lantern moved to Y 19.75
     "round 3 close-up: the west tall stone lantern in front of the hall"),
    ("CU_Taiko", (38.0, 4.3, 2.3), (41.0, 3.0, 1.9), 58.0, (1920, 1080),
     "round 3 close-up: the taiko on its stand (sticks, iron straps, lacquer)"),
    ("CU_Training", (9.6, 11.2, 1.5), (5.94, 9.57, 0.9), 70.0, (1920, 1080),
     "round 3 close-up: the west training yard: makiwara, weapon rack, wooden dummy"),
]

RETIRED_MESHES = {   # piece -> Unreal package path (round 3: the ground track's paver courses replace the path slabs)
    n: f"/Game/DojoKit/Ground/Meshes/{n}" for n in (
        "SM_DKG_PathSlab_100x60_A", "SM_DKG_PathSlab_100x60_B", "SM_DKG_PathSlab_100x80_A", "SM_DKG_PathSlab_100x80_B",
        "SM_DKG_PathSlab_100x100_A", "SM_DKG_PathSlab_100x100_B", "SM_DKG_PathSlab_100x120_A",
        "SM_DKG_PathSlab_100x120_B")}

# round 3: mesh distance-field build fixes (piece -> (resolution scale, two-sided)). The grey-box pavilion roof is a 0.2 m
# slab: at the default DF resolution its underside's Lumen traces start inside the field and the ceiling rendered pure
# black (2, 1, 0) in CAM_Drum (verifier r2).
DF_FIX = {"SM_DGB_Pavilion_Roof": (6.0, True)}

WALL_INNER_Y = 0.0   # the south wall's courtyard face (the wall runs Y -1.0 .. 0.0; the street is Y < -1.0)


# round 3: the grey-box pavilion roof (a 0.2 m slab, stand-in until kit 6) rendered its ceiling near black in CAM_Drum:
# M_DGB_RoofHall (#55585C, lin 0.09) in the roof's shade sits in the tonemapper's toe. The instance gets a lighter
# weathered-board flat colour on the actor (the shared grey-box MI and mesh stay as they are).
EXTRA_MATERIALS = {
    "M_DJS_PavilionRoof_GB": {"master": "M_DJ_Flat_Master", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
                              "textures": {}, "scalars": {"Roughness": 0.85, "Metallic": 0.0, "Specular": 0.5},
                              "vectors": {"Base Colour": [0.26, 0.25, 0.25]}, "switches": {},
                              "note": "round 3: actor override on the grey-box pavilion roof (ceiling was black)"}}
ACTOR_MATERIAL_OVERRIDES = {"SM_DGB_Pavilion_Roof": {0: "M_DJS_PavilionRoof_GB"}}


# round 3: lamp point lights by piece. The gate's roof underside is lit by nothing but the four bracket lamps (colour
# probe6: skylight x2 moved it 8 -> 11, the lamps x4 -> (57, 9, 0)); at 2400 K their light sits in the tonemapper's
# toe and rendered the ceiling pure red (verifier r2: (33, 0, 0)). 3000 K keeps the lamp warm and the posts amber-brown;
# x2 (tried) warmed the wall cap to R/B 1.54 and left the ceiling red (21, 3, 0), so the power stays.
LAMP_TUNE = {"SM_DK_Gate_Lamp": {"kelvin": 3000, "candela_mult": 1.0}}


def apply_lights(lights):
    """Apply LAMP_TUNE to layout lights in place (idempotent: the composed values are kept in 'base')."""
    done = {}
    for li in lights:
        base = li.setdefault("base", {"kelvin": li["kelvin"], "candela": li["candela"]})
        li["kelvin"], li["candela"] = base["kelvin"], base["candela"]
        for piece, t in LAMP_TUNE.items():
            if li["name"].startswith("Light_" + piece.replace("SM_", "") + "__"):
                li["kelvin"] = t.get("kelvin", li["kelvin"])
                li["candela"] = round(base["candela"] * t.get("candela_mult", 1.0), 2)
                done[li["name"]] = {"kelvin": li["kelvin"], "candela": li["candela"], "base": base}
    return done


def apply_materials(recipes):
    """Merge LOOK into the recipes in place; returns {slot: what was applied}. Idempotent and re-runnable on an
    already patched layout: the recipe's own values are kept in 'look_r3_base' and restored before every merge."""
    for r in recipes.values():   # undo a previous merge
        base = r.pop("look_r3_base", None)
        r.pop("look_r3", None)
        for sec, kv in (base or {}).items():
            for k, v in kv.items():
                if v is None:
                    r.get(sec, {}).pop(k, None)
                else:
                    r.setdefault(sec, {})[k] = v
    for k, v in EXTRA_MATERIALS.items():
        recipes[k] = copy.deepcopy(v)
    done = {}
    for slot, extra in LOOK.items():
        r = recipes.get(slot)
        if r is None:
            continue
        base = {}
        for sec in ("scalars", "vectors", "switches"):
            for k, v in extra.get(sec, {}).items():
                base.setdefault(sec, {})[k] = copy.deepcopy(r.get(sec, {}).get(k))
                r.setdefault(sec, {})[k] = copy.deepcopy(v)
        r["look_r3_base"] = base
        r["look_r3"] = copy.deepcopy(extra)
        done[slot] = extra
    return done


def check_no_invented_lamps(instances):
    """Raise if a street lamp stands inside the wall or a short lantern is placed anywhere (user, 2026-09-28)."""
    bad, street = [], []
    for i in instances:
        p = i["piece"]
        if p == "SM_DKP_Stone_LanternShort":
            bad.append(f"short lantern at {i['loc']}")
        if p.startswith("SM_DKP_Modern_StreetLamp"):
            street.append([round(v, 3) for v in i["loc"]])
            if i["loc"][1] > -1.0:
                bad.append(f"{p} inside the courtyard at {i['loc']}")
    if bad:
        raise RuntimeError("invented lamps placed (user 2026-09-28: drop them): " + "; ".join(bad))
    return {"short_lanterns": 0, "street_lamps_outside": street}


# ================================================================================================ round 3 FIX f1
# 2026-09-28, the two Unreal judges (whole 6/10, detail 6.5/10). Lighting + sky were the whole judge's first blocker:
# a flat mauve-grey gradient sky, no clouds, against reference 2's violet zenith, orange-lit cloud banks and warm raking
# sun. ENV is read by dj_sc_common (sky factor, sky light), dj_sc_level (clouds, grain, sun) and dj_sc_verify (gate 6);
# apply_sun() patches layout_showcase.json's sun in place (prep), keeping the composed sun in 'base'.
ENV = {
    "sun_elev_deg": 13.0, "sun_azimuth_deg_from_x": 160.0, "sun_kelvin": 5500, "sun_lux": 420.0,
    "sky_factor": (2.6, 1.8, 1.6),
    "skylight_intensity": 6.0,
    "clouds": None,                 # {"bottom_km", "height_km", "material" (asset path or None = engine default)}
    "film_grain_intensity": 0.0,
}
NO_SHADOW_PIECES = ()   # grey-box stand-ins whose shadows skew every lighting read (the tree canopies)


def apply_sun(sun):
    """ENV's sun onto the layout sun in place (idempotent; the composed values stay in 'base')."""
    import math
    base = sun.setdefault("base", {k: sun[k] for k in ("elev_deg", "azimuth_deg_from_x", "kelvin", "lux", "travel_dir")})
    e, a = math.radians(ENV["sun_elev_deg"]), math.radians(ENV["sun_azimuth_deg_from_x"])
    sun["elev_deg"], sun["azimuth_deg_from_x"] = ENV["sun_elev_deg"], ENV["sun_azimuth_deg_from_x"]
    sun["kelvin"], sun["lux"] = ENV["sun_kelvin"], ENV["sun_lux"]
    sun["travel_dir"] = [round(-math.cos(e) * math.cos(a), 5), round(-math.cos(e) * math.sin(a), 5),
                         round(-math.sin(e), 5)]
    return {"base": base, "now": {k: sun[k] for k in ("elev_deg", "azimuth_deg_from_x", "kelvin", "lux", "travel_dir")}}


# ---- f1 material look (instance values; the judges' colour deltas). Measured on the f1 captures, see BUILD_NOTES.
_TILE_MEAN = (0.0524, 0.0569, 0.0693)          # T_DJ_RoofTile_BC linear mean
_TIMBER_DARK_TEX = {"BC": "T_DJ_TimberDark_BC", "ORM": "T_DJ_TimberDark_ORM", "N": "T_DJ_TimberDark_N",
                    "WearMask": "T_DJ_WearMask_M"}
_TIMBER_DARK_END_TEX = {"BC": "T_DJ_TimberDarkEnd_BC", "ORM": "T_DJ_TimberDarkEnd_ORM", "N": "T_DJ_TimberDarkEnd_N",
                        "WearMask": "T_DJ_WearMask_M"}


def _tile(tint=(0.92, 1.0, 1.04), flat=0.55, vm=2.3, sat=0.3, rough=1.25):
    # f1: one tile look on every roof (gate, wall cap, hall) at a neutral slate; FlattenToMean kills the albedo fleck
    # speckle (judge: 'white fleck noise that reads as galvanised metal')
    return {"scalars": {"ValueMult": vm, "Saturation": sat, "RoughMult": rough, "FlattenToMean": flat},
            "vectors": {"Tint": list(tint), "MeanColour": [round(a * b, 5) for a, b in zip(_TILE_MEAN, tint)]}}


def _timber_variant(tex, tile, vm, sat, tint, note):
    return {"master": "M_DJ_Lib_Opaque", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
            "textures": dict(tex), "scalars": {"RoughMult": 1.0, "NormalStrength": 1.0, "ValueMult": vm, "Saturation": sat},
            "vectors": {"Tint": list(tint), "TileM": [tile, tile, 0.0, 0.0]}, "switches": {"UseWear": True}, "note": note}


LOOK.update({
    "M_DJ_RoofTile": _tile(),
    "M_DJ_Iron": {"scalars": {"Saturation": 0.4}},                          # dull straps / hardware, not copper bands
    "M_DJ_GlassAmber": {"scalars": {"EmissiveIntensity": 75.0, "Saturation": 0.6}},   # cream-amber paper, cores only
    "M_DKG_SandRaked": {"scalars": {"ValueMult": 0.95, "Saturation": 0.72, "NormalFarStrength": 0.6},
                        "vectors": {"Tint": [1.0, 1.0, 0.97]}},
    "M_DKG_SandEdge": {"scalars": {"ValueMult": 0.95, "Saturation": 0.72, "NormalFarStrength": 0.6},
                       "vectors": {"Tint": [1.0, 1.0, 0.97]}},
    "M_DKG_Gravel": {"scalars": {"Saturation": 0.55, "ValueMult": 1.05}, "vectors": {"Tint": [1.0, 1.0, 0.92]}},
    "M_DKG_GravelCoarse": {"scalars": {"Saturation": 0.55, "ValueMult": 1.5}, "vectors": {"Tint": [1.0, 1.0, 0.92]}},
    "M_DKG_EdgeTimber": {"scalars": {"ValueMult": 0.62, "Saturation": 0.5}},
    "M_DKP_Taiko_Lacquer": {"scalars": {"ValueMult": 1.4, "Saturation": 0.6, "FlattenToMean": 0.6},
                            "vectors": {"Tint": [1.0, 1.0, 1.0], "MeanColour": [0.06, 0.013, 0.013]}},
    "M_DKP_Train_RopeFuzz": {"scalars": {"Saturation": 0.5}},
    "M_DKP_Stone_Moss": {"scalars": {"Saturation": 0.6, "ValueMult": 1.3}, "vectors": {"Tint": [0.8, 1.0, 0.9]}},
})
EXTRA_MATERIALS.update({
    "M_DJS_TimberStand": _timber_variant(_TIMBER_DARK_TEX, 4.0, 1.2, 0.55, (0.8, 0.95, 1.0),
                                         "f1: the taiko stand, dark aged brown (the sheet), not the lifted timber"),
    "M_DJS_TimberStandEnd": _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 1.2, 0.55, (0.8, 0.95, 1.0), "f1: stand end grain"),
    "M_DJS_TimberMid": _timber_variant(_TIMBER_DARK_TEX, 4.0, 2.6, 0.6, (0.82, 1.0, 0.96),
                                       "f1: training props, mid warm brown with visible grain (judge: near-black)"),
    "M_DJS_TimberMidEnd": _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 2.6, 0.6, (0.82, 1.0, 0.96), "f1: end grain"),
})
_TRAIN = {0: "M_DJS_TimberMid", 1: "M_DJS_TimberMidEnd"}
ACTOR_MATERIAL_OVERRIDES.update({
    "SM_DKP_Taiko_Stand": {0: "M_DJS_TimberStand", 1: "M_DJS_TimberStandEnd"},
    "SM_DKP_Taiko_Stick": {0: "M_DK_TimberPale"},                      # plain light wood sticks (the sheet)
    "SM_DGB_Ground_Outside": {0: "M_DKG_Gravel"},                     # f1: gravel street, not a flat green plane
    **{p: dict(_TRAIN) for p in ("SM_DKP_Train_WeaponRack", "SM_DKP_Train_WoodenDummy", "SM_DKP_Train_LongArmDummy",
                                 "SM_DKP_Train_StrikingPost", "SM_DKP_Train_Makiwara", "SM_DKP_Train_Bench",
                                 "SM_DKP_Train_Stool")},
})
ENV.update({
    "sun_elev_deg": 9.0,
    "sky_factor": (2.0, 1.6, 2.0),
    "clouds": {"layer_bottom_altitude": 3.0, "layer_height": 3.0,
               "material_scalars": {"Cloud_GlobalCoverage": 0.1}},
    "grade_extra": {"film_grain_intensity": 0.15},
})
NO_SHADOW_PIECES = ("SM_DGB_Tree",)
# f1 L2 (L1 measured: 9 deg sun left the courtyard in the walls' shade and the sky violet (108, 110, 148) against
# reference 2's warm pink-grey top (175, 157, 160) and peach horizon (221, 162, 134); sand s 0.16 vs the ref's 0.29)
ENV.update({"sun_elev_deg": 12.0, "sun_kelvin": 5000, "sky_factor": (3.4, 2.6, 2.5), "skylight_intensity": 4.5,
            "clouds": {"layer_bottom_altitude": 2.0, "layer_height": 3.0,
                       "material_scalars": {"Cloud_GlobalCoverage": 0.35}}})
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.94, 1.0, 1.0))
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.88, "Saturation": 0.85, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.98, 0.95]}}
ENV["clouds"] = {"layer_bottom_altitude": 1.5, "layer_height": 3.0,
                 "material_scalars": {"Cloud_GlobalCoverage": 0.9, "Cloud_GlobalDensity": 0.03}}   # L3 probe
ENV["capture_cvars"] = ("r.VolumetricRenderTarget 0",)
ENV["capture_show_flags"] = ("Cloud",)
# L4: UE 5.8's VolumetricCloud does not show in the SceneCapture2D stills (L3 / L3b: coverage 0.9, the Cloud show flag,
# r.VolumetricRenderTarget 0: no cloud), so the cloud layer is our own painted dome (make_sky_clouds.py + sky_dome())
ENV["clouds"] = None
ENV["capture_cvars"] = ()
ENV["capture_show_flags"] = ()
ENV["sky_dome"] = {"centre": (22.0, 18.0, 0.0), "radius_m": 2400.0, "intensity": 1.0, "opacity": 1.0,
                   "coverage": 0.46, "seed": 7}
ENV["sky_dome"]["intensity"] = 60.0
# f1: the two-column slab path (ground f1) replaces the r3 paver courses: the level step deletes them from DojoLab
RETIRED_MESHES.update({f"SM_DKG_PaverCourse_2x0p42_{v}": f"/Game/DojoKit/Ground/Meshes/SM_DKG_PaverCourse_2x0p42_{v}"
                       for v in "ABCDEFGH"})
# f1 L7 (L6 measured, round3/f1_work/L6/regions_L6.json): taiko lacquer still (131, 26, 5) s 0.96 (the lit side's B in
# the tonemapper toe: the maroon mean must be lifted out of it), stand (118, 65, 23) s 0.80, rope s 0.55, rack / dummy
# (45-48, 35-41, 29-38) still dark, edging strip pale lilac, glow (212, 137, 90) s 0.58 (no clipping; a little paler)
LOOK["M_DKP_Taiko_Lacquer"] = {"scalars": {"ValueMult": 1.0, "Saturation": 1.0, "FlattenToMean": 0.85},
                               "vectors": {"Tint": [1.0, 1.0, 1.0], "MeanColour": [0.10, 0.045, 0.05]}}
LOOK["M_DKP_Train_RopeFuzz"] = {"scalars": {"Saturation": 0.38, "ValueMult": 1.2}}
LOOK["M_DKG_EdgeTimber"] = {"scalars": {"ValueMult": 0.42, "Saturation": 0.7}, "vectors": {"Tint": [1.0, 0.93, 0.84]}}
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 65.0, "Saturation": 0.5}}
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.91, 0.98, 1.05))
EXTRA_MATERIALS["M_DJS_TimberStand"] = _timber_variant(_TIMBER_DARK_TEX, 4.0, 0.85, 0.45, (0.75, 0.92, 1.1),
                                                       "f1: the taiko stand, dark aged brown (the sheet)")
EXTRA_MATERIALS["M_DJS_TimberStandEnd"] = _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 0.85, 0.45, (0.75, 0.92, 1.1),
                                                          "f1: stand end grain")
EXTRA_MATERIALS["M_DJS_TimberMid"] = _timber_variant(_TIMBER_DARK_TEX, 4.0, 3.8, 0.55, (0.82, 1.0, 0.96),
                                                     "f1: training props, mid warm brown with visible grain")
EXTRA_MATERIALS["M_DJS_TimberMidEnd"] = _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 3.8, 0.55, (0.82, 1.0, 0.96),
                                                        "f1: end grain")
ENV["sky_dome"]["intensity"] = 75.0
# f1 L8: lacquer (172, 54, 20) s 0.88 after L7 (too bright and orange), stand (95, 48, 16) s 0.83 (orange)
LOOK["M_DKP_Taiko_Lacquer"] = {"scalars": {"ValueMult": 0.75, "Saturation": 1.0, "FlattenToMean": 0.85},
                               "vectors": {"Tint": [1.0, 1.0, 1.0], "MeanColour": [0.075, 0.032, 0.055]}}
EXTRA_MATERIALS["M_DJS_TimberStand"] = _timber_variant(_TIMBER_DARK_TEX, 4.0, 0.9, 0.3, (0.7, 0.9, 1.35),
                                                       "f1: the taiko stand, dark aged brown (the sheet)")
EXTRA_MATERIALS["M_DJS_TimberStandEnd"] = _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 0.9, 0.3, (0.7, 0.9, 1.35),
                                                          "f1: stand end grain")


# ================================================================================================ ROUND 4
# 2026-09-29, the combined import of the remaining buildings (round4.py). The look values above stay as they are (the
# brief: do not regress round 3's look); the new kits use the same library instances, so they inherit them.
# - The grey-box pavilion (and its roof) is gone: its distance-field fix has nothing left to act on in the layout. The
#   actor override M_DJS_PavilionRoof_GB stays defined (unused) so older layouts still resolve.
DF_FIX.pop("SM_DGB_Pavilion_Roof", None)
# - The judge close-ups for the new buildings and the round-4 ridges (Blender frame, metres).
CLOSEUPS.extend([
    ("CU_R4_StorehouseFront", (8.8, 21.0, 1.75), (3.4, 28.0, 2.7), 70.0, (1920, 1080),
     "round 4: the storehouse (kura) from the courtyard, 3/4 from the south-east: door + canopy, granite band, roof"),
    ("CU_R4_ResidenceFront", (35.2, 21.0, 1.75), (40.6, 28.0, 2.7), 70.0, (1920, 1080),
     "round 4: the residence from the courtyard, 3/4 from the south-west: door + canopy, lattice window + hood, meter"),
    ("CU_R4_CorridorOpen", (10.2, 25.2, 1.6), (8.6, 31.0, 1.9), 68.0, (1920, 1080),
     "round 4: the west covered corridor from its open (south) side: posts on pedestals, lattice rail, roof"),
    ("CU_R4_ShedVending", (18.5, 4.5, 1.8), (7.0, 1.8, 1.5), 70.0, (1920, 1080),
     "round 4: the training shed (corrugated lean-to, rack, route-7 crate) with the vending machine"),
    ("CU_R4_PavilionTaiko", (33.0, 5.0, 2.2), (41.0, 3.0, 2.4), 64.0, (1920, 1080),
     "round 4: the drum pavilion on its granite plinth with the taiko under it (route-7 crate and eave pad)"),
    ("CU_R4_RidgeHall", (11.2, 25.2, 10.4), (15.2, 29.0, 9.3), 45.0, (1920, 1080),
     "round 4: the hall's upper ridge close: 4 noshi courses, cap row, the west onigawara"),
    ("CU_R4_RidgeGate", (27.2, 4.2, 5.6), (25.6, -0.5, 4.7), 48.0, (1920, 1080),
     "round 4: the gate ridge close from the courtyard side: noshi courses, cap row, the east onigawara"),
])
