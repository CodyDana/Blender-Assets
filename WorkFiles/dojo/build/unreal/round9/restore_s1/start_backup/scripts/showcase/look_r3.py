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
        base.setdefault("radius_m", li["radius_m"])   # round 8 s2: the radius is tunable too (its composed value kept)
        li["kelvin"], li["candela"], li["radius_m"] = base["kelvin"], base["candela"], base["radius_m"]
        for piece, t in LAMP_TUNE.items():
            if li["name"].startswith("Light_" + piece.replace("SM_", "") + "__"):
                li["kelvin"] = t.get("kelvin", li["kelvin"])
                li["candela"] = round(base["candela"] * t.get("candela_mult", 1.0), 2)
                li["radius_m"] = t.get("radius_m", li["radius_m"])
                done[li["name"]] = {"kelvin": li["kelvin"], "candela": li["candela"], "radius_m": li["radius_m"],
                                    "base": base}
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


# ================================================================================================ ROUND 4 FIX f1
# 2026-09-29, the two Unreal judges (whole 6.5 / buildings 6.4). Quick instance / grade values only (the full look pass
# comes later); every value below was set against the round-4 captures (unreal/round4/r4/regions_r4*.json) and
# re-measured on the f1 captures (unreal/round4/f1/).
# - Crushed shade (every new building: corridor 55 % near-black, the shed rack, the store door, the residence
#   wainscot, the pavilion ceiling): the filmic toe. probe2 (round 3) measured film toe ~0.3 lifting the shade out of
#   the crush and taking the post from s 0.85 to 0.65; applied here at 0.35 (UE default 0.55).
ENV["grade_extra"] = dict(ENV.get("grade_extra", {}), film_toe=0.35)
# - Timber (judges: near-black charcoal; every reference: warm mid chestnut / honey-brown, ref-2 deck (70, 44, 29)
#   s 0.59): about 2x the value and a warm tint, saturation held (the r3 verifier's sunlit-timber limit).
_TIMBER_F1 = {"scalars": {"ValueMult": 3.2, "Saturation": 0.55}, "vectors": {"Tint": [1.0, 0.93, 0.82]}}
for _s in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_s] = copy.deepcopy(_TIMBER_F1)
# - Roof tiles + ridge parts (one material): darker slate blue-grey that stays dark in the low sun (pavilion sunlit
#   R/B 1.55, gate ridge 1.46-1.61), less fleck (the ridge's noshi read speckled / granite-like)
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.84, 0.95, 1.12), flat=0.75, vm=1.75, sat=0.3)
# - Granite (store band, pavilion plinth read cream sandstone in the sun): cooler, less chroma
LOOK["M_DJ_Granite"] = _granite((0.93, 0.98, 1.02), sat=0.35)
LOOK["M_DJ_Granite_Tri"] = _granite((0.93, 0.98, 1.02), sat=0.35)
# - Taiko: dark oxblood-brown lacquer (was tomato red (121, 27, 14)); some crazing back through (less flatten)
LOOK["M_DKP_Taiko_Lacquer"] = {"scalars": {"ValueMult": 0.8, "Saturation": 0.62, "FlattenToMean": 0.7},
                               "vectors": {"Tint": [1.0, 0.95, 0.95], "MeanColour": [0.055, 0.02, 0.016]}}
# - Training props: warm oiled brown (were bleached silver-grey)
EXTRA_MATERIALS["M_DJS_TimberMid"] = _timber_variant(_TIMBER_DARK_TEX, 4.0, 3.4, 0.62, (1.0, 0.9, 0.76),
                                                     "f1 r4: training props, warm oiled brown (the sheet)")
EXTRA_MATERIALS["M_DJS_TimberMidEnd"] = _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 3.4, 0.62, (1.0, 0.9, 0.76),
                                                        "f1 r4: end grain")
# - Taiko sticks: smooth light-brown turned wood (TimberPale's stripes read as birch bark)
EXTRA_MATERIALS["M_DJS_StickPale"] = {"master": "M_DJ_Flat_Master", "kit": "showcase",
                                      "ue_dir": "/Game/DojoKit/Showcase/Materials", "textures": {},
                                      "scalars": {"Roughness": 0.55, "Metallic": 0.0, "Specular": 0.5},
                                      "vectors": {"Base Colour": [0.40, 0.26, 0.15]}, "switches": {},
                                      "note": "f1 r4: plain sanded light-brown bachi (the sheet), no bark stripes"}
ACTOR_MATERIAL_OVERRIDES["SM_DKP_Taiko_Stick"] = {0: "M_DJS_StickPale"}
# - Sand: pale cream, not peach (whole delta 9); gravel lighter and warmer (whole delta 4)
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.95, "Saturation": 0.62, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.99, 0.95]}}
LOOK["M_DKG_Gravel"] = {"scalars": {"Saturation": 0.6, "ValueMult": 1.22}, "vectors": {"Tint": [1.04, 1.0, 0.9]}}
LOOK["M_DKG_GravelCoarse"] = {"scalars": {"Saturation": 0.6, "ValueMult": 1.6}, "vectors": {"Tint": [1.04, 1.0, 0.9]}}
# - Cameras: the shed close-up looked along the board wall edge-on (the judges read the wall as a third of the
#   width); now from the courtyard in front of the shed with the vending machine at the edge
CLOSEUPS[:] = [c for c in CLOSEUPS if c[0] != "CU_R4_ShedVending"] + [
    ("CU_R4_ShedVending", (12.0, 12.0, 2.0), (6.2, 1.8, 1.3), 70.0, (1920, 1080),
     "round 4 f1: the training shed from the courtyard in front (full-width board wall, rack, corrugated lean-to, both "
     "post footings, the route-7 crate) with the vending machine at the edge")]
# - The Blender-side instance recipes that the kits own (the outbuildings' M_DKO_SteelGrey, the shed's
#   M_DKS_GalvWeathered) come through their layouts; nothing here.
# - The r4 outbuilding pieces the gable-front rebuild retired (eave-wall bays, the E-W gables, the one 7.05 m gutter):
#   the level step deletes them from DojoLab once no actor uses them
RETIRED_MESHES.update({n: f"/Game/DojoKit/Outbuildings/Meshes/{n}" for n in (
    "SM_DKO_Store_Bay_2m", "SM_DKO_Store_Bay_2p5", "SM_DKO_Store_Bay_Door", "SM_DKO_Store_Gable",
    "SM_DKO_Res_Bay_1p1", "SM_DKO_Res_Bay_2p15", "SM_DKO_Res_Bay_Door", "SM_DKO_Res_Bay_Window", "SM_DKO_Res_Gable",
    "SM_DKO_Gutter")})
# f1 L2 (L1 measured on unreal/round4/f1 run 1): shaded timber still grey-brown, sunlit pavilion posts orange-tan;
# the ridge stacks and pavilion tiles still tan where the 12 deg sun hits them square; the lacquer orange-brown; the
# store door's galvanised wear read as white blotches; the shoji / lattice glow salmon-pink (the refs: amber-gold)
_TIMBER_F1 = {"scalars": {"ValueMult": 3.4, "Saturation": 0.6}, "vectors": {"Tint": [1.0, 0.9, 0.76]}}
for _s in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_s] = copy.deepcopy(_TIMBER_F1)
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.8, 0.94, 1.18), flat=0.75, vm=1.45, sat=0.3)
LOOK["M_DJ_Granite"] = _granite((0.86, 0.94, 1.02), sat=0.25)
LOOK["M_DJ_Granite_Tri"] = _granite((0.86, 0.94, 1.02), sat=0.25)
LOOK["M_DKP_Taiko_Lacquer"] = {"scalars": {"ValueMult": 0.6, "Saturation": 0.55, "FlattenToMean": 0.7},
                               "vectors": {"Tint": [1.0, 0.95, 0.95], "MeanColour": [0.045, 0.016, 0.013]}}
LOOK["M_DKO_SteelGrey"] = {"scalars": {"NormalStrength": 0.5}, "vectors": {"Tint": [0.55, 0.56, 0.6]},
                           "switches": {"UseWear": False}}
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 65.0, "Saturation": 0.6},
                           "vectors": {"EmissiveTint": [1.0, 0.86, 0.55]}}
# f1 L3 (L2 measured): the lacquer fell into the toe (near black): lift it back; the door's galvanised BC carries
# white oxide patches (not the wear): flatten it most of the way to a mid steel grey
LOOK["M_DKP_Taiko_Lacquer"] = {"scalars": {"ValueMult": 1.0, "Saturation": 0.6, "FlattenToMean": 0.7},
                               "vectors": {"Tint": [1.0, 0.95, 0.95], "MeanColour": [0.06, 0.02, 0.016]}}
LOOK["M_DKO_SteelGrey"] = {"scalars": {"NormalStrength": 0.5, "FlattenToMean": 0.8},
                           "vectors": {"Tint": [0.55, 0.56, 0.6], "MeanColour": [0.2, 0.205, 0.22]},
                           "switches": {"UseWear": False}}
# f1 L4: the door's pale patches are the galvanised set's low-roughness oxide spots catching the sky (spec), not the
# albedo: dull the leaves (painted steel)
LOOK["M_DKO_SteelGrey"]["scalars"]["RoughMult"] = 2.6
# f1 L5: the door recipe itself (layout_outbuildings.json) now uses the library Iron on its clean UV band; the showcase
# adds nothing to it
LOOK.pop("M_DKO_SteelGrey", None)


# ================================================================================================ ROUND 5
# 2026-09-29, the final look pass WITHOUT vegetation (user: "start with everything else and leave the vegetation for
# later"). round5.py brings the dressing (the user's armory emblem plaques + 101 weathering decals) and the outside
# (approach road with the street lamps / power line, rear-alley fences, background town, far plain, mountains).
# - Close-ups for the judges (Blender frame, metres). The dressing / outside tracks' review framings where they exist.
CLOSEUPS.extend([
    ("CU_R5_ApproachRoad", (-2.0, -5.8, 1.7), (22.0, -2.4, 2.2), 62.0, (1920, 1080),
     "round 5: the approach road from the street toward the gate: cobbles, kerbs, gutter, street lamps B / A at the "
     "landing, the power line on the terrace edge, the gate front with its emblem plaque"),
    ("CU_R5_HallGableEmblem", (10.2, 26.2, 6.4), (14.5, 29.0, 7.93), 26.0, (1920, 1080),
     "round 5: the user's armory emblem plaque on the hall's west upper gable (king post over the collar beam)"),
    ("CU_R5_GateEmblem", (22.0, -4.3, 2.0), (22.0, -1.95, 2.98), 40.0, (1920, 1080),
     "round 5: the emblem plaque on the gate's street-side eave beam (centre peg)"),
    ("CU_R5_AlleyFence", (11.9, 29.0, 2.2), (11.8, 34.05, 1.1), 58.0, (1920, 1080),
     "round 5: the rear-alley board fence with its wicket gate (spec 4.6; closed in the 1v1), west side"),
    ("CU_R5_MossWallFoot", (11.6, 2.4, 1.0), (10.0, -0.05, 0.35), 50.0, (1920, 1080),
     "round 5: moss / damp decal at the south wall's courtyard foot (MossFoot_01: moss must sit at the FOOT)"),
    ("CU_R5_FarBackground", (22.0, -30.0, 18.0), (22.0, 60.0, 8.0), 80.0, (1920, 1080),
     "round 5: far view over the road and the compound to the background town, far plain and both mountain rings"),
    ("CU_R5_Skyline", (26.0, 6.0, 1.7), (2.0, 60.0, 9.0), 70.0, (1920, 1080),
     "round 5: player-eye skyline to the NW over the wall: town roofs, haze, mountain silhouettes"),
])
# - Lighting (the look pass's round-4 open items; set by measuring the round-5 captures, unreal/round5/): every value is
#   a real light / GI / tone-curve setting, no flat fill light and no global colour grade.
ENV["sky_texture"] = {"compression_settings": {"enum": "TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP"}}
ENV["pp_extra"] = {"lumen_final_gather_quality": 2.0, "lumen_scene_lighting_quality": 2.0, "lumen_scene_detail": 2.0}
ENV["skylight_extra"] = {}
ENV["fog"] = {}
ENV["sun_extra"] = {}
ENV["sky_atmosphere"] = {}
ENV["sky_dome"]["r5_shading"] = True     # make_sky_clouds.py: soft alpha, billowed shading, dithered (no posterised plates)
# - ROUND 5 lighting, set on the colour probes of unreal/round5/probe_a..k (the saved level, every variant from the same
#   base; regions by measure_r5.py). Findings:
#   * Lumen GI IS active in the SceneCapture stills (show flag LumenGlobalIllumination off -> unoccluded sky), but its
#     bounce under the deep roofs is weak at a 12 deg sun, so every shaded underside sat on the sky's occlusion alone:
#     pavilion ceiling (1, 0, 0), alley fence (1, 0, 0). Lumen final-gather / scene quality, hardware RT and the sky
#     light's lower hemisphere changed nothing measurable; the sky light, the sun's GI contribution and the tone curve
#     did (probe_a V3, probe_g L1, probe_h).
#   * Sunlit tiles read tan (pavilion R/B 1.89) and sunlit plaster orange (s 0.55-0.66): the 5000 K sun reddened again
#     by the atmosphere's transmittance at 12 deg. A 6500 K sun + a brighter sky light moves them toward reference 2
#     without a grade (tiles 1.89 -> 1.26, plaster s 0.55 -> 0.37).
ENV.update({"sun_kelvin": 6500, "skylight_intensity": 9.0})
ENV["sun_extra"] = {"indirect_lighting_intensity": 4.0}       # the sun's Lumen GI bounce x4 (probe_k K1): real light
ENV["pp_extra"] = {"lumen_final_gather_quality": 2.0, "lumen_scene_lighting_quality": 2.0, "lumen_scene_detail": 2.0,
                   "local_exposure_shadow_contrast_scale": 0.5}   # local exposure: shadow contrast lifted (tone curve)
