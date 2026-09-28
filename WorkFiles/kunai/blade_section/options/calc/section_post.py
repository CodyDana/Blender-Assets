"""Exact section figures from a measured outline (measure_mesh.py outline_yz_mm): the grind line is the first vertex
inward of the land on the top-right quadrant; the diamond face runs from it to the ridge."""
import math


def post(station):
    pts = station["outline_yz_mm"]
    h = max(p[0] for p in pts)
    top = sorted([p for p in pts if p[1] > 0 and p[0] > 1e-6], key=lambda p: -p[0])
    ridge_top = max(p[1] for p in pts if abs(p[0]) < 1e-4) if any(abs(p[0]) < 1e-4 for p in pts) else None
    land = top[0]
    grind = next((p for p in top[1:] if p[0] < land[0] - 1e-3), None)
    out = {"half_width_mm": h, "land_z_mm": land[1]}
    if grind and ridge_top is not None:
        slope = (ridge_top - grind[1]) / grind[0]
        out.update({"grind_line_y_mm": grind[0], "grind_band_mm": round(h - grind[0], 4),
                    "face_slope": round(slope, 4), "face_angle_deg": round(math.degrees(math.atan(slope)), 2),
                    "ridge_half_mm": ridge_top,
                    "edge_z_extrapolated_mm": round(ridge_top - slope * h, 4)})
    return out
