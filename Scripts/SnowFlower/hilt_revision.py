"""Snow Flower reference hilt revision, executed inside build_snow_flower globals.

Replace the old grip/pommel generation with this snippet AFTER collar is defined
and BEFORE tassel generation. Required helpers: add, tube, ellipsoid, collar,
flower; math and Vector. The helper flower supplies the revised sculpted petals.
Every explicit component is closed. Deliberately embedded ornamental shells are
separate solids; no booleans or data-block operations are performed here.
"""


def _sfh_ellipse(theta, z, rx=.0155, ry=.012, offset=0.0):
    normal = Vector((math.cos(theta) / rx, math.sin(theta) / ry, 0)).normalized()
    return Vector((rx * math.cos(theta), ry * math.sin(theta), z)) + normal * offset


def _sfh_surface(x, z, side, offset=.00085):
    # Smooth elliptical grip surface, sufficiently outside the thin leather weave.
    y = side * .012 * math.sqrt(max(.001, 1 - (x / .0155) ** 2))
    normal = Vector((x / .0155**2, y / .012**2, 0)).normalized()
    return Vector((x, y, z)) + normal * offset, normal


def _sfh_curve(knots, subdivisions=8):
    """Interpolating Catmull-Rom path in x/z; no duplicate segment junctions."""
    out = []
    knots = [Vector((x, z)) for x, z in knots]
    for i in range(len(knots) - 1):
        p0, p1 = knots[max(i - 1, 0)], knots[i]
        p2, p3 = knots[i + 1], knots[min(i + 2, len(knots) - 1)]
        for j in range(subdivisions):
            t = j / subdivisions
            p = .5 * ((2 * p1) + (-p0 + p2) * t
                      + (2*p0 - 5*p1 + 4*p2 - p3) * t*t
                      + (-p0 + 3*p1 - 3*p2 + p3) * t*t*t)
            out.append(tuple(p))
    out.append(tuple(knots[-1]))
    return out


def _sfh_branch(name, knots, side, radius=.00043, offset=.00091):
    path = [_sfh_surface(x, z, side, offset)[0] for x, z in _sfh_curve(knots)]
    tube(name, path,
         lambda t: radius * (1 - .58*t) * (1 + .09*math.sin(t*19 + .3)),
         'Silver', '04_Grip', 7)
    return path


# Tight oval leather core. Ends sit inside the two metal transitions.
collar('SF_Grip_Core', -.020, .0155, .012, .236, 'Leather', segments=64)

# Genuine alternating weave. Each helix is a closed, very thin bevelled strip;
# neither handedness sits above the other for its entire length. The two center
# lines cross at alpha = n*pi and alternate their radial order at each crossing.
_sfh_turns = 8.50
_sfh_steps = 900
_sfh_pitch_derivative = .236 / (math.tau * _sfh_turns)
_sfh_half_width = .00330
_sfh_half_thickness = .000040
_sfh_edge_bevel = .000014
_sfh_section = [
    (-_sfh_half_width + _sfh_edge_bevel, _sfh_half_thickness),
    (_sfh_half_width - _sfh_edge_bevel, _sfh_half_thickness),
    (_sfh_half_width, _sfh_half_thickness - _sfh_edge_bevel),
    (_sfh_half_width, -_sfh_half_thickness + _sfh_edge_bevel),
    (_sfh_half_width - _sfh_edge_bevel, -_sfh_half_thickness),
    (-_sfh_half_width + _sfh_edge_bevel, -_sfh_half_thickness),
    (-_sfh_half_width, -_sfh_half_thickness + _sfh_edge_bevel),
    (-_sfh_half_width, _sfh_half_thickness - _sfh_edge_bevel),
]
for _sfh_direction in (-1, 1):
    _sfh_vs, _sfh_fs = [], []
    for _sfh_i in range(_sfh_steps + 1):
        _sfh_t = _sfh_i / _sfh_steps
        _sfh_alpha = math.tau * _sfh_turns * _sfh_t
        # Shared phase deliberately locates the alternating crossings on the
        # front/back meridians. Side-meridian crossings read as a simple spiral
        # from the front even when both helix directions exist geometrically.
        _sfh_theta = _sfh_direction * _sfh_alpha - math.pi/2
        _sfh_z = -.138 + .236 * _sfh_t
        _sfh_arc = math.sqrt((.0155 * math.sin(_sfh_theta))**2
                             + (.012 * math.cos(_sfh_theta))**2)
        _sfh_den = math.sqrt(_sfh_arc**2 + _sfh_pitch_derivative**2)
        _sfh_lift = .00017 + _sfh_direction * .00008 * math.cos(_sfh_alpha)
        for _sfh_w, _sfh_depth in _sfh_section:
            # Width travels perpendicular to the helix within the grip surface.
            _sfh_a = _sfh_theta - _sfh_direction * _sfh_pitch_derivative * _sfh_w / (_sfh_den * _sfh_arc)
            _sfh_zz = _sfh_z + _sfh_arc * _sfh_w / _sfh_den
            _sfh_vs.append(_sfh_ellipse(_sfh_a, _sfh_zz, offset=_sfh_lift + _sfh_depth))
        if _sfh_i:
            for _sfh_k in range(8):
                _sfh_fs.append(((_sfh_i-1)*8 + _sfh_k, _sfh_i*8 + _sfh_k,
                                _sfh_i*8 + (_sfh_k+1)%8, (_sfh_i-1)*8 + (_sfh_k+1)%8))
    _sfh_fs.extend([tuple(reversed(range(8))), tuple(_sfh_steps*8 + k for k in range(8))])
    add('SF_Grip_CrossWrap', 'Leather', '04_Grip', _sfh_vs, _sfh_fs)

