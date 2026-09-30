"""Round 9 probe helpers: build shot dicts with exposure compensation (a bias change dEV multiplies the lamps and every
emissive intensity by 2^-dEV, as dj_sc_common does in the build)."""
BASE_BIAS = 1.5
EMISSIVE = {"M_DJ_GlassAmber": "EmissiveIntensity", "M_DJ_ShojiPaper": "EmissiveIntensity",
            "M_DJ_VendingPanel": "EmissiveIntensity", "M_DKP_Modern_BulbLit": "Emissive Intensity",
            "M_DKP_Modern_ButtonLit": "Emissive Intensity", "M_DKX_Ridge1": "Emissive Intensity",
            "M_DKX_Ridge2": "Emissive Intensity", "M_DKX_Ridge3": "Emissive Intensity",
            "M_DKX_Ridge4": "Emissive Intensity"}


def shot(out, cam="CAM_Ref2Match", bias=None, uds=None, pp=None, mat=None, lamps=None, emis=None, cmds=None, **kw):
    """emis: {MI: extra multiplier on its emissive intensity}; lamps: {prefix: {mult, radius_cm}} (mult on top of the
    exposure compensation)."""
    w, h = (1920, 1440) if cam in ("CAM_Ref2Match", "CAM_Establishing", "CAM_EstablishingRef2") else (1920, 1080)
    s = {"name": cam, "w": w, "h": h, "out": out}
    k = 1.0
    ppd = dict(pp or {})
    if bias is not None:
        ppd["auto_exposure_bias"] = float(bias)
        k = 2.0 ** -(float(bias) - BASE_BIAS)
    if ppd:
        s["pp"] = ppd
    m = {n: {"s_mul": {p: k * (emis or {}).get(n, 1.0)}} for n, p in EMISSIVE.items()}
    for n, sp in (mat or {}).items():
        m.setdefault(n, {})
        for kk, vv in sp.items():
            if kk == "s_mul":
                m[n].setdefault("s_mul", {}).update({p: v * k if p in ("EmissiveIntensity", "Emissive Intensity") else v
                                                     for p, v in vv.items()})
            else:
                m[n][kk] = vv
    s["mat"] = m
    lp = {"Light_": {"mult": k}}
    for pre, sp in (lamps or {}).items():
        lp[pre] = dict(sp, mult=k * sp.get("mult", 1.0))
    s["lamps"] = lp
    if uds:
        s["uds"] = uds
    if cmds:
        s["cmds"] = cmds
    s.update(kw)
    return s
