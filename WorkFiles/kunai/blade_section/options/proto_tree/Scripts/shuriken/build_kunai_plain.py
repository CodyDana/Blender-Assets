#!/usr/bin/env python
"""Build SM_Kunai_Plain - the plain (single-blade) kunai: leaf blade, wrapped grip, ring pommel, blank lettering band.

Source of truth for the asset (house rule: the script, not the .blend).  This file is only the form's SPEC and its
report text; the kunai generator (shuriken_lib.kunai + kunai_spec, plugged in through the non-radial Form hook as
``Form(geometry=KunaiGeometry(SPEC))``), M_Shuriken_Master (class mode) for the steel, M_Kunai_Wrap (shuriken_lib.
kunai_wrap) for the grip's cloth tape, the analytic UVs (two UV tiles), the two UCX hulls, sockets, LOD group, FBX, bake,
gallery renders, JSON report and qa_check live in Scripts/shuriken/shuriken_lib and are shared by every form.  Running
it alone rebuilds Assets/Shuriken.blend FROM SCRATCH with this one form; the canonical builder is build_pack.py
(``--forms four_point,eight_point,square_plate,six_point,spike,hooked_cross,kunai_plain``).

Authority: References/Kunai/KUNAI_STUDY.md (section 4, the BUILD-TO table; section 5 the modelling notes; section 6
franchise avoidance) and the pack style (References/Shuriken/style_reference/STYLE_TARGET.md top section,
shuriken_lib/material.py docstring).

The user's decisions (2026-09-18/19): a kunai in the pack, first the three-pronged "winged" look, then "make the plain
kunai too (the non winged one)", then "skip the winged kunai for now".  So this is the PLAIN kunai: the study's blade,
grip, wrap, ring and lettering band with the prongs and the crotch removed and the fork plane turned into a normal
kunai SHOULDER (the 16 mm blade base meets the 6 mm bare neck and the grip).  Generic and historical-modern: a leaf blade
on a one-piece tang with a cord / tape-wrapped grip and a ring pommel is how many unrelated makers build the modern
kunai (study 2); no franchise feature, NO lettering anywhere - the grip's +Z face carries a blank 72 x 12 mm band, a
rectangle of the wrap's own straight unroll, that samples T_Kunai_Lettering (shipped blank) for the user's own text
(References/Kunai/LETTERING_HOWTO.md).
The winged head stays a spec option (``KunaiSpec.prongs``), OFF, not built.  No franchise word anywhere in an object,
material, texture, socket, file or report name (FRANCHISE_TERMS below are gated on every name the build makes, on top of
qa_check's deny list).

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate,six_point,spike,hooked_cross,kunai_plain
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_kunai_plain.py -- [options]      (this form only)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import KunaiLodSpec, KunaiSpec, scaled_lod_screen_sizes  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Kunai_Plain.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "kunai_plain_report.json"
STUDY_BASIS = PROJECT / "WorkFiles" / "kunai" / "plain_calc" / "kunai_plain_mass_check.json"
# PROTOTYPE (blade_section/options): the option file may name its own study basis and mass-gate target
from shuriken_lib.kunai_spec import SECTION_OVERRIDE as _SO  # noqa: E402
if _SO.get("STUDY_BASIS"):
    STUDY_BASIS = Path(_SO["STUDY_BASIS"])
LETTERING_HOWTO = PROJECT / "References" / "Kunai" / "LETTERING_HOWTO.md"

# Study section 6: the pipeline's deny list catches "naruto" only; the rest is gated here on every name the build makes.
FRANCHISE_TERMS = ("naruto", "minato", "namikaze", "hiraishin", "flying thunder god", "flying raijin", "yondaime",
                   "hokage", "yellow flash", "konoha", "shippuden", "boruto")
# Unreal's bounds sphere about the bounding-box centre: the blade tip and the ring's far end, 140 mm each side (the ring's
# outer wall reaches x = -140 at z +-1.5 mm: sqrt(140^2 + 1.5^2) = 140.008 mm).
UE_BOUNDS_RADIUS_MM = math.hypot(140.0, 1.5)

_LOD0 = KunaiLodSpec(blade_base_intervals=3, blade_leaf_intervals=14, blade_tip_intervals=2, neck_intervals=1,
                     rear_intervals=2, land=0.15, chamfer=0.45, plateau_steiner=1, grip_sides=16, tape_relief=True,
                     taper_rings=2, ring_segments=24, ring_section="round", neck_chamfer=0.6, band=(1000, 2600),
                     note="LOD0: the full outline (kite corner, 14 leaf stations), the knife grind 35 deg to a 0.15 mm "
                          "land on both blade edges running out into the shoulder chamfer, the plunge, the study's "
                          "16-sided grip with the TAPE's overlap ridges as geometry (a 9 mm-pitch helix, 0.5 mm steps) "
                          "wound down onto the tang over the last 6 mm at both ends, 24 x 8 ring with r 1 mm rounds, "
                          "chamfered rear neck")
_LOD1 = KunaiLodSpec(blade_base_intervals=int(_SO.get("LOD1_BASE_INTERVALS", 1)), blade_leaf_intervals=7, blade_tip_intervals=1, neck_intervals=1,
                     rear_intervals=1, land=0.15, chamfer=0.45, plateau_steiner=1, grip_sides=16, tape_relief=False,
                     taper_rings=2, ring_segments=12, ring_section="round", neck_chamfer=0.0, band=(400, 900),
                     note="LOD1: half the stations, the grind kept (one facet per station), the grip at the tape's mean "
                          "radius (0.5 mm of tape relief is 0.5 px at the 0.89 m switch) but on LOD0's 16 vertex lines "
                          "and the same wound-down end sections, 12 x 8 ring, square rear neck")
_LOD2 = KunaiLodSpec(blade_base_intervals=1, blade_leaf_intervals=3, blade_tip_intervals=1, neck_intervals=1,
                     rear_intervals=1, land=0.0, chamfer=0.0, plateau_steiner=0, grip_sides=16, tape_relief=False,
                     taper_rings=1, ring_segments=8, ring_section="square", neck_chamfer=0.0, band=(150, 400),
                     note="LOD2: the silhouette and the ring hole kept; cutting edges are the edge line (land 0), neck "
                          "edges square, the smooth grip on LOD0's 16 vertex lines with one ring in each wound-down "
                          "end (the end sections are the grip's silhouette at arm's length), 8 x 4 square ring")

SPEC = KunaiSpec(
    form="kunai_plain",
    mesh_name="SM_Kunai_Plain",
    title="Plain kunai (leaf blade, wrapped grip, ring pommel; blank lettering band)",
    lods=(_LOD0, _LOD1, _LOD2),
    mass_target_g=float(_SO.get("MASS_TARGET_G", 153.02)),           # study basis, plain: un-ground steel 19,492.6 mm3 x 7.85 = 153.02 g (plain_calc)
    mass_tolerance_g=2.0,
    assembled_target_g=167.4,       # study basis, plain: 164.8-170.0 g assembled (DERIVED), reported
    revision=1,
    physics_mass_kg=None,           # the override is the finished (assembled) mass the build measures
    lod_screen_sizes=scaled_lod_screen_sizes(UE_BOUNDS_RADIUS_MM),
    prongs=False,                   # the winged head: an option for later, OFF (the user skipped it "for now")
    grip_x_mm=-54.0,                # study 5: mid grip
    trail_x_mm=-140.0,              # study 5: the ring's far end
    tip_x_mm=140.0,                 # study 5 (optional): the point
    ring_x_mm=-124.0,               # study 5 (optional): the ring centre - a rope, or the queued paper tag
    hero_yaw_deg=-25.0,             # gallery: the point toward the viewer (see GALLERY: the diamond faces catch the key)
    steel_px=2048,
    wrap_px=1024,
    lettering_px=(1536, 256),
    steel_px_per_mm=13.4,
    wrap_px_per_mm=10.0,
    study_mass_range_g=(164.8, 170.0),
    study_mass_typical_g=(167.4, 167.4),
)


# --------------------------------------------------------------------------- report text


def _study_basis() -> dict:
    try:
        return json.loads(STUDY_BASIS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _franchise_hits(names) -> list:
    pattern = re.compile("|".join(r"[\s_\-]*".join(re.escape(w) for w in t.split()) for t in FRANCHISE_TERMS),
                         re.IGNORECASE)
    return sorted({n for n in names if n and pattern.search(n)})


def _name_gate(report: dict) -> dict:
    import bpy
    names = []
    for kind in ("objects", "meshes", "materials", "images", "collections", "node_groups", "curves"):
        names += [item.name for item in getattr(bpy.data, kind)]
    tex = report.get("textures") or {}
    for group in (tex.get("maps") or {}, ((tex.get("wrap") or {}).get("maps") or {})):
        names += [Path(p).name for p in group.values()]
    for key in ("natural_bc",):
        p = (tex.get("wrap") or {}).get(key, {}).get("path")
        if p:
            names.append(Path(p).name)
    if (tex.get("lettering") or {}).get("path"):
        names.append(Path(tex["lettering"]["path"]).name)
    names += [report.get("fbx") or "", report.get("sockets_sidecar") or "", str(DEFAULT_REPORT.name)]
    names += list(report.get("sockets") or [])
    hits = _franchise_hits(names)
    return {"terms": list(FRANCHISE_TERMS), "names_checked": len(names), "hits": hits, "passed": not hits,
            "scope": "every datablock name in the scene (objects, meshes, materials, images, collections), every "
                     "texture and export file name, the sockets and the report file name"}


def _lettering_gate(report: dict) -> dict:
    """The band's rectangle is the exact image of the 72 x 12 mm grip region under the wrap's own straight unroll, on
    every LOD, and the shipped mask is blank.

    3.10.1: the band is no longer a separate UV island (its seam read as an outlined panel in the review), so the gate
    proves the MAPPING instead of an island: on every LOD, every face of the unrolled grip carries exactly the analytic
    UV u = (x - WRAP_X0), v = (phi + pi) * WRAP_R (in the wrap tile, at wrap_px_per_mm), and the recorded rectangle is
    that map's image of x -90..-18, |phi| <= BAND_ARC / 2 WRAP_R.  A mask drawn for LOD0 therefore lands identically on
    LOD1 and LOD2, and nothing else can reach the rectangle (the steel islands are in tile u 0..1, the two cut ends are
    their own rectangles elsewhere in the wrap tile)."""
    import bpy
    import math as _math
    import numpy as np
    from shuriken_lib.kunai_spec import BAND_HALF_DEG, BAND_X0, BAND_X1, WRAP_R, WRAP_X0
    tex = report.get("textures") or {}
    layout = (report.get("uv_layout") or {})
    rect = (tex.get("lettering_uv") or {}).get("uv0_blender") or (layout.get("lettering") or {}).get("uv0_blender")
    wrap_rect = ((layout.get("layout_px") or {}).get("wrap") or {}).get("wrap")
    tiles = (layout.get("tiles") or {}).get("wrap") or {}
    size = float(tiles.get("map_px") or 1024)
    dw = float(tiles.get("px_per_mm") or 10.0)
    shift = float((report.get("measured") or {}).get("pivot_design_x_mm") or 0.0)
    out = {"rect_uv0_blender": rect, "lods": {}}
    ok = rect is not None and wrap_rect is not None
    if ok:
        rx, ry, _rw, _rh = wrap_rect
        b = _math.radians(BAND_HALF_DEG)
        want = {"u_min": 1.0 + (rx + (BAND_X0 - WRAP_X0) * dw) / size,
                "u_max": 1.0 + (rx + (BAND_X1 - WRAP_X0) * dw) / size,
                "v_min": (ry + (_math.pi - b) * WRAP_R * dw) / size,
                "v_max": (ry + (_math.pi + b) * WRAP_R * dw) / size}
        out["rect_from_the_band_region"] = {k: round(v, 8) for k, v in want.items()}
        out["rect_matches_region"] = all(abs(rect[k] - want[k]) <= 1e-7 for k in want)
        ok = ok and out["rect_matches_region"]
    for name in report.get("objects") or []:
        obj = bpy.data.objects.get(name)
        if obj is None or not ok:
            ok = False
            continue
        mesh = obj.data
        uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
        mesh.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2).astype(np.float64)
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3).astype(np.float64) * 1000.0
        worst, body, in_band = 0.0, 0, 0
        for poly in mesh.polygons:
            if poly.material_index != 1 or abs(poly.normal[0]) > 0.95:     # the grip's own faces, not the cut ends
                continue
            body += 1
            loops = list(poly.loop_indices)
            verts = [co[mesh.loops[li].vertex_index] for li in loops]
            design_x = [v[0] + shift for v in verts]
            phis = [_math.atan2(v[1], v[2]) for v in verts]
            centre = _math.atan2(float(np.mean([v[1] for v in verts])), float(np.mean([v[2] for v in verts])))
            phis = [p - 2.0 * _math.pi if p - centre > _math.pi else
                    (p + 2.0 * _math.pi if centre - p > _math.pi else p) for p in phis]
            for li, x, phi in zip(loops, design_x, phis):
                u = 1.0 + (rx + (x - WRAP_X0) * dw) / size
                v = (ry + (phi + _math.pi) * WRAP_R * dw) / size
                worst = max(worst, abs(uv[li][0] - u) * size, abs(uv[li][1] - v) * size)
            if (min(design_x) >= BAND_X0 - 1e-6 and max(design_x) <= BAND_X1 + 1e-6
                    and max(abs(p) for p in phis) <= _math.radians(BAND_HALF_DEG) + 1e-9):
                in_band += 1
        # a coarse LOD's grip faces are big enough that none lies ENTIRELY inside the 72 x 12 mm band; what has to hold
        # on every LOD is the mapping (a mask drawn for LOD0 then lands on the same millimetres of cloth)
        lod_ok = body > 0 and worst <= 0.01
        out["lods"][name] = {"grip_faces": body, "faces_inside_the_band": in_band,
                             "max_uv_deviation_px": round(worst, 6), "passed": bool(lod_ok)}
        ok = ok and lod_ok
    lett = tex.get("lettering") or {}
    blank = False
    if lett.get("path") and Path(lett["path"]).exists():
        img = bpy.data.images.load(lett["path"], check_existing=False)
        try:
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            blank = bool(px.reshape(-1, 4)[:, :3].max() == 0.0)
            out["mask_size"] = list(img.size)
        finally:
            bpy.data.images.remove(img)
    out["mask_blank"] = blank
    out["passed"] = bool(ok and blank)
    out["rule"] = ("every face of the unrolled grip carries the analytic wrap UV (within 0.01 px at 1024), the recorded "
                   "band rectangle is that map's image of the 72 x 12 mm region on the +Z face, and T_Kunai_Lettering "
                   "ships blank")
    return out


def _uv_area_gate(report: dict) -> dict:
    """No UV0 face collapses: every face with a real surface has a real UV area, on every LOD, and its texel density lies
    within a factor of 3 of its island's map density (added after the 3.10 build's Unreal round trip found the bare neck's
    side wall unrolled to a line; qa_check's overlap test ignores zero-area UV triangles)."""
    import bpy
    import numpy as np
    out, ok = {}, True
    for name in report.get("objects") or []:
        mesh = bpy.data.objects[name].data
        uv = np.empty(len(mesh.loops) * 2, dtype=np.float64)
        mesh.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        worst, collapsed, faces = None, 0, 0
        for poly in mesh.polygons:
            if poly.area <= 1e-10:                       # 0.0001 mm2: hidden slivers are not textured surface
                continue
            faces += 1
            p = uv[list(poly.loop_indices)]
            a = 0.5 * abs(float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])))
            size = 2048.0 if poly.material_index == 0 else 1024.0
            texels = a * size * size
            density = (texels / (poly.area * 1e6)) ** 0.5 if texels > 0 else 0.0      # px per mm
            if texels < 1e-6:
                collapsed += 1
            worst = density if worst is None else min(worst, density)
        good = collapsed == 0
        out[name] = {"faces": faces, "collapsed_uv_faces": collapsed, "min_px_per_mm": round(worst or 0.0, 4),
                     "passed": good}
        ok = ok and good
    return {"per_lod": out, "passed": ok,
            "rule": "every face over 0.0001 mm2 has a UV0 area of more than 1e-6 texel on its own map"}


