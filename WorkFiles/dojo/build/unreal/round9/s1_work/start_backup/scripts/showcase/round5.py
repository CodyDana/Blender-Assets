"""Showcase ROUND 5 (2026-09-29, final look pass WITHOUT vegetation): the dressing and outside tracks in the combined
DojoLab layout (plain Python, no bpy / unreal). Read by compose_showcase.py; the tracks' files are read, never written.

  KITS             dressing (the user's armory emblem plaques, SM_DKD_*) and outside (road, background, SM_DKX_*)
  LD / LO          layout_dressing.json / layout_outside.json exactly as the tracks wrote them
  replaced_greybox()   SM_DGB_Ground_Outside + SM_DGB_AlleyFence -> 'outside' (the trees stay grey-box: vegetation later)
  modern_street()  (pieces to drop, rows to place): the street lamps, poles, wires and the gatehouse drop move OUTSIDE onto
                   the approach road (user: no street lamps inside the courtyard; street lamps + power lines only outside)
  kit_recipes()    the tracks' own material instances (M_DKD_EmblemPlaque, M_DKX_*) on the showcase's existing masters
  TEX_HOME         texture prefix -> (folder, kit) for those recipes' maps
  decal_recipes()  decals.json: M_DKD_Decal_Master + one instance per decal type, and their T_DKD_Decal_* maps
  decals()         the 101 measured decal placements (ray-cast centre / normal / up / size; Unreal rotator + half sizes)
  WALK_ROUTES / CLIMB_ROUTES   the outside track's BR street routes, alley-fence CONTROLs and outside wall climbs
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BUILD = ROOT / "WorkFiles" / "dojo" / "build"
EXP = ROOT / "Exports" / "DojoKit"
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "outside"))
import round5_outside as R5O  # noqa: E402  (the outside track's own integration module, read-only)

KITS = {"dressing": (EXP / "Dressing", EXP / "Dressing" / "Textures", "/Game/DojoKit/Dressing")}
KITS.update(R5O.KIT)
LAYOUT_FILES = {"dressing": BUILD / "dressing" / "layout_dressing.json", "outside": R5O.LAYOUT_FILE}
DECALS_FILE = BUILD / "dressing" / "decals.json"
LD = json.loads(LAYOUT_FILES["dressing"].read_text(encoding="utf-8"))
LO = R5O.LAYOUT
DEC = json.loads(DECALS_FILE.read_text(encoding="utf-8"))
LAYOUTS = {"dressing": LD, "outside": LO}
TEX_HOME = {"T_DKX_": (KITS["outside"][1], "outside"), "T_DKD_": (KITS["dressing"][1], "dressing")}
DECAL_MASTER = "M_DKD_Decal_Master"


def replaced_greybox():
    return R5O.replaced_greybox()


def modern_street():
    return R5O.modern_street()


def kit_recipes():
    out = {}
    for kit, L in LAYOUTS.items():
        for name, m in L.get("materials", {}).items():
            out[name] = json.loads(json.dumps({k: m.get(k, {} if k in ("textures", "scalars", "vectors", "switches")
                                                          else "") for k in ("master", "kit", "ue_dir", "textures",
                                                                             "scalars", "vectors", "switches", "note")}))
    return out


def decal_recipes():
    """name -> recipe (the MI loop of dj_sc_materials builds them like every other instance), textures table."""
    R, TEX = {}, {}
    for name, m in DEC["materials"].items():
        R[name] = {"master": DECAL_MASTER, "kit": "dressing", "ue_dir": m["ue_dir"], "textures": dict(m["textures"]),
                   "scalars": dict(m["scalars"]), "vectors": dict(m["vectors"]), "switches": {},
                   "note": "round 5 decal (dressing track decals.json): " + m.get("use", "")[:160]}
    for name, t in DEC["textures"].items():
        TEX[name] = {"png": t["png"], "ue_dir": t["ue_dir"], "kind": t["kind"]}
    return R, TEX


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def ue_decal(p):
    """The Unreal decal transform, MEASURED on the round-5 captures (CU_R5_MossWallFoot, it1 + it2): UE 5.8 samples a
    deferred decal's texture with U along local Z and V along local Y (image top at -Y), not (Y, Z) as the
    dressing track's decals.json assumed; with its rotators the 4 x 0.85 m moss strip came out as horizontal smears
    along the wall (U up the wall). So: local +X = -normal (projection), local +Z = the image's right, local -Y = the
    image's up; DecalSize = half extents (depth, height, width) cm; a mirrored frame or flip_u is an actor
    scale of -1 on Y (vertical) / Z (horizontal). Frame conversion Blender -> UE: (x, -y, z)."""
    conv = lambda v: [v[0], -v[1], v[2]]   # noqa: E731
    X = _unit(conv([-c for c in p["normal"]]))
    right = _unit(conv(p["right"]))
    up = _unit(conv(p["up"]))
    Z = right
    Y = _cross(Z, X)                       # UE: Y = Z x X for a rotation
    # it2 capture (CU_R5_MossWallFoot): with +Y = up the moss sat at the TOP of its wall-foot box, so the image's up is
    # local -Y (UV = (Z, Y) in practice): mirror so -Y points up
    sy = -1.0 if sum(a * b for a, b in zip(Y, up)) > 0 else 1.0
    sz = -1.0 if p.get("flip_u") else 1.0
    sp = max(-1.0, min(1.0, X[2]))
    pitch = math.degrees(math.asin(sp))
    if abs(sp) < 0.9999:
        yaw = math.degrees(math.atan2(X[1], X[0]))
        roll = math.degrees(math.atan2(-Y[2], Z[2]))
    else:                                  # straight down / up: yaw 0, roll from Y = (sr sp, cr, 0)
        yaw = 0.0
        roll = math.degrees(math.atan2(Y[0] * (1.0 if sp > 0 else -1.0), Y[1]))
    c = p["centre"]
    return {"location_cm": [round(c[0] * 100.0, 3), round(-c[1] * 100.0, 3), round(c[2] * 100.0, 3)],
            "rotation_deg": {"roll": round(roll, 4), "pitch": round(pitch, 4), "yaw": round(yaw, 4)},
            "decal_size_cm": [round(p["depth_m"] * 50.0, 3), round(p["size_m"][1] * 50.0, 3),
                              round(p["size_m"][0] * 50.0, 3)],
            "scale": [1.0, sy, sz], "axes_ue": {"x": [round(v, 5) for v in X], "z": [round(v, 5) for v in Z]},
            "uv_rule": "U along local Z (image right), V along local Y (image top at -Y); measured it1 + it2"}


# round 5 fix f1 (both judges: 'pale scribble-like weathering decals on the hall lower roof and the gate roof read as
# white marks / noise at distance'; the gate-roof lichen's 0.5 m box also printed black splatter on the gate soffit
# under it): the lichen on every tiled roof and wall cap is dropped; the stone-lantern lichen stays (darkened in
# look_r3). decals.json (the dressing track's) is not changed.
DROP_DECALS = ("gate roof;", "hall lower roof;", "outbuilding roof;", "pavilion roof;", "wall cap;")


def decals():
    out = []
    for p in DEC["placements"]:
        if p["material"] == "M_DKD_Decal_Lichen" and p.get("source", "").startswith(DROP_DECALS):
            continue
        out.append({"id": p["id"], "material": p["material"], "centre": p["centre"], "normal": p["normal"],
                    "up": p["up"], "right": p["right"], "size_m": p["size_m"], "depth_m": p["depth_m"],
                    "flip_u": bool(p.get("flip_u")), "ue": ue_decal(p), "ue_track": p["ue"],
                    "source": p.get("source", "")[:160]})
    return out


WALK_ROUTES = R5O.WALK_ROUTES
CLIMB_ROUTES = R5O.CLIMB_ROUTES
TREE_SLOTS = R5O.TREE_SLOTS
