"""One-off patch: paperbomb_art.py guide-access refusal -> provenance record."""
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_art.py"
s = open(p, encoding="utf-8").read()
assert "class provenance_recorder" not in s, "already patched"


def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)


# 1. the docstring's originality paragraph
a = s.index("    ORIGINALITY.  Nothing here is sampled")
b = s.index("    HEADLESS ONLY.")
s = s[:a] + """    PROVENANCE.  The paper bomb is the USER'S OWN design and they asked for it to be
    traced from their reference, References/PaperBomb/paperbomb_guide_v2_real_glyphs.png
    (the one source; path and SHA-256 in ``REFERENCE_SOURCE``).  The traced shapes live in
    ``props_lib/paperbomb_trace.py`` -> ``paperbomb_traced.json``; ``ELEMENT_DERIVATION``
    says, per element, whether this module still draws it or takes the traced shapes,
    and ``art_provenance()`` puts that, the source hash and every file the drawing opened
    in the build report.  (An earlier brief forbade reading the reference; that refusal
    guard is retired - see ``provenance_recorder``.)

""" + s[b:]

# 2. the docstring's gates paragraph
a = s.index("GATES, AND HOW THE ORIGINALITY CLAIM IS PROVED")
b = s.index("``font_codepoints()`` reads the .ttf's own cmap.")
s = s[:a] + """GATES AND PROVENANCE
--------------------
``provenance_recorder()`` records every file opened while the art is drawn, and
``art_provenance()`` reports it with the one source's path and SHA-256 and the traced
shapes' hash.  The build's gate 13 checks the source hash on disk and that no OTHER file
under References/PaperBomb was read; gate 13b checks that ``paperbomb_traced.json`` was
traced from that exact source and re-traces to the same bytes; gate 13c holds every
traced element's overlap with the reference to its tolerance.

""" + s[b:]

# 3. the fragment list
rep('''#: A build gate may assert that none of these appear in this module's resolved inputs.
FORBIDDEN_INPUT_FRAGMENTS = ("paperbomb_guide", "References/PaperBomb", "References\\\\PaperBomb")
''', "")

# 4. GuideAccess .. art_provenance -> the recorder + provenance record
a = s.index("class GuideAccess(RuntimeError):")
b = s.index("# ===========================================================================\n# 2.  Card, layout and colour")
new = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/pbt/pbt_prov_block.txt",
           encoding="utf-8").read()
s = s[:a] + new + s[b:]

# 5. the CLI
rep('''    # Everything that draws runs inside the guard, so the run itself is the evidence
    # that no reference image was read.
    guard = no_guide_access()''', '''    # the drawing runs inside the recorder, so the report lists every file it read
    guard = provenance_recorder()''')

for imp in ("import hashlib", "import json"):
    if "\n" + imp + "\n" not in s:
        s = s.replace("\nimport os\n", "\n" + imp + "\nimport os\n", 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
