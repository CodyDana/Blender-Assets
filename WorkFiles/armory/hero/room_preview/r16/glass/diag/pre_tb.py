"""glass-bug diagnosis only: override the transparent bounce limit (env TB) and render a border crop (env BORDER)."""
import os, bpy
sc = bpy.context.scene
tb = os.environ.get("TB")
if tb:
    sc.cycles.transparent_max_bounces = int(tb)
b = os.environ.get("BORDER")
if b:
    x0, y0, x1, y1 = (float(v) for v in b.split(","))
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0, y0, x1, y1
print("PRE transparent_max_bounces", sc.cycles.transparent_max_bounces, "border", b, flush=True)
