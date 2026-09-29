import bpy, os
for i in bpy.data.images:
    p = bpy.path.abspath(i.filepath)
    if any(k in p for k in ("HBayBoard", "HEntCoirB", "HEntTimberP", "HEntTimberF", "HPaintingTall")):
        print("SRC", os.path.normpath(p))
