"""The flashbang's UV-plane base-colour captures (np_render 'render' step, SCS_BASE_COLOR, one pixel per texel) vs the
look contract, WITH Metal From ORM (the pack's analyse_captures.py twin has no Metal From ORM branch, so this reads the
same EXRs and applies the sheath's contract itself; it writes only WorkFiles/flashbang/fin/).

    expected = lerp(twin(Colour, Detail16), BC, max(ORM.B, saturate((lum(BC) - 0.2) x 5)))

twin = np_twin.fabric_albedo (the v2 graph, node for node) at mip 0 with the instance's resolved params.  The capture's
orientation (one of 8 dihedral maps) is chosen by the smallest mean error of the default capture; the capture samples
may sit up to ~0.03 texel off the texel centres (analyse_captures.py's note), so p99 differences at high-contrast
texel edges are expected to be a few levels.  Reports mean / p50 / p99 / p99.9 |stored-level difference| for the
default (and the steel default vs BC), and for the stress colours the fraction of paint texels that follow the colour.
    blender -b --factory-startup --python fin_analyse_captures.py
"""
import json
import sys
from pathlib import Path

import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.dont_write_bytecode = True
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps"))
sys.path.insert(0, str(P / "Scripts/unreal/materials"))
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402
import np_spec  # noqa: E402
import bpy  # noqa: E402

CAPS = P / "WorkFiles/materials/ue_renders/captures"
OUT = P / "WorkFiles/flashbang/r2/fin2/uv_capture_analysis_flashbang_r2.json"
jobs_doc = json.loads((CAPS / "capture_jobs.json").read_text(encoding="utf-8"))
jobs = {j["name"]: j for j in jobs_doc["jobs"]}
res = jobs_doc["results"]
plan = np_spec.resolve()
params = next(s["params"] for s in plan["slots"] if s["instance"] == "MI_Flashbang_Paint")


def load_exr(p):
    im = bpy.data.images.load(str(p), check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)


def dihedral(a, k):
    b = np.rot90(a, k % 4)
    return b[:, ::-1] if k >= 4 else b


T = P / "Exports/Flashbang/Textures"
bc = rc.s2l(rc.load_levels8(T / "T_Flashbang_BC.png")[..., :3] / 255.0)
orm = rc.load_levels8(T / "T_Flashbang_ORM.png")[..., :3] / 255.0
d16, _, _ = rc.png_read(T / "Recolour/T_Flashbang_Paint_Detail16.png")
d = d16 / 65535.0
lum = bc @ np.array([0.2126, 0.7152, 0.0722])
w_keep = np.maximum(orm[..., 2], np.clip((lum - 0.2) * 5.0, 0, 1))[..., None]


def expected(colour):
    a, _ = tw.fabric_albedo(params, d, np.asarray(colour, float), lod=0.0)
    return a * (1 - w_keep) + bc * w_keep


def stats(lev_a, lev_b, mask=None):
    diff = np.abs(lev_a.astype(np.int32) - lev_b.astype(np.int32)).max(axis=-1)
    if mask is not None:
        diff = diff[mask]
    return {"mean": round(float(diff.mean()), 4), "p50": float(np.percentile(diff, 50)),
            "p99": float(np.percentile(diff, 99)), "p99.9": float(np.percentile(diff, 99.9)), "max": int(diff.max())}


out = {"contract": "lerp(twin, BC, max(ORM.B, saturate((lum(BC)-0.2)*5)))", "captures": {}}
name0 = "uv_MI_Flashbang_Paint_default"
cap0 = load_exr(res[name0]["exr"])
exp0 = expected(params["Colour"][:3])
errs = {k: float(np.abs(rc.q8_srgb(dihedral(cap0, k)).astype(int) - rc.q8_srgb(exp0).astype(int)).mean()) for k in range(8)}
k = min(errs, key=errs.get)
out["orientation"] = {"chosen": k, "mean_level_error_by_orientation": errs}
paint = (w_keep[..., 0] < 0.5)
for name, job in jobs.items():
    if "Flashbang" not in name or name not in res or "exr" not in res[name]:
        continue
    cap = dihedral(load_exr(res[name]["exr"]), k)
    lev = rc.q8_srgb(cap)
    rec = {"kind": job["kind"]}
    if job["kind"] == "steel_default":
        rec["vs_BC_all_texels"] = stats(lev, rc.q8_srgb(bc))
    else:
        col = job["overrides"].get("Colour", params["Colour"])[:3]
        e = expected(col)
        rec["colour_linear"] = [round(float(x), 6) for x in col]
        rec["vs_contract_all_texels"] = stats(lev, rc.q8_srgb(e))
        rec["vs_contract_paint_texels"] = stats(lev, rc.q8_srgb(e), paint)
        rec["vs_contract_kept_texels"] = stats(lev, rc.q8_srgb(e), ~paint)
        if job["kind"] == "fabric_default":
            rec["vs_BC_all_texels"] = stats(lev, rc.q8_srgb(bc))
            rec["mean_paint_lin_capture_vs_BC"] = [[round(float(x), 5) for x in cap[paint].mean(0)],
                                                    [round(float(x), 5) for x in bc[paint].mean(0)]]
        else:
            rec["kept_texels_unchanged_vs_default_capture_p99"] = None
    out["captures"][name] = rec
    print(name, json.dumps(rec)[:400], flush=True)
dflt = out["captures"].get(name0, {})
out["summary"] = {"default_vs_BC_paint_mean_levels": (dflt.get("vs_contract_paint_texels") or {}).get("mean"),
                  "default_equals_BC_p99_levels": (dflt.get("vs_BC_all_texels") or {}).get("p99")}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print("wrote", OUT)