ENV["grade_extra"] = dict(ENV.get("grade_extra", {}), film_toe=0.28)
ENV["fog"] = {"fog_density": 0.012, "fog_height_falloff": 0.2}   # ridges (49, 53, 77) vs ref 2 (60, 66, 84)
# - Material instance look (low-sun colour; the brief: sun / sky / MI values, no global grade)
_TIMBER_R5 = {"scalars": {"ValueMult": 3.0, "Saturation": 0.75, "AOStrength": 0.25},
              "vectors": {"Tint": [1.0, 0.82, 0.66]}}   # sunlit posts h 25 s 0.55-0.59; AO: the grain grooves no longer
for _s in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):   # crush in deep shade
    LOOK[_s] = copy.deepcopy(_TIMBER_R5)
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.64, 0.9, 1.36), flat=0.75, vm=1.45, sat=0.3)   # sunlit R/B toward <= 1.2
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.032, 0.049, 0.09]
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):          # ref 2 sand (192, 154, 128) s 0.33: warmer, more chroma
    LOOK[_s] = {"scalars": {"ValueMult": 0.92, "Saturation": 1.0, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.92, 0.84]}}
LOOK["M_DJ_PlasterCream"] = {"scalars": {"ValueMult": 1.05, "Saturation": 0.45},
                             "vectors": {"Tint": [1.0, 0.95, 0.95]}}   # ref 2 outbuilding plaster (155, 124, 112) s 0.28
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 90.0},
                           "vectors": {"EmissiveTint": [1.0, 0.72, 0.42]}}   # cores hue 42 -> amber (ref 2 shoji h 24)
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 70.0, "Saturation": 0.85},
                           "vectors": {"EmissiveTint": [1.0, 0.78, 0.48]}}   # lamp glass cores s 0.31 -> amber
# - it2 (unreal/round5/it2) read cold and blue overall: the r5 cloud layer came out thinner and greyer (fixed in
#   make_sky_clouds.py) and 9x sky light + the bluest tile tint pushed the shaded tiles to R/B 0.51 (ref 2: 0.86). it3:
#   a milder sky light and sun, the tile tint between f1 and it2
ENV.update({"sun_kelvin": 6000, "skylight_intensity": 7.5})
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.74, 0.92, 1.24), flat=0.75, vm=1.45, sat=0.3)
# - it3 (probe_n): the SkyAtmosphere lift toward reference 2's warm upper sky (top (192, 149, 142), horizon peach):
#   sky above the ridges (178, 177, 185) -> (190, 181, 169); the real-time sky light follows the sky it captures
ENV["sky_factor"] = (4.2, 2.8, 2.1)
# - it3 -> final (probe_o on the it3 level): 7000 K takes the sunlit pavilion tiles R/B 1.37 -> 1.29 and the gate noshi
#   1.26 -> 1.19 with sunlit timber still h 25-26 s 0.55-0.58; RoughMult 2.0 on the tiles cuts the blue sky sheen in
#   shade (hall upper roof R/B 0.83 -> 0.90, ref 2 0.89). Glow: the shoji cores clipped R over 21 % of the bay (hue 41);
#   the lamp glass cores read pale (s 0.5, hue 41)
ENV["sun_kelvin"] = 7000
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.72, 0.92, 1.26), flat=0.75, vm=1.45, sat=0.3, rough=2.0)
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 65.0}, "vectors": {"EmissiveTint": [1.0, 0.7, 0.4]}}
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 70.0, "Saturation": 1.0},
                           "vectors": {"EmissiveTint": [1.0, 0.7, 0.4]}}


# ================================================================================================ ROUND 5 FIX f1
# 2026-09-29, the two round-5 Unreal judges (whole 6.5 / detail 6.5). Their first blocker (both): the sky and key
# light read as an overcast late afternoon (grey-blue / lavender sky with smeared pink cloud texture, a front / side
# sun), where dojo1_reference2 is a BACKLIT sunset: the brightest warm band on the horizon behind the hall, the hall
# front in soft shade, rim light on the ridges. Every value below was set by measuring the f1 captures
# (unreal/round5/f1_work/, final stills unreal/round5/f1/).
# - Sun: low and behind the hall, left of the gate axis as the reference's glow (the gate looks +Y; azimuth 108 deg
#   from +X is 18 deg left of it). it1 (unreal/round5/f1_work/it1) at 10 deg / 108 deg: every building of 5 m or more
#   threw a 30 m shadow, so the whole courtyard stood in shade, flat and soft, with no raking light on the sand (the
#   detail judge's ask). Final: 125 deg (35 deg left of the gate axis, the reference's glow sits left of centre) at
#   14 deg: the hall front and the outbuildings' gable fronts stay backlit (shade), the ridges and the west faces take
#   the rim light, and the sun comes over the storehouse and the west wall across the west sand field (raking light),
#   while the hall's shadow runs diagonally over the east field.
ENV.update({"sun_elev_deg": 14.0, "sun_azimuth_deg_from_x": 125.0, "sun_kelvin": 5000})
# - Sky: our own painted backlit sunset sky, full and opaque (make_sky_sunset.py), in place of the translucent cloud
#   layer over the SkyAtmosphere (which stays for the sun's transmittance, the aerial perspective and the sky light)
ENV["sky_dome"] = {"centre": (22.0, 18.0, 0.0), "radius_m": 2400.0, "intensity": 90.0, "opacity": 1.0, "seed": 11,
                   "png": "Exports/DojoKit/Showcase/Textures/T_DJS_SunsetSky.png"}
ENV["sky_texture"] = {"compression_settings": {"enum": "TextureCompressionSettings.TC_BC7"}}
# - it2: the calibrated painting (fit_sky_calib.py on it1: the dome's texture -> capture response, pooled channels)
#   needs 1.65x the it1 dome Intensity (90)
ENV["sky_dome"]["intensity"] = 148.0
# - Shoji / window glow (both judges): r5 cores s 0.75-0.81 and the residence box clipped 12.9 %; target warm paper
#   white-amber (250, 205, 140) at the core, the kumiko dark over it: less saturated tint, lower intensity
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 50.0, "Saturation": 0.75},
                           "vectors": {"EmissiveTint": [1.0, 0.84, 0.6]}}
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 55.0, "Saturation": 0.8},
                           "vectors": {"EmissiveTint": [1.0, 0.82, 0.56]}}
# - Roof tiles (whole delta 5): the tiles read cool slate-blue (gate hue 245, R/B 0.82); reference 2's kawara are warm
#   charcoal grey. Neutral to slightly warm tint (the backlit sun leaves few sunlit tile faces to go tan)
LOOK["M_DJ_RoofTile"] = _tile(tint=(1.0, 0.98, 0.95), flat=0.75, vm=1.45, sat=0.3, rough=2.0)
LOOK["M_DKX_Kawara"] = {"scalars": {"ValueMult": 1.3, "Saturation": 0.3, "RoughMult": 1.8},
                        "vectors": {"Tint": [1.0, 0.98, 0.95]}}
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.058, 0.056, 0.054]   # the flatten target: warm charcoal, not the
#                                                                        # texture's blue mean (R/B 0.76)
# - Sand (it2 (215, 179, 134) h 33 s 0.38 against ref 2 (185, 146, 120) h 24 s 0.35): darker and redder; the
#   foreground falls off with a stronger vignette (whole delta 11)
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.66, "Saturation": 1.0, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.82, 0.92]}}
ENV["grade_extra"] = dict(ENV.get("grade_extra", {}), vignette_intensity=0.42)
# - Gate timber (detail delta 8: the soffit read a saturated mahogany (40, 11, 2) s 0.95; dojo_gatehouse_ref / ref 1:
#   weathered grey-brown): the gate's own instances of the aged timber, greyer and less saturated; the lamps a
#   little cooler and weaker under the gate roof
_TIMBER_AGED_TEX = {"BC": "T_DJ_TimberAged_BC", "ORM": "T_DJ_TimberAged_ORM", "N": "T_DJ_TimberAged_N",
                    "WearMask": "T_DJ_WearMask_M"}
_TIMBER_AGED_END_TEX = {"BC": "T_DJ_TimberAgedEnd_BC", "ORM": "T_DJ_TimberAgedEnd_ORM", "N": "T_DJ_TimberAgedEnd_N",
                        "WearMask": "T_DJ_WearMask_M"}
EXTRA_MATERIALS["M_DJS_GateTimber"] = _timber_variant(_TIMBER_AGED_TEX, 4.0, 2.6, 0.42, (0.96, 0.9, 0.84),
                                                      "r5 f1: the gate's weathered grey-brown timber (not mahogany)")
EXTRA_MATERIALS["M_DJS_GateTimberEnd"] = _timber_variant(_TIMBER_AGED_END_TEX, 2.0, 2.6, 0.42, (0.96, 0.9, 0.84),
                                                         "r5 f1: gate end grain")
EXTRA_MATERIALS["M_DJS_GateTimberEnd"]["vectors"]["TileM"] = [1.0, 1.0, 0.0, 0.0]
ACTOR_MATERIAL_OVERRIDES.update({
    "SM_DK_Gate_Frame": {1: "M_DJS_GateTimber", 3: "M_DJS_GateTimberEnd"},
    "SM_DK_Gate_Roof": {1: "M_DJS_GateTimber", 2: "M_DJS_GateTimberEnd"},
    "SM_DK_Gate_Leaf_L": {0: "M_DJS_GateTimber", 2: "M_DJS_GateTimberEnd"},
    "SM_DK_Gate_Leaf_R": {0: "M_DJS_GateTimber", 2: "M_DJS_GateTimberEnd"},
})
LAMP_TUNE["SM_DK_Gate_Lamp"] = {"kelvin": 3300, "candela_mult": 0.7}
# - Street lamps (whole delta 9: only the heads glowed): a visible warm pool on the road
LAMP_TUNE["SM_DKP_Modern_StreetLamp_A"] = {"kelvin": 2900, "candela_mult": 5.0}
LAMP_TUNE["SM_DKP_Modern_StreetLamp_B"] = {"kelvin": 2900, "candela_mult": 5.0}
# - Approach road (whole delta 9, detail delta 12): smaller cobbles (tile 4 m -> 2.4 m), macro variation, warmer and
#   lower in contrast; the town lanes paved with it, the town's yards a fine grey gravel (whole delta 3: 'the dirt
#   field between blocks reads unfinished')
LOOK["M_DKX_RoadCobble"] = {"scalars": {"Tile cm": 240.0, "Macro Tint": 0.3, "Macro Dirt": 0.28, "Macro Rough": 0.12,
                                        "Saturation": 0.7, "ValueMult": 0.92},
                            "vectors": {"Tint": [1.05, 1.0, 0.92]}}
EXTRA_MATERIALS["M_DJS_TownYard"] = {
    "master": "M_DJ_GroundXY_Master", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
    "textures": {"Base Colour Map": "T_DKG_Gravel_BC", "ORM Map": "T_DKG_Gravel_ORM", "Normal Map": "T_DKG_Gravel_N",
                 "Macro Map": "T_DKG_Macro_M"},
    "scalars": {"Tile cm": 300.0, "Macro Tint": 0.25, "Macro Dirt": 0.3, "Macro Rough": 0.05, "Saturation": 0.45,
                "ValueMult": 0.85}, "vectors": {"Tint": [1.0, 0.98, 0.92]}, "switches": {},
    "note": "r5 f1: the town's yards and plots (the outside ground's soil slot): fine grey gravel, not bare dirt"}
for _p in ("SM_DKX_Ground_W", "SM_DKX_Ground_E", "SM_DKX_Ground_N"):
    ACTOR_MATERIAL_OVERRIDES[_p] = {0: "M_DJS_TownYard", 1: "M_DKX_RoadCobble"}
# - Wall-foot gravel (detail delta 10: oversized, high-contrast pebbles): finer and flatter
LOOK["M_DKG_Gravel"] = {"scalars": {"Saturation": 0.5, "ValueMult": 1.15, "Tile cm": 200.0}, "vectors": {"Tint": [1.04, 1.0, 0.9]}}
LOOK["M_DKG_GravelCoarse"] = {"scalars": {"Saturation": 0.5, "ValueMult": 1.4, "Tile cm": 200.0},
                              "vectors": {"Tint": [1.04, 1.0, 0.9]}}
