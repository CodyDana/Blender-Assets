"""record everything reference_winding() needs; write props_lib/smokebomb_wind_fit.py."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py"
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("anchor: " + old[:90])
    s = s.replace(old, new)


rep('''def build_winding(seq, weaves, tail_deg=70.0):
    first = np.array(seq[0].n)
    ax = W.core_axes(CORE["n"], W.normalize(CORE["first_axis"]), first)''', '''TAIL_FOLD = 0.9


def build_winding(seq, weaves, tail_deg=70.0):
    first = np.array(seq[0].n)
    ax = W.core_axes(CORE["n"], W.normalize(CORE["first_axis"]), first)''')
rep('''    wd0 = W.assemble(list(seq), [], tail_deg=tail_deg, core=(CP[k:], CW[k:]))
    ws = split_weaves(wd0, weaves)
    wd = W.assemble(list(seq), ws, tail_deg=tail_deg, core=(CP[k:], CW[k:]),
                    connectors=[dict(La=c["La"], Lb=c["Lb"]) for c in wd0.notes["connectors"]])
    wd.notes["core_trim"] = k
    wd.notes["core_end"] = int(ke)
    return wd''', '''    wd0 = W.assemble(list(seq), [], tail_deg=tail_deg, core=(CP[k:], CW[k:]), tail_fold=TAIL_FOLD)
    ws = split_weaves(wd0, weaves)
    conns = [dict(La=c["La"], Lb=c["Lb"]) for c in wd0.notes["connectors"]]
    wd = W.assemble(list(seq), ws, tail_deg=tail_deg, core=(CP[k:], CW[k:]), connectors=conns, tail_fold=TAIL_FOLD)
    wd.notes["core_trim"] = k
    wd.notes["core_end"] = int(ke)
    wd.notes["core_axes"] = ax.tolist()
    wd.notes["frozen_connectors"] = conns
    wd.notes["tail_deg"] = float(tail_deg)
    return wd''')
rep('''    json.dump(rec, open(os.path.join(OUT, f"{tag}_design.json"), "w"), indent=1, default=float)''', '''    json.dump(rec, open(os.path.join(OUT, f"{tag}_design.json"), "w"), indent=1, default=float)
    if "--freeze" in sys.argv:
        write_fit_module(wd, tag)''')
rep('''def views(wd, tag, names, size=627):''', '''FIT_PATH = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind_fit.py"


def _t(v, nd=9):
    return "(" + ", ".join(repr(round(float(x), nd)) for x in v) + ("," if len(v) == 1 else "") + ")"


def write_fit_module(wd, tag):
    """freeze the design: every number reference_winding() needs, as a plain module."""
    L = []
    L.append('"""props_lib.smokebomb_wind_fit - the FROZEN winding of SM_SmokeBomb (generated, do not edit).')
    L.append("")
    L.append("Written by WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py (design %s) from the fit of" % tag)
    L.append("every visible pass to REFERENCE_SPEC's traced edges (the spec numbers only; the reference")
    L.append("pixels are never read).  props_lib.smokebomb_wind.reference_winding() assembles the tape")
    L.append("from these numbers alone.")
    L.append("")
    L.append("Camera frame (REFERENCE_SPEC 0): X right, Y up, Z toward the camera; unit sphere.")
    L.append("PassSpec angles in degrees, widths in frac D; weave ranges in the pass's own phi (deg) or,")
    L.append('with lower_where="tail", in degrees of arc past the end of the last front arc.')
    L.append('"""')
    L.append("")
    L.append("DESIGN = %r" % tag)
    L.append("#: the core: a continuous precessing winding round these loop axes (core_path), trimmed")
    L.append("CORE_WIDTH = %r" % float(CORE["width"]))
    L.append("CORE_AXES = (")
    for a in wd.notes["core_axes"]:
        L.append("    %s," % _t(a))
    L.append(")")
    L.append("CORE_TRIM = %d          # first core sample kept (the inner end, buried)" % wd.notes["core_trim"])
    L.append("CORE_END = %d          # last core sample kept (where it joins the first pass)" % wd.notes["core_end"])
    L.append("#: the fitted passes, in the order they are wound (later = on top)")
    L.append("PASSES = (")
    for p in wd.passes[1:]:
        L.append("    dict(name=%r, shows=%r, role=%r," % (p.name, tuple(p.shows), p.role))
        L.append("         n=%s, e1=%s," % (_t(p.n), _t(p.e1)))
        L.append("         phi_a=%r, phi_b=%r," % (float(p.phi_a), float(p.phi_b)))
        L.append("         beta=%s," % _t(p.beta, 6))
        L.append("         width=%s," % _t(p.width, 6))
        L.append("         gather=%s," % (_t(p.gather, 6) if p.gather else "()"))
        L.append("         note=%r)," % p.note)
    L.append(")")
    L.append("#: the far-side joins (core -> first pass, then pass k -> k+1): run-on lengths, deg")
    L.append("CONNECTORS = (")
    for c in wd.notes["frozen_connectors"]:
        L.append("    (%r, %r)," % (float(c["La"]), float(c["Lb"])))
    L.append(")")
    L.append("#: the free end: the last pass runs on this far past its front arc, folded (gathered)")
    L.append("TAIL_DEG = %r" % wd.notes["tail_deg"])
    L.append("TAIL_FOLD = %r" % TAIL_FOLD)
    L.append("#: the weaves (crossing-local layering)")
    L.append("WEAVES = (")
    for w in wd.weaves:
        up = w.upper if isinstance(w.upper, str) else tuple(w.upper)
        L.append("    dict(lower=%r, lower_range=%s, upper=%r, upper_range=%s," % (
            w.lower, _t(w.lower_range, 4), up, "None" if w.upper_range is None else _t(w.upper_range, 4)))
        L.append("         lower_where=%r, upper_where=%r, extend=%r, stop_hidden=%r," % (
            w.lower_where, w.upper_where, w.extend, w.stop_hidden))
        L.append("         why=%r)," % w.why)
    L.append(")")
    open(FIT_PATH, "w", encoding="utf-8").write("\\n".join(L) + "\\n")
    print("wrote", FIT_PATH)