def _slots_gate(report: dict) -> dict:
    import bpy
    out, ok = {}, True
    for name in report.get("objects") or []:
        obj = bpy.data.objects.get(name)
        mats = [m.name if m else None for m in obj.data.materials] if obj else []
        used = sorted({p.material_index for p in obj.data.polygons}) if obj else []
        good = mats == ["M_Shuriken_Master", "M_Kunai_Wrap"] and used == [0, 1]
        out[name] = {"slots": mats, "used": used, "passed": good}
        ok = ok and good
    return {"per_lod": out, "passed": ok,
            "rule": "every LOD: slot 0 M_Shuriken_Master (steel), slot 1 M_Kunai_Wrap (the grip wrap), both used"}


GALLERY = {
    "lead_image": "Renders/Shuriken/kunai_plain_persp.png",
    "order": ["kunai_plain_persp.png", "kunai_plain_top.png", "kunai_plain_lodgrind.png", "kunai_plain_wire.png",
              "kunai_plain_lods.png"],
    "reason": ("lead with the hero (the kunai turned -25 deg about Z for the shot only, the point toward the viewer, "
               "resting on its wrap, slid on the floor for the stars' lens shift, the hero lamps scaled with the camera "
               "distance). The yaw is chosen, not guessed: the diamond's coat faces tilt 4-12 deg off flat, so how much "
               "of the rig's key strip they mirror depends on the blade's direction; probed at 60 / 40 / 20 / 10 / 0 / "
               "-10 / -20 / -30 / -40 / 140 deg (96 samples, WorkFiles/kunai/iteration/hero_yaw_probe.json) the coat p50 "
               "ran 0.40 / 0.39 / 0.45 / 0.48 / 0.50 / 0.52 / 0.54 / 0.53 / 0.51 / 0.49 against the anchor forms' 0.56, "
               "and at 220 samples -20 / -25 / -30 / -35 gave coat means 0.510 / 0.509 / 0.505 / 0.498 against 0.550 +- "
               "0.05: only about -10 to -30 pass, the blade pointing along the camera-key line; -25 keeps a little "
               "diagonal with ~0.01 of headroom. A 3/4 pose across the frame (yaw 40, the spike's) reads 0.39. The top "
               "view shows the "
               "whole 280 mm knife along +X, tip right, at 5.0 px/mm (its own frame: the pack's 0.13 m frame is 0.231 m "
               "wide)"),
}