# Fine connected curling vines, rather than large empty repeated shields.
def _sfh_scrollband(name, z, rx, ry, halfheight, motifs, radius=.00016, point_map=None):
    def surface(a, zz):
        p = _sfh_ellipse(a, zz, rx, ry, .00010)
        return point_map(p) if point_map else p

    # A continuous wandering spine physically joins every scroll and thorn.
    spine = [surface(math.tau*i/(motifs*24),
                     z + halfheight*.18*math.sin(math.tau*i/24))
             for i in range(motifs*24)]
    group = '05_Pommel' if name.startswith('SF_Pommel_') else '04_Grip'
    tube(name, spine, radius, 'Silver', group, 6, True)
    for k in range(motifs):
        a = math.tau*k/motifs
        width = math.pi/motifs
        for direction in (-1, 1):
            flip = direction * (1 if k % 2 else -1)
            knots = [(0, 0), (.38, .22), (.74, .70), (.92, .43),
                     (.72, -.10), (.46, -.16), (.44, .13)]
            path = [surface(a + direction*width*u, z + flip*halfheight*v)
                    for u, v in _sfh_curve(knots, 6)]
            tube(name, path, lambda t: radius*(1-.30*t), 'Silver', group, 6)
            # One small hooked thorn stems from the shoulder of each curl.
            thorn = [(.74, .70), (.60, .96), (.40, .78)]
            tube(name, [surface(a + direction*width*u, z + flip*halfheight*v)
                        for u, v in _sfh_curve(thorn, 5)],
                 lambda t: radius*(.85-.45*t), 'Silver', group, 5)


# Faceted ferrule at the guard: shallow silver scrollwork and stepped borders.
collar('SF_Grip_LowerFerrule', .1050, .0175, .0142, .014, 'Recess', segments=16)
collar('SF_Grip_FerruleUpperEdge', .0987, .0177, .0144, .0016, 'Silver', segments=16)
collar('SF_Grip_FerruleLowerEdge', .1112, .0177, .0144, .0018, 'Silver', segments=16)
_sfh_scrollband('SF_Grip_FerruleEngraving', .1050, .0175, .0142, .0046, 12, .00017)

