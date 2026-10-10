"""gunlib 0.2.0 new-module tests, one headless Blender process (SMG_BUILD_PLAN 5 rail tests + W1a):

    blender -b --factory-startup --python Scripts/guns/gunlib/tests/test_parts.py -- [--out json]

1. Every new generator (rail_1913, mag_box, hinge, sights_flip, hardware) built through gunlib.parts.build_part at
   gunlib.lod levels 0-3: closed manifold (bl.manifold_report) and UD1-UD2 (gunlib.ud.check_object) on every object.
2. Rail: slot pitch and width measured by ray scans on the BUILT LOD0 rail (rays down the centre line; the floor hits
   between the walls) within 0.01 mm of 10.01 / 5.24; the profile widths (V, top flat, neck) measured by rays across.
3. Sights: the demo aperture + post pair on the rail, its triangles dumped and measured by gunlib.drivers.b4 in the
   aperture mode (post tip at the aperture centre within 0.2 mm, post visible, no occluder).
4. Magazine fit (straight path): a test well (walls 0.3 mm off the mag, a top shelf 1.5 mm above it, a rear window)
   and a paddle catch whose nose sits in the mag's notch, through gunlib.drivers.magfit_check.straight_gates (M1-M5b,
   F5): proves the generic straight-insert gate set on geometry with known answers.
Writes WorkFiles/guns/smg/scratch/regression/parts_test.json (folded into gates/gunlib_regression.json).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(ROOT / "Scripts"))

import bpy  # noqa: E402,F401  (Blender only)
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from gunlib import LIB_VERSION, bl, lod, ud  # noqa: E402
from gunlib import gateutil as GU  # noqa: E402
from gunlib.mesh import box  # noqa: E402
from gunlib.parts import PartDef, build_composite, build_part  # noqa: E402
from gunlib.parts import hardware as HW  # noqa: E402
from gunlib.parts import hinge as HG  # noqa: E402
from gunlib.parts import mag_box as MB  # noqa: E402
from gunlib.parts import rail_1913 as RL  # noqa: E402
from gunlib.parts import sights_flip as SF  # noqa: E402

argv = GU.argv_after_dashes()
OUT = Path(GU.opt(argv, "--out") or ROOT / "WorkFiles" / "guns" / "smg" / "scratch" / "regression" / "parts_test.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
ZERO = np.zeros(3)
RES = {"lib_version": LIB_VERSION, "date": time.strftime("%Y-%m-%dT%H:%M:%S"), "levels": {}, "checks": []}


def log(*a):
    print("[gunlib-test]", *a, flush=True)


def check(name, value, ok, threshold):
    RES["checks"].append({"name": name, "value": value, "threshold": threshold, "pass": bool(ok)})
    log("PASS" if ok else "FAIL", name, json.dumps(value, default=str)[:300])
    OUT.write_text(json.dumps(RES, indent=1, default=str))


# ------------------------------------------------------------------------------------------------ the test parts
RAIL_KW = dict(n_slots=28, pad_rear=1.0, pad_front=2.0, height=10.2, cut=[0] + list(range(2, 24)) + [27],
               flats=[(262.0, 268.0)])
RAIL_M4 = RL.placement((0.0, 0.0, 0.0))


def build_level(level, coll):
    lod.set_level(level)
    built = {}
    rail_p, rail_rec = RL.part("rail", RAIL_M4, slot="M_Metal", **RAIL_KW)
    built["rail"] = build_part(rail_p, coll, ZERO)
    # sights on the rail (rail frame = gun frame here)
    if level < 3:
        demo = SF.demo_pair(rail_rec, 0, 27)
        for nm, d in demo.items():
            if nm.startswith("_"):
                continue
            built[nm] = build_composite(nm, d["pieces"], coll, ZERO, bone=d["bone"], cutters=d["cutters"],
                                        joint=d.get("joint"))
    # magazine (mag frame placed 200 mm to the side)
    M4 = MB.placement((0.0, 120.0, 0.0), (0, 0, 1), (1, 0, 0))
    parts, mrec = MB.magazine(46.6, 29.0, -170.0, 60.0, wall=3.0,
                              lips={"opening": 12.0, "x_front": 12.0, "height": 3.0},
                              notch={"z_top": 30.0, "width": 8.0, "height": 5.0, "depth": 2.5},
                              ladder={"x0": -16.0, "x1": 12.0, "z0": -150.0, "z1": -40.0, "depth": 1.0,
                                      "ties": [-110.0, -75.0]},
                              spine={"z0": -165.0, "z1": 55.0, "width": 6.0, "proud": 0.8},
                              plate={"thickness": 7.5, "overhang": 1.5, "tab_hole": (0.0, 0.0, 8.0)}, M4=M4)
    for p in parts:
        built[p.name] = build_part(p, coll, ZERO)
    # hinge: a fixed / moving knuckle stack on a vertical axle, the axle, a latch bolt, a detent boss
    hp, hd = (0.0, -80.0, -20.0), (0.0, 0.0, 1.0)
    ks = HG.knuckle_stack(hp, hd, [(0.0, 12.0, "fixed"), (12.0, 28.0, "moving"), (28.0, 40.0, "fixed")], 6.0, 3.0,
                          radial=0.15, axial=0.15)
    built["hinge_fixed"] = build_part(PartDef("hinge_fixed", ks["fixed"][:1], unions=ks["fixed"][1:],
                                              cls="M-chamfer", recipe=[(0.3, 1, 40.0)]), coll, ZERO)
    built["hinge_moving"] = build_part(PartDef("hinge_moving", ks["moving"], cls="M-chamfer", recipe=[(0.3, 1, 40.0)]),
                                       coll, ZERO)
    built["hinge_axle"] = build_part(PartDef("hinge_axle", [HG.pin(hp, hd, -1.0, 41.0, 3.0, 0.3,
                                                                   head={"r": 4.5, "h": 1.5, "end": 1})],
                                             cls="M-chamfer", recipe=[]), coll, ZERO)
    built["latch_bolt"] = build_part(PartDef("latch_bolt", [HG.latch_bolt((20.0, -80.0, 10.0), (0, 1, 0), 0.0, 14.0,
                                                                          2.0, (4.0, 10.4, 1.25))],
                                             cls="M-chamfer", recipe=[]), coll, ZERO)
    built["detent_boss"] = build_part(PartDef("detent_boss", [HG.detent_boss((40.0, -80.0, 0.0), (0, 0, 1), 1.5, 1.2)],
                                              cls="M-chamfer", recipe=[]), coll, ZERO)
    # hardware: one of each head on a test plate's surface (each its own part)
    hw = {"hw_flush_pin": HW.flush_pin(4.0, 6.0, 0.15), "hw_roll_pin": HW.roll_pin(3.0, 6.0, 0.1),
          "hw_rivet_domed": HW.rivet(6.0, 1.6, 3.0, 4.0, True), "hw_rivet_flat": HW.rivet(6.0, 1.2, 3.0, 4.0, False),
          "hw_socket_cap": HW.socket_cap(4.0), "hw_button_head": HW.button_head(4.0),
          "hw_countersunk": HW.countersunk(4.0)}
    for i, (nm, m) in enumerate(hw.items()):
        mm = HW.place(m, (60.0 + 15.0 * i, -80.0, 0.0), (0, -1, 0), (1, 0, 0))
        cut = [HW.place(HW.slot_cutter(4.0), (60.0 + 15.0 * i, -80.0, 0.0), (0, -1, 0), (1, 0, 0))] \
            if nm == "hw_pan_slotted" and level < 2 else []
        built[nm] = build_part(PartDef(nm, [mm], cls="M-chamfer", recipe=[], post_cutters=cut), coll, ZERO)
    lod.set_level(0)
    return built, rail_rec, mrec


def level_report(built):
    rows = {}
    for nm, ob in built.items():
        mr = bl.manifold_report(ob)
        u = ud.check_object(ob)
        rows[nm] = {"triangles": u["triangles"], "boundary_edges": mr.get("boundary_edges"),
                    "multi_face_edges": mr.get("multi_face_edges"), "shells": mr.get("shells"),
                    "unreal_drops": u["unreal_drops"] + u["unreal_drops_polygons"], "min_area_mm2": u["min_area_mm2"],
                    "min_edge_mm": u["min_edge_mm"], "min_height_mm": u["min_height_mm"],
                    "strip_polygons": u["strip_polygons_under_0.1mm"], "needle_groups": u.get("needle_groups"),
                    "edge_on_groups": u.get("edge_on_groups"), "pass_ud1": u["pass_ud1"], "pass_ud2": u["pass_ud2"],
                    "closed": not mr.get("boundary_edges") and not mr.get("multi_face_edges")}
        if not (u["pass_ud1"] and u["pass_ud2"]):
            rows[nm]["locate"] = ud.locate(ob, 8)                  # where the failures sit (mm)
            rows[nm]["strips_at"] = u.get("strip_polygons_at_mm_width")
    return rows


def rail_measure(ob, rec):
    V, T = bl.tris_np(ob)
    t = BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in x) for x in T], all_triangles=True)
    H = rec["height"]
    floor = H - RL.D_VBOT
    out = {"slots": {}}
    for k in (0, 2, 3, 12, 23, 27):
        xc = rec["slot_centres"][k]
        xs = np.arange(xc - 3.5, xc + 3.5, 0.002)
        on = []
        for x in xs:
            h = t.ray_cast(Vector((x, 0.0, H + 5.0)), Vector((0, 0, -1)), 50.0)
            on.append(h[0] is not None and abs(h[0][2] - floor) < 0.005)
        on = np.array(on)
        idx = np.nonzero(on)[0]
        a, b = xs[idx[0]] - 0.001, xs[idx[-1]] + 0.001
        out["slots"][k] = {"x0": round(float(a), 4), "x1": round(float(b), 4), "width": round(float(b - a), 4),
                           "centre": round(float(0.5 * (a + b)), 4)}
    c = out["slots"]
    pitches = [(c[b]["centre"] - c[a]["centre"]) / (b - a) for a, b in ((2, 3), (3, 12), (12, 23), (0, 27))]
    out["pitches"] = [round(p, 5) for p in pitches]
    out["max_pitch_err"] = round(max(abs(p - RL.PITCH) for p in pitches), 5)
    out["max_width_err"] = round(max(abs(v["width"] - RL.SLOT_W) for v in c.values()), 5)

    def width_at(z, x):
        hl = t.ray_cast(Vector((x, -50.0, z)), Vector((0, 1, 0)), 100.0)
        hr = t.ray_cast(Vector((x, 50.0, z)), Vector((0, -1, 0)), 100.0)
        return None if hl[0] is None or hr[0] is None else round(float(hr[0][1] - hl[0][1]), 4)
    xt = 0.5 * (rec["slot_centres"][5] + rec["slot_centres"][6])          # mid tooth
    out["profile"] = {"V_width (at the V faces)": width_at(H - 0.5 * (RL.D_VTOP + RL.D_VBOT), xt),
                      "top_flat (0.05 below the top)": width_at(H - 0.05, xt),
                      "neck (1 mm under the neck top)": width_at(H - RL.D_NECK - 1.0, xt)}
    return out


def sights_b4(built, rail_rec):
    names = ["rail", "rear_sight_base", "rear_sight_leaf", "front_sight_base", "front_sight_leaf"]
    path = OUT.parent / "parts_test_sights.npz"
    bl.export_npz([built[n] for n in names], str(path), (0, 0, 0))
    demo = SF.demo_pair(rail_rec, 0, 27)
    slp = OUT.parent / "parts_test_sightline.json"
    slp.write_text(json.dumps(demo["_sight_line"]))
    import subprocess
    js = OUT.parent / "parts_test_b4.json"
    subprocess.run(["py", "-3", "-B", str(HERE / "b4_aperture_check.py"), str(path), str(slp), str(js),
                    str(OUT.parent / "parts_test_b4.png")], check=True, stdout=subprocess.DEVNULL)
    r = json.loads(js.read_text())
    return {k: r.get(k) for k in ("pass", "error", "lateral_offset_mm", "vertical_offset_mm", "aperture", "post",
                                   "occluders_in_aperture_px")}


def magfit_test():
    """A test well + paddle catch round a mag_box magazine in the mag frame (= the gun frame here, vertical)."""
    coll = bl.collection("MagFitTest")
    L, Tk, wall = 46.6, 29.0, 3.0
    parts, rec = MB.magazine(L, Tk, -170.0, 60.0, wall=wall, prefix="tmag", lips={"opening": 12.0, "x_front": 12.0, "height": 3.0},
                             notch={"z_top": 30.0, "width": 8.0, "height": 5.0, "depth": 2.5},
                             plate={"thickness": 7.5, "overhang": 1.5})
    for p in parts:
        build_part(p, coll, ZERO)
    c = 0.3
    hx, hy = L / 2.0 + c, Tk / 2.0 + c
    # receiver block with the well (open below), the top shelf 1.5 above the mag top, a rear window for the nose
    rcv = box(-hx - 4.0, hx + 4.0, -hy - 4.0, hy + 4.0, 0.0, 75.0)
    well = box(-hx, hx, -hy, hy, -1.0, 61.5)
    win = box(-hx - 5.0, -hx + 0.5, -4.6, 4.6, 24.0, 32.5)
    build_part(PartDef("trcv", [rcv], cls="P-round", cutters=[well, win], recipe=[]), coll, ZERO)
    # paddle catch: pivot behind the rear wall, nose into the notch (engagement 1.8, bearing gap 0.1)
    xn0 = -L / 2.0 + 1.8
    pivot = np.array([xn0, 0.0, -40.0])                 # below the nose tip: the nose leaves rearward, not up
    nose = box(-hx - 6.0, xn0, -3.5, 3.5, 25.5, 29.9)
    arm = box(-hx - 9.0, -hx - 5.0, -3.5, 3.5, -8.0, 30.0)
    build_part(PartDef("tcatch", [arm], cls="M-chamfer", unions=[nose], recipe=[]), coll, ZERO)

    class Cfg:
        grip = np.zeros(3)
        magfit = {"catch_pivot_M": pivot.tolist(), "catch_axis": [0.0, 1.0, 0.0], "release_deg": -11.0,
                  "mag_origin_M": [0.0, 0.0, 0.0], "mag_axes_M": {"x": [1, 0, 0], "z": [0, 0, 1]}, "insert_mm": 80.0,
                  "well_band": [2.0, 58.0], "lip_z": 0.0, "well_parts": ["trcv"], "half_thickness": Tk / 2.0,
                  "half_length": L / 2.0}
    from gunlib.drivers import magfit_check as MFC
    S = MFC.MagFitScene(Cfg, "MagFitTest", ("tmag", "tmag_follower", "tmag_floor_plate"), "tcatch")
    gates = MFC.straight_gates(S, Cfg.magfit)
    return {g["name"]: {"value": g["value"], "pass": g["pass"]} for g in gates}


def main():
    bl.reset_scene()
    for level in (0, 1, 2, 3):
        coll = bl.collection(f"L{level}")
        t0 = time.time()
        built, rail_rec, mrec = build_level(level, coll)
        rows = level_report(built)
        RES["levels"][f"LOD{level}"] = {"parts": rows, "seconds": round(time.time() - t0, 1)}
        bad = {n: r for n, r in rows.items() if not (r["closed"] and r["pass_ud1"] and r["pass_ud2"])}
        check(f"LOD{level}: every new-module part closed, UD1 + UD2", {"parts": len(rows), "failing": bad},
              not bad, "closed manifold; unreal_drops 0, min area >= 0.01 mm2; 0 edges < 0.05, 0 needles, 0 strips, "
                       "0 needle / edge-on corners")
        if level == 0:
            rm = rail_measure(built["rail"], rail_rec)
            RES["rail"] = {"record": {k: rail_rec[k] for k in ("length", "height", "cut", "top_z", "floor_z", "profile")},
                           "measured": rm}
            pr = rm["profile"]
            ok = rm["max_pitch_err"] <= 0.01 and rm["max_width_err"] <= 0.01 and \
                abs(pr["V_width (at the V faces)"] - 21.2) <= 0.01 and abs(pr["neck (1 mm under the neck top)"] - 15.67) <= 0.01
            check("rail slot pitch / width / profile (ray-measured on the built LOD0 rail)",
                  {"pitches": rm["pitches"], "max_pitch_err": rm["max_pitch_err"], "max_width_err": rm["max_width_err"],
                   "profile": pr}, ok, "pitch 10.01 and width 5.24 within 0.01 mm; V 21.2, neck 15.67 within 0.01")
            RES["mag_record_checks"] = mrec["checks"]
            b4 = sights_b4(built, rail_rec)
            check("sights_flip demo pair: B4 aperture method (post tip at the aperture centre)", b4, b4.get("pass"),
                  "|lateral|, |vertical| <= 0.2 mm; post visible >= 1 mm; no occluder")
    mf = magfit_test()
    RES["magfit_straight"] = mf
    must = [n for n in mf if not n.startswith("M5b")]
    check("magfit_check straight gate set on the test well (known answers)",
          {n: (v["pass"], v["value"]) for n, v in mf.items()}, all(mf[n]["pass"] for n in must),
          "M1, M2 (bearing 0.1, overtravel 1.5, seam 0.3), M3 (0.3, engagement 1.8), M4 (ride <= 2.1), M4b, M5, F5 pass")
    RES["status"] = "pass" if all(c["pass"] for c in RES["checks"]) else "fail"
    RES["failed"] = [c["name"] for c in RES["checks"] if not c["pass"]]
    OUT.write_text(json.dumps(RES, indent=1, default=str))
    log("DONE", RES["status"], RES["failed"])


main()
