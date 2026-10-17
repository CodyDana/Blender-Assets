"""W1b gates A1-A5 for SM_Att_Scope_LongRange on the built bytes: the gun blend opened, the scope's triangles from
scratch/w1/scope_tris.npz (frame M). Writes gates/scope_form.json.

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_scope_gates.py
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import GRIP, SCRATCH, GATES, D  # noqa: E402
import sr_motion as MO  # noqa: E402
from gunlib import fit, bl  # noqa: E402

GUN = {}
BONE = {}
for o in bpy.data.objects:
    # only the form parts: the final blend also holds the game stage's collision hulls (UCX_*) and LOD/twin copies,
    # which are not gun parts (a UCX hull hugging the rail read as a 0.0001 mm "clash" with the scope ring)
    if o.type == "MESH" and not o.name.startswith(("UCX_", "SM_", "SK_")) and "_LOD" not in o.name:
        V, T = bl.tris_np(o)
        GUN[o.name] = (V + GRIP, T)
        BONE[o.name] = json.loads(o.get("gun_part", "{}")).get("bone", "body")
z = np.load(SCRATCH / "scope_tris.npz", allow_pickle=True)
names = [str(n) for n in z["names"]]
SC = {}
for k, n in enumerate(names):
    T = z["T"][z["lab"] == k]
    idx = np.unique(T)
    remap = -np.ones(len(z["V"]), int)
    remap[idx] = np.arange(len(idx))
    SC[n] = (z["V"][idx], remap[T])
rep = json.loads((SCRATCH / "scope_build_report.json").read_text())
SA = D["scope_attachment"]
gates = []


def g(name, value, thr, ok, note=None):
    r = {"name": name, "value": value, "threshold": thr, "pass": bool(ok)}
    if note:
        r["note"] = note
    gates.append(r)


# A1: the rear ring's recoil lug centre = Mount = Rail_Top + 2 slots
slot0 = float(D["sockets"]["gun"][[s["socket"] for s in D["sockets"]["gun"]].index("Rail_Top")]["M_mm"][0])
pitch = 10.01
V = SC["scope_ring_2"][0]
lug = V[(V[:, 2] < 29.9) & (np.abs(V[:, 1]) < 7.5)]
lx = 0.5 * (lug[:, 0].min() + lug[:, 0].max())
g("A1 Mount (rear ring lug centre) at Rail_Top + 2 x 10.01", round(lx, 3), f"{slot0 + 2 * pitch:.2f} +-0.05",
  abs(lx - (slot0 + 2 * pitch)) <= 0.05, "Mount M %s; front ring on slot 12 (X %.2f)" % (SA["mount_M"], SA["ring_X"][1]))

# A2: lugs in their slots, fore-aft gap per side (rail slot walls)
a2 = {}
for rn in ("scope_ring_2", "scope_ring_12"):
    V = SC[rn][0]
    lug = V[(V[:, 2] < 29.9) & (np.abs(V[:, 1]) < 7.5)]
    x0, x1 = lug[:, 0].min(), lug[:, 0].max()
    k = round((0.5 * (x0 + x1) - slot0) / pitch)
    c = slot0 + k * pitch
    a2[rn] = {"slot": int(k), "rear_gap": round(x0 - (c - 2.62), 3), "front_gap": round((c + 2.62) - x1, 3)}
g("A2 ring recoil lugs in their slots, fore-aft gap per side (slot 5.24)", a2, "0.1-0.4",
  all(0.1 <= v[s] <= 0.4 for v in a2.values() for s in ("rear_gap", "front_gap")))

# A3: >= 2 mm from every gun part at rest (the rings bear on the rail by design: rings vs rail / receiver excluded),
# over the bolt cycle (bolt group moving) and over the riser travel
rest = []
for sn, sg in SC.items():
    for gn, gg in GUN.items():
        if sn.startswith("scope_ring") and gn in ("rail", "rail_screws", "receiver"):
            continue
        rest.append((sn, gn))
geo = {**{("s:" + k): v for k, v in SC.items()}, **{("g:" + k): v for k, v in GUN.items()}}
gaps = fit.min_gaps(geo, [("s:" + a, "g:" + b) for a, b in rest], 1.0, 6.0)
worst = min(gaps, key=lambda r: r["min_gap_mm"])
ring_rail = fit.min_gaps(geo, [("s:scope_ring_2", "g:rail"), ("s:scope_ring_12", "g:rail")], 0.25, 1.0)
g("A3 scope >= 2 mm from every gun part at rest", {"min_mm": worst["min_gap_mm"], "pair": [worst["a"], worst["b"]]},
  ">= 2.0 (cap 6)", worst["min_gap_mm"] >= 2.0, "rings on the rail (butt contact): %s" % ring_rail)
sc_all = np.vstack([v[0] for v in SC.values()])
off, Ts = 0, []
for v in SC.values():
    Ts.append(v[1] + off)
    off += len(v[0])
tS = fit.tree(sc_all, np.vstack(Ts))
bolt_parts = [n for n in GUN if BONE[n] == "bolt"]
pts = np.vstack([bl.surface_samples(*GUN[n], 1.0) for n in bolt_parts])
best = (1e9, None)
for u in np.linspace(0, 1, 161):
    d, _ = fit.nearest_dist(fit.apply(MO.bolt_cycle_param(u), pts), tS, 60.0)
    if d < best[0]:
        best = (d, round(float(u), 3))
g("A3 / F6 bolt group to the scope over rotate 0..-60 + slide 0..88", {"min_mm": round(best[0], 2), "at_u": best[1]},
  ">= 2.0 (F6: handle >= 20)", best[0] >= 2.0)
kn = bl.surface_samples(*GUN["bolt_handle"], 1.0)
kn = kn[np.linalg.norm(kn - np.array(D["bolt_cycle"]["knob_rest"]), axis=1) <= 12.6]     # the knob (F6 = knob)
kb = min(fit.nearest_dist(fit.apply(MO.bolt_cycle_param(u), kn), tS, 80.0)[0] for u in np.linspace(0, 1, 161))
g("F6 bolt knob to the mounted scope over rotate + slide (real attachment)", round(kb, 2), ">= 20 (W0 29.9)", kb >= 20.0)
rp = np.vstack([bl.surface_samples(*GUN[n], 1.0) for n in GUN if BONE[n] == "cheek_riser"])
rb = min(fit.nearest_dist(fit.apply(MO.riser(dz), rp), tS, 60.0)[0] for dz in np.linspace(-12.9, 12.0, 50))
g("A3 cheek riser travel -12.9..+12 to the scope", round(rb, 2), ">= 2.0", rb >= 2.0)

# A4: Sight on the tube axis Z 57.6 above the bore, parallel to the bore; EyePoint over the riser
B = SC["scope_body"][0]
oc = B[np.abs(B[:, 0] - B[:, 0].min()) < 0.05]
ob = B[np.abs(B[:, 0] - B[:, 0].max()) < 0.05]
c0 = 0.5 * (oc.min(0) + oc.max(0))
c1 = 0.5 * (ob.min(0) + ob.max(0))
ang = math.degrees(math.atan2(math.hypot(c1[1] - c0[1], c1[2] - c0[2]), c1[0] - c0[0]))
g("A4 Sight Z above the bore (eyepiece face centre)", round(float(c0[2]), 3), "57.6 +-0.2", abs(c0[2] - 57.6) <= 0.2,
  "Sight M %s (local %s)" % ([round(float(v), 2) for v in c0], [round(float(c0[0] - SA["mount_M"][0]), 2), 0.0,
                                                            round(float(c0[2] - SA["mount_M"][2]), 2)]))
g("A4 scope axis parallel to the bore", round(ang, 4), "<= 0.05 deg", ang <= 0.05)
ex = float(c0[0] - SA["eye_relief"])
g("A4 EyePoint (95 mm relief) over the cheek riser", round(ex, 2), "inside riser X 68.9..179.9", 68.9 <= ex <= 179.9)

# A5 budget + topology
tris = int(sum(r.get("triangles", 0) for r in rep.values()))
g("A5 scope LOD0 triangles (target 6-10k, ceiling 12k)", tris, "<= 12000 (target <= 10000)", tris <= 12000,
  "over the 10k target by %d" % (tris - 10000) if tris > 10000 else None)
closed = all(r["boundary_edges"] == 0 and r["multi_face_edges"] == 0 for r in rep.values())
g("A5 closed manifold parts; 2 slots (body, lens)", {"closed": closed, "slots": sorted({r["slot"] for r in rep.values()})},
  "all closed; 2 slots", closed and len({r["slot"] for r in rep.values()}) == 2,
  "qa_check on the exported SM_Att_Scope_LongRange runs at W3 export (no export in W1)")
drops = sum((r.get("ud") or {}).get("unreal_drops") or 0 for r in rep.values())
g("UD1 Unreal degenerate rule (scope)", drops, "0", drops == 0)

failed = [x["name"] for x in gates if not x["pass"]]
out = {"stage": "W1b SM_Att_Scope_LongRange form", "date": dt.datetime.now().isoformat(timespec="seconds"),
       "status": "pass" if not failed else "partial", "failed": failed, "gates": gates,
       "files": {"blend": "Assets/Guns/Att_Scope_LongRange.blend (built at the mounted pose in gun frame M; Empty "
                          "'Mount' = attachment origin)",
                 "renders": ["Renders/Guns/SR01/form_real_scope_q34.png", "Renders/Guns/SR01/form_real_scope_rings_close.png",
                             "Renders/Guns/SR01/form_real_scope_rear_q.png", "Renders/Guns/SR01/form_grey_scope_right.png",
                             "Renders/Guns/SR01/form_real_scope_deployed_hero.png"]},
       "details": {"build_report": rep, "rest_gaps_lowest": sorted(gaps, key=lambda r: r["min_gap_mm"])[:8]}}
(GATES / "scope_form.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
print(json.dumps({"status": out["status"], "failed": failed}, indent=1))
for x in gates:
    print("[A]", x["name"], "|", x["value"], "|", x["pass"])
