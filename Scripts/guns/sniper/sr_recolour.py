"""SR01 recolour maps (plain Python; the SMG's smg_recolour.py step without the pack derive, which is W6 under the
PackMaterials lock): one recolour group SR01 = the OD Cerakote of M_SR01_Chassis (M_Fabric_Master, Metal From ORM on).

    py -3 -B Scripts/guns/sniper/sr_recolour.py [--tex DIR]

Writes <tex>/Recolour/T_SR01_Chassis_Detail16.png (16-bit linear grey at the BC's size up to 2048: d = normalised
lum(BC) over the texels where Masks A = 1 (the OD paint only), one fill constant elsewhere) and recolour_maps.json
(Colour = the OD's mean linear albedo, Detail Bias / Scale so Colour x (Bias + Scale x d) reproduces the baked
luminance on the OD). Pre-check: the recolour reconstruction error on the OD at the default Colour (p99.9 levels),
and that A = 0 on every rubber / polymer / anodized / bare texel (the user colour never tints them).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_surface as SS  # noqa: E402
from gunlib import paint as PT  # noqa: E402

LW = np.array([0.2126, 0.7152, 0.0722])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default=str(SS.TEX))
    a = ap.parse_args()
    tex = Path(a.tex)
    st = "Chassis"
    bc = np.asarray(Image.open(tex / f"T_SR01_{st}_BC.png").convert("RGB"), float) / 255.0
    mk = np.asarray(Image.open(tex / f"T_SR01_{st}_Masks.png"), float) / 255.0
    S = bc.shape[0]
    A = np.asarray(Image.fromarray((mk[..., 3] * 255).astype(np.uint8)).resize((S, S), Image.NEAREST), float) / 255.0
    lin = PT.srgb_to_lin(bc)
    lum = lin @ LW
    od = A > 0.5
    colour = lin[od].mean(0)
    cl = float(colour @ LW)
    d = np.clip(lum / max(cl, 1e-6), 0.0, 4.0)
    dmax = float(np.percentile(d[od], 99.9))
    dn = np.where(od, d / dmax, 1.0 / dmax)
    bias, scale = 0.0, dmax
    out = tex / "Recolour"
    out.mkdir(parents=True, exist_ok=True)
    S2 = min(S, 2048)
    im = Image.fromarray(np.clip(dn * 65535.0, 0, 65535).astype(np.uint16), "I;16")
    if S2 != S:
        im = im.resize((S2, S2), Image.BILINEAR)
    im.save(out / f"T_SR01_{st}_Detail16.png")
    rec = lin * 0 + colour[None, None, :] * (bias + scale * dn)[..., None]
    err = np.abs(PT.lin_to_srgb(rec) - PT.lin_to_srgb(lin))[od] * 255.0
    # the hue the recolour cannot carry (the OD's per-texel hue drift vs one Colour): reported
    maps = {"group": "SR01", "member": f"M_SR01_{st}", "master": "M_Fabric_Master", "metal_from_orm": True,
            "colour_linear": [round(float(v), 5) for v in colour], "detail_bias": bias, "detail_scale": round(dmax, 5),
            "detail16": f"Recolour/T_SR01_{st}_Detail16.png", "detail16_size": S2,
            "masks_A": "1 only on the OD paint (sr_paint refin)"}
    (out / "recolour_maps.json").write_text(json.dumps(maps, indent=1))
    paint = json.loads((SS.SCRATCH / "paint" / "paint_report.json").read_text())
    non_od = {s: v.get("masks_A_on_non_od_texels") for s, v in paint.items()}
    gate = {"recon_error_srgb_levels_p50_p99_p999": [round(float(np.percentile(err.max(1), q)), 2) for q in (50, 99, 99.9)],
            "od_texels": int(od.sum()), "masks_A_on_non_od_texels_per_set": non_od,
            "pass": bool(np.percentile(err.max(1), 99.9) <= 6.0 and not any(non_od.values())),
            "rule": "p99.9 reconstruction <= 6 levels (the OD carries chip / rub hue the single Colour flattens: the "
                    "pack's P1 <= 2 applies to its derived constants in W6); A = 0 off the OD"}
    (SS.SCRATCH / "recolour_precheck.json").write_text(json.dumps({"maps": maps, "gate": gate}, indent=1))
    print("[SR01-recolour]", json.dumps(gate))


if __name__ == "__main__":
    main()