# Ornament occurs as connected, branching clusters near the two grip ends.
# Coordinates are shared by the twigs and blossom centers, so buds do not float.
for _sfh_side in (-1, 1):
    _sfh_s = 1 if _sfh_side == -1 else -1
    _sfh_clusters = [
        {
            'stem': [(-.0052, .105), (-.0028, .095), (-.0043, .085),
                     (.0004, .076), (-.0018, .065), (.0015, .053)],
            'twigs': [
                ([(-.0043, .085), (.0005, .086), (.0054, .080)], .0054, .080, .0052),
                ([(-.0028, .095), (.0018, .099), (.0046, .096)], .0046, .096, .0035),
                ([(-.0018, .065), (-.0050, .064), (-.0066, .068)], -.0066, .068, .0033),
            ],
            'buds': [([(.0004, .076), (-.0045, .073), (-.0075, .075)], -.0075, .075)],
        },
        {
            'stem': [(.0046, -.116), (.0014, -.107), (.0035, -.097),
                     (-.0018, -.086), (-.0004, -.075), (-.0035, -.062)],
            'twigs': [
                ([(-.0018, -.086), (.0026, -.084), (.0061, -.089)], .0061, -.089, .0048),
                ([(-.0004, -.075), (-.0036, -.073), (-.0060, -.077)], -.0060, -.077, .0038),
                ([(.0014, -.107), (-.0024, -.107), (-.0047, -.101)], -.0047, -.101, .0026),
            ],
            'buds': [([(.0035, -.097), (.0064, -.099), (.0080, -.096)], .0080, -.096)],
        },
    ]
    for _sfh_ci, _sfh_cluster in enumerate(_sfh_clusters):
        _sfh_branch('SF_Grip_SilverBranches', [(x*_sfh_s, z) for x, z in _sfh_cluster['stem']],
                    _sfh_side, .00043)
        for _sfh_fi, (_sfh_knots, _sfh_x, _sfh_z, _sfh_r) in enumerate(_sfh_cluster['twigs']):
            _sfh_branch('SF_Grip_SilverTwigs', [(x*_sfh_s, z) for x, z in _sfh_knots],
                        _sfh_side, .00031)
            _sfh_p, _sfh_n = _sfh_surface(_sfh_x*_sfh_s, _sfh_z, _sfh_side, .00104)
            flower('SF_Grip_Blossoms', _sfh_p, _sfh_r, _sfh_n,
                   .24 + _sfh_fi*.71 + _sfh_ci*.35, '04_Grip')
        for _sfh_knots, _sfh_x, _sfh_z in _sfh_cluster['buds']:
            _sfh_branch('SF_Grip_BudTwigs', [(x*_sfh_s, z) for x, z in _sfh_knots],
                        _sfh_side, .00024)
            _sfh_p, _sfh_n = _sfh_surface(_sfh_x*_sfh_s, _sfh_z, _sfh_side, .0010)
            _sfh_tangent = _sfh_n.cross(Vector((0, 0, 1))).normalized()
            ellipsoid('SF_Grip_Buds', _sfh_p, _sfh_tangent*.00067,
                      Vector((0, 0, .00095)), _sfh_n*.00042,
                      'Silver', '04_Grip', 10, 5)

# Revision 3: one closed double-sided wheel pommel, its axis aligned to Y.
# The front/back medallions belong to this housing, not additional side plates.
# The unchanged leather core reaches z=-.138; the wheel's lower arc overlaps it.
# This short metal seat covers that join without obscuring the flower relief.
collar('SF_Grip_PommelCollar', -.1344, .0162, .0128, .0068, 'Recess', segments=48)
collar('SF_Grip_PommelNeckEdge', -.1373, .01635, .01295, .0010, 'Silver', segments=48)
collar('SF_Grip_PommelNeckEdge', -.1316, .01635, .01295, .0010, 'Silver', segments=48)
_sfh_scrollband('SF_Grip_PommelNeckFiligree', -.1344, .0162, .0128, .00185, 14, .00012)

_sfh_wheel_z = -.1530
_sfh_wheel_depth_scale = 2.65


def _sfh_wheel_point(angle, radius, y):
    return Vector((radius*math.cos(angle), y*_sfh_wheel_depth_scale,
                   _sfh_wheel_z + radius*math.sin(angle)))


def _sfh_wheel_housing():
    """Single closed shell with two recessed fields and a rounded outer edge."""
    segments = 128
    # The profile follows the front floor outward, rounds the perimeter, then
    # returns across the rear floor. There are no coplanar stacked face discs.
    profile = [
        (.0050, -.00930), (.0100, -.00930), (.0128, -.00940),
        (.0137, -.01130), (.0148, -.01150), (.0155, -.01080),
        (.0169, -.00840), (.01780, -.00510), (.01815, -.00250),
        (.01822, 0.0),
        (.01815, .00250), (.01780, .00510), (.0169, .00840),
        (.0155, .01080), (.0148, .01150), (.0137, .01130),
        (.0128, .00940), (.0100, .00930), (.0050, .00930),
    ]
    verts, faces = [], []
    for radius, y in profile:
        verts.extend(_sfh_wheel_point(math.tau*i/segments, radius, y/_sfh_wheel_depth_scale)
                     for i in range(segments))
    for row in range(len(profile)-1):
        for i in range(segments):
            j = (i+1) % segments
            faces.append((row*segments+i, row*segments+j,
                          (row+1)*segments+j, (row+1)*segments+i))
    front = len(verts)
    verts.append((0, -.00930, _sfh_wheel_z))
    back = len(verts)
    verts.append((0, .00930, _sfh_wheel_z))
    last = (len(profile)-1)*segments
    for i in range(segments):
        j = (i+1) % segments
        faces.append((front, j, i))
        faces.append((back, last+i, last+j))
    add('SF_Pommel_Housing', 'Recess', '05_Pommel', verts, faces)


