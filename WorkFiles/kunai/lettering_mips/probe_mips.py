# Read-only probe: actual mip chain of the lettering textures (no saves).
import json, unreal
out = {}
paths = ["/Game/NinjaPack/Textures/Shuriken/T_Kunai_Lettering",
         "/Game/NinjaPack/Textures/Default/T_NP_Default_Lettering"]
for p in paths:
    t = unreal.EditorAssetLibrary.load_asset(p)
    r = {"exists": t is not None}
    if t:
        for k in ("power_of_two_mode", "mip_gen_settings", "compression_settings", "address_x", "address_y", "srgb", "lod_group"):
            try: r[k] = str(t.get_editor_property(k))
            except Exception as e: r[k] = "ERR " + str(e)
        r["_m"] = [m for m in dir(t) if any(s in m.lower() for s in ("mip", "size", "source"))]
        for m in ("blueprint_get_size_x", "blueprint_get_size_y", "blueprint_get_built_texture_size", "blueprint_get_memory_size", "blueprint_get_texture_source_disk_and_memory_size", "blueprint_get_texture_source_id_string"):
            f = getattr(t, m, None)
            if f:
                try: r[m] = str(f())
                except Exception as e: r[m] = "ERR " + str(e)
    out[p] = r
import sys
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/lettering_mips/probe_mips_rhi.json"
open(OUT, "w").write(json.dumps(out, indent=1))
print("PROBE_DONE")
