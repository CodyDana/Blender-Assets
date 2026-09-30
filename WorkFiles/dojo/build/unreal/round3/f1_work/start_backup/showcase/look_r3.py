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
    ("CU_Lantern", (17.4, 18.1, 1.55), (19.0, 20.5, 1.05), 44.0, (1920, 1080),
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
