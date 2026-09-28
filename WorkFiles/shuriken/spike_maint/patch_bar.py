"""One-off source patch for shuriken_lib/bar.py (spike maintenance, library 3.8.1).  Plain Python."""
from pathlib import Path

p = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib\bar.py")
s = p.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)


rep('''Smoothing by class, as in the other generators: every edge between two classes is hard; the
round (K >= 2) is smooth-shaded across its chords (a rounded arris, reported like the senban's
curved facets); the point / tail facets and faces are single planes, flat.''',
    '''Smoothing by class, as in the other generators: every edge between two classes is hard; the
round (K >= 2) is smooth-shaded across its chords (a rounded arris, reported like the senban's
curved facets); the point / tail facets and faces are single planes, flat.  3.8.1 (geometry
review): the round's corner normals are written as custom split normals - the ANALYTIC arc
normal at every chord vertex ((P - C) / rho, C the arc centre, N.x = 0) - instead of Blender's
corner-angle-weighted average, which the slanted run-outs skewed (9 deg off the arc bisector
between chords 0 and 1, a 1 deg twist along the bar, an 11.25 deg crease at the faces).  The
round now meets both faces tangent-continuously and every corner normal lies within half a
chord's turn (90 / 2K deg) of its own chord; every other loop keeps its face normal.''')

rep('''    layer = bm.faces.layers.int[FACE_CLASS_ATTR]
    ground = [1.0 if BAR_CLASSES[f[layer]] in GROUND_CLASSES else 0.0 for f in bm.faces]
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
''', '''    layer = bm.faces.layers.int[FACE_CLASS_ATTR]
    ground = [1.0 if BAR_CLASSES[f[layer]] in GROUND_CLASSES else 0.0 for f in bm.faces]
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    if lod.arris_segments >= 2:
        stats["custom_normals"] = write_round_normals(mesh, o)
''')

rep('''# =========================================================================== hull, sockets, unwrap
''', '''def write_round_normals(mesh, o: BarOutline) -> dict:
    """Custom split normals: the analytic arc normal on every arris-round loop, the face normal elsewhere.

    A round vertex (y, z) lies on the arc of radius rho about the corner's centre
    C = (sign(y) (a - rho), sign(z) (a - rho)); its normal is (0, y - Cy, z - Cz) / rho.  The
    classes come from the generator's temporary face-class attribute (still on the mesh here).
    """
    code = BAR_CLASS_CODE["round"]
    classes = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.attributes[FACE_CLASS_ATTR].data.foreach_get("value", classes)
    centre = o.a - o.rho
    normals, worst_radius = [], 0.0
    for poly in mesh.polygons:
        face_n = tuple(poly.normal)
        for li in poly.loop_indices:
            if classes[poly.index] != code:
                normals.append(face_n)
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            dy, dz = co.y - math.copysign(centre, co.y), co.z - math.copysign(centre, co.z)
            r = math.hypot(dy, dz)
            worst_radius = max(worst_radius, abs(r - o.rho))
            normals.append((0.0, dy / r, dz / r))
    mesh.normals_split_custom_set(normals)
    mesh.update()
    return {"method": "analytic arc normal (0, P - C) / rho on every arris-round loop; face normal elsewhere",
            "round_vertex_radius_error_mm": round(worst_radius / MM, 9)}


# =========================================================================== hull, sockets, unwrap
''')

rep('''    """``UCX_<obj.name>_NN``: the un-rounded bar itself (16 vertices: butt, tail base, point base, tip flat).

    The spike is convex, so its convex hull is the bar with square arrises: exactly C4, 28
    triangles, every LOD inside it (the round only removes material).''',
    '''    """``UCX_<obj.name>_NN``: the un-rounded bar itself (16 vertices: butt, tail base, point base, tip flat).

    The convex hull of the UN-ROUNDED bar (the bar is convex, so that is the square-arris bar
    itself): identical to LOD2, exactly C4, 28 triangles; LOD0 and LOD1 lie inside it with up to
    the round's 0.124 mm of slack at the arrises (the round only removes material).''')