# - Decals (both judges): moss subtler grey-green (the edge feather is in the decal master); the lichen that read as
#   white scribbles on the roofs and caps are dropped (round5.DROP_DECALS), the lantern ones darkened
LOOK["M_DKD_Decal_MossFoot"] = {"scalars": {"Opacity": 0.75, "Saturation": 0.5, "ValueMult": 0.9},
                                "vectors": {"Tint": [0.92, 0.95, 0.86]}}
LOOK["M_DKD_Decal_Lichen"] = {"scalars": {"Opacity": 0.55, "Saturation": 0.4, "ValueMult": 0.6}}
# - Hall gable emblem (both judges: a lemon-yellow sign in the sun): its own aged-gilt instance (antique gold (200, 150,
#   60) on the black lacquer, roughness 0.45); the gate plaque keeps the dressing track's instance
EXTRA_MATERIALS["M_DJS_EmblemPlaque_Aged"] = {
    "master": "M_DJ_Lib_Opaque", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
    "textures": {"BC": "T_DKD_Emblem_BC", "ORM": "T_DKD_Emblem_ORM", "N": "T_DKD_Emblem_N"},
    "scalars": {"RoughMult": 1.5, "NormalStrength": 1.0, "Saturation": 0.8, "ValueMult": 0.62},
    "vectors": {"Tint": [1.0, 0.82, 0.6], "TileM": [1.0, 1.0, 0.0, 0.0]}, "switches": {"UseWear": False},
    "note": "r5 f1: the hall plaque's aged gilt (the user's armory emblem textures, unchanged)"}
ACTOR_MATERIAL_OVERRIDES["SM_DKD_EmblemPlaque_Hall"] = {0: "M_DJS_EmblemPlaque_Aged"}
# - Training props (detail delta 9: bleached silver-grey; the sheet: dark walnut stain, dark iron)
EXTRA_MATERIALS["M_DJS_TimberMid"] = _timber_variant(_TIMBER_DARK_TEX, 4.0, 1.9, 0.7, (1.0, 0.84, 0.68),
                                                     "r5 f1: training props, dark walnut-stained wood (the sheet)")
EXTRA_MATERIALS["M_DJS_TimberMidEnd"] = _timber_variant(_TIMBER_DARK_END_TEX, 2.0, 1.9, 0.7, (1.0, 0.84, 0.68),
                                                        "r5 f1: end grain")
# - Far background: the two smooth shells are gone (four ridge rings + the far town, outside track f1)
RETIRED_MESHES.update({n: f"/Game/DojoKit/Outside/Meshes/{n}" for n in ("SM_DKX_Mountains_Near", "SM_DKX_Mountains_Far")})
# - Haze: explicit fog colours (lavender-grey inscatter, a warm lobe toward the sun) so the ranges take the horizon's
#   warmth; the atmosphere's own height-fog contribution off (it painted the far plain peach in it2)
ENV["fog"] = {"fog_density": 0.016, "fog_height_falloff": 0.18, "fog_inscattering_luminance": [16.0, 14.0, 19.0],
              "directional_inscattering_luminance": [34.0, 18.0, 8.0], "directional_inscattering_exponent": 6.0,
              "directional_inscattering_start_distance": 15000.0}
ENV["sky_atmosphere"] = {"height_fog_contribution": 0.0}
# - The reference-2 camera (whole delta 12): from the gate threshold, the granite sill across the bottom and the gate
#   posts bracketing both edges, as dojo1_reference2 is framed
CLOSEUPS.append(("CAM_Ref2Match", (22.0, -2.6, 2.1), (22.0, 24.0, -3.0), 74.0, (1448, 1086),
                 "round 5 f1: the reference-2 framing from the gate threshold (sill across the bottom, the gate posts at "
                 "both edges), for a like-for-like look comparison with dojo1_reference2"))
LOOK["M_DKD_Decal_MossFoot"]["scalars"]["EdgeFeather"] = 0.16
LOOK["M_DKD_Decal_Grime"] = {"scalars": {"EdgeFeather": 0.1}}
LOOK["M_DKD_Decal_RainStreak"] = {"scalars": {"EdgeFeather": 0.1}}
# - it3 (unreal/round5/f1_work/it3): the fog's warm lobe blew the ridges toward the sun to white (clip 43 % there) and
#   the lavender inscatter washed the far town; the ambient read orange everywhere (the sky light follows the warm
#   atmosphere factor); the sand went salmon (206, 151, 112) s 0.46
ENV["fog"] = {"fog_density": 0.014, "fog_height_falloff": 0.18, "fog_inscattering_luminance": [7.0, 6.4, 8.6],
              "directional_inscattering_luminance": [12.0, 6.5, 3.0], "directional_inscattering_exponent": 6.0,
              "directional_inscattering_start_distance": 15000.0}
ENV["sky_factor"] = (3.8, 2.8, 2.5)
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.62, "Saturation": 0.8, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.84, 0.94]}}
CLOSEUPS[:] = [c for c in CLOSEUPS if c[0] != "CAM_Ref2Match"] + [
    ("CAM_Ref2Match", (22.0, -1.2, 2.1), (22.0, 24.0, -3.4), 74.0, (1448, 1086),
     "round 5 f1: the reference-2 framing from the gate threshold (the threshold paving across the bottom, the gate's "
     "open leaves and posts at both edges), for a like-for-like look comparison with dojo1_reference2")]
# - it4 fog probe (unreal/round5/f1_work/probe_fog, CU_R5_FarBackground): at (7, 6.4, 8.6) / (12, 6.5, 3) the ranges
#   read (224, 195, 174) (washed out, near white toward the sun); at a sixth of that (V2) they recede from (93, 79, 81)
#   (ring 1) to (157, 134, 128) (ring 4) under a warm lobe toward the sun, ref 2's layered hazy ranges
ENV["fog"] = {"fog_density": 0.014, "fog_height_falloff": 0.18, "fog_inscattering_luminance": [1.2, 1.1, 1.45],
              "directional_inscattering_luminance": [2.0, 1.1, 0.5], "directional_inscattering_exponent": 6.0,
              "directional_inscattering_start_distance": 15000.0}
# - the far ground between the far town's houses caught the horizon glow at grazing angles (a thin orange strip under
#   ring 1 even with the fog off): no specular on it
LOOK["M_DKX_FarGround"] = {"scalars": {"Specular": 0.0, "Roughness": 1.0}}
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s]["vectors"]["Tint"] = [1.0, 0.84, 0.9]
CLOSEUPS[:] = [c for c in CLOSEUPS if c[0] != "CAM_Ref2Match"] + [
    ("CAM_Ref2Match", (22.0, -0.9, 2.1), (22.0, 24.0, -3.4), 74.0, (1448, 1086),
     "round 5 f1: the reference-2 framing from the gate threshold (the threshold paving across the bottom, the gate's "
     "open leaves and posts at both edges), for a like-for-like look comparison with dojo1_reference2")]
# - it5 (unreal/round5/f1_work/it5): glow cores now (223, 167, 101) s 0.55 (hall) and (230, 193, 115) s 0.50, clip 0
#   (residence; r5 12.9 %): the hall paper a little brighter and yellower toward (240-250, 195-205, 120-140)
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 62.0, "Saturation": 0.72},
                           "vectors": {"EmissiveTint": [1.0, 0.87, 0.64]}}
# - the plaster in direct low sun read orange (pavilion wall (222, 160, 92) s 0.59): a slightly whiter sun
ENV["sun_kelvin"] = 5600
# - Deep shade (detail blocker / delta 11: the alley wicket, the corridor bays and the pavilion ceiling crushed at
#   (30, 9, 2) / (34, 18, 11) / (10, 2, 1)): low, shadowless warm-neutral fill point lights where the bounce light would
#   be in a real courtyard (the round-5 stage measured Lumen's bounce under the deep roofs as physically weak). They
#   are listed as layout lights (name Light_Fill_*), so the level step places them and verify counts them.
FILL_LIGHTS = [   # name, loc (Blender m), candela (before LAMP_SCALE), kelvin, radius m, note
    ("Light_Fill_PavilionCeiling", (41.0, 3.0, 2.9), 160.0, 4300, 5.0, "under the drum pavilion's roof"),
    ("Light_Fill_AlleyW", (11.8, 32.4, 2.0), 160.0, 4300, 5.0, "the west rear-alley fence and wicket"),
    ("Light_Fill_AlleyE", (32.2, 32.4, 2.0), 160.0, 4300, 5.0, "the east rear-alley fence and wicket"),
    ("Light_Fill_CorridorW", (8.6, 30.4, 2.2), 160.0, 4300, 5.0, "inside the west covered corridor"),
    ("Light_Fill_CorridorE", (35.4, 30.4, 2.2), 160.0, 4300, 5.0, "inside the east covered corridor"),
]


def apply_fill_lights(lights):
    """Append FILL_LIGHTS to the layout lights (idempotent: earlier Light_Fill_* rows are replaced)."""
    lights[:] = [li for li in lights if not li["name"].startswith("Light_Fill_")]
    for name, loc, cd, k, rad, note in FILL_LIGHTS:
        lights.append({"name": name, "instance": -1, "loc": list(loc), "candela": cd, "kelvin": k, "radius_m": rad,
                       "shadows": False, "source": "round 5 f1 fill light: " + note})
    return [f[0] for f in FILL_LIGHTS]
# - it6: the fills lifted the alley boards (30, 9, 2) -> (41, 17, 6) and the pavilion ceiling (10, 2, 1) -> (26, 8, 2)
#   but the shade stayed a saturated red-brown (the dark timber in the tone curve's toe): brighter and neutral-white
FILL_LIGHTS[:] = [(n, loc, 420.0, 6000, rad, note) for (n, loc, _cd, _k, rad, note) in FILL_LIGHTS]
# - it7 (the ranges and the far ground now face the camera): with the horizon glow no longer seen through the culled
#   far plain, the sand went lilac (165, 139, 129) s 0.22 and the hall front darker (veranda band (40, 23, 15) against
#   ref 2's (72, 49, 32)): a warmer sand, a little more sky light
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.75, "Saturation": 0.9, "NormalFarStrength": 0.6},
                "vectors": {"Tint": [1.0, 0.78, 0.66]}}
ENV["skylight_intensity"] = 9.0
# - wall plaster (detail delta 6: smoother than dojo_wall_ref): the trowel normal a little stronger
LOOK["M_DJ_PlasterCream"]["scalars"]["NormalStrength"] = 1.7


# ================================================================================================ ROUND 6
# 2026-09-30, the fix round after the round-5 look pass (final judge 7.5, verify 12 / 17). User: "yes start first round.
# keep emblem for now" (the plaques stay as placed; vegetation later). Every value below is measured on the round-6
# captures (unreal/round6/, final stills unreal/round6/r6/); instance values, real lights and GI only, no flat fill.
# - Courtyard gravel (final judge: cold grey-white 'snow' from above; r5 f1 CAM_Overview (153, 146, 150) R/B 1.02 s 0.05
#   against ref 1 (148, 120, 109) R/B 1.36 s 0.26 and ref 2 (122-153, 98-120, 90-107) R/B 1.31-1.48 s 0.23-0.32): the
#   gravel map is warm (linear mean R/B 1.75); r5's Saturation 0.5 took it grey. Warm sandy beige, a little darker.
LOOK["M_DKG_Gravel"] = {"scalars": {"Saturation": 1.0, "ValueMult": 1.0, "Tile cm": 200.0},
                        "vectors": {"Tint": [1.06, 0.98, 0.86]}}
LOOK["M_DKG_GravelCoarse"] = {"scalars": {"Saturation": 1.0, "ValueMult": 1.25, "Tile cm": 200.0},
                              "vectors": {"Tint": [1.06, 0.98, 0.86]}}
# - Timber grain crush (verify_r5: the gate's street-side beam p25 (8, 2, 1), the corridor / hall lower-roof soffit (19, 8,
#   4) 33 % near-black, the residence / storehouse fronts, lantern / training close-ups): the timber maps' grain grooves
#   (5th-percentile luminance 0.011 linear, a seventh of the mean) sit in the tone curve's toe under any shade. Pull the
#   grooves partway to the board's own mean colour (FlattenToMean; MeanColour = the map's linear mean x the instance
#   Tint, i.e. the same hue): the grain stays, the crush goes.
_TMEAN = {"T_DJ_TimberAged_BC": (0.1041, 0.0727, 0.05), "T_DJ_TimberAgedEnd_BC": (0.0752, 0.0518, 0.0372),
          "T_DJ_TimberDark_BC": (0.0746, 0.0526, 0.0401), "T_DJ_TimberDarkEnd_BC": (0.0534, 0.0385, 0.0285)}
_T_FLAT = 0.35