_sfh_wheel_housing()

# Matching inset faces are modeled directly on the two sides of this wheel.
# Deeper rounded shoulders fill the side silhouette to about the grip's depth.
# Floral relief retains its original shallow height and is not stretched.
for _sfh_side in (-1, 1):
    _sfh_face_y = _sfh_side*.00940
    for _sfh_radius, _sfh_y, _sfh_wire in [
        (.01550, .01080/_sfh_wheel_depth_scale, .00036),
        (.01480, .01150/_sfh_wheel_depth_scale, .00023),
        (.01370, .01130/_sfh_wheel_depth_scale, .00017),
    ]:
        tube('SF_Pommel_ConcentricRims',
             [_sfh_wheel_point(math.tau*i/128, _sfh_radius, _sfh_side*_sfh_y)
              for i in range(128)], _sfh_wire, 'Silver', '05_Pommel', 8, True)

    # On both faces the distinctive narrow petal points toward the pommel top.
    # Normal -Y gives V=+Z, and normal +Y gives V=-Z in the shared flower helper.
    _sfh_phase = -math.pi/2 if _sfh_side == -1 else math.pi/2
    flower('SF_Pommel_FrontFlower' if _sfh_side == -1 else 'SF_Pommel_BackFlower',
           (0, _sfh_face_y, _sfh_wheel_z), .0118,
           (0, _sfh_side, 0), _sfh_phase, '05_Pommel', True)

    # A continuous irregular wreath anchors dense curling thorn scrolls between
    # the blossom tips and inner rim. The field stays recessed behind the rim.
    _sfh_wreath = []
    for _sfh_i in range(240):
        _sfh_angle = math.tau*_sfh_i/240
        _sfh_rad = (.01325 + .00034*math.sin(5*_sfh_angle+.2) + .00011*math.sin(15*_sfh_angle))*.90
        _sfh_wreath.append(_sfh_wheel_point(_sfh_angle, _sfh_rad, _sfh_side*.00384))
    tube('SF_Pommel_ThornWreath', _sfh_wreath, .00015, 'Inlay', '05_Pommel', 6, True)

    for _sfh_k in range(10):
        _sfh_a = math.tau*_sfh_k/10 - math.pi/2
        _sfh_direction = 1 if _sfh_k % 2 else -1
        # Begin on the wreath, curl toward the rim, then back toward a petal gap.
        _sfh_start = .01325 + .00034*math.sin(5*_sfh_a+.2) + .00011*math.sin(15*_sfh_a)
        _sfh_knots = [(0, _sfh_start), (.105, .01415), (.225, .01475),
                       (.355, .01420), (.330, .01340), (.220, .01278),
                       (.105, .01293), (.115, .01347)]
        _sfh_path = [_sfh_wheel_point(_sfh_a+_sfh_direction*da, radius*.90, _sfh_side*.00396)
                     for da, radius in _sfh_curve(_sfh_knots, 6)]
        tube('SF_Pommel_ThornScrolls', _sfh_path,
             lambda t: .000165*(1-.34*t), 'Silver', '05_Pommel', 6)
        # Short bifurcated thorn grows from the shoulder, with a tapered end.
        _sfh_thorn = [(.225, .01475), (.125, .01503), (.050, .01455)]
        tube('SF_Pommel_ThornScrolls',
             [_sfh_wheel_point(_sfh_a+_sfh_direction*da, radius*.90, _sfh_side*.0040)
              for da, radius in _sfh_curve(_sfh_thorn, 6)],
             lambda t: .000135*(1-.48*t), 'Silver', '05_Pommel', 5)

# Two very fine lines run around the rounded narrow edge. There is no end-facing
# axial flower, angled lid, or second housing hidden behind either medallion.
for _sfh_side in (-1, 1):
    tube('SF_Pommel_EdgeInlay',
         [_sfh_wheel_point(math.tau*i/144, .01818, _sfh_side*.00105)
          for i in range(144)], .000115, 'Inlay', '05_Pommel', 6, True)