def annotate(report: dict) -> None:
    """Kunai-only report text: study basis, masses, pivot, collision decision, sockets, lettering, gates, gaps."""
    measured = report["measured"]
    basis = _study_basis()
    m_fin, m_un = measured["masses_finished"], measured["masses_unground"]
    assembled = measured["assembled_mass_g"]
    replicas = basis.get("plain_replicas_in_the_study_g") or {}
    report["mass_check_kunai"] = {
        "study_basis": {"file": str(STUDY_BASIS),
                        "unground_steel_g": (basis.get("unground") or {}).get("steel_mass_g"),
                        "ground_steel_g": (basis.get("ground") or {}).get("steel_mass_g"),
                        "assembled_g_range": (basis.get("assembled") or {}).get("mass_g_range"),
                        "assembled_g_mid": (basis.get("assembled") or {}).get("mass_g_mid"),
                        "com_x_mm_mass_weighted": (basis.get("assembled") or {}).get("com_x_mm_mass_weighted"),
                        "com_x_mm_if_render_volume_uniform": (basis.get("assembled") or {}).get(
                            "com_x_mm_if_render_volume_uniform"),
                        "method": "the study's own arithmetic (kunai_mass_check.py, 0.05 mm grid) with the prongs and "
                                  "the fork web removed; the 6 mm bare neck is tang stock"},
        "mesh": {"unground_steel_g": m_un["steel_g"], "ground_steel_g": m_fin["steel_g"],
                 "wrap_g": m_fin["wrap_g"], "tape_g": m_fin["tape_g"], "core_g": m_fin["core_g"],
                 "assembled_g": assembled, "centre_of_mass_x_mm": m_fin["centre_of_mass_x_mm"],
                 "centre_if_uniform_density_x_mm": m_fin["centre_if_uniform_density_x_mm"],
                 "by_part_mm3": {k: m_fin[k] for k in ("head_mm3", "tang_hidden_mm3", "neck_mm3", "ring_mm3",
                                                       "neck_in_ring_mm3", "steel_mm3", "tape_mm3", "core_mm3")}},
        "mesh_minus_study_g": {
            "unground_steel": round(m_un["steel_g"] - ((basis.get("unground") or {}).get("steel_mass_g") or 0.0), 3),
            "assembled": round(assembled - ((basis.get("assembled") or {}).get("mass_g_mid") or 0.0), 3),
            "why": ("the mesh's rear neck tapers 16 x 5 -> 12 x 4.4 mm into the ring (the study's tang stays 16 x 5 to "
                    "x -110), its ring has r 1 mm rounds (finished only), and its flat neck stock reaches ~3.6 mm into "
                    "the blade base up to the plunge line (the study's diamond starts at x = 0)")},
        "gate": "PASS" if measured["mass_within_tolerance"] else "FAIL",
        "winged_study_for_comparison": {"assembled_g": 189.6, "com_x_mm": -18.63,
                                        "note": "KUNAI_STUDY.md 4: the three-prong head adds ~22 g forward of the grip"},
        "plain_replicas_in_the_study_g": replicas,
        "vs_replicas": ("the assembled plain kunai sits inside the plain replicas' spread: heavier than the zinc 290 x "
                        "50 mm casting (140 g) and the blunt 26 cm Atsu (162 g), close to the 12 in / 5.1 mm thrower (up "
                        "to 176 g), lighter than the Honshu 12 in (227 g: a 41.5 mm-wide, 305 mm, one-piece 7Cr13 blade) "
                        "and the unconfirmed 283 g forged piece. Ground steel against display castings, as the study "
                        "found for the winged figures"),
    }
    report["pivot"] = {
        "design_x_mm": measured["pivot_design_x_mm"],
        "from_the_wrap_front_mm": round(-6.0 - measured["pivot_design_x_mm"], 3),
        "method": "mass-weighted centre of the authored shells: steel 7.85, wooden core 0.70, cotton tape 0.75 g/cm3 "
                  "(study 5); the mesh is authored shifted by it, so the object origin IS the centre of mass",
        "wrong_if_volume": m_fin["centre_if_uniform_density_x_mm"],
        "note": ("the prongs gone, the centre of mass moves toward the grip: winged study -18.6 mm, plain study basis "
                 f"{(basis.get('assembled') or {}).get('com_x_mm_mass_weighted')} mm, this mesh "
                 f"{m_fin['centre_of_mass_x_mm']:.3f} mm. Origin to Center of Mass (Volume) would put it at "
                 f"{m_fin['centre_if_uniform_density_x_mm']:.3f} mm (the 20 mm grip counted as steel)"),
    }
    geo_choice = report.get("collision_choice") or {}
    report["sockets_design"] = {
        "Grip": "long axis, x = -54 mm (mid grip, study 5), +X to the tip, +Z out of the lettering face: hand attach, "
                "holster",
        "Trail": "long axis, x = -140 mm (the ring's far end): ribbon or spark trail",
        "Tip": "long axis, x = +140 mm: impact trace, stick-in-wall",
        "Ring": "the ring centre, x = -124 mm: a rope, or the queued paper tag",
        "frame": "positions from the shoulder in the study; stored relative to the pivot (the centre of mass)",
    }
    report["throwing"] = {
        "for_the_blueprint": ("ProjectileMovementComponent with Rotation Follows Velocity (study 5 [80]): the +X tip "
                              "flies point first with no offset; for a spinning throw spin a child mesh about the "
                              "pivot, which is the centre of mass"),
    }
    report["lettering"] = {
        "howto": str(LETTERING_HOWTO),
        "uv": (report.get("uv_layout") or {}).get("lettering"),
        "mask": (report.get("textures") or {}).get("lettering"),
        "gate": _lettering_gate(report),
        "rule": "no lettering modelled, traced or textured (study 6); the user writes their own into T_Kunai_Lettering",
    }
    report["material_slots_gate"] = _slots_gate(report)
    report["uv_area_gate"] = _uv_area_gate(report)
    report["franchise_gate"] = _name_gate(report)
    report["originality"] = {
        "basis": ("the modern plain kunai: a leaf blade on a one-piece tang with a wrapped grip and a ring pommel, made "
                  "by many unrelated makers (study 2); historical kunai were blunt 36-48 cm iron tools, the sharp grind "
                  "and the 28 cm scale follow the measured modern replicas (study 1, 4)"),
        "not_built": "the three-prong head (a franchise-specific, licensed silhouette, study 6): the prongs option is OFF",
        "lettering": "none; a blank band for the user's own",
        "franchise_strings": "gated: franchise_gate (study 6's terms) + qa_check no_franchise_strings",
    }
    report["gallery"] = GALLERY
    report["style_on_a_knife"] = {
        "steel": ("M_Shuriken_Master in class mode (shuriken_class_mode = 1: the surface class from the generator's "
                  "shuriken_class FACE attribute - 1 coat on the diamond faces, the neck plateau, the plunge, the ring "
                  "and the rear neck; 0.5 on the knife facets and the chamfers; 0 on the walls): the pack's satin coat "
                  "(linear ~0.10, metallic 1.0, roughness 0.34), the two-finish knife grind (0.7 mm polished band along "
                  "the 0.15 mm land, satin grimy rest) with the 3.9.1 run-out taper into the shoulder chamfer, the tip "
                  "polished over its last 2.5 mm, soft smears, fine mostly-dark micro-scratches, near-invisible pits, two "
                  "sub-pixel rust specks (blade top face, blade underside near the shoulder)"),
        "wrap": ("M_Kunai_Wrap (second material slot): worn dark cotton tape, linear ~0.04. From 3.10.1 the tape's "
                 "OVERLAP IS GEOMETRY (a 9 mm-pitch helix whose exposed edge stands 0.5 mm proud, wound down onto the "
                 "tang over the last 6 mm at both ends), so the material carries the burnished crown the hand rubs, "
                 "the dirt line at the foot of each step, fray along every tape edge and at the cut ends, an irregular "
                 "1.15 mm cotton weave with slubs and fibre fuzz, faded patches at 7 and 16 mm, hand grime mid-grip, "
                 "roughness 0.90 (grime 0.78, crowns 0.74); the undyed option (linear ~0.40) ships as "
                 "T_Kunai_Wrap_Natural_BC. The gallery's preview material adds a cloth SHEEN term (a shading model, "
                 "not a map: in Unreal use the Cloth shading model's fuzz for the same read)"),
        "gate_adaptations": [
            "hero_plate / top_plate: a knife reads its steel COAT pixels (flat up-facing steel: not a knife facet, a wall "
            "or the cloth wrap), like a bar; the whole object and the wrap are reported beside it",
            "hero_walls / hero_facets_near / top_facets: the cloth wrap (mask blue) is left out - the gates are about "
            "steel walls and ground edges, a dark cloth grip is neither",
            "pack_consistency: the kunai's coat pixels against PACK_COAT_ANCHOR (the anchor forms' own plate pixels) "
            "within 0.05; its whole-object and wrap figures are information (pack_consistency.knife_whole_object); the "
            "hero backdrop gate at the 12 fixed frame points applies as to every form",
            "the top view: its own frame (0.18 m tall, 5.0 px/mm; the pack's 0.13 m frame is 0.231 m wide) centred on "
            "the bounding box, the top lamps moved with the centre",
            "uv: every material slot's UV0 inside its own unit tile (the wrap in u 1..2) instead of the whole mesh in "
            "0..1 (pack.uv_tile_check)",
        ],
    }
    report["texture_layout"] = {
        "steel": ("T_Kunai_Plain_BC / _ORM / _N, 2048 x 2048, UV tile u 0..1, 13.4 px/mm (134 px/cm, the pack's 134-170 "
                  "band; the 147 mm head island is what limits it): head top and bottom as planar islands, the 0.15 mm "
                  "knife lands unfolded onto the top island along the edge they hang from, the remaining walls (run-out, "
                  "shoulder, neck, the hidden rear face) as strips unrolled along the outline, the ring's flat top and "
                  "bottom as planar islands and its inner / outer walls with their rounds as strips (seam under the rear "
                  "neck), the rear neck"),
        "wrap": ("T_Kunai_Wrap_BC / _ORM / _N (+ T_Kunai_Wrap_Natural_BC), 1024 x 1024, UV tile u 1..2, 10 px/mm: the "
                 "whole grip unrolled as ONE island (seam on -Z) with the lettering band a rectangle inside it "
                 "(3.10.1: its own island left a seam round the band that read as an outlined panel), and the two cut "
                 "ends as their own islands"),
        "lettering": "T_Kunai_Lettering, 1536 x 256, 8-bit greyscale, blank; sampled through the band's rectangle",
        "why_two_tiles": ("the two slots sample different maps; keeping the wrap's islands in tile u 1..2 means no UV0 "
                          "triangle overlaps another anywhere on the mesh (qa_check's rule, and Unreal generates the "
                          "lightmap UV from non-overlapping charts); Wrap texture addressing - Unreal's and Blender's "
                          "default - reads u 1..2 from the same texels as u 0..1"),
        "unused_texels": "outside every island + the 16 px bake margin: the covered texels' mean (BC, ORM), a flat normal",
        "why_the_lands_are_on_the_top_island": ("as part of the wall strip the lands made a 140 mm x 0.15 mm chart that "
                                                "Unreal's lightmap packer, which sees only a chart's texels, laid across the "
                                                "wrap's chart (UV1 overlap on LOD0 / LOD1 in the build's first Unreal run); "
                                                "unfolded, they belong to the head's big chart"),
        "note_on_report_uv": ("the generic 'uv' block measures both tiles together against one 2048 map (its px_per_cm "
                              "mixes the steel's 134 with the wrap's 100 at the wrong map size): use this block and "
                              "uv_layout.tiles"),
    }
    physics = report.get("physics") or {}
    exact = physics.get("mass_kg_override_exact")
    if exact is not None:
        physics["mass_kg_override"] = round(exact, 4)
        physics["source"] = ("the finished kunai: ground steel (LOD0 mesh volume x 7.85 g/cm3) + the wrap's tape (0.75) "
                             "and wooden core (0.70) - the assembled mass")
        physics["decision"] = (f"ONE figure: {round(exact, 4)} kg, the assembled LOD0 (the pack rule: the physics "
                               "override is the finished mass). The study's 0.19 kg was the WINGED kunai's. Set it on the "
                               "StaticMeshComponent's Body Instance in the throwing Blueprint, with the Center Of Mass "
                               "Offset from collision_choice.unreal_com_nudge_cm (Unreal derives the centre of mass from "
                               "the hulls at uniform density)")
    gaps = []
    for gap in report["known_gaps"]:
        if gap.startswith("LOD0 UV coverage is") or gap.startswith("Physics: the Mass in KG override") \
                or gap.startswith("The baked maps are 2048 px per form") or gap.startswith("Knife grind (style pass 2)"):
            continue
        gaps.append(gap)
    report["known_gaps"] = [
        "The Unreal side has no M_Shuriken_Master or M_Kunai_Wrap asset yet (pack-wide): the validation import runs with "
        "import_materials=False, so both slots bind to WorldGridMaterial until the pack's materials are built; the wrap "
        "material's lettering graph (TexCoord -> the band rectangle remapped to 0..1 -> T_Kunai_Lettering, clamped, "
        "masked outside the band -> lerp to the ink) is documented in LETTERING_HOWTO.md, not built.",
    ] + gaps + [
        f"Physics: the Mass in KG override ({physics.get('mass_kg_override')} kg, the assembled LOD0) and the Center Of "
        "Mass Offset (collision_choice.unreal_com_nudge_cm) are recorded here only; they have to be set on the component "
        "in the throwing Blueprint.",
        "The winged (three-prong) head is not built: KunaiSpec.prongs exists and defaults OFF, and KunaiPlan refuses it "
        "(the fork, crotch fillets and prong edges were paused work, WorkFiles/kunai/winged_wip_scripts_2026-09-19, "
        "untested). Bringing it back is a new outline chain in kunai_spec.KunaiPlan, then its own build and gates.",
        "The kunai's top view is drawn at 5.0 px/mm (its own 0.18 m frame), not the pack's common 6.9 px/mm: a 280 mm "
        "knife does not fit the 0.13 m frame. The line sheet labels it.",
        "Pack consistency compares the kunai like with like: its steel coat pixels against the anchor forms' plate "
        "pixels; its whole-object statistics (a third of it is dark cloth) are reported, not gated.",
        "The study's winged LOD table (1,600-2,800 / 650-1,100 / 220-400) does not apply: the plain kunai's LOD bands "
        "are its own (1,000-2,600 / 400-900 / 150-400), nothing padded. 3.10.1 raised LOD0's ceiling from 2,000 "
        "because the tape's overlap is modelled: the wrap is ~1,300 of its triangles.",
        "The lettering mask is 1536 x 256 (the band's 6:1 at square texels), not a power of two: Unreal imports such a "
        "PNG with Mip Gen Settings 'NoMipmaps', and Power Of Two Mode 'Stretch to power of two' does NOT reset that "
        "(3.10.1, measured twice in fresh processes). ue_import_textures.py sets Mip Gen Settings 'From Texture Group' "
        "as well and fails verification on NoMipmaps; a buyer importing by hand must set both.",
        "The assembled mass (ground steel + wrap) is under the study's plain range because the tape is modelled as it "
        "is wound: 0.5 mm of cotton, doubled over the 1 mm overlap (the study's '1 mm tape' as one layer gave 4.3 g of "
        "tape, the wound model 2.6 g). The MASS GATE is the un-ground steel and is unaffected. A core at the study's "
        "upper density (0.8 g/cm3 instead of 0.7) would add ~1.5 g.",
        "The two hulls carry 26 and 32 vertices against study 5's estimate of 10-16 and 12-20: the head hull needs its "
        "plan chain at both edge thicknesses plus the ridge line, and the grip hull the octagons, the wound-down end "
        "sections and the ring. Both are mirror-symmetric, contain every LOD's vertices and stop exactly at the tip.",
        "The steel's texel density (13.2 px/mm area-weighted on the head) is the pack's lowest: the 146.5 mm head "
        "island laid straight along u caps a 2048 map at 13.8 px/mm. Splitting the head island would buy ~1.5 px/mm "
        "and cost a seam across the blade.",
        "The front neck keeps the pack's 0.45 mm non-cutting chamfer, not the study's 0.5-1.0 mm round: it is the same "
        "treatment as the stars' scallops, and the shoulder runs the knife grind out into it.",
        "The hero is still nearly end-on (yaw -25): that is what keeps the diamond's coat inside the pack band. A 3/4 "
        "or side beauty shot for the Fab listing is a user decision; the review's black-slot artifact is gone either "
        "way. The kunai also rests on its 20 mm grip, so the 5 mm blade hovers ~7.5 mm above the floor, as a real one "
        "does until it tips onto its point.",
    ]
    report.setdefault("form_gates", {})
    report["form_gates"].update({
        "franchise_names_clean": bool(report["franchise_gate"]["passed"]),
        "lettering_band_island_and_blank_mask": bool(report["lettering"]["gate"]["passed"]),
        "two_material_slots_every_lod": bool(report["material_slots_gate"]["passed"]),
        "uv0_no_collapsed_faces_every_lod": bool(report["uv_area_gate"]["passed"]),
    })