def _flat_timber(rec, tex, flat=_T_FLAT):
    tint = rec.get("vectors", {}).get("Tint", [1.0, 1.0, 1.0])
    rec.setdefault("scalars", {})["FlattenToMean"] = flat
    rec.setdefault("vectors", {})["MeanColour"] = [round(a * b, 5) for a, b in zip(_TMEAN[tex], tint)]
    return rec


for _s, _t in (("M_DJ_TimberDark", "T_DJ_TimberDark_BC"), ("M_DJ_TimberDarkEnd", "T_DJ_TimberDarkEnd_BC"),
               ("M_DJ_TimberAged", "T_DJ_TimberAged_BC"), ("M_DJ_TimberAgedEnd", "T_DJ_TimberAgedEnd_BC")):
    LOOK[_s] = _flat_timber(copy.deepcopy(_TIMBER_R5), _t)
for _s, _t in (("M_DJS_GateTimber", "T_DJ_TimberAged_BC"), ("M_DJS_GateTimberEnd", "T_DJ_TimberAgedEnd_BC"),
               ("M_DJS_TimberMid", "T_DJ_TimberDark_BC"), ("M_DJS_TimberMidEnd", "T_DJ_TimberDarkEnd_BC"),
               ("M_DJS_TimberStand", "T_DJ_TimberDark_BC"), ("M_DJS_TimberStandEnd", "T_DJ_TimberDarkEnd_BC")):
    _flat_timber(EXTRA_MATERIALS[_s], _t)
# - Downpipes + gutters (verify_r5: left pipe median (8, 6, 6) against the sky-lit plaster): the library Iron is METAL
#   (ORM metallic 0.85), so under the eaves it mirrors the dark soffit. Their own weathered, oxide-dull mid-grey metal
#   (the Iron maps, MetallicMult 0.15, a lifted mid-grey mean); the Iron hardware elsewhere (straps, lamps) is unchanged.
EXTRA_MATERIALS["M_DJS_DownpipeMetal"] = {
    "master": "M_DJ_Lib_Opaque", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
    "textures": {"BC": "T_DJ_Iron_BC", "ORM": "T_DJ_Iron_ORM", "N": "T_DJ_Iron_N"},
    "scalars": {"RoughMult": 1.35, "NormalStrength": 1.0, "Saturation": 0.35, "ValueMult": 2.4, "FlattenToMean": 0.5,
                "MetallicMult": 0.15},
    "vectors": {"Tint": [1.0, 1.0, 1.0], "MeanColour": [0.07, 0.069, 0.07], "TileM": [2.0, 2.0, 0.0, 0.0]},
    "switches": {"UseWear": False},
    "note": "r6: downpipes and gutters, weathered oxide-dull mid-grey metal (was the bare-metal Iron, near-black in shade)"}
for _p in ("SM_DKH_Downpipe", "SM_DKO_Downpipe", "SM_DKC_Downpipe", "SM_DKO_Gutter_S", "SM_DKO_Gutter_N",
           "SM_DKO_Gutter_F"):
    ACTOR_MATERIAL_OVERRIDES[_p] = {0: "M_DJS_DownpipeMetal"}
for _p, _i in (("SM_DKH_RoofUpper_Front", 2), ("SM_DKH_RoofUpper_Back", 2), ("SM_DKH_RoofUpper_End", 2),
               ("SM_DKH_RoofLower_Front", 2), ("SM_DKH_RoofLower_SideW", 2), ("SM_DKH_RoofLower_SideE", 2),
               ("SM_DKH_RoofChidori_W", 3), ("SM_DKH_RoofChidori_E", 3), ("SM_DKO_Roof_Slope", 2),
               ("SM_DKO_Roof_SlopeNear_Store", 2), ("SM_DKO_Roof_SlopeNear_Res", 2), ("SM_DKC_Bay_Roof", 2),
               ("SM_DKC_EndWall_W_Roof", 2), ("SM_DKC_EndWall_E_Roof", 2), ("SM_DKC_EndGable_W_Roof", 2),
               ("SM_DKC_EndGable_E_Roof", 2)):
    ACTOR_MATERIAL_OVERRIDES[_p] = {_i: "M_DJS_DownpipeMetal"}   # the roofs' own eave gutters (their Iron slot)
# - Sunlit tiles (verify_r5: gate ridge onigawara 1.24-1.31, noshi 1.30-1.42, pavilion E face 1.34, E wall-cap 1.44 top
#   30 %; target R/B <= 1.2 with the shaded roofs not pushed blue (hall 0.83-0.93, ref 2 0.88)): a lower specular (the
#   warm sun's lobe on the rounded tiles), a slightly cool flatten target
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.97, 0.98, 1.0), flat=0.75, vm=1.45, sat=0.3, rough=2.0)
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.054, 0.056, 0.06]
LOOK["M_DJ_RoofTile"]["scalars"]["Specular"] = 0.3
# - The pavilion fill light (verify_r5: 5 cm above the drum top, a white hotspot of 212-342 px, read as a bulb where no
#   lamp exists): removed; the ceiling takes the timber flatten above and the GI instead
FILL_LIGHTS[:] = [f for f in FILL_LIGHTS if f[0] != "Light_Fill_PavilionCeiling"]
# - The retired round-5 f1 flat far-town instances (outside track round 6: impostor facades + kawara now): deleted from
#   DojoLab by the level step once nothing references them (the retired-asset list takes any package path)
RETIRED_MESHES.update({n: f"/Game/DojoKit/Outside/Materials/{n}" for n in (
    "M_DKX_FarRoofA", "M_DKX_FarRoofB", "M_DKX_FarWallPlaster", "M_DKX_FarWallWood")})
# - Round-6 cameras: the sealed rear alley from the courtyard side (both corridor ends) and from above, the far edge of
#   the town (the road now ends at house fronts) and the ridges to the north
CLOSEUPS.extend([
    ("CU_R6_AlleyPocketW", (12.6, 26.8, 1.7), (10.5, 33.2, 1.2), 62.0, (1920, 1080),
     "round 6: the west corridor end from the courtyard side: the new pocket fence closing the slot to the rear alley"),
    ("CU_R6_AlleyPocketE", (31.4, 26.8, 1.7), (33.5, 33.2, 1.2), 62.0, (1920, 1080),
     "round 6: the east corridor end from the courtyard side: the pocket fence (mirrored)"),
    ("CU_R6_AlleyAbove", (22.0, 46.0, 17.0), (22.0, 32.5, 0.5), 80.0, (1920, 1080),
     "round 6: the rear alley from above and behind (north): the strip, both pockets, the alley and pocket fences"),
    ("CU_R6_PocketAboveW", (4.0, 39.0, 9.0), (10.8, 32.8, 0.8), 60.0, (1920, 1080),
     "round 6: the west pocket from above: pocket fence, alley fence, the corridor end"),
    ("CU_R6_TownEdgeE", (30.0, -7.5, 2.4), (140.0, -7.5, 4.0), 60.0, (1920, 1080),
     "round 6: along the approach road to the east: the town's edge row (the road ends at house fronts), the ridges"),
    ("CU_R6_RidgesNorth", (22.0, 18.0, 13.0), (22.0, 500.0, 30.0), 75.0, (1920, 1080),
     "round 6: over the hall to the north: the far town impostors and the four jagged ridge rings, no crest strokes"),
])
# ---- round 6 it2: set on the probes unreal/round6/r6_work/probe_a..c (one offscreen editor each, every variant from
#      the saved it1 level; measure_r6.py regions)
# - Shade detail: the GI settings, not a fill. probe_a: Lumen skylight leaking 0.1 alone took the alley pockets' worst
#   4 x 4 cell 23 -> 12 %; the diffuse colour boost (the GI bounce off dark albedos) 2.0 took the gate emblem frame
#   15.3 -> 6.1 % near-black and the corridor soffit cell 29 -> 12 %; probe_c at boost 3.0 + leak 0.1: gate emblem 8 %,
#   corridor 6 %, drum 9 % worst cell. The timber flatten / AO alone moved them 1-2 points (the grooves are not the
#   crush; the unlit bounce was).
ENV["pp_extra"] = dict(ENV["pp_extra"], lumen_diffuse_color_boost=3.0, lumen_skylight_leaking=0.1)
for _s in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_s]["scalars"].update({"AOStrength": 0.15, "FlattenToMean": 0.4})
for _s in ("M_DJS_GateTimber", "M_DJS_GateTimberEnd", "M_DJS_TimberMid", "M_DJS_TimberMidEnd", "M_DJS_TimberStand",
           "M_DJS_TimberStandEnd"):
    EXTRA_MATERIALS[_s]["scalars"].update({"AOStrength": 0.15, "FlattenToMean": 0.4})   # the gate's baked-AO grooves
# - Sunlit tiles: Specular and the albedo value barely move them (probe_a V4-V6: +-0.03); the tile instance's
#   Saturation 0.3 was washing every tint out. At Saturation 1.0 the flatten target sets the albedo hue: probe_b T1
#   (albedo R/B 0.84) sunlit pavilion 1.15 / E wall cap 1.22 / gate ridge 1.10-1.16, shade 0.81; T2 (0.71) 1.06 / 1.11 /
#   1.04-1.06, shade 0.74. Between them: all sunlit tiles <= 1.2 with the shaded hall roofs ~0.8 (ref 2 0.88). The low
#   sun is warm, so a dark slate tile must be slightly cool to read neutral in it (and slightly blue in shade).
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.92, 0.975, 1.05), flat=0.75, vm=1.45, sat=1.0, rough=2.0)
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.05, 0.056, 0.064]
LOOK["M_DJ_RoofTile"]["scalars"].update({"Specular": 0.3, "AOStrength": 0.5})
# - Gravel it1 (152, 131, 119) R/B 1.28 s 0.22 (ref 1 / 2: R/B 1.31-1.48, s 0.23-0.32, value 122-153): a notch warmer
#   and darker (the GI boost lifts it ~8 %)
LOOK["M_DKG_Gravel"] = {"scalars": {"Saturation": 1.0, "ValueMult": 0.88, "Tile cm": 200.0},
                        "vectors": {"Tint": [1.08, 0.96, 0.8]}}
LOOK["M_DKG_GravelCoarse"] = {"scalars": {"Saturation": 1.0, "ValueMult": 1.1, "Tile cm": 200.0},
                              "vectors": {"Tint": [1.08, 0.96, 0.8]}}
# - Far town kawara (it1 CU_R5_FarBackground: a few far roofs flash white at grazing angles): no sky sheen
LOOK["M_DKX_FarKawara"] = {"scalars": {"Specular": 0.15, "RoughMult": 1.6}}
# - Taiko lacquer: its shaded underside sat under 12 in G / B (the drum cameras' last near-black cells): the oxblood mean
#   a little out of the toe, same hue
LOOK["M_DKP_Taiko_Lacquer"]["vectors"]["MeanColour"] = [0.072, 0.026, 0.021]
# ---- round 6 it3 (it2 measured: 2 stills left with a 4 x 4 cell over 10 % near-black: CU_Lantern 13.2 % = the void
#      under the veranda deck (true shade), CU_Taiko 11.1 % = the shaded wall-cap tile gaps + the dark stand; gravel
#      (161, 137, 120) R/B 1.28-1.34 s 0.22-0.26)
LOOK["M_DJ_RoofTile"]["scalars"]["AOStrength"] = 0.3
for _s in ("M_DJS_TimberStand", "M_DJS_TimberStandEnd"):
    EXTRA_MATERIALS[_s]["scalars"]["ValueMult"] = 1.2
for _s in ("M_DKG_Gravel", "M_DKG_GravelCoarse"):
    LOOK[_s]["vectors"]["Tint"] = [1.1, 0.95, 0.77]
LOOK["M_DKG_Gravel"]["scalars"]["ValueMult"] = 0.84
LOOK["M_DKG_GravelCoarse"]["scalars"]["ValueMult"] = 1.05


# ================================================================================================ ROUND 6 FIX f1
# 2026-09-30, the round-6 judge (7 / 10) and verifier (gravel hue) after the round-6 import. Every value is measured on
# unreal/round6/f1_work/it* (final stills unreal/round6/f1/). Blender side (outside track): ridges 40 % lower, the far
# town in three distance bands (M_DKX_Far*Mid / *Far, darker and greyer), per-block yaw / pitch variety.
# - Reference-2 framing (judge blocker 1 + delta 6: 'the hall sits against a dense band of dark town roofs with low hills
#   just above them'; 'raise the camera and widen the FOV'). Workbench studies (f1_work/wb/grid1-2.png): from any eye
#   under the gate roof (<= 3.1 m) the hall and the outbuildings hide the whole town; the town roofs and the ridges show
#   between the hall hips and the outbuilding gables from about 5.5 m up, as in ref 2 (whose camera sits well above the
#   gate: the image is not physically consistent with a real gate roof). CAM_Ref2Match: 7.5 m over the gate's street
#   side, the gate roof's ridge across the bottom as ref 2's threshold band; CAM_EstablishingRef2 just inside at 6.8 m.
CLOSEUPS[:] = [c for c in CLOSEUPS if c[0] not in ("CAM_Ref2Match", "CAM_EstablishingRef2")] + [
    ("CAM_Ref2Match", (22.0, -2.0, 7.5), (22.0, 26.0, 0.0), 84.0, (1448, 1086),
     "round 6 f1: the reference-2 framing, raised to ref 2's horizon (7.5 m over the gate, its roof ridge across the "
     "bottom as the reference's threshold band): the hall about half the width, both training yards, the corridors, the "
     "town roofs and the hills between the hall hips and the outbuilding gables"),
    ("CAM_EstablishingRef2", (22.0, 1.0, 6.8), (22.0, 26.0, 0.0), 80.0, (1448, 1086),
     "round 6 f1: the elevated establishing view just inside the gate (6.8 m): hall, corridors, outbuildings and the "
     "town / ridge band behind them")]
