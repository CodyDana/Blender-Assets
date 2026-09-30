"""swap2 (test only): run BEFORE render_armory.py on a preview blend. Env AK_SWAP2 = JSON {mat: {tex, tint, spec}};
textures from AK_TEXDIR (T_AK_<tex>_<BC|N|ORM>.png)."""
import json
import os
from pathlib import Path

import bpy

TEXDIR = Path(os.environ.get("AK_TEXDIR", ""))
for mname, spec in json.loads(os.environ.get("AK_SWAP2", "{}")).items():
    mat = bpy.data.materials[mname]
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for nd in mat.node_tree.nodes:
        if nd.type == "TEX_IMAGE" and nd.image and "tex" in spec:
            nm = next(s for s in (Path(nd.image.filepath.replace("\\", "/")).name, nd.image.name) if "T_AK_" in s)
            suf = nm.rsplit("_", 1)[1].split(".")[0]
            src = TEXDIR / f"T_AK_{spec['tex']}_{suf}.png"
            if not src.exists():
                src = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\ArmoryKit\Textures") / src.name
            img = bpy.data.images.load(str(src), check_existing=True)
            img.colorspace_settings.name = nd.image.colorspace_settings.name
            nd.image = img
        if nd.type == "VECT_MATH" and nd.operation == "MULTIPLY" and "tint" in spec:
            nd.inputs[1].default_value = (float(spec["tint"]),) * 3
    if "tint" in spec and not any(nd.type == "VECT_MATH" for nd in mat.node_tree.nodes):
        print("WARNING no tint node on", mname)
    if "spec" in spec:
        bsdf.inputs["Specular IOR Level"].default_value = spec["spec"]
    print("swapped", mname, spec)
