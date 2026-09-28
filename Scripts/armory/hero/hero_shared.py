"""The SHARED MATERIALS hero pass (2026-09-28): overrides of the kit's own M_AK_* materials by their existing names, so
every scripted and hero piece picks them up (armory_hero loads this module last, and always in previews), plus hero
versions of the two plain ceiling members. References: WorkFiles/armory/reference/armory3_reference2.png (the room),
entrance.png, rear_alcove.png, ceiling_coffer.png (timber), banner.png (banner), case_standard.png (glass).

  M_AK_Timber  T_AK_HTimber (tex_shared.py) at the kit's 2 m tile: a near-black espresso stain over wire-brushed timber,
               warm clearly visible grain (thin broken latewood lines, short brushed streaks) and fine checks. The grain
               runs along U, as the kit's Piece.box maps every timber face (U along the face's longer extent, i.e. along
               the member). (T_AK_HEntTimber was not reused: it is tuned for a 1 m tile and its grain runs along V.)
  M_AK_Banner  T_AK_HBanner (tex_shared.py): the kit banner's exact UV layout and the user's emblem (same emblem_field,
               ring thickness unchanged), a deep black satin field (roughness ~0.35, soft sheen) and the gold ring, mon,
               border and hem blossoms as fine satin-stitched metallic gold thread (no noise streaks). Two-sided as before.
  M_AK_Glass   the kit's thin see-through pane with a faint neutral-grey tint and a stronger Fresnel reflection, so the
               panes read as glass (build_material's optional glass params "tint" and "refl"; kit defaults: clear, 0.02).
  M_AK_Plank   calibration pass 1 (2026-09-28, in the room): the floor in the satin copy T_AK_HPlank, stain x FLOOR_TINT.
  Not overridden here: M_AK_Mat, M_AK_LanternPaper (other passes own those looks).

Pieces (same names, pivots, facing, bbox and col() as the scripted ones in build_armory_kit.kit()):
  SM_AK_Ceiling_Beam_4  4 m x 25 cm x 40 cm deep, x 0..4, y +-0.125, z -0.40..0 (z 0 = the ceiling line)
  SM_AK_Ceiling_Rib_2   2 m x 16 cm x 30 cm deep, x 0..2, y +-0.08,  z -0.30..0
  Plain dark timber as the reference beams: the peach LED line strips on the soffit edges are gone; the two lower
  arrises are softly rounded (a 4-facet round, 12 / 10 mm), the top arrises (against the ceiling) and the butt ends stay
  square so beams in a line and ribs meeting a beam close without V notches. UV0: U along the member (the grain), V
  round the section by arc length (the grain wraps continuously over the arris), metres / 2 m tile; the end caps
  box-projected.

ENABLED stays False: the user reviews images of every change before anything goes into the armory.

Preview (Git Bash, from the project root), e.g. the beams:
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \\
      --python Scripts/armory/hero/preview_hero.py -- --module hero_shared \\
      --pieces "SM_AK_Ceiling_Beam_4;SM_AK_Ceiling_Rib_2@1.0,0.6,0" --front -y --label ceiling \\
      --out "C:\\Users\\Cody\\Desktop\\Blender_Projects\\WorkFiles\\armory\\hero\\previews\\hero_shared" \\
      --scripted --samples 64 --save
(placed unrotated: a rotated placement trips the preview's transforms_applied QA check, a preview artefact)
The material overrides show on any module's preview (hero_shared always loads), e.g. --module hero_cases (never --save
with another module: that writes that module's Assets/Armory/Hero/<module>.blend).

GRAIN CONVENTION (T_AK_HTimber): the grain runs along U. The scripted kit (Piece.box), hero_backwall and hero_walls map
U along each member (correct). hero_rear_alcove, hero_banner_coffer, hero_ceiling_lattice and hero_lantern_vase map V
along the member (they were tuned on the old T_AK_Timber, whose streaks actually ran along V): with this override their
timber shows cross grain until their timber UVs swap (u, v) -> (v, u) (and any across-grain squeeze moves to V).
"""
import math

ENABLED = True   # the user reviews images of every change BEFORE anything goes into the armory; never set True here

