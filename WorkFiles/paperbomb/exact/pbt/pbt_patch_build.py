"""One-off patch: build_paper_bomb.py guide-refusal gates -> provenance + overlap gates."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_paper_bomb.py"
s = open(p, encoding="utf-8").read()
assert "_traced_check" not in s, "already patched"


def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)


rep('''AND WHAT IT NEVER OPENS
-----------------------
References/PaperBomb/paperbomb_guide*.png.  The art module draws inside
``no_guide_access()``, which replaces ``open`` for the duration and raises on any path
under References/PaperBomb; the list of files that WERE opened goes in the report.
"""''', '''PROVENANCE
----------
The paper bomb is the user's own design and is traced from ONE source,
References/PaperBomb/paperbomb_guide_v2_real_glyphs.png (SHA-256 in
``paperbomb_art.REFERENCE_SOURCE_SHA256``).  The art is drawn inside
``paperbomb_art.provenance_recorder()``, which records every file opened; the traced
shapes (props_lib/paperbomb_traced.json) are re-traced on every build and must come out
byte-identical.  Gates 13 / 13b / 13c check the source, the reproduction and each traced
element's overlap with the reference.
"""''')

rep('''def _no_image_loads() -> dict:
    """The static half of the guide-free proof; see ``collect_gates`` gate 13b."""
    try:
        from props_lib import paperbomb_art as _art
        return _art.no_image_loads()
    except Exception as exc:                                  # pragma: no cover
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"}''', '''def _traced_check() -> dict:
    """The traced shapes: from the one source, reproducible, within overlap tolerance.
    See ``collect_gates`` gates 13b / 13c."""
    try:
        from props_lib import paperbomb_trace as _pt
        t0 = time.time()
        res = _pt.verify_traced(retrace=True)
        log(f"  traced shapes: source verified {res.get('source_verified')}, reproduce "
            f"{res.get('reproduces')}, overlap {res.get('overlap_passed')} "
            f"({time.time() - t0:.1f} s)")
        return res
    except Exception as exc:                                  # pragma: no cover
        return {"source_verified": False, "error": f"{type(exc).__name__}: {exc}"}''')

rep('''        "no_image_loads": _no_image_loads(),''', '''        "traced_shapes": _traced_check(),''')

a = s.index('''    gates["13_no_guide_image_opened"] = bool(''')
b = s.index('''    gates["13b_art_module_contains_no_image_loads"] = bool(nil.get("passed"))''')
b = b + len('''    gates["13b_art_module_contains_no_image_loads"] = bool(nil.get("passed"))''')
s = s[:a] + '''    # PROVENANCE (replaces the retired "13_no_guide_image_opened" and
    # "13b_art_module_contains_no_image_loads": those enforced the old brief that the art
    # must never read the reference; the user's design is now traced from it).
    prov = art.get("provenance") or {}
    src_rel = prov.get("source")
    gates["13_one_source_provenance"] = bool(
        prov.get("source_matches")
        and all(p.replace("\\\\", "/").lower().endswith((src_rel or "").lower())
                for p in (prov.get("reference_files_opened") or [])))
    tr = art.get("traced_shapes") or {}
    gates["13b_traced_shapes_from_the_source_and_reproducible"] = bool(
        tr.get("source_verified") and tr.get("reproduces")
        and tr.get("source_sha256") == prov.get("source_sha256"))
    gates["13c_traced_elements_overlap_reference"] = bool(tr.get("overlap_passed"))''' + s[b:]
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