# - Roof tiles (judge delta 1: in sun / sky light the tile reads slate BLUE, CAM_Overview hall roof (64, 71, 95) hue 226
#   s 0.20; ref 1 (57, 56, 68) hue 245 s 0.09, ref 2 (66, 62, 70) s 0.06). The azure hue came from G > R in the flatten
#   target and tint (G / R 1.19); the value was 10-15 % high. Neutral charcoal with a faint violet cast, R = G, a
#   little darker; the R / B ratio (which sets the sunlit R/B <= 1.2 gate) is kept close to the r6 value.
LOOK["M_DJ_RoofTile"] = _tile(tint=(0.95, 0.94, 1.0), flat=0.8, vm=1.3, sat=1.0, rough=2.0)
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.047, 0.046, 0.058]
LOOK["M_DJ_RoofTile"]["scalars"].update({"Specular": 0.3, "AOStrength": 0.3})
# - Courtyard gravel (verifier: shaded gravel 16.6-24 deg against a 25-40 deg band; the references themselves measure
#   13-18 deg, so the band is replaced by the references (13-30 deg, R/B >= 1.2, s >= 0.15), see BUILD_NOTES. Judge
#   delta 4: the gravel reads warm tan sand (176, 144, 122) s 0.25 with a uniform fine grain; ref 2 (150, 119, 107)
#   s 0.17 with individual stones): greyer, a notch darker, bigger stones (tile 2 m -> 2.8 m). The alley reads
#   red-brown (103, 73, 64) only through the warm bounce on the warmer gravel: the same material, so it follows.
for _s, _vm in (("M_DKG_Gravel", 0.8), ("M_DKG_GravelCoarse", 1.0)):
    LOOK[_s] = {"scalars": {"Saturation": 0.72, "ValueMult": _vm, "Tile cm": 280.0},
                "vectors": {"Tint": [1.06, 0.96, 0.86]}}
# - Raked sand (judge delta 3: coarse even corrugations, 'ribbed metal' at eye level; the gate view too saturated,
#   CAM_Ref2Match s 0.43 against ref 2 s 0.32): the rake lines at half the spacing (UV Scale 2 on the field's UV0) and
#   the rake normal weaker everywhere: NormalFade from -30 m to 25 m depth gives about 65 % strength at the feet, 53 % at
#   10 m and 35 % from 25 m (N = lerp(N, flat, fade x (1 - far))); a little less chroma
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s] = {"scalars": {"ValueMult": 0.75, "Saturation": 0.8, "NormalFarStrength": 0.35, "NormalFadeStart": -3000.0,
                            "NormalFadeEnd": 2500.0},
                "vectors": {"Tint": [1.0, 0.8, 0.7]}}
LOOK["M_DKG_SandRaked"]["scalars"]["UV Scale"] = 2.0
# - Town ground (judge blocker 2: the streets and open lots read pale grey-pink (138, 125, 127), 'snow', against
#   ref 1's street (77, 75, 87)): about 40 % darker, and the lots paved in the road's cobble set (larger, dirtier macro)
#   so they break up instead of reading as a flat plane
EXTRA_MATERIALS["M_DJS_TownYard"].update({
    "textures": {"Base Colour Map": "T_DKX_Cobble_BC", "ORM Map": "T_DKX_Cobble_ORM", "Normal Map": "T_DKX_Cobble_N",
                 "Macro Map": "T_DKG_Macro_M"},
    "scalars": {"Tile cm": 330.0, "Macro Tint": 0.35, "Macro Dirt": 0.45, "Macro Rough": 0.1, "Saturation": 0.5,
                "ValueMult": 0.52},
    "vectors": {"Tint": [1.0, 0.97, 0.98]},
    "note": "r6 f1: the town's yards and lots: dark worn cobble paving (ref 1's dark low-contrast town), not pale gravel"})
LOOK["M_DKX_RoadCobble"] = {"scalars": {"Tile cm": 240.0, "Macro Tint": 0.3, "Macro Dirt": 0.35, "Macro Rough": 0.12,
                                        "Saturation": 0.6, "ValueMult": 0.6},
                            "vectors": {"Tint": [1.0, 0.98, 0.98]}}
# - Ridges (judge delta 2: four stacked flat cards, too tall (Blender: 40 % lower), the nearest too dark against the
#   haze, a hard glow step toward the sun): the ladder compressed toward the haze (ring 1 lifted most) and the fog's sun
#   lobe wider and weaker (exponent 6 -> 3) so the glow falls off smoothly
for _k, _e in (("M_DKX_Ridge1", (7.8, 8.2, 10.6)), ("M_DKX_Ridge2", (9.4, 9.7, 12.4)),
               ("M_DKX_Ridge3", (11.0, 11.0, 13.8)), ("M_DKX_Ridge4", (13.0, 12.8, 16.4))):
    LOOK[_k] = {"vectors": {"Emissive Colour": list(_e)}}
ENV["fog"] = dict(ENV["fog"], directional_inscattering_luminance=[1.5, 0.9, 0.45], directional_inscattering_exponent=3.0)
# - Shadows (judge delta 5: soft, low contrast; props do not sit on the ground): a smaller sun disc (0.53 -> 0.3 deg)
#   for crisper edges and screen-space contact shadows for the small props' contact
ENV["sun_extra"] = dict(ENV.get("sun_extra", {}), light_source_angle=0.3, contact_shadow_length=0.04)
# ---- round 6 fix f1 it2 (it1 measured, f1_work/it1/measure_f1.json): the gravel overshot grey-pink in shade (Overview
#      hall front (147, 131, 129) h 7, R/B 1.14; the refs 13-18 deg, R/B >= 1.3): back toward warm, still greyer than r6
#      (158, 133, 117); the town lots under ref 1's street (60, 53, 56) L 0.22 vs (77, 75, 87) L 0.32: a notch lighter and
#      cooler; CAM_Ref2Match: over the gate ridge (its tile rolls filled the lower fifth of it1)
for _s, _vm in (("M_DKG_Gravel", 0.8), ("M_DKG_GravelCoarse", 1.0)):
    LOOK[_s] = {"scalars": {"Saturation": 0.9, "ValueMult": _vm, "Tile cm": 280.0},
                "vectors": {"Tint": [1.08, 0.955, 0.8]}}
EXTRA_MATERIALS["M_DJS_TownYard"]["scalars"]["ValueMult"] = 0.68
EXTRA_MATERIALS["M_DJS_TownYard"]["vectors"]["Tint"] = [0.97, 0.97, 1.0]
LOOK["M_DKX_RoadCobble"]["scalars"]["ValueMult"] = 0.66
CLOSEUPS[:] = [c for c in CLOSEUPS if c[0] != "CAM_Ref2Match"] + [
    ("CAM_Ref2Match", (22.0, -0.3, 7.3), (22.0, 26.0, 0.0), 84.0, (1448, 1086),
     "round 6 f1: the reference-2 framing, raised to ref 2's horizon (7.3 m over the gate ridge, the gate roof itself "
     "below the frame): the hall about half the width, both training yards, the corridors, the town roofs and the hills "
     "between the hall hips and the outbuilding gables")]
# ---- round 6 fix f1 it3 (probe f1_work/probe_a, variants from the it2 level): a warm sky-light tint (V1 / V2 / V4)
#      neutralises the shaded tiles (Overview R/B 0.68 -> 0.89 / 1.00) but the backlit scene is sky-lit almost
#      everywhere, so every 'sunlit' tile box rose with it (gate 1.14 -> 1.35 / 1.47, over the <= 1.2 gate) and the
#      gravel / sand went orange (R/B 1.5-1.8): rejected. Lumen colour boost 2.0 (V3) added a near-black corridor cell and
#      left the alley bounce red. Kept: the neutral tile albedo (hue 226 -> 238-243, HLS s 0.20 -> 0.16, L 0.25-0.31
#      against ref 1 0.24), with B a hair up for the E wall cap (lit30 1.22 -> <= 1.2) and the value a notch back (the
#      darker tile took CU_Taiko's wall-cap crease cell 11 -> 15 % near-black). The sand's chroma back to r6 (the raised
#      CAM_Ref2Match now reads s 0.21 against ref 2's 0.32; the Overview matched ref 1 at r6); the town lots and lanes
#      toward ref 1's street (77, 75, 87) (it2: (63, 55, 59) L 0.23, too dark)
LOOK["M_DJ_RoofTile"]["scalars"]["ValueMult"] = 1.4
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.046, 0.045, 0.059]
for _s in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_s]["scalars"]["Saturation"] = 0.9
    LOOK[_s]["vectors"]["Tint"] = [1.0, 0.78, 0.66]
EXTRA_MATERIALS["M_DJS_TownYard"]["scalars"]["ValueMult"] = 0.88
EXTRA_MATERIALS["M_DJS_TownYard"]["vectors"]["Tint"] = [0.95, 0.96, 1.02]
LOOK["M_DKX_RoadCobble"]["scalars"]["ValueMult"] = 0.8
LOOK["M_DKX_RoadCobble"]["vectors"]["Tint"] = [0.97, 0.97, 1.0]
# ---- round 6 fix f1 it4 (it3 measured): the gravel's eye-level shade boxes still R/B 1.14-1.18 (ref 1 hall front 1.36,
#      ref 2 >= 1.3) and CU_Training (172, 144, 127) lighter than ref 2's (150, 119, 107): a notch warmer and darker; the
#      sunlit town lots in CU_R5_FarBackground only 18 % under r6 ((130, 111, 106) -> (106, 93, 95); the judge: ~40 %)
for _s, _vm in (("M_DKG_Gravel", 0.74), ("M_DKG_GravelCoarse", 0.94)):
    LOOK[_s]["scalars"]["ValueMult"] = _vm
    LOOK[_s]["vectors"]["Tint"] = [1.1, 0.95, 0.78]
EXTRA_MATERIALS["M_DJS_TownYard"]["scalars"]["ValueMult"] = 0.74
LOOK["M_DKX_RoadCobble"]["scalars"]["ValueMult"] = 0.7
# ---- round 6 fix f1 final (probe f1_work/probe_b on the it4 level): a lower sky light (8 / 7) crisps the shade but takes
#      the sunlit E wall cap to R/B 1.25 / 1.29 (over 1.2) and CU_Taiko's crease cell to 16 / 18 % near-black: kept at 9.
#      The gravel a last notch warmer (eye-level foreground boxes R/B 1.15-1.19); the tiles' baked AO a little weaker
#      (CU_Taiko's shaded wall-cap tile creases 11 -> 14 % near-black after the darker tile)
for _s in ("M_DKG_Gravel", "M_DKG_GravelCoarse"):
    LOOK[_s]["vectors"]["Tint"] = [1.12, 0.95, 0.76]
LOOK["M_DJ_RoofTile"]["scalars"]["AOStrength"] = 0.2