def _form():
    from shuriken_lib import Form, KunaiGeometry  # needs bpy; SPEC above does not
    geometry = KunaiGeometry(SPEC)

    def annotate_all(report: dict) -> None:
        report["collision_choice"] = dict(geometry.hull_choice or {})
        report["collision_choice"]["hulls"] = geometry.hull_info
        report["collision_choice"]["decision"] = (
            "TWO hulls (study 5): the head (blade + bare neck) and the grip + rear neck + ring. The plain head is 36 mm "
            "wide against the winged 100 mm, which removes the winged head's worst case (a 100 mm prong span in one "
            "hull), but ONE hull still has to span the 21 mm grip and the 5 mm blade together: its top and bottom run "
            "from the grip's collars (+-11 mm) down to the tip, ~8 mm of invisible collider above and below the blade at "
            "its widest (one_over_two x the two hulls' volume), so a kunai stuck in a wall or hitting a character would "
            "touch 5-8 mm before the steel does. Two hulls follow the blade (head hull 1.2 x the steel head) and the "
            "grip. A third (the ring apart from the grip) would take a further 21 % off at the ring end (three_hulls_mm3) "
            "- the wedge between the wrap's end and the ring - for one more shape per collision test; not taken: the "
            "study's plan is two, and the ring end is behind the hand. Unreal derives the centre of mass from the hulls "
            "(uniform density): hull_derived_centre_of_mass_mm, corrected by unreal_com_nudge_cm")
        annotate(report)
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate_all, report_name="kunai_plain_report.json",
                geometry=geometry)


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_kunai_plain.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(parser)
    parser.add_argument("--fbx", default=str(DEFAULT_FBX))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args(blender_argv(argv))


def main() -> int:
    from shuriken_lib import run_single
    return run_single(FORM, parse_args())


if __name__ == "__main__":
    sys.exit(main())
