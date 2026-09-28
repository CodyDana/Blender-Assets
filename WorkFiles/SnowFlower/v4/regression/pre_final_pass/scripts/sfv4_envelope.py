"""Snow Flower v4: the blade and guard envelope handed to the sheath (measured on the SHIPPED LOD0 and
on the v4 high-poly), written to WorkFiles/SnowFlower/v4/blade_envelope_v4.json.

    blender -b --factory-startup --python sfv4_envelope.py
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_spec as S  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "blade_envelope_v4.json"


def verts_of(objs):
    out = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        a = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", a)
        a = a.reshape(-1, 3)
        m = np.array(o.matrix_world)
        out.append(a @ m[:3, :3].T + m[:3, 3])
        o.evaluated_get(dg).to_mesh_clear()
    return np.vstack(out) * 1000.0


def slices(V, z0, z1, step):
    rows = []
    for z in np.arange(z0, z1, step):
        sel = (V[:, 2] >= z) & (V[:, 2] < z + step)
        if not sel.any():
            continue
        P = V[sel]
        rows.append({"z": round(float(z + step / 2), 2), "x_min": round(float(P[:, 0].min()), 3),
                     "x_max": round(float(P[:, 0].max()), 3), "y_min": round(float(P[:, 1].min()), 3),
                     "y_max": round(float(P[:, 1].max()), 3)})
    return rows


def main():
    game = ROOT / "Assets" / "SnowFlower" / "SnowFlower_Game_v4.blend"
    bpy.ops.wm.open_mainfile(filepath=str(game))
    V0 = verts_of([bpy.data.objects["SM_SnowFlower_LOD0"]])
    blade0 = V0[V0[:, 2] > S.Z_PENDANT_TIP]
    guard0 = V0[(V0[:, 2] > S.Z_COLLAR_BOT) & (V0[:, 2] <= S.Z_PENDANT_TIP + 0.01)]
    high = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "SnowFlower_HighPoly_v4.blend"
    with bpy.data.libraries.load(str(high)) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("SF4_H_blade") or n.startswith("SF4_H_relief")
                       or n.startswith("SF4_H_guard")]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
    VH = verts_of([o for o in dst.objects if not o.name.startswith("SF4_H_guard")])
    VG = verts_of([o for o in dst.objects if o.name.startswith("SF4_H_guard")])
    zs = np.arange(S.Z_PENDANT_TIP, S.Z_TIP, 10.0)
    analytic = [{"z": round(float(z), 1), "spine_x": round(float(S.spine_x(z)), 3), "edge_x": round(float(S.edge_x(z)), 3),
                 "width": round(float(S.width(z)), 3), "steel_half_thickness_max": round(float(0.5 * S.thickness(z)), 3)}
                for z in zs]
    env = {
        "frame": "millimetres, sword model frame: origin = Grip socket (primary-hand centre on the grip axis), "
                 "+Z toward the tip, +X = blade SPINE side (the tip sweeps toward +X), -X = cutting edge, "
                 "-Y = front face (the sheet's FRONT VIEW face)",
        "overall_mm": [S.Z_POMMEL_TOP, S.Z_TIP],
        "guard_seat_plane_z": S.Z_PENDANT_TIP,
        "guard_seat_note": "lowest guard point = the front/back pendant leaf tips (z 128.5); the sheath mouth rim "
                           "sits here when sheathed; SOCKET BladeBase is on this plane at the blade centre line",
        "blade_visible_mm": [S.Z_PENDANT_TIP, S.Z_TIP],
        "blade_length_from_guard_seat_mm": round(S.Z_TIP - S.Z_PENDANT_TIP, 2),
        "tip_xyz_mm": [float(S.spine_x(S.Z_TIP)), 0.0, S.Z_TIP],
        "spine_sweep_mm": round(S.SWEEP_MM, 3), "sweep_starts_z": S.SWEEP_Z0,
        "sweep_law": "spine_x(z) = 22.4 + 9.4 * clip((z - 680) / 360, 0, 1) ** 1.9",
        "width_table_mm": S.WIDTH_TABLE,
        "thickness_law": "spine thickness 6.2 mm at z 104 -> 2.3 mm at 92 % of the blade, closing to the point",
        "analytic_profile_10mm": analytic,
        "shipped_lod0_blade_slices_5mm": slices(blade0, S.Z_PENDANT_TIP, S.Z_TIP + 0.01, 5.0),
        "highpoly_blade_relief_slices_5mm": slices(VH[VH[:, 2] > S.Z_PENDANT_TIP], S.Z_PENDANT_TIP, S.Z_TIP + 0.01, 5.0),
        "blade_envelope_lod0": {"x": [round(float(blade0[:, 0].min()), 3), round(float(blade0[:, 0].max()), 3)],
                                "y": [round(float(blade0[:, 1].min()), 3), round(float(blade0[:, 1].max()), 3)]},
        "blade_envelope_high": {"x": [round(float(VH[VH[:, 2] > S.Z_PENDANT_TIP][:, 0].min()), 3),
                                      round(float(VH[VH[:, 2] > S.Z_PENDANT_TIP][:, 0].max()), 3)],
                                "y": [round(float(VH[VH[:, 2] > S.Z_PENDANT_TIP][:, 1].min()), 3),
                                      round(float(VH[VH[:, 2] > S.Z_PENDANT_TIP][:, 1].max()), 3)]},
        "guard_lod0": {"x": [round(float(guard0[:, 0].min()), 3), round(float(guard0[:, 0].max()), 3)],
                       "y": [round(float(guard0[:, 1].min()), 3), round(float(guard0[:, 1].max()), 3)],
                       "z": [round(float(guard0[:, 2].min()), 3), round(float(guard0[:, 2].max()), 3)]},
        "guard_below_z110_lod0 (pendant pocket the throat must clear)":
            {"x": [round(float(guard0[guard0[:, 2] > 110][:, 0].min()), 3), round(float(guard0[guard0[:, 2] > 110][:, 0].max()), 3)],
             "y": [round(float(guard0[guard0[:, 2] > 110][:, 1].min()), 3), round(float(guard0[guard0[:, 2] > 110][:, 1].max()), 3)]},
        "guard_high": {"x": [round(float(VG[:, 0].min()), 3), round(float(VG[:, 0].max()), 3)],
                       "y": [round(float(VG[:, 1].min()), 3), round(float(VG[:, 1].max()), 3)],
                       "z": [round(float(VG[:, 2].min()), 3), round(float(VG[:, 2].max()), 3)]},
        "sockets_mm": {k: list(v) for k, v in S.socket_positions().items()},
        "holster_rule": "sheath SOCKET Holster = where the sword's Grip socket (= mesh pivot) sits when fully sheathed; "
                        "the sword needs zero rotation relative to it. Guard seat plane is 128.5 mm above the pivot along +Z.",
    }
    OUT.write_text(json.dumps(env, indent=1), encoding="utf-8")
    print("SF4_ENVELOPE", json.dumps({k: env[k] for k in ("blade_envelope_lod0", "blade_envelope_high", "guard_lod0",
                                                           "tip_xyz_mm")}))


main()
