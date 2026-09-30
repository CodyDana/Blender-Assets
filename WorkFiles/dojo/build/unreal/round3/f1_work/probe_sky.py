import unreal, json
out = {}
for p in ("/Engine/EngineSky/SM_SkySphere", "/Engine/BasicShapes/Sphere", "/Engine/EngineMeshes/SM_SkySphere", "/Engine/EngineSky/SM_SkyDome"):
    a = unreal.load_asset(p)
    if a:
        b = a.get_bounds()
        out[p] = {"ok": True, "extent": [b.box_extent.x, b.box_extent.y, b.box_extent.z], "origin": [b.origin.x, b.origin.y, b.origin.z],
                  "tris": a.get_num_triangles(0) if hasattr(a, "get_num_triangles") else None}
    else:
        out[p] = None
out["enginesky"] = [str(x) for x in unreal.EditorAssetLibrary.list_assets("/Engine/EngineSky", False, False)][:60]
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round3\f1_work\probe_sky.json", "w").write(json.dumps(out, indent=1))