# ================================================================================================ ROUND 8
# 2026-09-30, Ultra Dynamic Sky (the user's owned copy, file-copied from DemoGame_1 into DojoLab/Content/UltraDynamicSky)
# + the research's GAMEPLAY preset (WorkFiles/dojo/CINEMATIC_LOOK_RESEARCH.md 5.1). UDS replaces our DirectionalLight,
# SkyAtmosphere, SkyLight, ExponentialHeightFog, VolumetricCloud and the painted sky dome: dj_sc_level spawns the UDS
# actor instead of those six when ENV["uds"] is set (the round-6 f1 values above stay as the record and the fallback:
# delete this section to restore them). The material-instance values above are kept.
# - UDS sun, measured (round8/s1_work/probe/uds_probe1.json): the non-simulated sun path peaks at 60 deg, so its
#   elevation is asin(sin 60 x sin(90 x (Dusk - t) / (Dusk - Dawn) x 2)): 12.95 deg at 60 min before Dusk (20-40 min
#   gives only 4.3-8.6 deg); its azimuth (from the sun, UE frame) is Sun Yaw - 97.63 deg at that time. Sun Yaw 332.63 puts
#   the sun at 125 deg from +X in the Blender frame: behind-left of the hall from the gate, round 5 / 6's azimuth.
ENV["uds"] = {
    "class": "/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky",
    "loc_m": (22.0, 18.0, 0.0),      # ground level (courtyard floor Z 0); cloud height by Bottom Altitude, never Z
    "props": {                       # UDS actor variables, set in this order (time last)
        "Project Mode": {"enum": "UDS_Project_Mode.GAME_REAL_TIME_NON_VR"},
        "Sky Mode": {"enum": "UDS_SkyMode.VOLUMETRIC_CLOUDS"},
        "Volumetric Cloud Rendering Mode": {"enum": "UDS_VolRT_Mode.FIDELITY_PERFORMANCE"},
        "Color Mode": {"enum": "UDS_ColorMode.SKY_ATMOSPHERE"},
        "Sky Light Mode": {"enum": "UDS_SkyLightMode.CAPTURE_BASED"},
        "Apply Exposure Settings": False,          # ONE exposure owner: our PPV (manual), see "exposure" below
        "Half Rate Tick": True,
        "Use Volumetric Fog": True,
        "Cloud Coverage": 3.0,                     # scattered-to-broken (UDS default 3.8)
        "Cloud Speed": 0.2,
        "Randomize Cloud Formation on Run": False,
        "Clouds Move with Time of Day": False,
        "Sun Source Angle Scale": 0.53,            # UDS default 1.0 -> a 1.0 deg disc; the real sun is 0.53
        "Simulate Real Sun": False,
        "Manually Position Sun Target": False,
        "Animate Time of Day": False,              # locked sunset
        "Dawn Time": 600.0,
        "Dusk Time": 1800.0,
        "Sun Yaw": 332.63,
        "Time of Day": 1700.0,
    },
    "sun": {"contact_shadow_length": 0.02},        # on UDS's Sun component (research 2.3: 0-0.02)
    "ppv_priority": 10.0,                          # our PPV's fields win over UDS's own post-process components
}
ENV.update({"sun_elev_deg": 12.952, "sun_azimuth_deg_from_x": 125.0})   # the layout sun record = the UDS sun (measured)
ENV["sky_dome"] = None
ENV["clouds"] = None
ENV["sun_extra"] = {}      # the round-5 sun GI bounce x4 (indirect_lighting_intensity 4.0) goes with our sun
ENV["skylight_extra"] = {}
ENV["sky_atmosphere"] = {}
ENV["fog"] = {}
# - The fill lights existed only to fight near-black: removed (the verify count follows the layout)
FILL_LIGHTS[:] = []
# - Gameplay preset, PPV (research 5.1), reverting the five shadow-lifting overrides: tone curve Toe back to 0.55 (was
#   0.28), local-exposure shadow contrast 0.9 (was 0.5), Lumen diffuse colour boost 1.0 (was 3.0), skylight leaking 0 (was
#   0.1); the sun's source angle (was 0.3) is the UDS scale above
ENV["pp_extra"] = {
    "lumen_final_gather_quality": 1.0, "lumen_scene_lighting_quality": 1.0, "lumen_scene_detail": 1.0,
    "lumen_final_gather_lighting_update_speed": 1.0,
    "lumen_diffuse_color_boost": 1.0, "lumen_skylight_leaking": 0.0,
    "lumen_ray_lighting_mode": {"enum": "LumenRayLightingModeOverride.SURFACE_CACHE"},
    "local_exposure_shadow_contrast_scale": 0.9, "local_exposure_highlight_contrast_scale": 0.8,
    "local_exposure_detail_strength": 1.0,
    "motion_blur_amount": 0.3, "motion_blur_max": 2.5,
    "lens_flare_intensity": 0.0, "scene_fringe_intensity": 0.0,
}
ENV["grade_extra"] = {"film_toe": 0.55, "film_slope": 0.88, "film_shoulder": 0.26, "film_black_clip": 0.0,
                      "film_white_clip": 0.04, "film_grain_intensity": 0.0, "vignette_intensity": 0.42,
                      "bloom_intensity": 0.5}
# - Exposure (one owner: this PPV, manual). exposure_ev_ref = the round-6 f1 bias (layout -6.0439 + 2.0); the lamps
#   (candela) and every EmissiveIntensity are multiplied by 2^-(bias - ref) so they keep their look against the new
#   exposure (dj_sc_common LAMP_SCALE / EMISSIVE_SCALE)
ENV["exposure"] = {"owner": "ppv_manual", "bias_ev": 2.35, "ev_ref": -4.0439}
# ---- round 8 it2 (the -game probes round8/s1_work/probe_t..g, UDS variables set at runtime on CAM_Ref2Match, measured
#      against dojo1_reference2 with measure_r8.py):
# - At 10-14 deg UDS's physical sky stays a pale blue-white afternoon (horizon behind the hall R/B 1.06-1.12, ref 2 1.59)
#   whatever the sky knobs do (Saturation 1.4, Mie x3, Rayleigh x2 and the sunset absorption scale x3-7 all tested: the
#   absorption turned the whole scene violet). The sunset palette (orange-lit cloud undersides, warm horizon, the
#   courtyard in soft shade with rim light on the ridges, glowing shoji / lanterns) appears at 4-6 deg. UDS Time of Day is
#   hours x 100 (1760 = 17:36): measured sun elevation 12.95 deg at 1700 (60 min before Dusk 1800), 11.02 at 1715, 7.79 at
#   1740, 5.19 at 1760 (24 min before Dusk, inside the brief's 20-40 min), 3.90 at 1770. Chosen: 1760 = 5.19 deg. Sun Yaw
#   305 puts the sun at 148 deg from +X, just outside the reference camera's left edge (behind-left of the hall; the
#   125 deg sun showed its disc in frame). (The round-8 header's 'asin(sin 60 ...)' path model is superseded by these
#   measurements.)
ENV["uds"]["props"].update({"Time of Day": 1760.0, "Sun Yaw": 305.0})
ENV.update({"sun_elev_deg": 5.19, "sun_azimuth_deg_from_x": 148.01})
# - Dusk light vs the sky (UDS 'Lighting Brightness (Dawn/Dusk)' scales the sun and sky light, not the sky): at 1 the
#   ground sat ~2 EV under the sky (sand (59, 39, 25) under a (173, 150, 133) horizon); at 4 the histogram lands on ref 2
#   (12.7 % under luma 40 against 13.7 %) with the exposure unchanged. The dusk sky light tinted cooler (the captured
#   orange sky tinted every shade red: tiles R/B 1.62 -> 1.30-1.39 in shade, gravel 1.74 -> 1.38 against ref 1.43).
ENV["uds"]["props"] = dict(ENV["uds"]["props"], **{"Lighting Brightness (Dawn/Dusk)": 4.0,
                                                   "Sky Light Color Multiplier (Dawn/Dusk)": [0.75, 0.88, 1.25]})
_t = ENV["uds"]["props"].pop("Time of Day")             # keep the time last (every set re-runs the construction script)
ENV["uds"]["props"]["Time of Day"] = _t
# - Far ridges: emissive haze cards; under the dusk sky they read (184, 183, 195) against the sky above (~150): ref 2's
#   hills sit about half the sky's brightness ((109, 99, 113) / (60, 66, 84)). x 0.25 on the ladder.
for _k in ("M_DKX_Ridge1", "M_DKX_Ridge2", "M_DKX_Ridge3", "M_DKX_Ridge4"):
    LOOK[_k] = {"vectors": {"Emissive Colour": [round(c * 0.25, 4) for c in LOOK[_k]["vectors"]["Emissive Colour"]]}}
# - Small corrections for the new light (instance values): the shaded kawara read warm red-brown under the dusk sky light
#   (R/B 1.39, ref 2 0.96): a cooler flatten target and tint; the shoji paper read pale cream (218, 183, 145) against ref
#   2's deep amber (182, 118, 53): a more saturated tint, same intensity
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.9, 0.95, 1.06]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.041, 0.044, 0.063]
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 62.0, "Saturation": 0.85},
                           "vectors": {"EmissiveTint": [1.0, 0.78, 0.48]}}
# ================================================================================================ ROUND 8 s2 (retune)
# 2026-09-30, from the s1 judge (5/10): the key light was inverted (the sun behind-left of the hall put the sand, the hall
# front and the gables in shade: a blue-hour read) and the rake had no relief. -game probes round8/s2_work/probe_a..e
# (UDS variables set at runtime on CAM_Ref2Match / CAM_Establishing / CAM_Overview, measured with measure_r8.py):
# - Sun: at 5.2 deg the 2-3 m courtyard walls and the gatehouse shade most of the sand from any yaw (probe a: a01/a02);
#   from 10.4 deg (1720) the sand takes the sun. Sun Yaw 268 at 1730 = 9.08 deg elevation, 187.29 deg from +X (Blender):
#   from the west, 7 deg south of the hall's face line, so the sand rakes from the left with the west-yard shadows
#   streaming across its left field and the hall's south face takes a grazing light (ref 2's key). Yaw 255 (200 deg)
#   dropped the gatehouse shadow over the path (c3); 1740 / 7.8 deg shaded the near field (c4).
# - Sky at 9 deg: the physical sky is a pale blue daytime sky; the flattened Rayleigh colour (0.45, 0.38, 0.52) turns the
#   upper sky mauve-grey (top sky (162, 141, 142) against ref 2's (166, 147, 148)); UDS fog colour logic (Fog Color Mode
#   UDS Fog Settings) with a warm All Fog Colors Multiplier and Fog 2.2 lays a peach haze band on the horizon and the far
#   ridges (the aerial perspective the judge asked for). The absorption knobs stay default (they turned it violet in s1).
# - Clouds: coverage 2.6 with a flat thin layer (Layer Height Scale 0.35) at 2.5x scale gives layered stratus streaks
#   (probe c2) instead of scattered cumulus puffs; wisps up (the high streaks, tinted by UDS's dawn/dusk wisps tint).
# - Sun colour: Sun Light Color (1.0, 0.86, 0.84) takes the saturated yellow toward peach-pink (judge delta 10).
ENV["uds"]["props"].update({
    "Sun Yaw": 268.0,
    "Cloud Coverage": 2.6, "Layer Height Scale": 0.35, "Volumetric Clouds Scale": 2.5,
    "Cloud Wisps Opacity (Clear)": 1.0, "Cloud Wisps Color Intensity": 3.0,
    "Rayleigh Scattering Color (Dawn/Dusk)": [0.45, 0.38, 0.52],
    "Fog Color Mode": {"enum": "UDS_FogColorMode.UDS_FOG_SETTINGS"},
    "All Fog Colors Multiplier": [3.2, 1.7, 0.75],
    "Fog": 2.2,
    "Sun Light Color": [1.0, 0.86, 0.84],
    "Time of Day": 1730.0,
})
_t = ENV["uds"]["props"].pop("Time of Day")             # keep the time last
ENV["uds"]["props"]["Time of Day"] = _t
ENV.update({"sun_elev_deg": 9.08, "sun_azimuth_deg_from_x": 187.29})
# - Exposure: with the sand sunlit the frame sat ~0.45 EV over ref 2 (luma mean 134 against 108): bias 2.35 -> 1.9. The
#   lamps and emissives follow the bias (dj_sc_common), so they read ~1.37x hotter against the darker scene.
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.9)
# - Sand: in the sun it read salmon-orange (s 0.47-0.62 against ref 2's cream s 0.28): a cream tint, less saturation; the
#   rake normal keeps more of its strength with distance (far 0.35 -> 0.75, fade from 15 m to 50 m; the edge strip keeps
#   the round-3 moire guard).
LOOK["M_DKG_SandRaked"] = {"scalars": dict(LOOK["M_DKG_SandRaked"]["scalars"], **{
    "ValueMult": 0.78, "Saturation": 0.5, "NormalFarStrength": 0.75, "NormalFadeStart": 1500.0, "NormalFadeEnd": 5000.0}),
    "vectors": {"Tint": [1.0, 0.9, 0.82]}}
LOOK["M_DKG_SandEdge"] = {"scalars": dict(LOOK["M_DKG_SandEdge"]["scalars"], **{"ValueMult": 0.78, "Saturation": 0.5}),
                          "vectors": {"Tint": [1.0, 0.9, 0.82]}}
# - Kawara: sunlit tiles read warm (R/B 1.41 against 0.97): a cooler tint
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.85, 0.93, 1.12]
# - Plaster / gravel about 0.5 EV under ref 2 relative to the sand: value up, plaster less saturated
LOOK["M_DJ_PlasterCream"] = {"scalars": dict(LOOK["M_DJ_PlasterCream"]["scalars"], ValueMult=1.2, Saturation=0.38),
                             "vectors": dict(LOOK["M_DJ_PlasterCream"]["vectors"])}
for _k, _v in (("M_DKG_Gravel", 0.95), ("M_DKG_GravelCoarse", 1.15)):
    LOOK[_k] = {"scalars": dict(LOOK[_k]["scalars"], ValueMult=_v), "vectors": dict(LOOK[_k]["vectors"])}