rep('''        return hull, ("bar_prism: shuriken_lib.bar.author_bar_hull, the un-rounded bar itself (16 vertices: butt, "
                      "tail base, point base, tip flat; 28 triangles) - the spike is convex, so this is its exact "
                      "convex hull less the arris round; exactly C4, encloses every LOD")''',
    '''        return hull, ("bar_prism: shuriken_lib.bar.author_bar_hull, the convex hull of the UN-ROUNDED bar (the "
                      "square-arris bar itself: 16 vertices at the butt, tail base, point base and tip flat; 28 "
                      "triangles; identical to LOD2); exactly C4; encloses every LOD, LOD0 with up to 0.124 mm of "
                      "slack at the arrises where the 0.3 mm round takes material off")''')

start = s.index("def bar_unwrap(obj, island_margin: float) -> dict:")
end = s.index("# =========================================================================== measurement")
s = s[:start] + '''SIDE_ACROSS = ("+z", "-z", "+y", "-y")


def bar_uv_layout(o: BarOutline, texture_px: Tuple[int, int]) -> dict:
    """Deterministic island rectangles (pixels, origin at the map's lower-left corner) and the density.

    One texel density for every island, set by the strips: the bar's length spans the map's
    width less a BAR_UV_BORDER_PX border at either end.  Each side strip RESERVES the full +-a
    section (the square-arris LOD's corners at +-a sit inside it; LOD0's islands end at the
    round's diagonal, 0.088 mm short); strips are stacked with BAR_UV_GAP_PX between them, the butt
    and the tip flat share the last row.
    """
    width, height = texture_px
    border, gap = BAR_UV_BORDER_PX, BAR_UV_GAP_PX
    px_per_m = (width - 2 * border) / o.length
    strip = 2.0 * o.a * px_per_m
    rows, y = {}, float(border)
    for key in ("+z", "+y", "-z", "-y"):
        rows[key] = {"x0": float(border), "y0": y, "w": o.length * px_per_m, "h": strip, "half": o.a}
        y += strip + gap
    tau = max(o.tau, 1e-6)
    butt, tip = 2.0 * o.e * px_per_m, 2.0 * tau * px_per_m
    rows["butt"] = {"x0": float(border), "y0": y, "w": butt, "h": butt, "half": o.e}
    rows["tip"] = {"x0": border + butt + gap, "y0": y, "w": tip, "h": tip, "half": tau}
    top = y + max(butt, tip)
    if top + border > height + 1e-9 or border + o.length * px_per_m > width - border + 1e-9:
        raise ValueError(f"bar UV layout needs {width} x {top + border:.1f} px, the map is {width} x {height}")
    return {"texture_px": [int(width), int(height)], "px_per_m": px_per_m, "px_per_cm": px_per_m / 100.0,
            "border_px": border, "gap_px": gap, "rects": rows, "used_height_px": round(top + border, 3)}


def bar_unwrap(obj, o: BarOutline, texture_px: Tuple[int, int]) -> dict:
    """LOD0 UV0: one planar island per side of the bar, laid out deterministically (no packer).

    Every face goes to the side its normal points at (the four faces with their point facet,
    tail facet and the half of each arris round on their side; the tip flat; the butt) and
    is projected along that side's normal: u along the bar, v across it (u x v = the outward
    normal, so no island is mirrored), at ONE texel density that is isotropic in pixels on the
    non-square map (``bar_uv_layout``).  One planar projection per island is what the LOD1..n
    transfer needs (shuriken_lib.uv fits an exact affine map per island).

    3.8.1 (geometry review): the pack's packer (scaled margin 0.005) packed the 2046 px strips
    2.5-4x tighter than every other form - 1.66 px between islands, 0.83 px to the border - and
    LOD2's square corners, 0.088 mm past LOD0's islands, overlapped the neighbouring island and
    were clamped (1.2 px off the island map, two loops onto u = 0).  Here every strip reserves
    the full section, so every LOD maps through its island's exact affine map, BAR_UV_GAP_PX apart
    and BAR_UV_BORDER_PX from the border.
    """
    layout = bar_uv_layout(o, texture_px)
    width, height = texture_px
    ppm = layout["px_per_m"]
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    data = mesh.uv_layers[0].data
    counts: Dict[str, int] = {}
    for poly in mesh.polygons:
        key = _uv_group(poly.normal)
        counts[key] = counts.get(key, 0) + 1
        u_axis, v_axis = UV_FRAMES[key]
        rect = layout["rects"][key]
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            cu = co.x * u_axis[0] + co.y * u_axis[1] + co.z * u_axis[2]
            cv = co.x * v_axis[0] + co.y * v_axis[1] + co.z * v_axis[2]
            if key in SIDE_ACROSS:
                pu = rect["x0"] + (cu - o.x_butt) * ppm
            else:
                pu = rect["x0"] + (cu + rect["half"]) * ppm
            pv = rect["y0"] + (cv + rect["half"]) * ppm
            data[li].uv = (pu / width, pv / height)
    mesh.update()
    layout["rects"] = {k: {kk: round(vv, 4) for kk, vv in r.items()} for k, r in layout["rects"].items()}
    return {"method": ("shuriken_lib.bar.bar_unwrap: one planar projection per side (+-Z, +-Y faces with their facets "
                       "and half-rounds, the tip flat, the butt), u along the bar, laid out deterministically at one "
                       "texel density on a non-square map (bar_uv_layout; no packer): each side strip reserves the full "
                       "section, BAR_UV_GAP_PX between islands, BAR_UV_BORDER_PX to the border"),
            "faces_per_island": counts, "layout": layout}


''' + s[end:]