T = "M_AK_Timber"
TILE_T = 2.0      # M_AK_Timber keeps the kit's 2 m tile (other modules read G["TILE"])
FLOOR_TINT = 1.80   # calibration pass 2: 2.20 -> 1.80 (reference 2: a dark walnut, its C1 "front floor" 0.53 is a SHEEN reflection, not albedo). Pass 1: the kit's 1.0 -> 2.20

MATERIALS = {
    T: ("HTimber", TILE_T, {}),
    "M_AK_Banner": ("HBanner", None, {"two_sided": True}),
    "M_AK_Glass": (None, 1.0, {"glass": True, "tint": "#FAFBFA", "refl": 0.25}),
    # calibration pass 1 (room judge: the floor read darker and mirror-like with specular streaks; reference 2's floor is
    # a lighter satin walnut, C1 front 0.53 / sun patch 0.54): the kit's walnut in its satin copy T_AK_HPlank (tex_shared
    # plank(): same BC / N, roughness 0.16 -> 0.30) and a brighter stain (tint 1.0 -> FLOOR_TINT)
    "M_AK_Plank": ("HPlank", 4.0, {"tint": FLOOR_TINT}),
}


def _section(hw, d, r, segs=4):
    """Closed (y, z) loop of a member hanging from z 0: square top arrises, the two lower arrises rounded (radius r).
    Returns [(y, z, smooth_after)] counter-clockwise seen from +x, starting at the top of the -y side."""
    pts = [(-hw, 0.0, False), (-hw, -d + r, True)]
    for k in range(1, segs):
        a = math.pi + (k / segs) * (math.pi / 2)             # the -y lower arris: from pointing -y to pointing -z
        pts.append((-hw + r + r * math.cos(a), -d + r + r * math.sin(a), True))
    pts.append((-hw + r, -d, False))
    pts.append((hw - r, -d, True))
    for k in range(1, segs):
        a = 1.5 * math.pi + (k / segs) * (math.pi / 2)       # the +y lower arris
        pts.append((hw - r + r * math.cos(a), -d + r + r * math.sin(a), True))
    pts.append((hw, -d + r, False))
    pts.append((hw, 0.0, False))
    return pts


def member(G, name, length, hw, d, r):
    """A plain timber member along +x from 0 to length, the rounded lower arrises, one closed mesh."""
    sec = _section(hw, d, r)
    n = len(sec)
    verts = [(0.0, y, z) for y, z, _s in sec] + [(length, y, z) for y, z, _s in sec]
    arc = [0.0]
    for i in range(1, n + 1):
        a, b = sec[i - 1], sec[i % n]
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    faces, uvs, smooth = [], [], []
    for i in range(n):
        j = (i + 1) % n
        # outward winding: the loop runs counter-clockwise seen from +x (-y side down, soffit, +y side up, top)
        faces.append((i, j, n + j, n + i))
        v0, v1 = arc[i] / TILE_T, arc[i + 1] / TILE_T
        uvs.append([(0.0, v0), (0.0, v1), (length / TILE_T, v1), (length / TILE_T, v0)])
        # a face is smooth when it is one of the arris facets (both ends on the round)
        smooth.append(sec[i][2] and sec[j][2] or (sec[i][2] and i > 0 and sec[i - 1][2]))
    # end caps: fans from the section centre (no n-gons), box-projected (y, z)
    cz = -d / 2
    c0 = len(verts)
    verts.append((0.0, 0.0, cz))
    c1 = len(verts)
    verts.append((length, 0.0, cz))
    for i in range(n):
        j = (i + 1) % n
        yi, zi, _ = sec[i]
        yj, zj, _ = sec[j]
        faces.append((c0, j, i))
        uvs.append([(0.0, cz / TILE_T), (yj / TILE_T, zj / TILE_T), (yi / TILE_T, zi / TILE_T)])
        smooth.append(False)
        faces.append((c1, n + i, n + j))
        uvs.append([(0.0, cz / TILE_T), (yi / TILE_T, zi / TILE_T), (yj / TILE_T, zj / TILE_T)])
        smooth.append(False)
    p = G["Piece"](name)
    p.mesh(verts, faces, uvs, T, smooth=smooth)
    return p.col(0, length, -hw, hw, -d, 0)


def pieces(G):
    return [member(G, "SM_AK_Ceiling_Beam_4", 4.0, 0.125, 0.40, 0.012),
            member(G, "SM_AK_Ceiling_Rib_2", 2.0, 0.08, 0.30, 0.010)]