# - Timber: the sunlit veranda read (142-166) against ref 2's dark amber (75, 49, 30): value 3.0 -> 2.2
for _k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_k] = {"scalars": dict(LOOK[_k]["scalars"], ValueMult=2.2), "vectors": dict(LOOK[_k]["vectors"])}
# - Shoji: deeper amber, a touch lower (judge delta 9: R/B 1.82 against 3.43); lantern glass hotter and deeper (delta 8)
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 55.0, "Saturation": 1.0},
                           "vectors": {"EmissiveTint": [1.0, 0.64, 0.28]}}
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 85.0, "Saturation": 0.9},
                           "vectors": {"EmissiveTint": [1.0, 0.72, 0.36]}}
# - Lamps (delta 8 / 12): the toro 1.5x with a 10 m radius (visible pools on the gravel), the gate lamps 0.7 -> 1.1x, 12 m
LAMP_TUNE["SM_DK_Gate_Lamp"] = {"kelvin": 3300, "candela_mult": 1.1, "radius_m": 12.0}
LAMP_TUNE["SM_DKP_Stone_LanternTall"] = {"candela_mult": 1.5, "radius_m": 10.0}
# - Far ridges: warm mauve instead of lavender (ref 2's hills (109, 99, 113)), same value ladder
for _k in ("M_DKX_Ridge1", "M_DKX_Ridge2", "M_DKX_Ridge3", "M_DKX_Ridge4"):
    _c = LOOK[_k]["vectors"]["Emissive Colour"]
    LOOK[_k] = {"vectors": {"Emissive Colour": [round(_c[0] * 1.12, 4), round(_c[1], 4), round(_c[2] * 0.86, 4)]}}
# ---- round 8 s2 it2 (s2_work/it1 + probe_f measured on CAM_Ref2Match against ref 2):
# - it1 read warm everywhere: plaster R/B 1.98 (ref 1.40), gravel 2.04 (1.43), tiles lit / shade 1.50 / 1.38 (0.97 / 0.96).
#   The fog is not the cause (Fog 1.4 and a 50 m fog start changed < 0.05); it is the orange 9 deg sun on warm albedos and the
#   sky light captured from the warm sky. The sun is taken back toward a neutral peach (Sun Light Color (0.94, 0.92, 1.06)),
#   the dusk sky light cooler, the plaster / gravel / tile albedos neutralised; a stronger warm fog tint for the horizon
#   band (probe f3: R/B 1.33 -> 1.38). Exposure -0.3 EV (probe f5: mean 121.7 -> 109.4, ref 107.9).
ENV["uds"]["props"].update({"Sun Light Color": [0.94, 0.92, 1.06],
                            "Sky Light Color Multiplier (Dawn/Dusk)": [0.62, 0.8, 1.45],
                            "All Fog Colors Multiplier": [3.6, 1.8, 0.7]})
_t = ENV["uds"]["props"].pop("Time of Day")
ENV["uds"]["props"]["Time of Day"] = _t
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.6)
LOOK["M_DJ_PlasterCream"]["scalars"].update({"Saturation": 0.22})
LOOK["M_DJ_PlasterCream"]["vectors"]["Tint"] = [0.97, 0.96, 1.0]
for _k in ("M_DKG_Gravel", "M_DKG_GravelCoarse"):
    LOOK[_k]["scalars"]["Saturation"] = 0.7
    LOOK[_k]["vectors"]["Tint"] = [1.02, 0.96, 0.9]
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.8, 0.92, 1.18]
for _k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_k]["scalars"]["ValueMult"] = 1.5
LOOK["M_DJ_GlassAmber"]["vectors"]["EmissiveTint"] = [1.0, 0.62, 0.25]
# - Rake relief (judge blocker 2: high-pass std 4.8 against ref 2's 11.7): the round-6 half spacing (UV Scale 2, 4.8 cm)
#   averages out in the mips beyond ~10 m; back to the spec's 9.5 cm lines (UV Scale 1, ref 2 shows ~the spec's line
#   count), the normal at full strength to 20 m and 70 % beyond 30 m (the grazing sun now reads the grooves)
LOOK["M_DKG_SandRaked"]["scalars"].update({"UV Scale": 1.0, "NormalFadeStart": 2000.0, "NormalFadeEnd": 3000.0,
                                           "NormalFarStrength": 0.7})
# ---- round 8 s2 it3 (s2_work/it2 + probe_g): the horizon band follows the fog tint (All Fog Colors Multiplier (5, 2.2,
#   0.6): horizon R/B 1.30 -> 1.42, but hue 36 = yellow against ref 2's 18 = peach): a redder tint (5.0, 1.6, 0.75). Sun
#   yaw kept (262 / 258 put the gatehouse / shed shadow over the near field, g1 / g2). The south gables (plaster (85, 63,
#   58) against (148, 117, 106)) and the side-yard gravel ((85, 61, 60) against (136, 106, 95)) take only grazing sun at
#   187 deg: value up on the albedo; the lit kawara (75 against 91, R/B 1.21) a little brighter and cooler; the sand a
#   little brighter (near 154 against 182); the lantern glass deeper amber (R/B 2.0 against 2.68).
ENV["uds"]["props"].update({"All Fog Colors Multiplier": [5.0, 1.6, 0.75]})
_t = ENV["uds"]["props"].pop("Time of Day")
ENV["uds"]["props"]["Time of Day"] = _t
LOOK["M_DJ_PlasterCream"]["scalars"]["ValueMult"] = 1.5
LOOK["M_DKG_Gravel"]["scalars"]["ValueMult"] = 1.3
LOOK["M_DKG_GravelCoarse"]["scalars"]["ValueMult"] = 1.45
for _k in ("M_DKG_Gravel", "M_DKG_GravelCoarse"):
    LOOK[_k]["vectors"]["Tint"] = [1.04, 0.96, 0.86]
LOOK["M_DJ_RoofTile"]["scalars"]["ValueMult"] = 1.6
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.76, 0.9, 1.22]
for _k in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_k]["scalars"]["ValueMult"] = 0.88
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 95.0, "Saturation": 1.0},
                           "vectors": {"EmissiveTint": [1.0, 0.55, 0.18]}}
# ---- round 8 s2 it4 (it3 + probe_h): it3 read pink-lilac: the mauve sky (the flattened Rayleigh) captured into the sky
#   light put magenta in every shade (tiles shade hue 318, s 0.20 against ref 2's neutral (43, 39, 45)); the green of
#   the dusk sky-light multiplier up (probe h1: hue 318 -> 324, lit tiles hue 350 -> 0) and further; the sun colour a
#   touch less blue (a warmer sun (1, 0.96, 0.94) overshot to R/B 1.4-1.8, h2); the sand albedo a little more yellow
#   (it3 sand h22 against 24); exposure -0.1 EV (it3 mean 115.6 against 107.9).
ENV["uds"]["props"].update({"Sky Light Color Multiplier (Dawn/Dusk)": [0.6, 1.25, 1.5],
                            "Sun Light Color": [0.96, 0.94, 1.0]})
_t = ENV["uds"]["props"].pop("Time of Day")
ENV["uds"]["props"]["Time of Day"] = _t
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.5)
for _k in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_k]["vectors"]["Tint"] = [1.0, 0.92, 0.8]
# ================================================================================================ ROUND 9
# 2026-09-30, the round-8 s2 judges (5.5 / 10) and the owner's decision: the sun STAYS at 9.08 deg from the west (Time of
# Day 1730, Sun Yaw 268 unchanged, the sand stays lit). -game probes round9/s1_work/probe_a..i (UDS variables, PPV fields,
# MIDs and lamps set at runtime on CAM_Ref2Match / CAM_Establishing, measured with measure_r8.py + extra_r9.py against
# dojo1_reference2). Every value below was chosen on those numbers:
# - Gate / wall shadow (sand lit / shade 1.53, ref 2 1.12): a softer sun disc (Sun Source Angle Scale 0.53 -> 3.0 deg:
#   ~1.5 m penumbrae at 30 m, probe a1) and more sky fill against a weaker sun (Sky Light Intensity 1 -> 2.8, Sun Light
#   Intensity 5 -> 4; probe g/i: 1.26-1.28). The shadow length is the owner's 9 deg: no yaw lights the yard without the
#   west wall's 16 m shadow (round 8 s2 probes).
# - Sky: the flat pink haze read posterised (unique colours 5.4k, zero-gradient 26.5 % in the sky band; ref 2 30k / 6.5 %).
#   r.Tonemapper.GrainQuantization does not exist in 5.8 (the -game read-back fails), so the dither is the film grain
#   (0.1: zero-gradient 26 -> 5 %), and the sky gets real cloud structure: Contrast 0.1 -> 0.6, Cloud Coverage 3.2 -> 3.6,
#   High Frequency Noise 0.24 -> 0.5, warm-rimmed cloud light (1, 0.55, 0.3), a violet-grey cloud ambient and dark colour
#   (probe g2 / h4: 24-33k unique colours). The height fog carried a red cast over the whole scene (tiles, plaster, gravel
#   R/B 1.6-1.9): a steeper fog falloff (0.065 -> 0.2) keeps the fog at the horizon, where a stronger red fog tint
#   (14, 2.8, 1.1) at Fog 2.0 warms the band behind the hall (probe i2: (196, 147, 128) R/B 1.53 against (207, 153, 130));
#   the Rayleigh colour bluer (0.4, 0.45, 0.9) for a violet-grey upper sky; Lighting Brightness (Dawn/Dusk) 4 -> 2.4 (the
#   sun and sky light, not the sky: the sky ~0.7 EV brighter against the ground, the exposure bias follows).
ENV["uds"]["props"].update({
    "Sun Source Angle Scale": 3.0,
    "Sky Light Intensity": 2.8,
    "Sun Light Intensity": 4.0,
    "Lighting Brightness (Dawn/Dusk)": 2.4,
    "Sun Light Color": [0.94, 0.94, 1.0],
    "Sky Light Color Multiplier (Dawn/Dusk)": [0.62, 1.25, 1.4],
    "Rayleigh Scattering Color (Dawn/Dusk)": [0.4, 0.45, 0.9],
    "Saturation": 1.0,
    "Contrast": 0.6,
    "Cloud Coverage": 3.6,
    "High Frequency Noise Amount": 0.5,
    "Cloud Light Color (Dawn/Dusk)": [1.0, 0.55, 0.3],
    "Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.5, 0.5, 0.75],
    "Cloud Dark Color (Dawn/Dusk)": [0.08, 0.08, 0.14],
    "Fog": 2.0,
    "Base Height Fog Falloff": 0.2,
    "All Fog Colors Multiplier": [14.0, 2.8, 1.1],
})
_t = ENV["uds"]["props"].pop("Time of Day")             # keep the time last
ENV["uds"]["props"]["Time of Day"] = _t
# - Post: film grain 0.1 (the sky dither), a deeper toe (0.55 -> 0.66) and a gentler slope (0.88 -> 0.84) with local
#   exposure shadow contrast 1.0 (no lift): the eave shadows deepen while the sand's lit / shade ratio stays soft;
#   exposure 1.5 -> 1.02 (the lighting brightness above -0.74 EV; frame mean ~108 as ref 2). The lamps and emissives follow
#   the bias (dj_sc_common).
ENV["grade_extra"] = dict(ENV["grade_extra"], film_grain_intensity=0.1, film_toe=0.66, film_slope=0.84)
ENV["pp_extra"] = dict(ENV["pp_extra"], local_exposure_shadow_contrast_scale=1.0)
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.02)
# - Kawara: cool neutral charcoal (ref 2 lit (91, 84, 94) R/B 0.97, shade (43, 39, 45) 0.96); probe g/i: the warm-pink
#   light needs a green-blue albedo tint to land neutral
LOOK["M_DJ_RoofTile"]["scalars"]["ValueMult"] = 2.0
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.77, 1.7, 2.07]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.041, 0.082, 0.1]
# - Shoji: less bright, less yellow (luma ~150, hue ~33; probe g: (215, 141, 66) luma 150 hue 30); the clerestory band
#   (SM_DKH_Bay_ClereFrieze) 35 % dimmer than the main shoji through its own instance
LOOK["M_DJ_ShojiPaper"] = {"scalars": {"EmissiveIntensity": 45.0, "Saturation": 1.0},
                           "vectors": {"EmissiveTint": [1.0, 0.55, 0.34]}}
EXTRA_MATERIALS["M_DJS_ShojiClere"] = {
    "master": "M_DJ_Lib_Emissive", "kit": "showcase", "ue_dir": "/Game/DojoKit/Showcase/Materials",
    "textures": {"BC": "T_DJ_ShojiPaper_BC", "ORM": "T_DJ_ShojiPaper_ORM", "N": "T_DJ_ShojiPaper_N"},
    "scalars": {"EmissiveIntensity": 29.25, "BaseMult": 0.25, "RoughMult": 1.0, "NormalStrength": 0.3, "Saturation": 1.0},
    "vectors": {"EmissiveTint": [1.0, 0.55, 0.34]}, "switches": {},
    "note": "round 9: the hall's clerestory shoji band, 35 % under M_DJ_ShojiPaper (ref 2's upper band is dimmer)"}