def views(wd, tag, names, size=627):''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind.py"
s = open(p, encoding="utf-8").read()
rep('''# --------------------------------------------------------------------------- views + raster''', '''# --------------------------------------------------------------------------- the frozen design
def reference_winding(fit=None) -> Winding:
    """SM_SmokeBomb's tape, assembled from the frozen numbers in props_lib.smokebomb_wind_fit:
    the core path, the fitted passes in winding order, the far-side joins, the folded free
    end and the weaves.  Deterministic; numpy only."""
    if fit is None:
        from . import smokebomb_wind_fit as fit
    axes = np.array(fit.CORE_AXES, np.float64)
    CP, CW = core_path(axes, fit.CORE_WIDTH)
    CP, CW = CP[:fit.CORE_END + 1], CW[:fit.CORE_END + 1]
    CP, CW = CP[fit.CORE_TRIM:], CW[fit.CORE_TRIM:]
    passes = [PassSpec(name=p["name"], shows=tuple(p["shows"]), n=tuple(p["n"]), e1=tuple(p["e1"]),
                       phi_a=p["phi_a"], phi_b=p["phi_b"], beta=tuple(p["beta"]), width=tuple(p["width"]),
                       gather=tuple(p["gather"]), role=p["role"], note=p["note"]) for p in fit.PASSES]
    weaves = [Weave(**w) for w in fit.WEAVES]
    conns = [dict(La=a, Lb=b) for a, b in fit.CONNECTORS]
    wd = assemble(passes, weaves, tail_deg=fit.TAIL_DEG, core=(CP, CW), connectors=conns,
                  tail_fold=fit.TAIL_FOLD)
    wd.notes["design"] = fit.DESIGN
    return wd


# --------------------------------------------------------------------------- views + raster''')
rep('''"core_start_trim", "assemble", "VIEWS",''', '''"core_start_trim", "assemble", "reference_winding", "VIEWS",''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