rep('''from .bar_spec import (BAR_CLASS_CODE, BAR_CLASSES, GROUND_CLASSES, BarLodSpec, BarOutline, BarSpec, bar_analytic,
                       bar_triangles)''', '''from .bar_spec import (BAR_CLASS_CODE, BAR_CLASSES, BAR_UV_BORDER_PX, BAR_UV_GAP_PX, GROUND_CLASSES, BarLodSpec,
                       BarOutline, BarSpec, bar_analytic, bar_triangles)''')

rep('''    def custom_unwrap(self, obj, island_margin: float):
        return bar_unwrap(obj, island_margin)''', '''    def custom_unwrap(self, obj, island_margin: float):
        return bar_unwrap(obj, self.o, self.spec.texture_px)

    # --- 3.8.1 optional hooks (pack.py's defaults are the old code paths)
    noun = "spike"
    outline_wording = "outline (the un-ground bar: square arrises, a sharp point, no tip flat)"
    fill_unused_texels = True

    def texture_size(self, default):
        return tuple(int(v) for v in self.spec.texture_px)

    def lod_deviation_headline(self) -> str:
        # every LOD0 vertex lies on one of LOD2's planes, so the one-sided rev2 metric reads 0.0 there
        return "two_sided"

    def bounds_radius(self, lod0) -> float:
        """Unreal's bounds-sphere radius (from the bounding-box centre), which the screen sizes are built from."""
        co = np.array([v.co[:] for v in lod0.data.vertices], dtype=np.float64)
        centre = 0.5 * (co.min(axis=0) + co.max(axis=0))
        return float(np.max(np.linalg.norm(co - centre, axis=1)))

    def surface_snapshot(self, obj) -> dict:
        from .measure import surface_snapshot
        snap = surface_snapshot(obj, 4)
        snap.pop("tip_radius_per_arm_mm", None)          # a star's figure: meaningless on a bar
        co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
        snap.update({"x_tip_mm": round(float(co[:, 0].max()) / MM, 6), "x_butt_mm": round(float(co[:, 0].min()) / MM, 6),
                     "section_mm": [round(float(np.ptp(co[:, 1])) / MM, 6), round(float(np.ptp(co[:, 2])) / MM, 6)]})
        return snap''')

rep('''__all__ = ["BarGeometry", "author_bar_hull", "author_bar_lod", "bar_centroid", "bar_quadrant", "bar_topology_quality",
           "bar_unwrap",''', '''__all__ = ["BarGeometry", "author_bar_hull", "author_bar_lod", "bar_centroid", "bar_quadrant", "bar_topology_quality",
           "bar_unwrap", "bar_uv_layout", "write_round_normals",''')
p.write_text(s, encoding="utf-8")
print("patched bar.py")