ACTOR_MATERIAL_OVERRIDES["SM_DKH_Bay_ClereFrieze"] = {1: "M_DJS_ShojiClere"}
# - Lantern glass: saturated amber (ref 2 (241, 180, 90) s 0.84; probe g: (238, 186, 93) s 0.81); warm pools on the gravel:
#   the tall stone lanterns 1.5 -> 3.0 x with a 12 m radius, the hall's wall lamps 2 x with a 10 m radius
LOOK["M_DJ_GlassAmber"] = {"scalars": {"EmissiveIntensity": 133.0, "Saturation": 1.0},
                           "vectors": {"EmissiveTint": [1.0, 0.4, 0.12]}}
LAMP_TUNE["SM_DKP_Stone_LanternTall"] = {"candela_mult": 3.0, "radius_m": 12.0}
LAMP_TUNE["SM_DKP_Modern_WallLamp"] = {"candela_mult": 2.0, "radius_m": 10.0}
# - The warm albedos under the neutral light (probe g / i: plaster (139, 108, 96) R/B 1.45, gravel R/B 1.44, sand near
#   R/B 1.54 against ref 2 1.40 / 1.43 / 1.46): less saturation, a slightly cooler tint; timber less saturated
LOOK["M_DJ_PlasterCream"]["scalars"].update({"Saturation": 0.08, "ValueMult": 1.9})
LOOK["M_DJ_PlasterCream"]["vectors"]["Tint"] = [1.0, 0.95, 1.08]
for _k, _v in (("M_DKG_Gravel", 1.4), ("M_DKG_GravelCoarse", 1.55)):
    LOOK[_k]["scalars"].update({"Saturation": 0.35, "ValueMult": _v})
    LOOK[_k]["vectors"]["Tint"] = [0.97, 0.94, 0.98]
for _k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_k]["scalars"]["Saturation"] = 0.4
# - Sand rake: break the regular stripes (dj_sc_materials build_ground, switch UseRakeVar): the lines wobble by up to
#   up to ~+-2.5 cm (0.015 UV of a 4.2 m tile) on a 4 m noise, a fine albedo grain, and a low-frequency patch where the rake is shallower; the normal fade a
#   little earlier and softer at distance (moire)
for _k in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_k]["vectors"]["Tint"] = [1.0, 0.9, 0.88]
LOOK["M_DKG_SandRaked"]["scalars"].update({"RakeWarp": 0.015, "RakeWarpU": 0.01, "RakeWarpTile": 400.0,
                                           "GrainAmount": 0.12, "GrainTile": 25.0, "NormalVar": 0.35,
                                           "NormalVarTile": 700.0, "NormalFadeStart": 1500.0, "NormalFadeEnd": 4500.0,
                                           "NormalFarStrength": 0.6})
LOOK["M_DKG_SandRaked"]["switches"] = {"UseRakeVar": True}
# ---- round 9 it2 (s1_work/it1 measured on CAM_Ref2Match): the built level reads ~0.15 EV darker and a touch warmer than
#   the runtime probes (mean 105.1, plaster R/B 1.57, sand near 1.63); the kawara read teal (lit (78, 82, 79), the green
#   tint overshot): G/R of the tint 2.2 -> 1.65; the cloud shade a greyer violet and brighter (top sky (115, 80, 83)
#   against ref 2's (166, 147, 148)); exposure +0.1 EV; the warm albedos a little cooler
ENV["uds"]["props"].update({"Volumetric Cloud Ambient Light (Dawn/Dusk)": [0.65, 0.6, 0.72],
                            "Cloud Dark Color (Dawn/Dusk)": [0.09, 0.085, 0.11]})
_t = ENV["uds"]["props"].pop("Time of Day")
ENV["uds"]["props"]["Time of Day"] = _t
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.12)
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [1.02, 1.68, 2.57]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.053, 0.087, 0.134]
LOOK["M_DJ_PlasterCream"]["vectors"]["Tint"] = [0.97, 0.95, 1.12]
for _k in ("M_DKG_SandRaked", "M_DKG_SandEdge"):
    LOOK[_k]["vectors"]["Tint"] = [1.0, 0.91, 0.94]
for _k in ("M_DKG_Gravel", "M_DKG_GravelCoarse"):
    LOOK[_k]["vectors"]["Tint"] = [0.95, 0.94, 1.02]
for _k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_k]["scalars"]["Saturation"] = 0.34
# ---- round 9 it3 (s1_work/it2): the kawara read slate blue (shade (46, 42, 62) R/B 0.74 against (43, 39, 45)): the tint's
#   blue down, a little darker; a deeper toe (0.66 -> 0.72) for the eave / roof darks (under-40 share 8.8 % against ref 2's
#   13.7 %) with the exposure +0.08 EV so the sand keeps its level
LOOK["M_DJ_RoofTile"]["scalars"]["ValueMult"] = 1.85
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [1.02, 1.68, 2.15]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.053, 0.087, 0.108]
ENV["grade_extra"] = dict(ENV["grade_extra"], film_toe=0.72)
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.2)
# ---- round 9 it4 (s1_work/it3): the toe 0.72 took the under-40 share to 11.7 % but pushed the darks' saturation (timber
#   (70, 36, 18) s 0.59, plaster / gravel R/B 1.61): shadow saturation 0.8 in the grade (research 2.5: a small shadows
#   correction, no lift); the kawara between it2 and it3 (lit R/B 1.09 / shade 0.90 against 0.97 / 0.96)
ENV["grade_extra"] = dict(ENV["grade_extra"], color_saturation_shadows=(1.0, 1.0, 1.0, 0.8))
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [1.02, 1.68, 2.28]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.053, 0.087, 0.115]
# ================================================================================================ ROUND 9 s2 (retune)
# 2026-09-30, the round-9 paired judge (5.5 / 10) checked delta by delta against dojo1_reference2 first (judge-steer rule);
# -game probes round9/s2_work/probe_a..h (UDS variables, PPV fields, MIDs, lamps at runtime on the s1 build), measured with
# measure_r8.py, extra_r9.py, skym.py and health.py. The sun stays the owner's 9.08 deg from the west (1730 / Yaw 268).
# - Sky (deltas 2 / 3): the maroon deck was the 3.6 coverage in a thin 0.35 layer plus opaque wisps over a dark base
#   sky. Coverage 3.2 with Macro Variation 0.5 in a full-height layer at 1.2x scale gives separated cumulus with clear gaps
#   (probe c3 / d), the wisps at half opacity, a bluer Rayleigh (0.3, 0.4, 1.0); the red fog tint confined to the
#   horizon by a steeper falloff (0.5) with a peach, less magenta tint (16, 4, 1.2) and Fog 2.3. Clear-sky gaps (130, 101,
#   114) -> ref 2 (138, 123, 137) in probe e. Contrast 0.6 -> 0.45 (the posterised cloud edges).
# - Light (delta 4): the dusk lighting brightness 2.4 -> 1.2 (sun + sky light, not the sky: the sky ~1 EV brighter
#   against the ground) with more sky-light fill (Sky Light Intensity 2.8 -> 3.8) and the sky-light tint (0.7, 1.28, 1.25)
#   that lands the shade neutral under the bluer sky (tiles shade hue 312-320, ref 2 280; (0.8, 1, 1.15) read magenta,
#   probe d); local exposure shadow contrast 1.0 -> 0.65 and highlight 0.8 -> 0.7 (lifts the eave / veranda darks in the
#   high-contrast frames, rolls off the sky round the sun); toe 0.72 -> 0.7. The bias follows (1.2 + 1.0 for the lighting
#   brightness, -0.75 measured: frame mean ~112 against ref 2's 108).
ENV["uds"]["props"].update({
    "Cloud Coverage": 3.2, "Macro Variation": 0.5, "Contrast": 0.45,
    "Layer Height Scale": 1.0, "Volumetric Clouds Scale": 1.2, "Cloud Wisps Opacity (Clear)": 0.5,
    "Rayleigh Scattering Color (Dawn/Dusk)": [0.3, 0.4, 1.0],
    "All Fog Colors Multiplier": [16.0, 4.0, 1.2], "Base Height Fog Falloff": 0.5, "Fog": 2.3,
    "Lighting Brightness (Dawn/Dusk)": 1.2, "Sky Light Intensity": 3.8,
    "Sky Light Color Multiplier (Dawn/Dusk)": [0.7, 1.28, 1.25],
})
_t = ENV["uds"]["props"].pop("Time of Day")             # keep the time last
ENV["uds"]["props"]["Time of Day"] = _t
ENV["pp_extra"] = dict(ENV["pp_extra"], local_exposure_shadow_contrast_scale=0.65, local_exposure_highlight_contrast_scale=0.7)
ENV["grade_extra"] = dict(ENV["grade_extra"], film_toe=0.7)
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.45)
# - Kawara (delta 1): the teal albedo (G / R 1.65 in the tint, it4) goes; a cool charcoal close to round 8 s2's (the judge's
#   'correct' roof) with a little more blue: tiles lit / shade (96, 76, 79) / (49, 39, 46) in probe g (ref 2 (91, 84, 94) /
#   (43, 39, 45)); slate-grey in CU_HallUpperRoof
LOOK["M_DJ_RoofTile"]["scalars"]["ValueMult"] = 1.75
LOOK["M_DJ_RoofTile"]["vectors"]["Tint"] = [0.85, 0.97, 1.3]
LOOK["M_DJ_RoofTile"]["vectors"]["MeanColour"] = [0.045, 0.05, 0.072]
# - Shoji (delta 7): 22 % dimmer and a little less saturated (probe g: (206, 138, 87) s 0.55 against ref 2 (182, 118, 53)
#   s 0.55; it3 (215, 140, 59) s 0.66); the clerestory band keeps its 65 % ratio
LOOK["M_DJ_ShojiPaper"]["scalars"].update({"EmissiveIntensity": 35.1, "Saturation": 0.9})
EXTRA_MATERIALS["M_DJS_ShojiClere"]["scalars"].update({"EmissiveIntensity": 22.8, "Saturation": 0.9})
# - Lantern pools (delta 9): the round-9 3x / 12 m pools back to a modest spill (1.5x / 7 m), the wall lamps 1.5x / 8 m
LAMP_TUNE["SM_DKP_Stone_LanternTall"] = {"candela_mult": 1.5, "radius_m": 7.0}
LAMP_TUNE["SM_DKP_Modern_WallLamp"] = {"candela_mult": 1.5, "radius_m": 8.0}
# - Timber (delta 4): the veranda darks read orange-brown (it3 (70, 36, 18) s 0.59): saturation 0.34 -> 0.26 (probe g
#   (81, 55, 36) s 0.39 against ref 2 (75, 49, 30) s 0.43)
for _k in ("M_DJ_TimberDark", "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_TimberAgedEnd"):
    LOOK[_k]["scalars"]["Saturation"] = 0.26
# - Sand rake (delta 5, checked against ref 2): ref 2's grooves are straight, regular and COARSER than ours in the matched
#   frame (period 7.5 px against our 5.4 px at 1448 wide, FFT of the near sand), so the judge's 'higher frequency' is
#   rejected: UV Scale 1 -> 0.72 (13 cm lines), the round-9 wobble and patchy normal almost off (RakeWarp 0.015 -> 0.004,
#   RakeWarpU 0.01 -> 0.002, NormalVar 0.35 -> 0.1: they made the blotchy bands), value 0.88 -> 1.0 (sand near 150 -> 160,
#   ref 2 182)
LOOK["M_DKG_SandRaked"]["scalars"].update({"UV Scale": 0.72, "RakeWarp": 0.004, "RakeWarpU": 0.002, "NormalVar": 0.1,
                                           "ValueMult": 1.0})
LOOK["M_DKG_SandEdge"]["scalars"]["ValueMult"] = 1.0
# ---- round 9 s2 it2 (the built s2 level + probe_i, CAM_Ref2Match against ref 2): the sky still sat ~0.5 EV under the
#   ground's ratio (top sky (116, 94, 99) against (166, 147, 148), clear gaps (116, 95, 102) against (138, 123, 137)).
#   Two causes: local-exposure highlight contrast 0.7 compressed the sky, and the dusk lighting brightness still set the
#   ground against the sky. Lighting Brightness (Dawn/Dusk) 1.2 -> 0.7 with the bias +0.3 (ground level kept: sand near
#   (171, 146, 123) against ref 2 (182, 148, 125)) and highlight contrast 0.7 -> 0.8 (1.0 clipped 4.75 % of CAM_EastYard
#   round the sun): gaps (144, 124, 133), top sky (140, 118, 124) in probe i3
ENV["uds"]["props"].update({"Lighting Brightness (Dawn/Dusk)": 0.7})
_t = ENV["uds"]["props"].pop("Time of Day")
ENV["uds"]["props"]["Time of Day"] = _t
ENV["pp_extra"] = dict(ENV["pp_extra"], local_exposure_highlight_contrast_scale=0.8)
ENV["exposure"] = dict(ENV["exposure"], bias_ev=1.75)
