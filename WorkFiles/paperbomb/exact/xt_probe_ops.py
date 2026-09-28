import bpy
names = []
for mod in dir(bpy.ops):
    try:
        sub = getattr(bpy.ops, mod)
        for op in dir(sub):
            if 'trace' in op.lower() or 'potrace' in op.lower() or 'vectori' in op.lower():
                names.append(mod + '.' + op)
    except Exception:
        pass
print("TRACE_OPS", names)
try:
    print(bpy.ops.grease_pencil.trace_image.get_rna_type().properties.keys())
except Exception as e:
    print("no grease_pencil.trace_image", e)
