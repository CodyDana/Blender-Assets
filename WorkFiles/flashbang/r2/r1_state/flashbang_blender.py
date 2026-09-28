#!/usr/bin/env python
"""props_lib.flashbang_blender - MeshBuilder -> Blender objects, the part split, sockets, hulls, mass (bpy).

Everything numeric comes from props_lib.flashbang_geom / flashbang_spec; this module only turns it into Blender data
the pipeline helpers can export.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import flashbang_geom as G
from .flashbang_spec import FLASHBANG, FlashbangSpec, DENSITY as RHO

MM = 0.001
SHARP_DEG = 35.0
PART_SETS = {
    "assembled": None,
    "body": {"tube", "sleeve", "cap", "fuze"},
    "pullring": {"ring", "pin"},
    "lever": {"lever"},
}


def island_index_table(packing: G.Packing) -> Dict[str, int]:
    return {n: i + 1 for i, n in enumerate(sorted(packing.place))}


def to_blender(mb: G.MeshBuilder, packing: G.Packing, name: str, parts: Optional[set] = None,
               frame: Optional[Matrix] = None, materials: Sequence[bpy.types.Material] = (),
               lm_packing: Optional[G.Packing] = None) -> bpy.types.Object:
    """Build one mesh object (metres) from the builder's faces whose part is in ``parts`` (None = all), with
    vertices mapped through ``frame``'s inverse (the part mesh's pivot), UV0 = the packed atlas, UV1 = a copy
    (or the same islands re-packed with lightmap padding), face attributes fb_look / fb_island,
    material slots by LOOK, smooth faces and sharp edges above SHARP_DEG."""
    faces = [f for f in mb.faces if parts is None or f.part in parts]
    used = sorted({i for f in faces for i in f.v})
    remap = {old: new for new, old in enumerate(used)}
    V = np.array([mb.verts[i] for i in used], float) * MM
    if frame is not None:
        inv = np.array(frame.inverted())
        V = (inv[:3, :3] @ V.T).T + inv[:3, 3]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in V], [], [tuple(remap[i] for i in f.v) for f in faces])
    me.update(calc_edges=True)
    assert len(me.polygons) == len(faces), (len(me.polygons), len(faces))
    uv0 = me.uv_layers.new(name="UVMap")
    uvs = []
    for f in faces:
        for (u, v) in f.uv:
            uvs.extend(packing.uv(f.island, u, v))
    uv0.data.foreach_set("uv", np.array(uvs, np.float32))
    uv1 = me.uv_layers.new(name="Lightmap")
    if lm_packing is not None:
        lm = []
        for f in faces:
            for (u, v) in f.uv:
                lm.extend(lm_packing.uv(f.island, u, v))
        uv1.data.foreach_set("uv", np.array(lm, np.float32))
    else:
        uv1.data.foreach_set("uv", np.array(uvs, np.float32))
    me.uv_layers.active_index = 0
    isl = island_index_table(packing)
    a_look = me.attributes.new("fb_look", "INT", "FACE")
    a_look.data.foreach_set("value", np.array([f.look for f in faces], np.int32))
    a_isl = me.attributes.new("fb_island", "INT", "FACE")
    a_isl.data.foreach_set("value", np.array([isl[f.island] for f in faces], np.int32))
    for m in materials:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array([G.LOOK_SLOT[f.look] for f in faces], np.int32)
                            if len(materials) > 1 else np.zeros(len(faces), np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    # sharp edges by dihedral angle, plus every UV-island boundary between different islands is left smooth
    bm = bmesh.new()
    bm.from_mesh(me)
    sharp = np.zeros(len(bm.edges), bool)
    lim = math.radians(SHARP_DEG)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.calc_face_angle(0.0) > lim:
                sharp[e.index] = True
        else:
            sharp[e.index] = True
    bm.free()
    attr = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    attr.data.foreach_set("value", sharp)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def fix_island_handedness(mb: G.MeshBuilder):
    """Flip an island's u (in its parameter space) when its UV winding disagrees with the 3D face orientation, so
    no island is mirrored (MikkTSpace and the normal map need that)."""
    V = np.array(mb.verts)
    votes: Dict[str, float] = {}
    for f in mb.faces:
        P = V[list(f.v[:3])]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        uv = np.array(f.uv[:3])
        a = (uv[1, 0] - uv[0, 0]) * (uv[2, 1] - uv[0, 1]) - (uv[2, 0] - uv[0, 0]) * (uv[1, 1] - uv[0, 1])
        area3 = np.linalg.norm(n)
        votes[f.island] = votes.get(f.island, 0.0) + (np.sign(a) * area3)
    flip = {k for k, v in votes.items() if v < 0}
    for f in mb.faces:
        if f.island in flip:
            f.uv = tuple((-u, v) for (u, v) in f.uv)
    return sorted(flip)


# =============================================================================== sockets (rules on the built parts)
def socket_frames(spec: FlashbangSpec, com_mm) -> Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    """name -> (position mm, rotation deg XYZ as wanted in Unreal expressed in Blender local space)."""
    px, pz = spec.pin_c
    kx, _ky, kz = spec.knuckle_c
    return {
        "Grip": ((0.0, 0.0, spec.grip_z()), (0.0, 0.0, 0.0)),
        "Throw": (tuple(round(float(c), 1) for c in com_mm), (0.0, 0.0, 0.0)),
        "Pin": ((px, spec.pin_eye_y(), pz), (0.0, 0.0, -90.0)),
        "LeverHinge": ((kx, 0.0, kz), (0.0, 0.0, 0.0)),
        "Flash": ((0.0, 0.0, sorted(spec.hole_rows_z)[1]), (0.0, 0.0, 0.0)),
    }


def frame_matrix(pos_mm, rot_deg) -> Matrix:
    return Matrix.Translation(Vector(pos_mm) * MM) @ Euler(tuple(math.radians(a) for a in rot_deg), "XYZ").to_matrix().to_4x4()


# =============================================================================== mass model
def mass_model(spec: FlashbangSpec) -> Dict[str, object]:
    """Analytic volumes x densities (plan 6.3): steel shells, brass tube + charge, fuze, lever, ring.  mm, g."""
    s = spec
    parts = []

    def cyl_shell(name, r_out, r_in, z0, z1, rho, cx=0.0, cy=0.0, frac=1.0):
        v = math.pi * (r_out ** 2 - r_in ** 2) * (z1 - z0) * frac / 1000.0     # cm3
        parts.append((name, v * rho, (cx, cy, 0.5 * (z0 + z1))))

    hole_area = len(s.hole_thetas()) * 3 * math.pi * (s.body_r * math.radians(s.hole_ang_w_deg / 2)) * (s.hole_h / 2)
    tube_area = 2 * math.pi * s.body_r * (s.sleeve_z0 - s.body_z0)
    cyl_shell("outer_tube", s.body_r, s.body_r_in, s.body_z0, s.sleeve_z0, RHO["steel"], frac=1 - hole_area / tube_area)
    cyl_shell("sleeve", s.sleeve_r, s.inner_tube_r, s.sleeve_z0, s.sleeve_top_z, RHO["steel"])
    cyl_shell("base_cap", s.cap_apothem * 1.01, 0.0, 0.0, s.body_z0, RHO["steel"], frac=0.55)   # hollowed cap
    cyl_shell("brass_tube", s.inner_tube_r, s.inner_tube_r - 0.8, s.body_z0, s.sleeve_z0, RHO["brass"])
    cyl_shell("charge", s.inner_tube_r - 0.8, 0.0, s.body_z0, s.sleeve_z0, RHO["charge"], frac=0.8)
    cyl_shell("collar", s.collar_r, 0.0, s.collar_z0, s.collar_z1, RHO["steel"], frac=0.5)
    h = s.housing_half
    parts.append(("housing", (2 * h) ** 2 * (s.housing_z1 - s.housing_z0) * 0.45 / 1000 * RHO["steel"],
                  (0.0, 0.0, 0.5 * (s.housing_z0 + s.housing_z1))))
    parts.append(("top_plate", (s.plate_x[1] - s.plate_x[0]) * 2 * s.plate_y * (s.plate_z1 - s.housing_z1) / 1000
                  * RHO["steel"], (0.5 * (s.plate_x[0] + s.plate_x[1]), 0.0, 0.5 * (s.housing_z1 + s.plate_z1))))
    lever_len = 150.0
    parts.append(("lever", s.lever_mass_kg * 1000.0, (s.lever_lower_x + 1.1, 0.0, 95.0)))
    px, pz = s.pin_c
    parts.append(("ring_pin", s.ring_mass_kg * 1000.0, (px, s.pin_eye_y() - 5.0, pz - 18.0)))
    m = sum(p[1] for p in parts)
    com = np.sum([np.array(p[2]) * p[1] for p in parts], axis=0) / m
    return {"parts": [{"name": n, "g": round(g, 2), "centroid_mm": [round(c, 2) for c in cc]} for n, g, cc in parts],
            "model_mass_g": round(m, 1), "com_mm": [round(float(c), 2) for c in com],
            "note": "analytic volumes x densities (steel 7.85, brass 8.5, charge 1.6 g/cm3); the physics override is "
                    "the design mass 0.30 kg, the centre of mass is what Throw carries"}


def hull_com(hulls: Sequence[bpy.types.Object]) -> Tuple[List[float], float]:
    """Volume centroid of the union-approximating hulls (sum over hulls; overlap small)."""
    vol_tot = 0.0
    c_tot = np.zeros(3)
    for h in hulls:
        me = h.data
        me.calc_loop_triangles()
        V = np.array([v.co[:] for v in me.vertices])
        o = V.mean(axis=0)
        for t in me.loop_triangles:
            a, b, c = (V[i] - o for i in t.vertices)
            vol = np.dot(a, np.cross(b, c)) / 6.0
            vol_tot += vol
            c_tot += vol * (o + (a + b + c) / 4.0)
    return [round(float(x) * 1000, 2) for x in c_tot / vol_tot], vol_tot


__all__ = ["to_blender", "fix_island_handedness", "socket_frames", "frame_matrix", "mass_model", "hull_com",
           "PART_SETS", "MM"]
