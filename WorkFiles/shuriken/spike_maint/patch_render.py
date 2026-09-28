"""One-off source patch (spike maintenance, library 3.8.1): render.py.

Every addition is read with a default that is the old behaviour, so the plate forms render as before:
hero rig scale (bar only), backdrop points (measured on every shot; gated in pack_consistency), a bar's
side-face gates (dark-dot count, wall anchor), the LOD strip's end-on section insets (bar only)."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib")
name = "render.py"
p = root / name
s = p.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


rep('''Form-dependent inputs, and only these: the ground sits at -thickness/2, the LOD camera''',
    '''3.8.1 (spike maintenance, visual review), again read with defaults that are the old behaviour:

* ``hero_rig_match`` (a bar): the dolly fit puts the camera ~0.30 m from a 150 mm bar against ~0.22 m
  for the stars, and the larger frame showed more floor - the key's floor reflection ended at 0.88 of
  the frame width (a dark wedge down the right edge) and rake A's reflection glowed in the top-right
  corner.  The hero lamps are scaled about the origin by the fitted camera distance over
  HERO_RIG_REFERENCE_M (the anchor forms' mean), sizes x s and power x s^2: every lamp keeps its
  direction, solid angle and radiance, so the lighting reads the same from the camera and the plate
  forms (scale 1, nothing touched) render exactly as before.  The lamps are restored after the hero.
* ``image_stats`` reports ``backdrop_points`` on every shot: backdrop luminance (11 x 11 px median, the
  object and 3 px around it excluded) at BACKDROP_POINTS, fixed frame fractions at the corners and down
  the right third; ``pack_consistency`` gates every form's hero backdrop against PACK_BACKDROP_ANCHOR (the
  anchor forms' range at each point) +- BACKDROP_TOLERANCE.
* A bar's side faces (``bar_wall_gate``; mask red = |N.z| < 0.5, not blue = not ground): their
  luminance (``bar_wall_luminance``) and an isolated dark-dot count (``dark_dots``: blobs of <= 16 px and
  <= 5 px across in the face interior, eroded 4 px, at least 30 % darker than the 7 x 7 median of the
  face around them) - the pits on the hero side face read as black pepper at 8.3 dots / 10k px (stars'
  plates 0.03-0.08, reference 0.74).  render gate ``hero_bar_walls``: dots <= BAR_WALL_DOT_GATE; and
  ``pack_consistency`` gates the side face's p50 against PACK_WALL_ANCHOR (the anchor forms' hero wall p50).
* ``lod_section_inset`` (a bar): the plan-view LOD strip cannot show the 0.3 mm arris round (4 chords /
  2 / square), so each LOD gets an end-on section of its butt end beside it at that scale.

Form-dependent inputs, and only these: the ground sits at -thickness/2, the LOD camera''')

rep('''HERO_CENTRE = (0.5, 0.47)         # camera-view coordinates (y up): 0.53 of the height from the top''',
    '''# 3.8.1: the hero lamps of a ``hero_rig_match`` form are scaled by its fitted camera distance over this, the mean
# fitted distance of the anchor forms (four-point 201.161, eight-point 222.455, senban 223.475 mm; render_rig.
# hero_depth_of_field.focus_mm of the 3.8.0 build).
HERO_RIG_REFERENCE_M = 0.215697
# Backdrop points (3.8.1): (x, y) frame fractions, x from the left, y from the top; 11 x 11 px medians.
BACKDROP_POINTS = {"tl": (0.0125, 0.0222), "tr": (0.9875, 0.0222), "bl": (0.0125, 0.9778), "br": (0.9875, 0.9778),
                   "r28": (0.9875, 0.28), "r50": (0.9875, 0.50), "r78": (0.9875, 0.78),
                   "q11": (0.90, 0.11), "q50": (0.90, 0.50), "q78": (0.90, 0.78), "t03": (0.80, 0.03), "t97": (0.80, 0.97)}
BACKDROP_PATCH_HALF = 5
BACKDROP_TOLERANCE = 0.05
# The anchor forms' hero backdrop at each point, [min, max] (3.8.0 build renders; WorkFiles/shuriken/spike_maint/
# backdrop_probe.py).  A form's point must lie within [min - tol, max + tol]; a point covered by the object is skipped.
PACK_BACKDROP_ANCHOR = {
    "forms": ("four_point", "eight_point", "square_plate"),
    "source": "hero backdrop of the anchor forms, 3.8.0 build (spike_maint/backdrop_probe.py)",
    "hero": {"tl": (0.4070, 0.4555), "tr": (0.3535, 0.3653), "bl": (0.3725, 0.4000), "br": (0.3958, 0.4280),
             "r28": (0.4826, 0.5297), "r50": (0.6403, 0.7187), "r78": (0.5336, 0.6050), "q11": (0.4003, 0.4123),
             "q50": (0.7381, 0.7498), "q78": (0.6314, 0.6431), "t03": (0.3683, 0.3770), "t97": (0.4518, 0.4661)},
}
# A bar's side faces, like with like (3.8.1): their hero p50 against the anchor forms' hero WALL p50 (0.2272 /
# 0.2373 / 0.3390 in the 3.8.0 reports) within PACK_P50_TOLERANCE.
PACK_WALL_ANCHOR = {"forms": ("four_point", "eight_point", "square_plate"),
                    "source": "render_stats.<form>_persp.wall_luminance.p50, 3.8.0 build", "hero": {"p50": 0.2678}}
# Isolated dark dots on a bar's hero side faces (pits read as pepper): per 10k face-interior px, at 30 % darker.
BAR_WALL_DOT_GATE = {"threshold": 0.70, "max_per_10k": 1.0, "erode_px": 4, "window_px": 7, "max_blob_px": 16,
                     "max_blob_extent_px": 5}
LOD_STRIP_INSET_GAP = 0.012       # m between a bar and its end-on section inset
HERO_CENTRE = (0.5, 0.47)         # camera-view coordinates (y up): 0.53 of the height from the top''')

# ---------------------------------------------------------------- wire_pair: optional basis
rep('''def wire_pair(source, coll, name: str, offset=(0.0, 0.0, 0.0), thickness: float = 0.00016):
    """Flat-lit copy plus a Wireframe-modifier copy floated just above it."""
    solid = source.copy()
    solid.data = source.data.copy()
    solid.name = f"PREVIEW_{name}Solid"
    solid.parent = None
    solid.matrix_world = Matrix.Translation(offset)''', '''def wire_pair(source, coll, name: str, offset=(0.0, 0.0, 0.0), thickness: float = 0.00016, basis=None):
    """Flat-lit copy plus a Wireframe-modifier copy floated just above it.

    ``basis`` (3.8.1): an optional 4x4 rotation / scale applied before the offset (the bar's end-on insets)."""
    solid = source.copy()
    solid.data = source.data.copy()
    solid.name = f"PREVIEW_{name}Solid"
    solid.parent = None
    solid.matrix_world = Matrix.Translation(offset) if basis is None else Matrix.Translation(offset) @ basis''')
rep('''    wires.matrix_world = Matrix.Translation((offset[0], offset[1], offset[2] + 0.0006))''',
    '''    lifted = Matrix.Translation((offset[0], offset[1], offset[2] + 0.0006))
    wires.matrix_world = lifted if basis is None else lifted @ basis''')

# ---------------------------------------------------------------- image_stats: backdrop points, bar walls, dots
rep('''def image_stats(beauty: Path, mask: Path, n: int = 4) -> dict:
    """Read a render back and report what a buyer will actually see.

    ``mask`` is the wall-mask pass: alpha is the subject's coverage, red is 1 on faces with
    |N.z| < 0.5 (walls and steep facet segments).
    """''', '''def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(radius):
        step = out.copy()
        for axis in (0, 1):
            step &= np.roll(out, 1, axis=axis)
            step &= np.roll(out, -1, axis=axis)
        out = step
    return out


def dark_dots(lum: np.ndarray, region: np.ndarray, gate: dict = BAR_WALL_DOT_GATE, thresholds=(0.80, 0.70)) -> Optional[dict]:
    """Isolated dark dots inside ``region`` (3.8.1; the visual review's pepper metric).

    The interior is ``region`` eroded by ``erode_px``; a pixel is dark when it is below ``threshold`` x the
    median of the ``region`` pixels in the ``window_px`` square around it; dark pixels are grouped 8-connected
    and a group of at most ``max_blob_px`` pixels and ``max_blob_extent_px`` across is a dot.  Per 10k interior px.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    core = _erode(region, gate["erode_px"])
    count = int(core.sum())
    if count < 500:
        return None
    r = gate["window_px"] // 2
    ys, xs = np.nonzero(core)
    y0, y1, x0, x1 = ys.min() - r, ys.max() + r + 1, xs.min() - r, xs.max() + r + 1
    padded = np.full((y1 - y0, x1 - x0), np.nan, dtype=np.float32)
    sy0, sy1, sx0, sx1 = max(y0, 0), min(y1, lum.shape[0]), max(x0, 0), min(x1, lum.shape[1])
    padded[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = np.where(region[sy0:sy1, sx0:sx1], lum[sy0:sy1, sx0:sx1], np.nan)
    windows = sliding_window_view(padded, (2 * r + 1, 2 * r + 1))
    median = np.nanmedian(windows[ys - y0, xs - x0].reshape(count, -1), axis=1)
    values = lum[ys, xs]
    out = {"interior_px": count, "window_px": gate["window_px"], "erode_px": gate["erode_px"]}
    for threshold in thresholds:
        dark = values < median * threshold
        points = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(ys[dark], xs[dark]))}
        parent = list(range(len(points)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        keys = list(points)
        for i, (y, x) in enumerate(keys):
            for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                j = points.get((y + dy, x + dx))
                if j is not None:
                    a, b = find(i), find(j)
                    if a != b:
                        parent[a] = b
        groups: Dict[int, list] = {}
        for i in range(len(keys)):
            groups.setdefault(find(i), []).append(keys[i])
        dots = 0
        for members in groups.values():
            gy = [m[0] for m in members]
            gx = [m[1] for m in members]
            if len(members) <= gate["max_blob_px"] and max(max(gy) - min(gy), max(gx) - min(gx)) + 1 <= gate["max_blob_extent_px"]:
                dots += 1
        key = f"{int(round((1.0 - threshold) * 100))}pct"
        out[key] = {"dark_px_per_1000": round(float(dark.sum()) / count * 1000.0, 3),
                    "dots": dots, "dots_per_10k_px": round(dots / count * 1e4, 3)}
    return out


def backdrop_points(lum: np.ndarray, selection_any: np.ndarray) -> dict:
    """Backdrop luminance at BACKDROP_POINTS: 11 x 11 px medians, the object and 3 px around it excluded."""
    excluded = _dilate(selection_any, 3)
    height, width = lum.shape
    out = {}
    for key, (fx, fy) in BACKDROP_POINTS.items():
        cx, cy = int(round(fx * (width - 1))), int(round(fy * (height - 1)))
        y0, y1 = max(cy - BACKDROP_PATCH_HALF, 0), min(cy + BACKDROP_PATCH_HALF + 1, height)
        x0, x1 = max(cx - BACKDROP_PATCH_HALF, 0), min(cx + BACKDROP_PATCH_HALF + 1, width)
        valid = ~excluded[y0:y1, x0:x1]
        out[key] = round(float(np.median(lum[y0:y1, x0:x1][valid])), 4) if valid.mean() >= 0.5 else None
    return out


def image_stats(beauty: Path, mask: Path, n: int = 4, bar: bool = False) -> dict:
    """Read a render back and report what a buyer will actually see.

    ``mask`` is the wall-mask pass: alpha is the subject's coverage, red is 1 on faces with
    |N.z| < 0.5 (walls and steep facet segments), green the chamfer facets, blue a bar's ground
    surfaces.  ``bar`` (3.8.1) adds the side-face luminance and the dark-dot counts.
    """''')
rep('''        background = lum[~selection]
        stats["backdrop_luminance_mean"] = round(float(background.mean()), 4)''',
    '''        background = lum[~selection]
        stats["backdrop_luminance_mean"] = round(float(background.mean()), 4)
        stats["backdrop_points"] = backdrop_points(lum, alpha > 0.02)
        if bar:
            side = selection & (mask_px[..., 0] > 0.5) & (mask_px[..., 2] <= 0.5)
            if side.any():
                side_lum = lum[side]
                side_rgb = rgb[side].mean(axis=0)
                stats["bar_wall_luminance"] = {
                    "pixels": int(side.sum()),
                    "fraction_of_object": round(float(side.sum() / selection.sum()), 5),
                    "mean": round(float(side_lum.mean()), 4),
                    "p05": round(float(np.percentile(side_lum, 5)), 4),
                    "p50": round(float(np.percentile(side_lum, 50)), 4),
                    "p95": round(float(np.percentile(side_lum, 95)), 4),
                    "mean_rgb": [round(float(v), 4) for v in side_rgb],
                    "rgb_spread": round(float((side_rgb.max() - side_rgb.min()) / max(side_rgb.mean(), 1e-6)), 4),
                    "note": "a bar's side faces: |N.z| < 0.5 and not ground (mask red, not blue)",
                }
                stats["bar_wall_dots"] = dark_dots(lum, side)
            coat_region = selection & (mask_px[..., 0] <= 0.5) & (mask_px[..., 1] <= 0.5) & (mask_px[..., 2] <= 0.5)
            if coat_region.any():
                stats["coat_dots"] = dark_dots(lum, coat_region)''')

# ---------------------------------------------------------------- gates
rep('''def pack_consistency(reports: dict) -> dict:''', '''def bar_wall_gate(stats: dict) -> dict:
    """A bar's hero side faces carry no pepper: isolated dark dots per 10k interior px within BAR_WALL_DOT_GATE."""
    dots = stats.get("bar_wall_dots")
    if not dots:
        return {"passed": False, "detail": "no side-face interior measured"}
    key = f"{int(round((1.0 - BAR_WALL_DOT_GATE['threshold']) * 100))}pct"
    value = dots[key]["dots_per_10k_px"]
    return {"passed": bool(value <= BAR_WALL_DOT_GATE["max_per_10k"]), "dots_per_10k_px": value,
            "threshold": f"{key} darker than the 7 x 7 face median", "max_per_10k": BAR_WALL_DOT_GATE["max_per_10k"],
            "interior_px": dots["interior_px"],
            "reference": "visual review: stars' plates 0.03-0.08, the reference asset 0.74, the 3.8.0 spike 8.28"}


def pack_consistency(reports: dict) -> dict:''')

rep('''            elif lum:
                out["bar_whole_object"][shot][name] = {
                    "p50": lum.get("p50"), "mean": lum.get("mean"),
                    "offset_vs_anchor": {st: round(lum.get(st) - PACK_ANCHOR[shot][st], 4) for st in ("p50", "mean")},
                    "note": ("information only: 55-65 % of a bar's hero pixels are the vertical side face, which mirrors the floor, not the key")}''',
    '''            elif lum:
                out["bar_whole_object"][shot][name] = {
                    "p50": lum.get("p50"), "mean": lum.get("mean"),
                    "offset_vs_anchor": {st: round(lum.get(st) - PACK_ANCHOR[shot][st], 4) for st in ("p50", "mean")},
                    "note": ("information only: about half of a bar's hero pixels are its vertical side face, which "
                             "mirrors the floor beside it, not the key (gated like with like: bar_walls_vs_wall_anchor)"
                             if shot == "hero" else
                             "information only: a bar seen from above is its top face, the polished point and the "
                             "tail facets (no side face shows); its coat pixels are the gated figure")}''')

rep('''    out["bar_coat_vs_coat_anchor"] = bar_offsets''', '''    out["bar_coat_vs_coat_anchor"] = bar_offsets
    # --- bars (3.8.1): the side faces against the anchor forms' walls, like with like
    wall_offsets = {}
    for name, cls in out["classes"].items():
        if cls != "bar":
            continue
        side = ((reports[name].get("render_stats") or {}).get(f"{name}_persp") or {}).get("bar_wall_luminance") or {}
        if side.get("p50") is None:
            passed = False
            wall_offsets[name] = {"error": "no side-face pixels measured"}
            continue
        off = side["p50"] - PACK_WALL_ANCHOR["hero"]["p50"]
        wall_offsets[name] = {"p50": side["p50"], "offset": round(off, 4) + 0.0, "headroom": round(tol - abs(off), 4),
                              "rgb_spread": side.get("rgb_spread")}
        passed = passed and abs(off) <= tol
    out["wall_anchor"] = {"forms": list(PACK_WALL_ANCHOR["forms"]), "source": PACK_WALL_ANCHOR["source"],
                          "hero": dict(PACK_WALL_ANCHOR["hero"])}
    out["bar_walls_vs_wall_anchor"] = wall_offsets
    # --- every form (3.8.1): the hero backdrop at fixed frame points against the anchor forms' range
    btol = BACKDROP_TOLERANCE
    backdrop = {}
    for name in out["classes"]:
        points = ((reports[name].get("render_stats") or {}).get(f"{name}_persp") or {}).get("backdrop_points")
        if not points:
            continue
        misses, worst = {}, None
        for key, (lo, hi) in PACK_BACKDROP_ANCHOR["hero"].items():
            value = points.get(key)
            if value is None:
                continue
            off = 0.0 if lo <= value <= hi else (value - hi if value > hi else value - lo)
            room = round(btol - abs(off), 4)
            if worst is None or room < worst["headroom"]:
                worst = {"point": key, "value": value, "anchor_range": [lo, hi], "headroom": room}
            if abs(off) > btol:
                misses[key] = {"value": value, "anchor_range": [lo, hi], "off_by": round(off, 4)}
        backdrop[name] = {"passed": not misses, "misses": misses, "min_headroom": worst,
                          "points_measured": sum(1 for v in points.values() if v is not None)}
        passed = passed and not misses
    out["backdrop"] = {"points": {k: list(v) for k, v in BACKDROP_POINTS.items()}, "tolerance": btol,
                       "anchor": {k: list(v) for k, v in PACK_BACKDROP_ANCHOR["hero"].items()},
                       "anchor_source": PACK_BACKDROP_ANCHOR["source"], "per_form": backdrop,
                       "rule": ("hero backdrop luminance (11 x 11 px median, object excluded) at fixed frame points "
                                "within the anchor forms' range +- the tolerance; points under the object skipped")}''')

rep('''           "rule": ("like with like (3.8): every PLATE form's hero and top p50 and mean within the tolerance of the "
                    "fixed anchor (the mean of the forms frozen at restyle pass 2); a BAR's coat pixels (its up-facing "
                    "faces) within the tolerance of the anchor forms' coat pixels (PACK_COAT_ANCHOR), its whole-object "
                    "figures reported as information; the all-forms mean is information only"),''',
    '''           "rule": ("like with like (3.8): every PLATE form's hero and top p50 and mean within the tolerance of the "
                    "fixed anchor (the mean of the forms frozen at restyle pass 2); a BAR's coat pixels (its up-facing "
                    "faces) within the tolerance of the anchor forms' coat pixels (PACK_COAT_ANCHOR) and (3.8.1) its "
                    "hero side faces' p50 within the tolerance of the anchor forms' hero wall p50 (PACK_WALL_ANCHOR), "
                    "its whole-object figures reported as information; (3.8.1) every form's hero backdrop at fixed "
                    "frame points within the anchor forms' range (PACK_BACKDROP_ANCHOR); the all-forms mean is "
                    "information only"),''')

# ---------------------------------------------------------------- render_previews: stats flag, rig scale, insets
rep('''            written[name] = str(beauty)
            try:
                stats[name] = image_stats(beauty, mask, o.n)''', '''            written[name] = str(beauty)
            try:
                stats[name] = image_stats(beauty, mask, o.n, bar=bool(getattr(o, "bar_wall_gate", False)))''')

rep('''        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        shoot(f"{form}_persp", rig["cam_persp"], rig["hero_lights"], card=True)
        if yaw:
            lod0.rotation_euler = saved_rotation
            bpy.context.view_layer.update()''', '''        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        rig_scale, saved_lamps = 1.0, []
        if getattr(o, "hero_rig_match", False):
            # 3.8.1: the hero lamps follow the fitted camera distance (see the module docstring); restored below
            rig_scale = rig["cam_persp"].location.length / HERO_RIG_REFERENCE_M
            for light in rig["hero_lights"]:
                saved_lamps.append((light, light.location.copy(), light.data.size, light.data.size_y,
                                    light.data.energy))
                light.location = light.location * rig_scale
                light.data.size *= rig_scale
                light.data.size_y *= rig_scale
                light.data.energy *= rig_scale ** 2
            bpy.context.view_layer.update()
        shoot(f"{form}_persp", rig["cam_persp"], rig["hero_lights"], card=True)
        for light, location, size, size_y, energy in saved_lamps:
            light.location, light.data.size, light.data.size_y, light.data.energy = location, size, size_y, energy
        if saved_lamps:
            bpy.context.view_layer.update()
        if yaw:
            lod0.rotation_euler = saved_rotation
            bpy.context.view_layer.update()''')

rep('''        stack_y = getattr(o, "lod_strip_axis", "x") == "y"    # a long form (the spike): LODs top to bottom
        if stack_y:
            spacing = rig["span_y"] + LOD_STRIP_Y_GAP
            fit_ortho(rig["cam_lod"], rig["span_x"], len(lods) * spacing + rig["span_y"] + LOD_STRIP_Y_GAP, 0.86, 0.90,
                      res_x, res_y)
        else:''', '''        stack_y = getattr(o, "lod_strip_axis", "x") == "y"    # a long form (the spike): LODs top to bottom
        inset_k = float(getattr(o, "lod_section_inset", 0.0) or 0.0) if stack_y else 0.0
        inset = 2.0 * o.a * inset_k if inset_k else 0.0      # 3.8.1: the end-on section's side at the inset scale
        bar_dx = 0.0
        if stack_y:
            row_h = max(rig["span_y"], inset)
            spacing = row_h + LOD_STRIP_Y_GAP
            total_w = rig["span_x"] + (LOD_STRIP_INSET_GAP + inset if inset_k else 0.0)
            if inset_k:
                bar_dx = -0.5 * (LOD_STRIP_INSET_GAP + inset)   # the bars move left, the insets sit on their right
            fit_ortho(rig["cam_lod"], total_w, len(lods) * spacing + row_h + LOD_STRIP_Y_GAP, 0.86, 0.90,
                      res_x, res_y)
            rig["cam_lod"].location.x = bar_dx + 0.5 * (getattr(o, "x_butt", -0.5 * rig["span_x"])
                                                        + getattr(o, "x_tip", 0.5 * rig["span_x"])) + (
                0.5 * (LOD_STRIP_INSET_GAP + inset) if inset_k else 0.0)
        else:''')

rep('''        for i, obj in enumerate([lod0] + list(lods)):
            offset = ((0.0, (0.5 * len(lods) - i) * spacing, 0.0) if stack_y
                      else ((i - 0.5 * len(lods)) * spacing, 0.0, 0.0))
            strip_objects += list(wire_pair(obj, coll, f"Lod{i}", offset=offset,
                                            thickness=WIRE_PX / lod_px_per_m))''', '''        inset_info = None
        for i, obj in enumerate([lod0] + list(lods)):
            offset = ((bar_dx, (0.5 * len(lods) - i) * spacing, 0.0) if stack_y
                      else ((i - 0.5 * len(lods)) * spacing, 0.0, 0.0))
            strip_objects += list(wire_pair(obj, coll, f"Lod{i}", offset=offset,
                                            thickness=WIRE_PX / lod_px_per_m))
            if inset_k:
                # the butt end seen end-on: R_y(90 deg) turns -X up toward the ortho camera, x inset_k; placed right
                # of the bar and well below it in z (under the camera's clip start, off every other object)
                basis = Matrix.Scale(inset_k, 4) @ Matrix.Rotation(math.radians(90.0), 4, "Y")
                cx = bar_dx + o.x_tip + LOD_STRIP_INSET_GAP + 0.5 * inset
                cz = -0.05 - inset_k * (-o.x_butt)
                strip_objects += list(wire_pair(obj, coll, f"LodEnd{i}", offset=(cx, offset[1], cz),
                                                thickness=WIRE_PX / lod_px_per_m / inset_k, basis=basis))
                inset_info = {"scale": inset_k, "view": "the butt end, end-on (-X toward the camera)",
                              "side_mm": round(inset * 1000.0, 3)}''')

rep('''            for i, text in enumerate(lod_labels):
                if stack_y:
                    y = (0.5 * len(lods) - i) * spacing
                    labels.append(label(coll, f"PREVIEW_LodLabel{i}", text.replace(chr(10), "   "),
                                        (0.0, y - 0.5 * rig["span_y"] - 0.02 * frame_h, 0.001), size))''', '''            for i, text in enumerate(lod_labels):
                if stack_y:
                    y = (0.5 * len(lods) - i) * spacing
                    bar_mid = bar_dx + 0.5 * (getattr(o, "x_butt", 0.0) + getattr(o, "x_tip", 0.0)) if inset_k else 0.0
                    labels.append(label(coll, f"PREVIEW_LodLabel{i}", text.replace(chr(10), "   "),
                                        (bar_mid, y - 0.5 * rig["span_y"] - 0.02 * frame_h, 0.001), size))
                    if inset_k:
                        cx = bar_dx + o.x_tip + LOD_STRIP_INSET_GAP + 0.5 * inset
                        labels.append(label(coll, f"PREVIEW_LodEndLabel{i}", f"butt end x{inset_k:g}",
                                            (cx, y - 0.5 * inset - 0.02 * frame_h, 0.001), 0.75 * size))''')

rep('''            if stack_y:
                label_bottom = min(obj.location.y - obj.dimensions.y for obj in labels)
                top = 0.5 * len(lods) * spacing + 0.5 * rig["span_y"]
                rig["cam_lod"].location.y = 0.5 * (top + label_bottom)''', '''            if stack_y:
                label_bottom = min(obj.location.y - obj.dimensions.y for obj in labels)
                top = 0.5 * len(lods) * spacing + 0.5 * max(rig["span_y"], inset)
                rig["cam_lod"].location.y = 0.5 * (top + label_bottom)''')

rep('''        rig_info = {
            "hero_yaw_deg": yaw,''', '''        rig_info = {
            "hero_yaw_deg": yaw,
            "hero_rig_scale": round(rig_scale, 6),
            "hero_rig_reference_m": HERO_RIG_REFERENCE_M if rig_scale != 1.0 else None,
            "lod_strip_section_inset": inset_info,''')

rep('''__all__ = ["FACET_GATE", "PACK_ANCHOR", "PACK_ANCHOR_DRIFT_MAX", "PACK_COAT_ANCHOR", "PACK_P50_TOLERANCE", "PLATE_BAND",''',
    '''__all__ = ["BACKDROP_POINTS", "BAR_WALL_DOT_GATE", "HERO_RIG_REFERENCE_M", "PACK_BACKDROP_ANCHOR", "PACK_WALL_ANCHOR",
           "bar_wall_gate", "dark_dots", "backdrop_points",
           "FACET_GATE", "PACK_ANCHOR", "PACK_ANCHOR_DRIFT_MAX", "PACK_COAT_ANCHOR", "PACK_P50_TOLERANCE", "PLATE_BAND",''')
p.write_text(s, encoding="utf-8")
print("patched render.py")
