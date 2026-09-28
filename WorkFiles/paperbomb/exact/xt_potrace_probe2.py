import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.load(os.path.join(HERE, "_potrace_in_Fx8.png"))
emp = bpy.data.objects.new("IMG", None); emp.empty_display_type = "IMAGE"; emp.data = img
bpy.context.scene.collection.objects.link(emp); bpy.context.view_layer.objects.active = emp; emp.select_set(True)
bpy.ops.grease_pencil.trace_image(target="NEW", threshold=0.5, turnpolicy="MINORITY", mode="SINGLE")
gp = [o for o in bpy.data.objects if o.type == 'GREASEPENCIL'][0]
dr = gp.data.layers[0].frames[0].drawing
print("attrs", [a.name for a in dr.attributes])
st = dr.strokes[0]
print("stroke attrs", [k for k in dir(st) if not k.startswith('_')])
print("curve_type", getattr(st, 'curve_type', None), "cyclic", st.cyclic, "npts", len(st.points))
try:
    hl = dr.attributes["handle_left"]; print("handle_left len", len(hl.data))
except Exception as e: print("no handles", e)
print(dr.attributes.get('curve_type'), )
ct = dr.attributes.get('curve_type')
if ct: print([d.value for d in ct.data][:10])
print("resolution", [d.value for d in dr.attributes['resolution'].data][:5] if dr.attributes.get('resolution') else None)
print(gp.matrix_world)
