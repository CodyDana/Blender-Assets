"""r17 mat iteration helper (test only): run BEFORE render_armory.py on a preview blend. Env AK_SWAP:
"MATNAME=SET:tint[;MATNAME=...]" (SET '-' keeps the images; tint '-' keeps the tint); textures from AK_TEXDIR."""
import os
from pathlib import Path

import bpy

TEXDIR = Path(os.environ.get("AK_TEXDIR", ""))
for spec in filter(None, os.environ.get("AK_SWAP", "").split(";")):
    mname, rest = spec.split("=")
    tex, tint = rest.split(":")
    mat = bpy.data.materials[mname]
    for nd in mat.node_tree.nodes:
        if nd.type == "TEX_IMAGE" and nd.image and tex != "-":
            nm = next(s for s in (Path(nd.image.filepath.replace("\\", "/")).name, nd.image.name) if "T_AK_" in s)
            suf = nm.rsplit("_", 1)[1].split(".")[0] + ".png"
            new = TEXDIR / f"T_AK_{tex}_{suf}"
            img = bpy.data.images.load(str(new), check_existing=True)
            img.colorspace_settings.name = nd.image.colorspace_settings.name
            nd.image = img
        if nd.type == "VECT_MATH" and nd.operation == "MULTIPLY" and tint != "-":
            nd.inputs[1].default_value = (float(tint),) * 3
    print("swapped", mname, tex, tint)
